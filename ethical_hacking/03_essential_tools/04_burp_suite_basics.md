# 03-4 · Burp Suite Basics

> **Level:** Beginner · **Prerequisites:** [03-3 netcat & curl](03_netcat_and_curl.md)
> **Time:** ~1.5 hours · **Verified:** 2026-06-25 (Burp Suite Community 2024.x)

> ⚠️ **LEGAL REMINDER:** Configure Burp's browser proxy to point only at the local lab. Never route production traffic through Burp without a signed scope agreement.

---

## Why this matters

Burp Suite is the web pentester's primary tool. It sits between your browser and the web app, intercepting every HTTP request so you can inspect, modify, and replay them. Manual SQL injection, XSS testing, authentication bypass — all done through Burp.

---

## Setup: install Burp Community

Download from [portswigger.net/burp/communitydownload](https://portswigger.net/burp/communitydownload) — free, runs on Linux, Mac, Windows.

```bash
# On your host machine
java -jar burpsuite_community_v*.jar
```

Or use the installer they provide.

---

## Proxy setup

Burp runs a proxy on `127.0.0.1:8080` by default. Configure your browser to use it:

**Firefox:** Settings → Network Settings → Manual proxy → HTTP Proxy: `127.0.0.1:8080`

**Or use Burp's built-in browser** (Proxy tab → Open Browser) — pre-configured, no setup needed.

Then visit `http://localhost:8080` (DVWA) in the proxied browser — all requests appear in Burp's **Proxy → Intercept** tab.

---

## The four Burp tools you need

### 1. Proxy — Intercept & modify requests

Every request pauses in Burp. You see the raw HTTP, can modify it (change a parameter, add a header, inject a payload), then forward it.

```
POST /login.php HTTP/1.1
Host: localhost:8080
Content-Type: application/x-www-form-urlencoded

username=admin&password=wrong&Login=Login
```

Change `password=wrong` to `password=password` and forward — you bypassed the login.

### 2. Repeater — Replay and iterate requests

Right-click any intercepted request → **Send to Repeater**. Now you can modify and resend the request as many times as you want, comparing responses. This is how you:
- Test different SQL injection payloads
- Fuzz parameter values
- Test for IDOR by changing an ID

### 3. Intruder — Automated fuzzing

Mark one or more positions in a request with `§markers§`, then supply a wordlist. Intruder iterates through all values and shows you the responses. Common uses:
- Brute-force login (username + password wordlists)
- Find hidden parameters or endpoints
- Enumerate user IDs (IDOR discovery)

> Note: In Community edition, Intruder is rate-limited (slow). Use hydra for brute-forcing instead.

### 4. Target → Site map

Burp builds a map of every host, path, and parameter it sees as you browse. Gives you a quick overview of the application's attack surface.

---

## Practical: intercept a DVWA login

1. Start the lab: `docker compose up -d` in `99_project_pentest_lab/`
2. Open Burp, start Burp's browser
3. Navigate to `http://localhost:8080`
4. Enable Intercept in Proxy tab
5. Submit the DVWA login form (admin/password)
6. Observe the raw POST request in Burp
7. Send to Repeater, change the password, observe the response

The goal: understand that EVERY form field, cookie, and header is modifiable. The server trusts nothing — you trust nothing.

---

## Recap & next

- ✅ Burp proxy: sits between browser and app, intercepts every request
- ✅ Repeater: modify and resend requests — essential for manual testing
- ✅ Intruder: automated fuzzing with wordlists (Community rate-limited)
- ✅ Site map: automatic attack surface enumeration as you browse

**Self-check:** You're testing a web app and notice a request like `GET /profile?id=42`. How would you use Burp Repeater to test for IDOR?

<details>
<summary>Answer</summary>

Intercept the request, send to Repeater. In Repeater, change `id=42` to `id=1`, `id=2`, etc. and send each. If the server returns other users' profiles without checking that you own ID 1 or 2, that's IDOR. Compare the response body — different `username` / `email` values with different IDs confirms the vulnerability.

</details>

---

**Next → [05 Metasploit introduction](05_metasploit_introduction.md)**
