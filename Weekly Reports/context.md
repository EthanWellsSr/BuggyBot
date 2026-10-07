# Weekly Report — Context & Build Guide
Use this guide with the current slides, previous report, and Ethan's account of
the team's work and hours.

## What to produce
A file `Self_Driving_RC_Car.docx` and a matching `Self_Driving_RC_Car.pdf` in this folder, in the TA's required template format. Ethan will give you a plain list of what the team did that week plus per-person hours; you turn it into the report. **Submit the PDF only** — see Submission rules.

> **Format changed in Week 3 (Sep 8 2026).** TA Ruben Ramirez's required
> `project_name.docx` controls the current report. The prior advisor format is
> retired. `build_report.py` is the maintained builder.

## Project facts
- **Project name** (document title + used in filenames): **Self Driving RC Car**
- **Course:** CENG 4265 — Senior Project  (confirmed by Ethan; the Week 1 report's "CENG 4266" was a typo)
- **School:** University of Houston – Clear Lake (UHCL)
- **Faculty advisor (the "client"):** Professor Nguyen
- **Team (list in this order):** Ethan Wells, Alexis Perez, Ethan Bishop, Abigail Duran  (Alexis is male)
- **Terminology — fix Ethan's occasional slips:**
  - Compute: **Raspberry Pi Compute Module 5 (CM5)** on its IO Board for bench testing; the custom carrier PCB is planned — NOT "Arduino"
  - Prototyping board: **Raspberry Pi Compute Module I/O Board** — NOT "breadboard"
  - Sensors: camera (primary, reads signs) + ultrasonic (obstacle/wall distance) + IMU (heading/turns); no LiDAR
  - Scope: self-driving RC car that follows a controlled course AND obeys traffic signs. Fall = stationary recognition system; Spring = autonomous vehicle.
- **Ethan's voice:** plain, concrete, sequential, honest, no embellishment. Read
  the previous weekly reports before drafting so new wording matches them.

## File conventions
- This folder: `~/Desktop/BuggyBot/Weekly Reports` on Ethan's Mac.
- Output filenames (TA's rule — project name, underscores, no week number): `Self_Driving_RC_Car.docx` / `Self_Driving_RC_Car.pdf`. Canvas versions per submission, so the same filename each week is correct.
- **The undated `Self_Driving_RC_Car.docx` / `.pdf` are the WORKING copies — they get rebuilt and overwritten in place each week, and `Self_Driving_RC_Car.pdf` is the file submitted to Canvas.** Each week, update the data in `build_report.py` and rerun; it overwrites these undated files. They live at the TOP LEVEL of this folder alongside the tooling.
- **Per-week folders.** Each week gets its own `Week N/` subfolder holding that week's frozen deliverables: the dated report PDF (`Self_Driving_RC_Car - Week N.pdf` — for Weeks 1–2, `Self Driving RC Car - Week N.pdf`) plus a dated report docx, and from Week 4 on the dated presentation (`Self-Driving-RC-Car - Week N.pptx`). These dated copies are frozen history — never edit them; only the top-level working copies are edited/rebuilt.
- **After the report is final each week:** copy the working files into that week's folder — `cp "Self_Driving_RC_Car.pdf" "Week N/Self_Driving_RC_Car - Week N.pdf"` and `cp "Self_Driving_RC_Car.docx" "Week N/Self_Driving_RC_Car - Week N.docx"`. (Weeks 1–3 already archived; going forward, create `Week N/` and drop the frozen copies in.)
- **Presentation (pptx).** `Self-Driving-RC-Car.pptx` at the top level is the ROLLING working deck — edit it in place each week (started Week 4, Sep 2026). After it's final, freeze a dated copy into that week's folder: `cp "Self-Driving-RC-Car.pptx" "Week N/Self-Driving-RC-Car - Week N.pptx"`.
- TEMPLATE: `project_name.docx` at the top level — the exact file the TA distributed. The build script edits a copy of it in place, so fonts/margins/styles stay identical to what the TA expects (12 pt throughout; section headers bold + underlined). Do NOT hand-rebuild from scratch.

## Submission rules (from Ruben's email, Sep 8 2026)
- **Only the group leader (Ethan Wells) submits on Canvas** — one report per group, NOT one per student.
- **PDF only**, filename = project name (`Self_Driving_RC_Car.pdf`).
- Questions go to Ruben Ramirez (TA) or Dr. Nguyen.

## Required format (do NOT deviate — mirrors `project_name.docx`)
Header block (each on its own line; label prefix bold, section headers bold+underlined):
1. `WEEKLY REPORT :` (bold+underline)
2. `Project Title: Self Driving RC Car`
3. `Date: M/D/YYYY`  (the report/class date Ethan gives)
4. `Instructor: Dr. Nguyen`
5. `TA: Ruben Ramirez`
6. `Project Members:` (bold+underline) then one line per member; mark Ethan as `(Group Leader)`.

Then four sections, each header bold+underlined:
7. `Weekly Summary (M/D/YYYY):` — one paragraph, group-level, what got done in the last week, WITH specifics (name each part and its purpose — e.g. "Raspberry Pi Compute Module I/O Board", "ultrasonic sensor for wall distance").
8. `Proposed Plan for Next Week:` — **next-week goals are now REQUIRED** (opposite of the old rule). One line per member: underlined `Name:` + a specific, non-ambiguous goal. No vague goals. For reports after the first, this is what next week's report updates against.
9. `Weekly Contributions:` — per member: an underlined `Name:` subhead, then one line per task in the form `M/D/YYYY – <what they did> (N hours)`. Ask for missing task dates and hours before finalizing; mark unavailable details for Ethan's review rather than inventing them.
10. `Hour Tracker:` — the table in the template: `Name | Hours For the Week | Cumulative Hours`, one row per member.

## Turning Ethan's input into content
- Ethan gives: what each person did, and hours (with rough dates). Map each task to its owner for both `Weekly Contributions` (dated + hours) and the `Weekly Summary` (fold into the group paragraph).
- **Hours you cannot infer — always ask** for per-person hours/dates and cumulative totals if not given. Cumulative = prior cumulative + this week (hour tracking started Week 3, Sep 8 2026, so Week 3 cumulative == weekly).
- `Proposed Plan for Next Week`: if Ethan doesn't dictate goals, draft specific ones from the obvious next steps (e.g. receive & bench-test an ordered sensor; get a first TensorFlow training run going) and have him approve.
- For reports after the first: open each member's contribution/summary by updating the previous week's `Proposed Plan` — say how the goal was met, or explain in detail what was done and why it wasn't (damage, shipping delays, other roadblocks). The email explicitly wants this.
- Dates/cadence: Week 1 = Aug 18–24 2026; Week 2 = Aug 25–31 2026; Week 3 = Sep 1–7 2026 (report dated Sep 8). Continue ~weekly or ask Ethan for the exact date to stamp.

## Weekly documentation review
Before a weekly report and slideshow are pushed, inspect every maintained
repository document, including the root guides and nested READMEs. Start with
`rg --files -g '*.md' -g '*.txt'`, then check any other current documentation
affected by the week's work. Compare claims with the current code, saved model
results, hardware evidence, slides, and report. Update stale facts in the same
work and include those edits in Ethan's diff review. Leave unknown hardware
models, prices, dates, and purchase links blank rather than guessing. Historical
proposals and frozen weekly deliverables are reference material.

## Build and verify
1. Read the previous report and this week's per-person slides. Confirm the
   report date, each person's tasks and hours, and cumulative totals. Compare
   progress with the previous report's proposed plan. Ask Ethan for missing work
   dates or hours; do not invent them.
2. Update the data at the top of `build_report.py`. Run `python3 build_report.py`
   from `Weekly Reports/`. The script starts with a fresh copy of the TA's
   `project_name.docx`. It preserves the template's paragraph types: project
   members are plain lines; summary, plans, and contribution names use the
   first list level; contribution tasks use the indented second level. Keep the
   original template and its numbering definitions unchanged.
3. Render `Self_Driving_RC_Car.docx` to PDF with the available document renderer
   and inspect every page. Check that bullets follow the TA's hierarchy, text
   is readable, and the hour table is complete. The working PDF must be named
   `Self_Driving_RC_Car.pdf` for Canvas.
4. Run `python3 assemble_deck.py` from this folder. It combines the files in
   `slides/` by filename into `Self-Driving-RC-Car.pptx`. Inspect the rendered
   deck for missing slides, broken images, and text overflow.
5. Once final, copy the working DOCX, PDF, and PPTX into the dated `Week N/`
   folder. Complete the repository documentation review above before proposing
   a commit and push. Ethan approves those Git actions separately.

## Accuracy notes
- The TA template's example text, including its Arduino reference, is a
  placeholder. Describe the current CM5 hardware and code instead.
- Training-set and test-set scores use different images. Use each model's
  measured result and state its test set. A crop-based score does not measure
  BuggyBot's live camera pipeline.
- The fall prototype currently uses simulated sign predictions; the PCB,
  ROS 2 pipeline, and vehicle autonomy remain planned or under study unless
  current code and hardware evidence establish otherwise.
