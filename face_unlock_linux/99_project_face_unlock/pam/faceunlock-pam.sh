#!/usr/bin/env bash
# pam_exec hook: run the face verifier for the PAM user.
# Exit 0 = face accepted (PAM 'sufficient' -> auth succeeds).
# Any non-zero (no model, no face, timeout, mismatch) = fall through to the
# next PAM line (the password). FAIL CLOSED — never exit 0 on error.
set -euo pipefail

USER_NAME="${PAM_USER:-$(id -un)}"
MODEL="/etc/faceunlock/models/${USER_NAME}.yml"
PYTHON="/opt/faceunlock/.venv/bin/python"      # the project venv on the target machine

[ -x "$PYTHON" ] || exit 1
[ -f "$MODEL" ]  || exit 1

# 8s cap so a stuck camera never hangs authentication; timeout's exit code
# propagates (124 on timeout) -> non-zero -> password fallback.
exec timeout 8 "$PYTHON" -m faceunlock.verify --model "$MODEL" >/dev/null 2>&1
