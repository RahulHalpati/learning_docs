# 02-3 · Networking Commands

> **Level:** Beginner · **Prerequisites:** [02-2 Files, permissions & users](02_files_permissions_users.md)
> **Time:** ~1.5 hours · **Verified:** 2026-06-25 (Kali Linux attacker container)

> ⚠️ **LEGAL REMINDER:** Run all network probing commands against the lab containers only (`10.0.0.0/24`).

---

## Why this matters

Before you run nmap, you need to know your own network interface, confirm you can reach a target, and understand what's listening on your own machine. These basic commands are the first things you run on any new system — yours or a compromised target.

---

## Your own network: `ip` and `ss`

```bash
# Show all network interfaces and IPs
ip addr
# or short form:
ip a
```

Inside the attacker container:
```
1: lo: <LOOPBACK> ...
    inet 127.0.0.1/8 scope host lo
2: eth0: <BROADCAST,MULTICAST,UP,LOWER_UP> ...
    inet 10.0.0.10/24 brd 10.0.0.255 scope global eth0
```

```bash
# Show active connections and listening ports
ss -tlnp        # TCP, listening, numeric (no DNS), show process

# Older alternative
netstat -tlnp
```

Output:
```
State   Recv-Q  Send-Q  Local Address:Port  Peer Address:Port
LISTEN  0       128     0.0.0.0:22          0.0.0.0:*      users:(("sshd",pid=123))
```

**Why it matters on a compromised machine:** `ss -tlnp` reveals every service listening locally — including ones not visible from the network. A database on `127.0.0.1:3306` only accessible locally is still a target from inside the machine.

---

## Connectivity testing: `ping`, `traceroute`, `curl`

```bash
# Test if a host is reachable (ICMP)
ping -c 3 10.0.0.20

# Trace the route
traceroute 10.0.0.20

# Make an HTTP request
curl http://10.0.0.30:5000/
curl -s http://10.0.0.30:5000/   # silent (no progress bar)
curl -v http://10.0.0.30:5000/   # verbose (show headers)
curl -I http://10.0.0.30:5000/   # headers only (HEAD request)
```

Verified output (from attacker container):
```bash
root@attacker:~# ping -c 3 10.0.0.20
PING 10.0.0.20 (10.0.0.20) 56(84) bytes of data.
64 bytes from 10.0.0.20: icmp_seq=1 ttl=64 time=0.152 ms
64 bytes from 10.0.0.20: icmp_seq=2 ttl=64 time=0.098 ms
64 bytes from 10.0.0.20: icmp_seq=3 ttl=64 time=0.089 ms

--- 10.0.0.20 ping statistics ---
3 packets transmitted, 3 received, 0% packet loss
```

---

## DNS lookups: `dig`, `nslookup`, `host`

```bash
# Full DNS lookup
dig google.com

# Quick short answer
dig +short google.com

# Reverse lookup
dig -x 8.8.8.8

# Simple lookup
host google.com
nslookup google.com
```

---

## Download files: `wget`, `curl`

```bash
# Download a file
wget http://10.0.0.30:5000/       # saves as index.html
curl -O http://10.0.0.30:5000/    # saves with remote filename
curl -o output.json http://10.0.0.30:5000/   # custom output filename
```

These are how you'll download exploit scripts or exfiltrate data in post-exploitation scenarios.

---

## Recap & next

- ✅ `ip addr` — show your IPs; `ss -tlnp` — show listening services
- ✅ `ping` tests ICMP reachability; `traceroute` shows the path
- ✅ `curl -v` shows full HTTP request/response headers
- ✅ `dig` and `host` resolve DNS; `dig -x` does reverse lookup

**Self-check:** You gain access to a machine and run `ss -tlnp`. You see a service on `127.0.0.1:5432` that isn't in any public nmap scan. What is port 5432 and why is this significant?

<details>
<summary>Answer</summary>

Port 5432 is PostgreSQL. It's bound to `127.0.0.1` (loopback only) so it's not visible from the network — that's why nmap didn't show it. From inside the machine, you can connect directly: `psql -h 127.0.0.1 -U postgres`. In a pentest this is significant: you may find database credentials in config files, and the database may contain sensitive data or allow command execution (`COPY TO/FROM PROGRAM` in PostgreSQL).

</details>

---

## Exercises

**1. Verify the lab topology.** From inside the attacker container, ping all four lab IPs (10.0.0.10, 10.0.0.20, 10.0.0.30, 10.0.0.40). Which ones respond to ping? Does the database (10.0.0.40) respond?

**2. Read response headers.** Use `curl -I http://10.0.0.30:5000/`. What server software and version does the Flask app reveal in the `Server` header? Why is this a security concern?

<details>
<summary>Answer</summary>

```
Server: Werkzeug/3.0.1 Python/3.11.6
```

This reveals the exact software and version. An attacker can look up CVEs for `Werkzeug 3.0.1` and `Python 3.11.6`. In production, the `Server` header should be suppressed or replaced with a generic string. This is called **information disclosure** — covered in Module 05-1.

</details>

---

**Next → [04 Process & service management](04_process_and_service_management.md)**
