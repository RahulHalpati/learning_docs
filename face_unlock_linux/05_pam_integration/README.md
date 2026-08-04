# Section 05 · PAM integration

> **Prerequisites:** [03 · Recognition & enrollment](../03_recognition_and_enrollment/README.md) · [01-4 · PAM primer](../01_foundations/04_pam_primer.md) · **Time:** ~90 min

Wire the verify CLI into Linux authentication — **safely**. Sandbox with `pamtester` first (can't lock you out), then add face unlock to `sudo` with a password fallback, then harden.

> 🛑 **SAFETY (repeated in every module here):** open a **second terminal with a live root shell** (`sudo -i`) and leave it open. **Test in the `pamtester` sandbox before touching `sudo`.** **Never remove password auth.** Every change is backed up and reversible with one `cp`.

## Modules

| # | Module | The question it answers |
|---|--------|-------------------------|
| 05-1 | [PAM sandbox](01_pam_sandbox.md) | How do I test PAM face auth with zero lockout risk? |
| 05-2 | [Wiring sudo](02_wiring_sudo.md) | How do I add face unlock to `sudo` with a password fallback? |
| 05-3 | [Hardening & fallback](03_hardening_and_fallback.md) | How do I make it fail-closed, logged, and easy to disable? |

## What you'll be able to do after this section

- Test a `pam_exec` face hook against a throwaway service with `pamtester`.
- Add face auth to `/etc/pam.d/sudo` as `sufficient`, keeping the password path intact.
- Store models securely, fail closed, log attempts, and disable it instantly.

→ Start: **[05-1 · PAM sandbox](01_pam_sandbox.md)**
