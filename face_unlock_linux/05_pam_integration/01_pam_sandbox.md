# 05-1 · PAM sandbox

> **Level:** Intermediate → Advanced · **Prerequisites:** [01-4 · PAM primer](../01_foundations/04_pam_primer.md) · [03-3 · The verify CLI](../03_recognition_and_enrollment/03_verify_cli.md)
> **Time:** 30 min · **Verified:** 2026-07-22 (config + hook validated offline; `pamtester` run is on your machine)

> 🛑 **SAFETY:** this lesson is the *reason* the safety rule works — a sandbox service can't lock you out. Even so, keep your root shell open and never edit real `sudo`/login yet.

## Why this matters

Before face auth guards anything real, prove the PAM plumbing works somewhere harmless. A **custom PAM service** tested with **`pamtester`** runs the exact `pam_exec` → `verify.py` chain you'll later put in `sudo`, but touches *nothing* that can lock you out. Get a green here, then promote.

---

## The pieces

**1. The hook** (`pam/faceunlock-pam.sh`) — what `pam_exec` runs. Exit 0 = accept; anything else falls through:

```bash
#!/usr/bin/env bash
set -euo pipefail
USER_NAME="${PAM_USER:-$(id -un)}"           # PAM sets PAM_USER
MODEL="/etc/faceunlock/models/${USER_NAME}.yml"
PYTHON="/opt/faceunlock/.venv/bin/python"
[ -x "$PYTHON" ] || exit 1                    # fail closed
[ -f "$MODEL" ]  || exit 1
exec timeout 8 "$PYTHON" -m faceunlock.verify --model "$MODEL" >/dev/null 2>&1
```

The `timeout 8` guarantees a stuck camera can't hang authentication — on timeout it returns non-zero → password fallback.

**2. The sandbox service** (`pam/faceunlock-test` → `/etc/pam.d/faceunlock-test`):

```
auth       sufficient   pam_exec.so quiet /opt/faceunlock/pam/faceunlock-pam.sh
auth       required     pam_unix.so
account    required     pam_unix.so
```

`sufficient` means: face hook exits 0 → auth succeeds now; otherwise fall through to `pam_unix` (your password). This is the *same* pattern we'll use for `sudo` — rehearsed safely.

---

## Deploy the project where PAM can reach it

PAM services run as root and don't see your user venv, so place the project and its venv at a fixed root-readable path, and each user's model under root ownership:

```bash
sudo mkdir -p /opt/faceunlock /etc/faceunlock/models
sudo cp -r faceunlock /opt/faceunlock/
sudo python3 -m venv /opt/faceunlock/.venv
sudo /opt/faceunlock/.venv/bin/pip install opencv-contrib-python==4.11.0.86 numpy pillow
sudo install -m 0755 pam/faceunlock-pam.sh /opt/faceunlock/pam/faceunlock-pam.sh
sudo cp model.yml /etc/faceunlock/models/"$USER".yml     # your enrolled model (03-2)
sudo cp pam/faceunlock-test /etc/pam.d/faceunlock-test
```

> ⚠️ Models live in **root-owned** `/etc/faceunlock/models/` so a normal user can't drop in their own model and impersonate you. The hook derives the filename from `PAM_USER`.

---

## Test with pamtester (safe)

```bash
sudo apt install -y pamtester        # Arch: pamtester (AUR)   Fedora: pamtester
pamtester faceunlock-test "$USER" authenticate
```

- Look at the camera → the hook's `verify.py` matches → **`pamtester: successfully authenticated`**.
- Cover the camera / no match → hook exits non-zero → `pamtester` prompts for your **password** (the fallback) → authenticates via `pam_unix`.

Because this is the `faceunlock-test` service, **nothing** you do here affects `login` or `sudo`. Break it, fix it, repeat — zero risk. Only when this behaves correctly do you move to [05-2](02_wiring_sudo.md).

> **Tip:** run the hook directly to debug outside PAM: `sudo PAM_USER="$USER" /opt/faceunlock/pam/faceunlock-pam.sh; echo $?` — `0` means it would accept.

---

## Recap & next

- ✅ A custom PAM service + `pamtester` rehearses the real chain with **zero lockout risk**.
- ✅ Hook contract: exit 0 = accept; `timeout` + missing-file checks = **fail closed**.
- ✅ Project at `/opt/faceunlock`, models root-owned in `/etc/faceunlock/models/<user>.yml`.
- ✅ Get a clean pass here **before** touching `sudo`.
- ✅ Self-check: why can breaking `faceunlock-test` never lock you out, but breaking `sudo` can?

→ Next: **[05-2 · Wiring sudo](02_wiring_sudo.md)**

## Exercises

1. Delete your model file and re-run `pamtester`. Confirm it falls through to the password (fail-closed), not an error that blocks auth.

<details>
<summary>Solution</summary>

With the model gone, the hook's `[ -f "$MODEL" ] || exit 1` fires → non-zero → `sufficient` line is skipped → `pam_unix` prompts for the password. Missing model = degrade to password, never lockout. That's the fail-closed design working.
</details>
