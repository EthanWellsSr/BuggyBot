# Presentation slides — one file per person

**Why:** a `.pptx` is a binary file, so git can't merge two people's edits to the
same deck — you get an unresolvable conflict. To avoid that, everyone edits their
**own** file here. Two people never touch the same file, so conflicts can't happen,
and you can all work at the same time.

## The rule

- **Edit only your own file** in this folder (e.g. Alexis edits `2-alexis-perez.pptx`).
  Edit it in PowerPoint like normal — text, images, whatever.
- **Do not hand-edit** `../Self-Driving-RC-Car.pptx` or
  `../../Semester 1 Deliverables/Final Presentation.pptx`. Both are generated and
  your changes there get overwritten.
- Pull, edit your file, commit, push — as usual. No coordination needed.

## Building the deck

Whoever is assembling the deck (usually the group leader, before submission) runs
one of these from the `Weekly Reports` folder:

```
python3 assemble_deck.py           # weekly deck
python3 assemble_deck.py --final   # Semester 1 final presentation
```

Both stitch every `slides/*.pptx`, in filename order, into one deck. The weekly
deck goes to `../Self-Driving-RC-Car.pptx`; `--final` writes
[`Final Presentation.pptx`](../../Semester%201%20Deliverables/) in
`Semester 1 Deliverables/`. Commit the deck alongside the slide files.

The script also puts each person's first and last name, taken from the file name,
in small black text at the bottom right of their slides (not on the title slide or
the team's shared closing slides in `NN-team.pptx`),
so you don't need to add your name yourself. Check the assembled deck for slides
that look different from their source file; images and charts from different
files are renamed so they can't overwrite each other.

## Files / order

Slide order comes from the numeric prefix:

| File | Slide |
|---|---|
| `0-title.pptx` | Title / team |
| `1-ethan-wells.pptx` | Ethan Wells |
| `2-alexis-perez.pptx` | Alexis Perez |
| `3-ethan-bishop.pptx` | Ethan Bishop |
| `4-abigail-duran.pptx` | Abigail Duran |
| `5-team.pptx` | Shared closing slides (cost breakdown, future work); no name label |

Add a person by dropping a new `NN-name.pptx` here; remove one by deleting their file.
For weekly decks, each member's slide keeps the four sections: **Goals for the week**,
**Progress for the week**, **Goals for next week**, **Hours spent on progress**. The
Semester 1 final presentation (built 11/12) used narrative slides instead, so the files
here currently hold final-presentation content; earlier weekly versions are in Git
history and in each `Week N/` deck.
