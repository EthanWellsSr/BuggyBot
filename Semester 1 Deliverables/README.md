# Semester 1 Deliverables

Final Semester 1 (Fall 2026) submissions for CENG 4265. Each deliverable keeps
its editable source and the PDF that was submitted. Individual self-analysis
reports are not stored here. The Technical Paper is a Semester 2 deliverable,
not due this semester.

`Auto-Aeroponics Project Report-2 (1).pdf` is an unrelated project report kept
here as a reference; it is not a BuggyBot deliverable.

| Deliverable | Due | Files | Status |
| --- | --- | --- | --- |
| Project poster | 11/05 | `Senior Project Poster Semester 1_FinalVersion.pdf`, `.png` | Final |
| Final presentation | — | `Final Presentation.pptx` | Built 11/12; presented with the live demo to the class |
| Project Report | 11/19, 11:59 pm | `Project Report.md` (source), `.docx`, `.pdf`, `figures/` | Draft complete; no open notes |

The final presentation is generated from the per-person files in
[`Weekly Reports/slides/`](../Weekly%20Reports/slides/README.md): run
`python3 assemble_deck.py --final` from `Weekly Reports/`. Do not hand-edit the
generated deck.

The Project Report is written in `Project Report.md`. Rebuild the DOCX and PDF
after editing it (needs python-docx and LibreOffice):

```
python3 "Semester 1 Deliverables/build_paper.py" "Semester 1 Deliverables/Project Report.md" --no-indent
```

Notes in the form `[TEAM: ...]` are open questions; they print highlighted in
yellow and must be resolved before submission. Do not hand-edit the generated
DOCX or PDF.
