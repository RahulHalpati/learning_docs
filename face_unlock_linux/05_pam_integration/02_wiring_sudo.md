# 05-2 · Wiring sudo

> **Level:** Advanced · **Prerequisites:** [05-1 · PAM sandbox](01_pam_sandbox.md) (get a clean pass there first)
> **Time:** 30 min · **Verified:** 2026-07-22 (config + installer validated offline; live `sudo` change is on your machine)

> 🛑 **SAFETY — do this now, not after:** open a **second terminal** and run `sudo -i`; **leave that root shell open** for the whole lesson. Back up the file: `sudo cp /etc/pam.d/sudo /etc/pam.d/sudo.faceunlock.bak`. If anything goes wrong, the open root shell restores it instantly. Never remove password auth. We only *add* an optional line.

## Why this matters

`sudo` is the right first real target: it's the lowest-risk place to integrate. If face auth on `sudo` breaks, you still have a logged-in desktop and (per the safety rule) an open root shell — unlike breaking `login`/GDM, which can lock you out of the session entirely. Same PAM chain you sandboxed, now guarding a real command.

---

## The change: one prepended line

We add the face hook to `/etc/pam.d/sudo` as **`sufficient`, before** the password include:

```
auth       sufficient   pam_exec.so quiet /opt/faceunlock/pam/faceunlock-pam.sh
@include common-auth      # ← untouched: your password still works
```

`sudo` now tries the face first; a match (`sufficient` → exit 0) authorizes immediately; a non-match falls through to `common-auth` → your password. **Nothing is removed.**

---

## Use the guarded installer

`pam/install-sudo.sh` does this defensively — backup, prepend only, print a test + recovery drill:

```bash
sudo ./pam/install-sudo.sh
```

**What it does (annotated):**
```bash
cp /etc/pam.d/sudo /etc/pam.d/sudo.faceunlock.bak          # backup
printf '%s\n%s\n' "$LINE" "$(cat /etc/pam.d/sudo)" > .new  # PREPEND the sufficient line
mv .new /etc/pam.d/sudo                                    # (password include untouched)
```

It refuses to run twice, requires the hook to exist, and prints the recovery command.

---

## Test immediately (with the root shell open)

In your *normal* terminal:

```bash
sudo -k          # forget any cached sudo credential, so auth runs fresh
sudo true        # triggers the sudo PAM stack
```

Two outcomes must both work:

1. **Face matches** → `sudo` proceeds with no password. 🎉
2. **Face fails / you cover the camera / Ctrl-C the face step** → `sudo` **prompts for your password** and works. ✅ ← *verify this one especially.*

If (2) doesn't fall back to a working password prompt, **stop** and restore from the root shell:

```bash
sudo cp /etc/pam.d/sudo.faceunlock.bak /etc/pam.d/sudo     # instant undo
```

Only once *both* paths work is the integration sound. This is why the sandbox came first — you're not debugging the hook here, only the placement.

> ⚠️ **Do not proceed to `login`/GDM in this course.** `sudo` is deliberately the ceiling: recoverable, low-blast-radius. Display-manager integration is possible but multiplies lockout risk and recovery complexity — out of scope for a safe learning path.

---

## Recap & next

- ✅ Add face auth to `/etc/pam.d/sudo` as one **`sufficient`** line *before* `@include common-auth`.
- ✅ Back up first; keep a **root shell open**; use the guarded installer.
- ✅ Test **both** paths: face-match success *and* fallback-to-password. Restore instantly if fallback breaks.
- ✅ Stop at `sudo` — don't wire login/GDM here.
- ✅ Self-check: why is testing the *fallback* path more important than testing the success path?

→ Next: **[05-3 · Hardening & fallback](03_hardening_and_fallback.md)**

## Exercises

1. Install on `sudo`, then run the recovery drill: restore the backup, `sudo -k; sudo true`, confirm password-only works, then reinstall. Practicing undo is the point.

<details>
<summary>Solution</summary>

`sudo cp /etc/pam.d/sudo.faceunlock.bak /etc/pam.d/sudo` returns to password-only; `sudo -k; sudo true` should prompt for and accept your password. Re-run `sudo ./pam/install-sudo.sh` to add face auth back. You now know the escape hatch works *before* you ever need it.
</details>
