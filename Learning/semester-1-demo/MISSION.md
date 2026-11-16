# Mission: The BuggyBot Semester 1 Demo

## Why
Give someone outside the team (the advisor, a judge, a new member) a fast,
accurate understanding of what the Semester 1 demo does and how it works, so
they can follow a live demo, ask good questions, and judge the results fairly.

## Success looks like
- Explain in one sentence what the demo does and what it does not do yet.
- Name the main hardware parts and what each one does in the demo.
- Trace one frame through the pipeline: camera, OpenCV proposals, classifier,
  rejection checks, confirmation, LCD and stream.
- Explain why a classifier alone is not enough to find signs in a frame.
- State the measured results and the conditions that are still untested.

## Constraints
- The audience knows basic software and computer engineering, but nothing about
  BuggyBot, computer vision, or neural networks beyond the basics.
- Each lesson is short enough to finish in one sitting.
- Every claim must match the current code and READMEs in this repository.

## Out of scope
- Training the model (datasets, architecture search, hyperparameters).
- The spring work: driving, line following, ROS 2.
- The custom PCB.
