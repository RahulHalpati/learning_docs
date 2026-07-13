# 06-5 · Home Test — Prove You've Got It

> **Level:** Beginner → Intermediate · **Prerequisites:** Sections 01–05 + the [Capstone Lab](../99_project_pentest_lab/README.md) running
> **Time:** ~3 h · **Verified:** 2026-06-25

---

## Why this matters

Reading and following along feels like learning. Doing it **cold, from memory, against a live target** is learning. This is a self-graded exam you run at home against your own lab — the same shape as an eJPT-style practical: you get objectives, you find the answers yourself, and you grade against the key at the bottom.

> ⚠️ **LEGAL REMINDER:** Every task below targets the local lab (`10.0.0.0/24`) only. Start it first:
> ```bash
> cd ../99_project_pentest_lab && docker compose up -d
> docker compose exec attacker bash
> ```

**Rules:** no peeking at earlier modules until you've attempted each task. Give yourself the time limit shown. Write your answers in a file (`home_test_answers.md`) — that habit *is* the job.

---

## Part A · Concepts (no lab needed) — 20 min

Answer from memory. 1 point each, 10 points.

1. A friend finds a serious bug on a company's site, reports it to them for free without asking first. Which hat is this, and is it legal?
2. Name the five broad ways vulnerabilities get detected. Which one is your strongest given your background, and why?
3. What single condition legally separates a white hat from a black hat?
4. Which OSI layer does a firewall filtering by port number operate at? Which layer does Burp Suite operate at?
5. What does a TCP three-way handshake look like (the three packets)?
6. In `10.0.0.0/24`, how many usable host addresses are there, and what is the broadcast address?
7. What is the difference between SAST and DAST?
8. Explain the difference between reflected and stored XSS in one sentence each.
9. What is IDOR, and why does adding a login page *not* fix it?
10. In a pentest report, name the three things every finding must contain.

---

## Part B · Reconnaissance & scanning — 30 min

Target: the whole lab network. 15 points.

1. **(3 pts)** From the attacker box, discover every live host on `10.0.0.0/24`. List their IPs. What command did you use?
2. **(4 pts)** Full service+version scan of the DVWA host (`10.0.0.20`). What ports are open, what service and version runs on each?
3. **(3 pts)** Scan `vuln-flask` (`10.0.0.30`). What port is the app on, and what does the HTTP server header reveal?
4. **(3 pts)** Which host runs MySQL? Is its port reachable *from the attacker box*? Explain what your scan result means about the DB's exposure.
5. **(2 pts)** Save your scan of `10.0.0.20` to a file in a format you could paste into a report.

---

## Part C · Web exploitation — 60 min

Targets: DVWA (`http://10.0.0.20`) and vuln-flask (`http://10.0.0.30:5000`). 25 points.

1. **(5 pts)** Set DVWA security to **low**. Find the SQL injection input. Extract the list of usernames and password hashes from the database. Paste your injection payload.
2. **(4 pts)** Crack at least one of the hashes you extracted. What tool did you use and what is one plaintext password?
3. **(4 pts)** Trigger a **reflected XSS** on DVWA that pops an alert box. Paste the exact payload and the parameter it went into.
4. **(4 pts)** Trigger a **stored XSS** that fires for *any* visitor to the page. Where is it stored?
5. **(5 pts)** In vuln-flask, find one access-control flaw (IDOR or missing auth check). Describe how you access data you shouldn't, with the exact request.
6. **(3 pts)** Automate the DVWA SQLi with `sqlmap` — dump the `users` table. Paste the command.

---

## Part D · The deliverable — 40 min

25 points. **This part is worth as much as all the hacking — that's deliberate.** Anyone can run sqlmap; companies pay for the writeup.

Write a **one-page pentest report** covering your three best findings from Parts B/C. Each finding must have:

- **Title & severity** (Critical / High / Medium / Low — justify it)
- **Affected asset** (host + endpoint)
- **Description** — what the flaw is, in plain English a manager understands
- **Steps to reproduce** — numbered, copy-pasteable, so a developer can confirm it
- **Impact** — what an attacker actually gains
- **Remediation** — the specific fix (not "sanitise inputs" — say *how*)

Model it on [Section 04-6 Reporting](../04_ethical_hacking_methodology/06_reporting_and_remediation.md) and the [capstone report](../99_project_pentest_lab/07_full_pentest_report.md).

---

## Scoring

| Range | Verdict |
|---|---|
| **90–100** | You're ready to attempt **eJPT** and start CTFs seriously. |
| **70–89** | Solid. Re-do the parts you lost points on, then start [TryHackMe Jr Pentester](03_career_paths.md#the-realistic-12-month-plan). |
| **50–69** | Foundations are there but shaky. Replay Sections 03 & 05 hands-on. |
| **< 50** | Don't be discouraged — go back and *run every command yourself* this time. That's the whole difference. |

Grade Part D hardest on yourself: **could a stranger reproduce your finding from your writeup alone?** If not, it wouldn't get paid in the real world.

---

## Answer key (no peeking)

<details>
<summary>Click to reveal — attempt everything first</summary>

**Part A**
1. Grey hat — illegal. No prior authorisation, regardless of good intent.
2. Manual testing, DAST, SAST, SCA, fuzzing. Code review / SAST is strongest for a Python dev — you read source fluently.
3. Explicit written authorisation for a defined scope.
4. Port-filtering firewall = Layer 4 (Transport). Burp = Layer 7 (Application).
5. SYN → SYN-ACK → ACK.
6. 254 usable hosts (`.1`–`.254`); broadcast is `10.0.0.255`.
7. SAST reads static source code for dangerous patterns; DAST attacks the running application from the outside.
8. Reflected: payload is in the request and echoed straight back in the response (needs a victim to click a crafted link). Stored: payload is saved server-side and served to every later visitor.
9. Insecure Direct Object Reference — the app trusts a user-supplied ID (`/account?id=123`) without checking you own it. A login proves *who* you are (authentication); IDOR is a failure to check *what you're allowed to see* (authorisation) — so being logged in doesn't help.
10. Steps to reproduce, impact, remediation (plus a severity rating).

**Part B**
1. `nmap -sn 10.0.0.0/24` → `.10` (you), `.20` dvwa, `.30` vuln-flask, `.40` db.
2. `nmap -sV 10.0.0.20` → 80/tcp Apache + PHP (DVWA).
3. `nmap -sV 10.0.0.30` → 5000/tcp, server header reveals Werkzeug/Python (Flask dev server).
4. `10.0.0.40` runs MySQL 3306. It's reachable from the attacker box on the lab network but **not published to the host** — in a real network you'd flag that the DB shouldn't be reachable from a web-tier attacker foothold.
5. `nmap -sV -oN dvwa_scan.txt 10.0.0.20` (`-oN` normal, `-oA` for all formats).

**Part C**
1. In DVWA SQLi box: `1' OR '1'='1' UNION SELECT user, password FROM users-- -`.
2. `hashcat` or `john` against the MD5 hashes → e.g. `admin:password`, `gordonb:abc123` (DVWA defaults).
3. XSS-reflected box: `<script>alert(1)</script>` in the `name` parameter.
4. XSS-stored guestbook: `<script>alert(document.cookie)</script>` — stored in the message table, fires for every viewer.
5. vuln-flask: change an `id`/`user` parameter to another value and read another user's data, or hit an endpoint with no auth check. Exact request depends on your build — see [04_vuln_flask_attacks](../99_project_pentest_lab/04_vuln_flask_attacks.md).
6. `sqlmap -u "http://10.0.0.20/vulnerabilities/sqli/?id=1&Submit=Submit" --cookie="PHPSESSID=...; security=low" --dump -T users`.

**Part D** — self-graded against the reproducibility test above.

</details>

---

## Recap & next

- ✅ You ran a full recon → exploit → report cycle cold, from memory
- ✅ You graded your own writeup on the standard that actually matters: reproducibility
- ✅ If you scored 70+, you're ready for real CTFs and eJPT prep

**→ Next: [06 The future of this field](06_future_of_the_field.md)**
