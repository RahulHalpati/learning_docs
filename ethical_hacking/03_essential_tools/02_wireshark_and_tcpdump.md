# 03-2 · Wireshark & tcpdump

> **Level:** Beginner · **Prerequisites:** [03-1 nmap](01_nmap_port_scanning.md)
> **Time:** ~2 hours · **Verified:** 2026-06-25 (tcpdump 4.99, attacker container)

> ⚠️ **LEGAL REMINDER:** Capture traffic only on networks you own. Capturing traffic on a shared network (corporate WiFi, etc.) without permission is illegal. All exercises in this module use the isolated lab network.

---

## Why this matters

A packet capture shows you *everything* — exactly what data is transmitted, including credentials sent over HTTP (unencrypted). It's how you understand what tools are doing under the hood and how you verify that encryption is (or isn't) protecting sensitive data.

---

## tcpdump: command-line packet capture

tcpdump is installed in the attacker container. It captures and displays packets in real time.

### Basic syntax

```bash
tcpdump [options] [filter]

-i eth0          # interface to capture on
-n               # don't resolve hostnames (faster)
-v               # verbose output
-w file.pcap     # save to a file (open with Wireshark later)
-r file.pcap     # read from a saved file
```

### Useful filters

```bash
# Capture all traffic to/from DVWA
tcpdump -i eth0 -n host 10.0.0.20

# Capture only HTTP traffic (port 80)
tcpdump -i eth0 -n port 80

# Capture HTTP and show ASCII content
tcpdump -i eth0 -n -A port 80

# Capture and save
tcpdump -i eth0 -n -w /shared/lab_capture.pcap
```

---

## Verified output: capturing a login over HTTP

**Terminal 1** (inside attacker container) — start capture:
```bash
tcpdump -i eth0 -n -A port 80
```

**Terminal 2** (host machine) — send a login:
```bash
curl -X POST http://localhost:8080/login.php \
  -d "username=admin&password=password&Login=Login"
```

**Terminal 1 shows:**
```
GET /login.php HTTP/1.1
Host: 10.0.0.20

HTTP/1.1 302 Found
Set-Cookie: PHPSESSID=abc123; path=/; HttpOnly

POST /login.php HTTP/1.1
...
username=admin&password=password&Login=Login
```

The password appears in plaintext in the packet capture — this is why HTTP (not HTTPS) is dangerous on any network where someone can run tcpdump.

---

## Save and analyse

```bash
# Save 60 seconds of traffic
timeout 60 tcpdump -i eth0 -n -w /shared/lab.pcap

# Read and filter saved file
tcpdump -r /shared/lab.pcap -n port 5000
tcpdump -r /shared/lab.pcap -n -A 'host 10.0.0.30 and port 5000'
```

The `.pcap` file in `/shared/` is also accessible from your host machine — open it in Wireshark (GUI) for easier analysis.

---

## Wireshark: GUI packet analysis

Wireshark is the GUI version of tcpdump. Install it on your host machine:
```bash
# Ubuntu/Debian
sudo apt install wireshark

# Mac
brew install --cask wireshark
```

Open `99_project_pentest_lab/shared/lab.pcap` in Wireshark.

**Key Wireshark skills:**

- **Filter bar:** `http`, `tcp.port == 5000`, `ip.addr == 10.0.0.30`
- **Follow stream:** right-click a packet → `Follow → TCP Stream` — shows the full conversation as text
- **Find credentials:** filter `http.request.method == "POST"` then inspect the packet details

---

## Recap & next

- ✅ `tcpdump -i eth0 -n -A port 80` — capture and show HTTP traffic in ASCII
- ✅ `-w file.pcap` saves captures; `-r` reads them
- ✅ HTTP passwords are visible in captures — always use HTTPS in production
- ✅ Wireshark's "Follow TCP Stream" reassembles the full conversation

**Self-check:** You capture traffic and see HTTPS (port 443) requests. Can you read the login credentials in the capture? Why or why not?

<details>
<summary>Answer</summary>

No — HTTPS encrypts the HTTP layer with TLS. tcpdump sees encrypted bytes, not the plaintext. The TLS handshake (ClientHello, ServerHello, etc.) is visible, but the HTTP request and response bodies are encrypted. To see HTTPS content, you'd need the server's private key or perform an SSL interception (man-in-the-middle) — which is what Burp Suite does when you install its certificate.

</details>

---

## Exercise

**Capture a login.** Start tcpdump capturing port 5000, then use curl to login to vuln-flask. Find the username and password in the capture output.

```bash
# Terminal 1 (attacker container)
tcpdump -i eth0 -n -A port 5000

# Terminal 2 (host machine)
curl -X POST http://localhost:5001/login \
  -H "Content-Type: application/json" \
  -d '{"username":"alice","password":"alice2024"}'
```

<details>
<summary>What you see</summary>

tcpdump shows the JSON body including `"password":"alice2024"` in plaintext. This proves that the vuln-flask app needs HTTPS to protect credentials in transit. In Section 05-07 you'll see how to configure HTTPS and the `Secure` cookie flag.

</details>

---

**Next → [03 netcat & curl](03_netcat_and_curl.md)**
