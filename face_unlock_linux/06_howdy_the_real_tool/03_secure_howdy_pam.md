# 06-3 · Secure Howdy's PAM

> **Level:** Advanced · **Prerequisites:** [06-2 · Enroll & configure](02_enroll_and_configure.md) · [05-2 · Wiring sudo](../05_pam_integration/02_wiring_sudo.md)
> **Time:** 20 min · **Verified:** 2026-07-22 (integration pattern; run on your machine)

> 🛑 **SAFETY:** same rules as Section 05 — **root shell open**, back up PAM files, test the **password fallback**, one-command disable ready. Howdy edits the same `/etc/pam.d/` files you now understand.

## Why this matters

Howdy wires itself into PAM using the exact `sufficient` + fallback pattern you built by hand — so you can integrate it *knowingly*, verify it's safe, and harden it, rather than trusting an installer blindly. You also need to know its security caveats: Howdy has had real CVEs.

---

## How Howdy integrates

Howdy adds a line to a PAM service (e.g. `/etc/pam.d/sudo`) like:

```
auth  sufficient  pam_python.so /lib/security/howdy/pam.py
```

Structurally **identical** to your `pam_exec` line ([05-2](../05_pam_integration/02_wiring_sudo.md)): `sufficient` means a face match authorizes and a failure falls through to the password. Everything you learned about placement, fallback, and fail-closed applies unchanged.

```bash
# add to a service (Howdy ships a helper on some distros; else edit as in 05-2)
sudo howdy config          # ensure it's set up, then verify the PAM line yourself
```

## Verify it like you built it

Do the **same two-path test** from [05-2](../05_pam_integration/02_wiring_sudo.md), root shell open:

```bash
sudo -k; sudo true
# 1. face matches  -> no password.  2. cover camera / fail -> PASSWORD prompt works.
```

If the fallback prompt doesn't appear and work, restore your PAM backup immediately. Never trust "the installer did it" — verify the fallback yourself.

## Security caveats (know these)

- **RGB = still spoofable.** Howdy on a plain RGB webcam is photo-defeatable, like your build. Its real strength needs **IR** ([04-2](../04_liveness_and_antispoofing/02_liveness_defenses.md)).
- **Howdy has had CVEs** — e.g. a past issue where a darkness/edge case could bypass auth, and IR-vs-RGB confusion weakening checks. Keep it **updated**, and set `certainty` conservatively.
- **Don't put it on `login`/GDM until `sudo` is rock-solid** for you — same escalation caution as Section 05.
- **It's a convenience factor.** Keep your password/2FA strong; Howdy sits on top, never replaces them.

## Disable instantly

```bash
sudo howdy disable 1                 # Howdy's own off switch
# or remove the PAM line / restore your backup, exactly as in 05-3
```

---

## From-scratch vs Howdy — when to use which

| | Your build (Sections 02–05) | Howdy |
|---|---|---|
| Purpose | **learning** the mechanics | **daily use** |
| Model | LBPH (readable) | dlib embeddings (accurate) |
| IR / anti-spoof | none | yes (with IR camera) |
| Maintenance | you | upstream (with CVEs — patch it) |
| Verdict | understand, then retire | run this for real |

You built the prototype to *understand*; run Howdy (ideally on IR, kept updated, `certainty` strict, password fallback intact) for real.

---

## Recap & next

- ✅ Howdy uses the same `sufficient` + password-fallback PAM pattern you built — integrate knowingly.
- ✅ Run the **two-path test**; verify the fallback yourself; keep the one-command disable ready.
- ✅ RGB Howdy is still spoofable; it's had CVEs — use **IR**, keep it **updated**, `certainty` strict.
- ✅ Retire your LBPH prototype; run Howdy for daily use as a convenience factor over a strong password.
- ✅ Self-check: why should you personally verify Howdy's password fallback instead of trusting its installer?

→ Next: **[99 · Capstone](../99_project_face_unlock/README.md)**

## Exercises

1. After integrating Howdy on `sudo`, run the fallback drill (cover camera → password works), then `sudo howdy disable 1` and confirm `sudo` is back to password-only.

<details>
<summary>Solution</summary>

Covering the camera must yield a working password prompt (fail-closed fallback). `sudo howdy disable 1` turns Howdy off globally; `sudo -k; sudo true` should then prompt for the password normally — your escape hatch, verified.
</details>
