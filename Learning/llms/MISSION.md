# Mission: Understanding LLM Training Feasibility

## Why
Ethan just trained a ~475k-parameter image classifier on his own workstation in
minutes, then wanted to build a small model that writes Python. He hit the wall
that LLMs can't be self-trained. He wants to genuinely understand *where* that
wall is and *why* — so he knows what is and isn't buildable by one person, and
can make smart build-vs-use decisions on future AI ideas.

## Success looks like
- Can explain, in concrete numbers, the three reasons an LLM can't be trained at home (compute, memory, data).
- Can compare his GTSRB model to a frontier LLM and articulate the scale gap.
- Knows the realistic at-home alternatives (use a pretrained API; fine-tune a small model) and roughly where each becomes feasible.

## Constraints
- Prefers short, clinical explanations grounded in real numbers — dislikes long outputs.
- Learns by doing; wants understanding tied to things he can actually act on.
- This is a side-quest from the senior project (BuggyBot, an autonomous car), not the main goal.

## Out of scope
- The low-level math of gradient descent / backprop (covered just enough, not deeply).
- Actually building or fine-tuning an LLM right now.
