# Semester 1 Deliverables

Final Semester 1 (Fall 2026) submissions for CENG 4265. Each deliverable keeps
its editable source and the PDF that was submitted. Individual self-analysis
reports are not stored here.

| Deliverable | Due | Files | Status |
| --- | --- | --- | --- |
| Project poster | 11/05 | `Senior Project Poster Semester 1_FinalVersion.pdf`, `.png` | Final |
| Final presentation | — | `Final Presentation.pptx` | Built 11/12 |
| Project Report | 11/19, 11:59 pm | `Project Report.md` (source), `.docx`, `.pdf`, `figures/` | Draft; open `[TEAM: ...]` notes |
| Technical Paper | 11/19, 11:59 pm | — | Not started |

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
