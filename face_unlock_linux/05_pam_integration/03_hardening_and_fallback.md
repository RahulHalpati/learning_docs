# 05-3 · Hardening & fallback

> **Level:** Advanced · **Prerequisites:** [05-2 · Wiring sudo](02_wiring_sudo.md)
> **Time:** 30 min · **Verified:** 2026-07-22 (practices; config validated offline)

> 🛑 **SAFETY:** keep the root shell open while changing anything under `/etc/pam.d` or `/etc/faceunlock`. Every edit stays backed up and reversible.

## Why this matters

A working face unlock isn't a *safe* one until it fails correctly, resists tampering, and can be turned off in one command. This lesson is the checklist that separates "cool demo" from "I trust this on my machine".

---

## 1. Fail closed, always

Every failure path must **deny** (→ password), never accept:

- No model / no camera / no face → exit 1. ✅ (built into the hook)
- Camera hangs → `timeout 8` → non-zero → password. ✅
- Unexpected exception in `verify.py` → non-zero exit → password. ✅ (don't `except: pass` into a `sys.exit(0)`)

> **The cardinal rule:** an error must never become an *accept*. Audit your hook so there's no path that exits 0 without a genuine match.

## 2. Protect the model and code

- Models in **root-owned** `/etc/faceunlock/models/<user>.yml` (mode `0644` or stricter), so a user can't swap in a model that matches their own face to impersonate another user.
- Code/venv in **root-owned** `/opt/faceunlock` so a user can't edit `verify.py` to always exit 0.
- If either is user-writable, face auth is worthless — a local user just rewrites the verdict.

```bash
sudo chown -R root:root /opt/faceunlock /etc/faceunlock
sudo chmod -R go-w      /opt/faceunlock /etc/faceunlock
```

## 3. Log attempts

Send outcomes to the journal so you can see accepts/rejects and spot abuse:

```bash
# in faceunlock-pam.sh, before exit:
logger -t faceunlock "user=$USER_NAME result=$?"      # view: journalctl -t faceunlock
```

## 4. Tune for security, not convenience

- Bias the **threshold stricter** ([03-3](../03_recognition_and_enrollment/03_verify_cli.md)) — a false reject costs a password prompt; a false accept is a breach.
- Keep the `timeout` short (a few seconds) so `sudo` never feels hung.
- Consider limiting face auth to interactive sessions (skip it for scripts/SSH where there's no camera).

## 5. The off switch (know it cold)

Disable instantly by restoring the backup — no reboot:

```bash
sudo cp /etc/pam.d/sudo.faceunlock.bak /etc/pam.d/sudo     # sudo back to password-only
sudo rm -f /etc/pam.d/faceunlock-test                      # remove the sandbox service
```

Because face auth was only ever a prepended `sufficient` line over an untouched password stack, removing it always leaves a working password login.

---

## Hardening checklist

| Check | Why |
|-------|-----|
| ☐ Hook fails closed on every error path | an error must never mean "accept" |
| ☐ Model + code root-owned, not user-writable | stop users rewriting the verdict |
| ☐ Password fallback present and tested | the floor under a spoof/failure |
| ☐ `timeout` on the camera step | never hang authentication |
| ☐ Attempts logged to journal | visibility / audit |
| ☐ Threshold biased strict | prefer false-reject over false-accept |
| ☐ One-command disable rehearsed | you can always get back in |
| ☐ (RGB only) accept it's convenience-grade | use IR/Howdy for stronger needs |

---

## Recap & next

- ✅ **Fail closed** on every path; audit for any error→accept route.
- ✅ Root-own model + code so users can't tamper with the verdict.
- ✅ Log attempts, keep `timeout` short, bias threshold strict, keep the password.
- ✅ One `cp` disables it — rehearse the off switch.
- ✅ Self-check: if `/opt/faceunlock/verify.py` were user-writable, how would a local user bypass the whole system in one edit?

→ Next: **[06 · Howdy — the real tool](../06_howdy_the_real_tool/README.md)**

## Exercises

1. Add the `logger` line to the hook, run a few `sudo` attempts (some matching, some not), and read them back with `journalctl -t faceunlock`.

<details>
<summary>Solution</summary>

Each attempt logs `user=<you> result=<code>` (0 = accepted). `journalctl -t faceunlock` shows the trail — your first taste of biometric-auth observability, and how you'd notice repeated failed attempts.
</details>
