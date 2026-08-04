# 01-3 · Environment & safety

> **Level:** Beginner · **Prerequisites:** [01-1 · How face auth works](01_how_face_auth_works.md)
> **Time:** 20 min · **Verified:** 2026-07-22 (Python 3.10, opencv-contrib-python 4.11.0.86, Ubuntu/Debian)

## Why this matters

Two setups matter here: the **Python environment** (so the code runs) and the **safety setup** (so a later PAM mistake doesn't lock you out of your own machine). The second one is not optional — internalize it now, before Section 05.

---

## Python environment

```bash
# Ubuntu/Debian
sudo apt update && sudo apt install -y python3-venv v4l-utils
python3 -m venv .venv && source .venv/bin/activate       # Windows users: this course is Linux-only
pip install opencv-contrib-python==4.11.0.86 numpy pillow
```

> ⚠️ **Use `opencv-contrib-python`, not `opencv-python`.** We need `cv2.face` (LBPH), which is only in the *contrib* build. And stay on the **4.x** line — OpenCV **5.0 dropped the bundled Haar cascades** we rely on.

Distro notes: **Arch** `sudo pacman -S python-opencv v4l-utils` (or pip in a venv); **Fedora** `sudo dnf install python3-opencv v4l-utils` (or pip).

## Check your webcam

```bash
ls /dev/video*
```

**Output (real run):**
```
/dev/video0
/dev/video1
```

Each `/dev/videoN` is a camera node (laptops often expose two: the RGB stream and metadata). `v4l2-ctl --list-devices` (from `v4l-utils`) shows names. **No camera?** You can still do Sections 02–03 fully — the bundled sample images drive the whole detect/enroll/verify pipeline offline.

---

## 🛑 The safety rule (memorize this)

From Section 05 you edit **PAM**, which authenticates you. A wrong line in `/etc/pam.d/sudo` can make `sudo` refuse you; a wrong line in login/GDM can lock you out of the desktop. **These are recoverable only if you prepared.** So, whenever a lesson touches PAM:

> ⚠️ **1. Keep a live root shell open.** In a *second* terminal, run `sudo -i` and **leave it open**. If you break `sudo`, this shell can still fix the file.
> **2. Test in the `pamtester` sandbox first** — a throwaway PAM service that can't affect login or `sudo` ([05-1](../05_pam_integration/01_pam_sandbox.md)).
> **3. Never remove password authentication.** Face auth is only ever *added* as an optional factor.
> **4. Know your recovery path.** Every change we make is backed up and reversible with one `cp`.

We also stick to `sudo` (not login/GDM) as the integration target: it's the lowest-risk place to fail, because a broken `sudo` still leaves you a logged-in desktop and that spare root shell.

> **Analogy — locksmithing your own door.** You never change the lock without a key already in your pocket and a window you can climb through. The root shell is the key in your pocket; `pamtester` is practicing on a spare door first.

---

## Project layout

We'll build toward the capstone package (Sections 02–05 develop these files):

```
faceunlock/   pipeline.py · detect.py · enroll.py · verify.py · capture.py
samples/      bundled faces (offline)          pam/  sandbox + sudo wiring
tests/        offline pytest
```

---

## Recap & next

- ✅ `opencv-contrib-python==4.11.x` (contrib for `cv2.face`; 4.x for bundled cascades), in a venv.
- ✅ `ls /dev/video*` checks the camera; Sections 02–03 also run camera-free on sample images.
- ✅ The safety rule: **root shell open, sandbox first, never drop the password, know the undo.**
- ✅ Self-check: why do we target `sudo` rather than graphical login for our first real integration?

→ Next: **[01-4 · PAM primer](04_pam_primer.md)**

## Exercises

1. Open a second terminal, run `sudo -i`, and confirm you have a root prompt. Leave it open for the rest of the course. Then `cp /etc/pam.d/sudo /tmp/sudo.backup` to feel the recovery habit.

<details>
<summary>Solution</summary>

The root shell (`#` prompt) is your safety net; the backup is your undo. If you never break anything, you've lost nothing — if you do, you'll be very glad both exist.
</details>
