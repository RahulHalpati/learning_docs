# Section 01 · Foundations

> **Prerequisites:** [00 · Introduction](../00_introduction.md) · **Time:** ~90 min

Before touching a camera or PAM, get the mental model right: how biometric authentication works, how secure it really is, how to set up safely, and what PAM is (the thing you must not break).

## Modules

| # | Module | The question it answers |
|---|--------|-------------------------|
| 01-1 | [How face auth works](01_how_face_auth_works.md) | Enroll → template → verify — and what a threshold actually trades off |
| 01-2 | [The security reality](02_security_reality.md) | How secure is webcam face unlock, really? When should I trust it? |
| 01-3 | [Environment & safety](03_environment_and_safety.md) | How do I set up — and the one safety rule that stops me locking myself out |
| 01-4 | [PAM primer](04_pam_primer.md) | What is PAM, how does `/etc/pam.d` work, and why is it dangerous to edit? |

## What you'll be able to do after this section

- Describe the enroll/verify pipeline and the **FAR/FRR** threshold trade-off.
- State the honest threat model of 2D face unlock.
- Set up the environment and follow the "keep a root shell open" safety rule.
- Read a PAM config, name the control flags, and know why `pamtester` exists.

> ⚠️ **Safety rule (you'll see this in every PAM module):** keep a second terminal with a live root shell (`sudo -i`) open, never remove password auth, and test with `pamtester` before touching `sudo`.

→ Start: **[01-1 · How face auth works](01_how_face_auth_works.md)**
