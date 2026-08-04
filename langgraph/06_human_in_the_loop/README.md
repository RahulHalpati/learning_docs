# Section 06 · Human-in-the-loop

> **Prerequisites:** [05-1 · Checkpointers](../05_persistence_and_memory/01_checkpointers.md) · **Time:** ~60 min

Autonomous agents shouldn't send the email, run the refund, or delete the record without a human's nod. **Human-in-the-loop** (HITL) pauses a graph mid-run, surfaces something for a person to decide, and resumes with their answer. It's built on checkpointing — the pause *is* a saved checkpoint.

## Modules

| # | Module | The question it answers |
|---|--------|-------------------------|
| 06-1 | [Interrupt & resume](01_interrupt_and_resume.md) | How do I pause with `interrupt()` and continue with `Command(resume=...)`? |
| 06-2 | [Approve / edit / review](02_approve_edit_review.md) | What are the standard HITL patterns, and how do static breakpoints differ? |

## What you'll be able to do after this section

- Pause a node with `interrupt(payload)` and resume with `Command(resume=value)`.
- Build **approve/reject**, **edit-state**, and **review-tool-call** gates.
- Use static breakpoints (`interrupt_before`/`interrupt_after`) to pause without code changes.

→ Start: **[06-1 · Interrupt & resume](01_interrupt_and_resume.md)**
