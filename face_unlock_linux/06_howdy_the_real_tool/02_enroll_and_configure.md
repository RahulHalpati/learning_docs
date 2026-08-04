# 06-2 · Enroll & configure

> **Level:** Intermediate · **Prerequisites:** [06-1 · Install Howdy](01_install_howdy.md)
> **Time:** 20 min · **Verified:** 2026-07-22 (commands; run on your machine)

## Why this matters

Howdy's enroll/configure maps one-to-one onto what you built: `howdy add` is enrollment ([03-2](../03_recognition_and_enrollment/02_enrollment.md)), and `config.ini`'s `certainty` is your threshold ([03-3](../03_recognition_and_enrollment/03_verify_cli.md)) — just inverted. You already understand every knob.

---

## Enroll your face

```bash
sudo howdy add           # capture a face model for the current user
sudo howdy list          # list enrolled models
sudo howdy test          # live preview: does it recognize you?
```

Add several models under different conditions (glasses on/off, day/evening) — the same "varied but consistent enrollment" advice from [03-2](../03_recognition_and_enrollment/02_enrollment.md). `howdy remove <id>` drops one.

---

## Configure — `config.ini`

```bash
sudo howdy config        # opens /lib/security/howdy/config.ini (path varies by version)
```

The knobs that matter, and their equivalents in your build:

| `config.ini` setting | What it does | Your build's equivalent |
|----------------------|--------------|-------------------------|
| `device_path` | which camera (point at the **IR** node) | `VideoCapture(index)` ([02-1](../02_capturing_and_detecting/01_webcam_capture.md)) |
| `certainty` | **max distance** to accept — LOWER = stricter | your `THRESHOLD` (same idea) |
| `dark_threshold` | skip when the frame is too dark | (we had none) |
| `timeout` | give up after N seconds → fall back | your hook's `timeout 8` |
| `capture_failed`/`abort_if_lid_closed` | behavior on failure | your fail-closed logic |

> ⚠️ **`certainty` is a distance, like LBPH's — lower is stricter.** Howdy's default is deliberately conservative. **Lower it toward stricter**, not looser; a false accept is a breach, a false reject just asks for your password. Exactly the FAR/FRR bias from [03-3](../03_recognition_and_enrollment/03_verify_cli.md).

---

## Test before trusting

```bash
howdy test               # watch the recognition live; confirm it's you, reliably
```

Enroll well and set `certainty` strict, then confirm `howdy test` recognizes you consistently across your normal conditions before wiring it into PAM ([06-3](03_secure_howdy_pam.md)). Bad enrollment → constant false rejects → you'll be tempted to loosen `certainty` → weaker security. Fix enrollment instead.

---

## Recap & next

- ✅ `howdy add`/`list`/`remove`/`test` manage enrollment (like your `enroll.py`/`capture.py`).
- ✅ `config.ini`: set `device_path` to the IR camera; `certainty` is the threshold (lower = stricter).
- ✅ Enroll varied-but-consistent; bias `certainty` strict; confirm with `howdy test` first.
- ✅ Self-check: Howdy's `certainty` and your `THRESHOLD` are the same concept — is "lower" stricter or looser?

→ Next: **[06-3 · Secure Howdy's PAM](03_secure_howdy_pam.md)**

## Exercises

1. `sudo howdy add`, then `howdy test` under two lighting conditions. If it fails in one, add a model there instead of loosening `certainty`.

<details>
<summary>Solution</summary>

Adding a model per condition lowers your false-reject rate *without* raising false-accepts — the right fix. Loosening `certainty` lowers FRR but raises FAR (lets lookalikes/photos closer). Enrollment quality beats a loose threshold every time.
</details>
