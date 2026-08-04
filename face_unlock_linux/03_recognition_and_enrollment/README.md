# Section 03 · Recognition & enrollment

> **Prerequisites:** [02 · Capturing & detecting](../02_capturing_and_detecting/README.md) · **Time:** ~90 min

Now the core: turn a face into a **template**, **enroll** an identity, and build a **verify CLI** that answers accept/reject with an exit code — the contract PAM needs.

## Modules

| # | Module | The question it answers |
|---|--------|-------------------------|
| 03-1 | [Embeddings & matching](01_embeddings_and_matching.md) | How is a face turned into something comparable, and how do we match? |
| 03-2 | [Enrollment](02_enrollment.md) | How do I train and save a model of *my* face? |
| 03-3 | [The verify CLI](03_verify_cli.md) | How do I turn a match into exit 0/1 for PAM — and tune the threshold? |

## What you'll be able to do after this section

- Explain LBPH templates and distance-based matching (and the dlib upgrade path).
- Enroll a face into a saved model from images (offline) or the webcam.
- Run a verify CLI that returns exit 0 (accept) / 1 (reject), and tune its threshold for FAR/FRR.

→ Start: **[03-1 · Embeddings & matching](01_embeddings_and_matching.md)**
