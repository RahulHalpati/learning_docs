# 02-1 · Terminal Survival

> **Level:** Beginner · **Prerequisites:** [Section 01 complete](../01_networking_fundamentals/README.md)
> **Time:** ~1 hour · **Verified:** 2026-06-25 (Kali Linux rolling, attacker container)

> ⚠️ **LEGAL REMINDER:** Practice all commands inside the lab attacker container or your own machine. Never run recon commands against systems you don't own.

---

## Why this matters

Every tool in the hacker's toolkit is a command-line program. GUI wrappers exist for some tools (Burp Suite, Wireshark), but the power user interface — and the interface you'll use on a remote shell after exploitation — is always the terminal. You need to be fast and confident here.

---

## Start your attacker container

All commands in Sections 02–05 should be run from inside the attacker container unless noted otherwise:

```bash
# From the 99_project_pentest_lab/ directory
docker compose up -d
docker compose exec attacker bash
# root@attacker:/workspace#
```

---

## The essential commands

### Navigation

```bash
pwd                    # where am I?
ls -la                 # list files, long format, show hidden
cd /etc                # change directory
cd ..                  # go up one level
cd ~                   # go to home directory
cd -                   # go to previous directory
```

### Files & text

```bash
cat /etc/hostname      # print a file
less /etc/hosts        # paginate a long file (q to quit)
head -5 /etc/passwd    # first 5 lines
tail -f /var/log/syslog # follow a file in real time

grep "root" /etc/passwd          # search inside a file
grep -r "password" /var/www/     # recursive search
grep -i "admin" file.txt         # case-insensitive

find / -name "*.conf" 2>/dev/null      # find all .conf files
find / -perm -4000 2>/dev/null         # find SUID files (covered in 02-2)
```

### Pipes and redirection

```bash
# Pipe: send output of one command as input to another
cat /etc/passwd | grep root
nmap -sV 10.0.0.0/24 | grep "open"

# Redirect output to a file
nmap 10.0.0.20 > scan.txt
nmap 10.0.0.20 >> scan.txt   # append (don't overwrite)

# Redirect stderr (error messages) to /dev/null
find / -name "secret" 2>/dev/null   # suppress "Permission denied" noise
```

### Networking (quick reference — covered more in 02-3)

```bash
ip addr                # show your IP addresses
ping -c 3 10.0.0.20    # test connectivity (3 packets)
curl http://10.0.0.30:5000/   # make an HTTP request
```

---

## Getting help

```bash
man nmap               # the manual page (press / to search, q to quit)
nmap --help            # most tools have --help
nmap -h                # or -h
```

---

## Verified output (inside attacker container)

```bash
root@attacker:/workspace# ip addr | grep inet
    inet 127.0.0.1/8 scope host lo
    inet 10.0.0.10/24 brd 10.0.0.255 scope global eth0
```

Your attacker container is `10.0.0.10` on the lab network — confirmed.

---

## Recap & next

- ✅ `ls -la`, `cd`, `cat`, `grep`, `find` — navigation and file searching
- ✅ Pipes (`|`) chain commands; `>` and `>>` redirect output to files
- ✅ `2>/dev/null` silences error messages
- ✅ `man <command>` and `--help` give you documentation for any tool

**Self-check:** You want to find all files owned by root with the SUID bit set on the system. What single find command does this?

<details>
<summary>Answer</summary>

```bash
find / -user root -perm -4000 2>/dev/null
```

`-perm -4000` matches any file with at least the SUID bit set. `2>/dev/null` suppresses permission errors for directories you can't read. SUID files run as their owner (root) regardless of who executes them — a common privilege escalation vector.

</details>

---

## Exercises

**1. Explore the attacker container.** Inside the attacker container, find where nmap is installed (`which nmap`), how many lines are in `/etc/passwd`, and the contents of `/etc/hostname`.

<details>
<summary>Solution</summary>

```bash
which nmap          # → /usr/bin/nmap
wc -l /etc/passwd   # count lines
cat /etc/hostname   # → attacker
```

</details>

**2. Pipe practice.** Run `nmap -sn 10.0.0.0/24` and pipe the output through `grep "report"` to show only the lines with discovered hosts. Save that output to `/shared/hosts.txt`.

<details>
<summary>Solution</summary>

```bash
nmap -sn 10.0.0.0/24 | grep "report" > /shared/hosts.txt
cat /shared/hosts.txt
```

The `/shared/` directory is mounted from your host machine, so `hosts.txt` will appear in `99_project_pentest_lab/shared/` on your laptop too.

</details>

---

**Next → [02 Files, permissions & users](02_files_permissions_users.md)**
