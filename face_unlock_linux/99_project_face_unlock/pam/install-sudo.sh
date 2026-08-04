#!/usr/bin/env bash
# Add face auth to `sudo` as an OPTIONAL first factor (falls back to password).
#
#   ⚠️  READ FIRST. A broken /etc/pam.d/sudo can stop sudo working.
#   BEFORE running: open a SECOND terminal and run `sudo -i` so you keep a live
#   root shell. This script backs up the file and only PREPENDS a 'sufficient'
#   line, so your password still works — but verify that before you close the
#   root shell.  Undo with:  sudo cp /etc/pam.d/sudo.faceunlock.bak /etc/pam.d/sudo
set -euo pipefail

PAM_SUDO="/etc/pam.d/sudo"
HOOK="/opt/faceunlock/pam/faceunlock-pam.sh"
LINE="auth       sufficient   pam_exec.so quiet ${HOOK}"

[ "$(id -u)" -eq 0 ] || { echo "Run with sudo."; exit 1; }
[ -x "$HOOK" ] || { echo "Hook not found/executable: $HOOK"; exit 1; }

if grep -qF "$HOOK" "$PAM_SUDO"; then
    echo "Already installed in $PAM_SUDO — nothing to do."
    exit 0
fi

cp "$PAM_SUDO" "${PAM_SUDO}.faceunlock.bak"          # backup
printf '%s\n%s\n' "$LINE" "$(cat "$PAM_SUDO")" > "${PAM_SUDO}.new"
mv "${PAM_SUDO}.new" "$PAM_SUDO"                       # prepend the sufficient line

echo "Installed. Backup at ${PAM_SUDO}.faceunlock.bak"
echo "TEST NOW in another shell: 'sudo -k; sudo true' — it should face-unlock,"
echo "and pressing Ctrl-C / failing the face check must still let you type your PASSWORD."
echo "If anything is wrong, restore: cp ${PAM_SUDO}.faceunlock.bak $PAM_SUDO"
