"""Render a Markdown paper to DOCX and PDF.

Usage (from anywhere):
    python3 "Semester 1 Deliverables/build_paper.py" "Semester 1 Deliverables/Project Report.md"

Needs python-docx and LibreOffice (`soffice`) on the development computer.
Writes the .docx and .pdf next to the Markdown file.

Supported Markdown, and nothing else:
    ---            title page: every line between the two --- markers is
    ---            centered on its own page; a blank line adds space
    # / ## / ###   headings
    paragraphs     consecutive lines are joined; **bold** and *italic* work
    - item         bullets; indent two spaces for a second level
    | a | b |      pipe tables with a header row
    ![caption](path){width=5}   figure, numbered automatically; width in inches

Text in square brackets that starts with TEAM: or ETHAN: is highlighted yellow
so an open question cannot reach the submitted PDF unnoticed.
"""

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK, WD_COLOR_INDEX
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt

FONT = "Times New Roman"
BODY_PT = 12
INLINE = re.compile(r"(\[(?:TEAM|ETHAN):[^\]]*\]|\*\*[^*]+\*\*|\*[^*]+\*)")
FIGURE = re.compile(r"^!\[(.*)\]\(([^)]+)\)(?:\{width=([\d.]+)\})?$")
BULLET = re.compile(r"^(\s*)- (.*)$")


def add_runs(paragraph, text, size=BODY_PT, bold=False, italic=False):
    """Add text to a paragraph, handling **bold**, *italic*, and open notes."""
    for part in INLINE.split(text):
        if not part:
            continue
        run_bold, run_italic, note = bold, italic, False
        if part.startswith("[") and INLINE.fullmatch(part):
            note = True
        elif part.startswith("**") and part.endswith("**") and len(part) > 4:
            part, run_bold = part[2:-2], True
        elif part.startswith("*") and part.endswith("*") and len(part) > 2:
            part, run_italic = part[1:-1], True
        run = paragraph.add_run(part)
        run.font.name = FONT
        run._element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
        run.font.size = Pt(size)
        run.bold = run_bold
        run.italic = run_italic
        if note:
            run.font.highlight_color = WD_COLOR_INDEX.YELLOW


def set_spacing(paragraph, line, before=0, after=0):
    fmt = paragraph.paragraph_format
    fmt.line_spacing = line
    fmt.space_before = Pt(before)
    fmt.space_after = Pt(after)


def add_page_number(section):
    """Centered page number in the footer (a Word PAGE field)."""
    paragraph = section.footer.paragraphs[0]
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = paragraph.add_run()
    run.font.name = FONT
    run.font.size = Pt(BODY_PT)
    for kind, text in (("begin", None), (None, "PAGE"), ("end", None)):
        if kind:
            element = OxmlElement("w:fldChar")
            element.set(qn("w:fldCharType"), kind)
        else:
            element = OxmlElement("w:instrText")
            element.set(qn("xml:space"), "preserve")
            element.text = text
        run._element.append(element)


def title_page(doc, lines):
    # Push the block down to roughly the middle of the page, as in the examples.
    for _ in range(9):
        set_spacing(doc.add_paragraph(), 1.0)
    for line in lines:
        paragraph = doc.add_paragraph()
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        set_spacing(paragraph, 1.5)
        add_runs(paragraph, line)
    doc.paragraphs[-1].add_run().add_break(WD_BREAK.PAGE)


def add_table(doc, rows):
    table = doc.add_table(rows=len(rows), cols=len(rows[0]))
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    for r, row in enumerate(rows):
        # Keep each row on one page, and repeat the header row after a break.
        tr_pr = table.rows[r]._tr.get_or_add_trPr()
        tr_pr.append(OxmlElement("w:cantSplit"))
        if r == 0:
            tr_pr.append(OxmlElement("w:tblHeader"))
        for c, text in enumerate(row):
            paragraph = table.cell(r, c).paragraphs[0]
            set_spacing(paragraph, 1.0, before=2, after=2)
            add_runs(paragraph, text, size=10, bold=(r == 0))
    set_spacing(doc.add_paragraph(), 1.0)


def add_figure(doc, number, caption, image, width):
    paragraph = doc.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    paragraph.paragraph_format.keep_with_next = True
    set_spacing(paragraph, 1.0, before=6)
    paragraph.add_run().add_picture(str(image), width=Inches(width))
    label = doc.add_paragraph()
    label.alignment = WD_ALIGN_PARAGRAPH.CENTER
    set_spacing(label, 1.0, before=4, after=12)
    add_runs(label, f"Figure {number}. {caption}", size=11)


def split_row(line):
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def build(markdown_path, line_spacing, indent):
    lines = markdown_path.read_text(encoding="utf-8").splitlines()
    doc = Document()
    section = doc.sections[0]
    for side in ("left_margin", "right_margin", "top_margin", "bottom_margin"):
        setattr(section, side, Inches(1))
    section.different_first_page_header_footer = True  # no number on the title page
    add_page_number(section)

    i = 0
    if lines and lines[0].strip() == "---":
        end = lines.index("---", 1)
        title_page(doc, [line.strip() for line in lines[1:end]])
        i = end + 1

    figure_number = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if not stripped:
            i += 1
        elif stripped.startswith("#"):
            level = len(stripped) - len(stripped.lstrip("#"))
            paragraph = doc.add_paragraph()
            paragraph.paragraph_format.keep_with_next = True
            set_spacing(paragraph, line_spacing, before=6 if level > 1 else 12)
            add_runs(paragraph, stripped.lstrip("#").strip(),
                     size=14 if level == 1 else BODY_PT,
                     bold=level < 3, italic=level >= 3)
            i += 1
        elif FIGURE.match(stripped):
            caption, path, width = FIGURE.match(stripped).groups()
            image = markdown_path.parent / path.replace("%20", " ")
            if not image.exists():
                sys.exit(f"Missing figure: {image}")
            figure_number += 1
            add_figure(doc, figure_number, caption, image, float(width or 5.5))
            i += 1
        elif stripped.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                cells = split_row(lines[i])
                if not all(re.fullmatch(r":?-+:?", cell) for cell in cells):
                    rows.append(cells)
                i += 1
            add_table(doc, rows)
        elif BULLET.match(line):
            while i < len(lines) and BULLET.match(lines[i]):
                spaces, text = BULLET.match(lines[i]).groups()
                i += 1
                # A wrapped bullet continues on indented lines.
                while (i < len(lines) and lines[i].strip()
                       and not BULLET.match(lines[i]) and lines[i].startswith("  ")):
                    text += " " + lines[i].strip()
                    i += 1
                nested = len(spaces) >= 2
                paragraph = doc.add_paragraph(
                    style="List Bullet 2" if nested else "List Bullet")
                set_spacing(paragraph, min(line_spacing, 1.5))
                add_runs(paragraph, text)
        else:
            parts = []
            while (i < len(lines) and lines[i].strip()
                   and not lines[i].lstrip().startswith(("#", "|", "!["))
                   and not BULLET.match(lines[i])):
                parts.append(lines[i].strip())
                i += 1
            paragraph = doc.add_paragraph()
            # Unindented paragraphs need a gap to stay distinct.
            set_spacing(paragraph, line_spacing, after=0 if indent else 6)
            if indent:
                paragraph.paragraph_format.first_line_indent = Inches(0.5)
            add_runs(paragraph, " ".join(parts))

    docx_path = markdown_path.with_suffix(".docx")
    doc.save(docx_path)
    return docx_path


def to_pdf(docx_path):
    soffice = shutil.which("soffice")
    if not soffice:
        sys.exit("LibreOffice (soffice) not found; the DOCX was written but not the PDF.")
    subprocess.run(
        [soffice, "--headless", "--convert-to", "pdf",
         "--outdir", str(docx_path.parent), str(docx_path)],
        check=True, capture_output=True)
    return docx_path.with_suffix(".pdf")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("markdown", type=Path)
    parser.add_argument("--spacing", type=float, default=2.0,
                        help="body line spacing (default 2.0, double)")
    parser.add_argument("--no-indent", action="store_true",
                        help="do not indent the first line of each paragraph")
    args = parser.parse_args()
    docx_path = build(args.markdown.resolve(), args.spacing, not args.no_indent)
    print(f"Wrote {docx_path}")
    print(f"Wrote {to_pdf(docx_path)}")


if __name__ == "__main__":
    main()
