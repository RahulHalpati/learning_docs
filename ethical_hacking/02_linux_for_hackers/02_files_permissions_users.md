# 02-2 · Files, Permissions & Users

> **Level:** Beginner · **Prerequisites:** [02-1 Terminal survival](01_terminal_survival.md)
> **Time:** ~1.5 hours · **Verified:** 2026-06-25 (Kali Linux rolling)

> ⚠️ **LEGAL REMINDER:** Practice all commands on the attacker container or your own machines only.

---

## Why this matters

Linux permissions are the foundation of system security — and the most common path to privilege escalation. When you get initial access to a Linux system as a low-privilege user, the next step is always: "can I read sensitive files? can I run something as root?" Understanding how permissions work tells you where to look.

---

## The permission model

Every file has three sets of permissions: **owner**, **group**, and **others**.

```bash
ls -la /etc/passwd
# -rw-r--r-- 1 root root 2891 Jun 25 12:00 /etc/passwd
#  ↑↑↑↑↑↑↑↑↑
#  │└──┤└──┤└──┤
#  │   │   │   └── others: r-- (read only)
#  │   │   └────── group:  r-- (read only)
#  │   └────────── owner:  rw- (read + write)
#  └────────────── file type: - (regular file), d (directory), l (symlink)
```

Permission bits:
- `r` (4) — read
- `w` (2) — write
- `x` (1) — execute (for files) / enter (for directories)
- `-` — permission not set

In octal: `rw-r--r--` = 6+4+4 = `644`

```bash
chmod 755 script.sh    # rwxr-xr-x  (owner: rwx, group: rx, others: rx)
chmod 600 secret.txt   # rw-------  (owner only)
chmod +x script.sh     # add execute for everyone
```

---

## Users and groups

```bash
whoami          # current user
id              # user ID, group memberships
cat /etc/passwd # all users: username:x:uid:gid:comment:home:shell
cat /etc/shadow # password hashes (root only — can you read this?)
```

`/etc/passwd` format:
```
root:x:0:0:root:/root:/bin/bash
alice:x:1001:1001::/home/alice:/bin/bash
```
Fields: `username : password(x=in shadow) : UID : GID : comment : home : shell`

`/etc/shadow` format (root only):
```
alice:$6$salt$hashedpassword...:19000:0:99999:7:::
```
The hash format `$6$` = SHA-512. If you can read this file, you can crack these hashes offline with John the Ripper.

---

## SUID and SGID (privilege escalation vectors)

**SUID (Set User ID):** when a file with SUID is executed, it runs as its **owner** regardless of who runs it. If root owns an SUID binary — it runs as root.

```bash
# Find all SUID binaries on the system
find / -perm -4000 -type f 2>/dev/null
```

Inside the attacker container:
```
/usr/bin/passwd
/usr/bin/su
/usr/bin/newgrp
```

`/usr/bin/passwd` is SUID root — this is intentional (users need root's access to write to `/etc/shadow` when changing passwords). Unintentional SUID on unusual binaries is a privilege escalation path.

**GTFOBins** (gtfobins.github.io) lists every Linux binary that can be abused for privilege escalation — check it whenever you find an unusual SUID binary.

---

## Practical: can you read the shadow file?

Inside the attacker container (you're root):
```bash
cat /etc/shadow | head -3
```

```
root:!:20000:0:99999:7:::
daemon:*:19900:0:99999:7:::
...
```

On a real pentest, you start as a low-privilege user. The goal is to find a path to reading `/etc/shadow` (then crack hashes offline) or directly escalating to root.

---

## Recap & next

- ✅ Permission bits: rwx (4+2+1) for owner, group, others
- ✅ `chmod` changes permissions; `chown` changes owner
- ✅ `/etc/passwd` lists users; `/etc/shadow` stores password hashes (root only)
- ✅ SUID binaries run as their owner — a misconfigured SUID binary can mean root access

**Self-check:** You find a file `backup.sh` with permissions `-rwsr-xr-x` owned by root. What does the `s` in the owner's execute position mean, and why is this interesting?

<details>
<summary>Answer</summary>

The `s` in the execute bit for the owner means **SUID is set**. Running `backup.sh` will execute it as root, regardless of your current user. If this script runs any user-controlled input (e.g., reads a filename from an argument and passes it to `cat` or `bash`), you can potentially execute arbitrary commands as root. Check GTFOBins for the specific binary, and look for ways to inject commands via the script's inputs.

</details>

---

## Exercises

**1. Permission math.** What octal value represents `rwxr-x---`? What does this mean in plain English?

<details>
<summary>Answer</summary>

`rwx` = 7, `r-x` = 5, `---` = 0 → **750**

Owner can read/write/execute. Group can read/execute. Others have no access. This is typical for executable scripts you want to share with your group but not the world.

</details>

**2. Find writable files.** Inside the attacker container, find all world-writable files (permissions include `w` for others):

```bash
find / -perm -002 -type f 2>/dev/null
```

Are any of them interesting (system files, scripts, config files)?

<details>
<summary>What to look for</summary>

World-writable files are files anyone can modify. If a cron job runs a world-writable script as root, you can modify the script to add your own commands. In a real pentest, world-writable files in `/etc/`, `/usr/`, or any directory that contains scripts run by privileged processes are high-value findings.

</details>

---

**Next → [03 Networking commands](03_networking_commands.md)**
