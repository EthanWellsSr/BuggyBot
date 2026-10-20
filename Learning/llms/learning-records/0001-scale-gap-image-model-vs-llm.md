# Corrected: an LLM is not just a "bigger" version of his image model

Ethan built a 162k-param GTSRB classifier, then assumed a Python-writing model was
a similar "small model" he could train. Lesson 1 corrected this: LLMs fail at home
on three independent walls — compute (~30.8M H100-hrs for 405B), memory (~16–20
bytes/param, so even 7B overflows a 24 GB GPU), and data (~15T tokens).

Implications for future sessions: he now has the scale intuition, so the productive
next topics are the *feasible* paths he cared about — what a token is, how LoRA
fine-tuning works, or a nanoGPT toy — not training a frontier model. He learns by
doing and wants concrete numbers.
