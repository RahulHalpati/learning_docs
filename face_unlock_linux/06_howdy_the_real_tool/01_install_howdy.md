# 06-1 · Install Howdy

> **Level:** Intermediate · **Prerequisites:** [05 · PAM integration](../05_pam_integration/README.md)
> **Time:** 20 min · **Verified:** 2026-07-22 (install commands; run on your machine — needs a camera)

## Why this matters

Howdy is what you'd actually run: it uses **dlib's deep face embeddings** (far better than our LBPH) and supports **IR cameras** (real anti-spoofing), with a maintained PAM integration. Everything you learned — enroll/verify, thresholds, `sufficient` + password fallback, fail-closed — maps directly onto it; you're now an informed user, not a copy-paster.

---

## Install (Ubuntu/Debian)

```bash
sudo add-apt-repository ppa:boltgolt/howdy
sudo apt update
sudo apt install howdy
```

Other distros:
- **Arch:** `yay -S howdy` (AUR).
- **Fedora:** enable the COPR (`sudo dnf copr enable principis/howdy`) then `sudo dnf install howdy` — check the current COPR name, it moves.

> ⚠️ **Project status:** the original `boltgolt/howdy` has had maintenance gaps and community forks (e.g. a "howdy" reboot). Package names/PPAs shift over time — if the PPA 404s, search your distro's current Howdy package. The *concepts* below are stable even as packaging changes.

---

## Check your camera — IR vs RGB matters a lot

Howdy shines with an **IR** camera (many laptops have one for Windows Hello). IR gives real anti-spoofing ([04-2](../04_liveness_and_antispoofing/02_liveness_defenses.md)); a plain RGB webcam is still photo-spoofable even through Howdy.

```bash
# list video devices and identify the IR one
v4l2-ctl --list-devices          # from v4l-utils
ls /dev/video*
```

Howdy needs the correct device path in its config (the IR node, not the RGB one). The IR camera often appears as a second `/dev/videoN` and may show a dark/greyscale image in a normal viewer.

> **Tip:** if `howdy test` shows a black frame, you've likely pointed it at the IR device without IR illumination, or at the wrong node. Getting `device_path` right is the #1 Howdy setup snag.

---

## Verify the install

```bash
sudo howdy config        # opens the config (confirms Howdy is installed)
howdy --help             # subcommands: add, remove, list, test, config, disable
```

---

## Recap & next

- ✅ Install via the PPA (Ubuntu) / AUR (Arch) / COPR (Fedora); packaging shifts, concepts don't.
- ✅ Howdy uses dlib embeddings + IR support — much stronger than our LBPH build.
- ✅ Identify your **IR** camera device; RGB-only Howdy is still photo-spoofable.
- ✅ Self-check: why is Howdy on an IR camera meaningfully more secure than our RGB prototype?

→ Next: **[06-2 · Enroll & configure](02_enroll_and_configure.md)**

## Exercises

1. Run `v4l2-ctl --list-devices` and identify which `/dev/videoN` is your IR camera (if any). No IR? Note that you'll be in RGB/convenience mode.

<details>
<summary>Solution</summary>

IR cameras usually list as a separate device (sometimes named with "IR"). If you only have one RGB webcam, Howdy still works but at the security level of our from-scratch build — convenience with a password fallback, not strong auth.
</details>
