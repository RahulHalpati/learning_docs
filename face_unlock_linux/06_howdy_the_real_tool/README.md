# Section 06 · Howdy — the real tool

> **Prerequisites:** [05 · PAM integration](../05_pam_integration/README.md) · **Time:** ~60 min

You built face unlock from scratch to *understand* it. For daily use, don't ship your LBPH prototype — use **Howdy**, the established Windows-Hello-style face auth for Linux (dlib embeddings, IR-camera support, maintained PAM integration). This section installs, configures, and hardens it — applying everything you now know.

> 🛑 **SAFETY (still applies):** Howdy edits the same PAM files. Keep a **root shell open**, and know that Howdy's own installer wires PAM — verify the password fallback after setup.

## Modules

| # | Module | The question it answers |
|---|--------|-------------------------|
| 06-1 | [Install Howdy](01_install_howdy.md) | How do I install Howdy on Ubuntu (and Arch/Fedora)? |
| 06-2 | [Enroll & configure](02_enroll_and_configure.md) | How do I add my face and tune `config.ini`? |
| 06-3 | [Secure Howdy's PAM](03_secure_howdy_pam.md) | How do I integrate it safely and harden it? |

## What you'll be able to do after this section

- Install Howdy and check camera compatibility (IR vs RGB).
- Enroll faces (`howdy add`) and tune certainty/dark-threshold in `config.ini`.
- Integrate with `sudo` safely and apply hardening (and know Howdy's security history).

→ Start: **[06-1 · Install Howdy](01_install_howdy.md)**
