"""Assemble the weekly or final presentation from the per-person files in slides/.

Each team member edits ONLY their own file in slides/ (e.g. slides/1-ethan-wells.pptx),
so no two people ever touch the same file and git never has a binary merge conflict.
This script stitches those files, in filename order, into the final deck:

    Self-Driving-RC-Car.pptx   (generated -- do not hand-edit; your edits get overwritten)

Run it (from inside the Weekly Reports folder) whenever slides change:

    python3 assemble_deck.py           # weekly deck -> Self-Driving-RC-Car.pptx
    python3 assemble_deck.py --final   # Semester 1 final presentation ->
                                       #   ../Semester 1 Deliverables/Final Presentation.pptx

Every slide from a person's file gets their first and last name, taken from the
file name, in small black text at the bottom right. The title file is skipped.

Naming: the numeric prefix sets slide order (0-title, 1-ethan-wells, ...). Add a member
by dropping a new NN-name.pptx into slides/; remove one by deleting their file.
"""
import argparse
import copy
import glob
import os
import re
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.opc.packuri import PackURI
from pptx.oxml.ns import qn
from pptx.util import Inches, Pt

HERE = os.path.dirname(os.path.abspath(__file__))
SLIDES_DIR = os.path.join(HERE, "slides")
OUT = os.path.join(HERE, "Self-Driving-RC-Car.pptx")
FINAL_OUT = os.path.join(HERE, "..", "Semester 1 Deliverables", "Final Presentation.pptx")

# name label: small black text in the bottom-right corner of each person's slides
LABEL_W, LABEL_H, LABEL_MARGIN = Inches(2.2), Inches(0.3), Inches(0.1)
LABEL_SIZE = Pt(11)

# relationships namespace, used to find/rewrite image & hyperlink references (r:embed, r:id, ...)
RNS = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"


def match_layout(name, dest):
    """Find the output deck's layout for a source layout name.

    PowerPoint names a copied layout "1_Title and Content", which the output deck
    may not have. Falling back to the last layout picked "Vertical Title and
    Text" and turned every title and bullet sideways, so strip that prefix and
    fall back to "Title and Content" instead.
    """
    by_name = {l.name: l for l in dest.slide_layouts}
    base = re.sub(r"^\d+_", "", name)
    return by_name.get(name) or by_name.get(base) or by_name.get("Title and Content") or dest.slide_layouts[0]


def copy_slide(src_slide, dest):
    """Append a deep copy of src_slide (all shapes + images) to dest presentation."""
    # match the source slide's layout by name so placeholders inherit correct position/format
    layout = match_layout(src_slide.slide_layout.name, dest)
    new = dest.slides.add_slide(layout)

    # drop the empty placeholders the layout auto-adds; we bring our own shapes over
    for sh in list(new.shapes):
        sh._element.getparent().remove(sh._element)

    # copy every shape's XML
    for sh in src_slide.shapes:
        new.shapes._spTree.append(copy.deepcopy(sh._element))

    # re-create the slide's relationships (images, media, hyperlinks), building a
    # complete old-rId -> new-rId map BEFORE touching the shapes
    rid_map = {}
    for rId, rel in src_slide.part.rels.items():
        if rel.reltype.endswith("slideLayout") or rel.reltype.endswith("notesSlide"):
            continue
        if rel.is_external:
            rid_map[rId] = new.part.rels.get_or_add_ext_rel(rel.reltype, rel.target_ref)
        else:
            rid_map[rId] = new.part.relate_to(rel.target_part, rel.reltype)

    # then remap in ONE pass, so every r: attribute is rewritten exactly once.
    # Rewriting per relationship instead would let a value written by an earlier
    # mapping (rId1 -> rId2) be matched again by a later one (rId2 -> rId3), which
    # collapses two shapes onto the same image.
    for el in new.shapes._spTree.iter():
        for attr, val in list(el.attrib.items()):
            if attr.startswith(RNS) and val in rid_map:
                el.set(attr, rid_map[val])


def owner_name(path):
    """'1-ethan-wells.pptx' -> 'Ethan Wells'; None for the title file."""
    stem = os.path.splitext(os.path.basename(path))[0]
    words = stem.split("-")[1:]  # drop the numeric order prefix
    if not words or words == ["title"]:
        return None
    return " ".join(w.capitalize() for w in words)


def add_name_label(slide, name, slide_w, slide_h):
    """Put `name` in small black right-aligned text at the slide's bottom-right corner."""
    box = slide.shapes.add_textbox(slide_w - LABEL_W - LABEL_MARGIN,
                                   slide_h - LABEL_H - LABEL_MARGIN, LABEL_W, LABEL_H)
    box.name = "Name label"
    tf = box.text_frame
    tf.word_wrap = False
    tf.vertical_anchor = MSO_ANCHOR.BOTTOM
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    para = tf.paragraphs[0]
    para.alignment = PP_ALIGN.RIGHT
    run = para.add_run()
    run.text = name
    run.font.size = LABEL_SIZE
    run.font.color.rgb = RGBColor(0, 0, 0)


def dedupe_media(dest):
    """Give every image/media part a unique name inside the output package.

    Each source deck numbers its own media from image1 up, so two people can both
    ship a ppt/media/image2.jpeg. Those parts keep their original names when they
    are copied in, the saved .pptx then holds two zip entries with the same name,
    and PowerPoint resolves both references to whichever one it reads -- so one
    person's picture silently replaces another's. Renumbering them here keeps each
    picture pointing at its own file.
    """
    used = set()
    n = 0
    for part in dest.part.package.iter_parts():
        name = str(part.partname)
        if not name.startswith("/ppt/media/"):
            continue
        ext = name.rsplit(".", 1)[-1]
        while True:
            n += 1
            new = "/ppt/media/image%d.%s" % (n, ext)
            if new.lower() not in used:
                break
        used.add(new.lower())
        part.partname = PackURI(new)


def dedupe_parts(dest):
    """Rename any other part whose name collides with one from another deck.

    The same problem as dedupe_media, for charts and their embedded workbooks and
    style parts: two people's ppt/charts/chart1.xml would both be saved under one
    zip name, and one chart would replace the other. The first part keeps its
    name; each later duplicate gets the next number no other part uses.
    """
    parts = list(dest.part.package.iter_parts())
    taken = {str(p.partname).lower() for p in parts}
    seen = set()
    for part in parts:
        name = str(part.partname)
        if name.lower() not in seen:
            seen.add(name.lower())
            continue
        base, ext = name.rsplit(".", 1)
        stem = base.rstrip("0123456789")
        n = 1
        while ("%s%d.%s" % (stem, n, ext)).lower() in taken:
            n += 1
        new = "%s%d.%s" % (stem, n, ext)
        taken.add(new.lower())
        seen.add(new.lower())
        part.partname = PackURI(new)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--final", action="store_true",
                        help="write the Semester 1 final presentation into Semester 1 Deliverables/")
    out = os.path.normpath(FINAL_OUT if parser.parse_args().final else OUT)

    files = sorted(glob.glob(os.path.join(SLIDES_DIR, "*.pptx")))
    if not files:
        raise SystemExit("no slide files found in " + SLIDES_DIR)

    # base the output on the first file so it inherits the theme/layouts, then clear its slides
    dest = Presentation(files[0])
    for sid in list(dest.slides._sldIdLst):
        dest.part.drop_rel(sid.get(qn("r:id")))
        dest.slides._sldIdLst.remove(sid)

    for f in files:
        name = owner_name(f)
        for slide in Presentation(f).slides:
            copy_slide(slide, dest)
            if name:
                add_name_label(dest.slides[-1], name, dest.slide_width, dest.slide_height)

    dedupe_media(dest)
    dedupe_parts(dest)

    dest.save(out)
    print("assembled %d slides from %d files -> %s"
          % (len(dest.slides._sldIdLst), len(files), os.path.relpath(out, HERE)))


if __name__ == "__main__":
    main()
