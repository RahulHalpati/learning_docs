# 04-6 · Reporting & Remediation

> **Level:** Beginner · **Prerequisites:** [04-5 Post-exploitation & pivoting](05_post_exploitation_and_pivoting.md)
> **Time:** ~30 min · **Verified:** 2026-06-25 (concept module)

---

## Why this matters

A vulnerability that isn't reported doesn't exist to the client. Your hacking is only as valuable as your ability to communicate what you found, how bad it is, and how to fix it. Many good pentesters lose clients because they can't write clearly. The report IS the deliverable.

---

## Pentest report structure

A professional report has these sections:

1. **Executive Summary** — 1-2 pages, non-technical, for management. What you tested, overall risk level, 3-5 key findings in plain English.

2. **Scope and methodology** — What was tested, what wasn't, what techniques were used, testing dates.

3. **Findings** — One entry per vulnerability, in CVSS order (Critical → High → Medium → Low → Informational).

4. **Remediation roadmap** — Prioritised fix list with effort estimates.

5. **Appendices** — Full tool output, screenshots, raw evidence.

---

## Writing a finding

Each finding follows this template:

```
Title: SQL Injection in /login endpoint
Severity: Critical (CVSS 9.8)
Affected component: vuln-flask /login (POST)
Description:
  The login endpoint constructs SQL queries using string concatenation with
  user-supplied input. This allows an attacker to bypass authentication by
  injecting SQL syntax into the username field.

Proof of concept:
  POST /login HTTP/1.1
  Content-Type: application/json
  {"username": "' OR '1'='1' --", "password": "x"}

  Response: {"message": "Login successful", "role": "admin"}

Impact:
  Complete authentication bypass. An unauthenticated attacker can log in
  as any user, including administrators. The attacker can then access all
  user data and administrative functions.

Remediation:
  Replace string concatenation with parameterised queries:
  conn.execute("SELECT * FROM users WHERE username=? AND password=?", (user, pw_hash))

References: CWE-89, OWASP A03:2021
```

---

## CVSS scoring basics

CVSS v3.1 scores three dimensions:

| Metric | Options | High-score scenario |
|---|---|---|
| **Attack Vector** | Network / Adjacent / Local / Physical | Network (remote, internet-facing) |
| **Attack Complexity** | Low / High | Low (no special conditions) |
| **Privileges Required** | None / Low / High | None (unauthenticated) |
| **User Interaction** | None / Required | None |
| **Scope** | Unchanged / Changed | Changed (affects other systems) |
| **Impact (C/I/A)** | None / Low / High | High/High/High |

The SQL injection above scores 9.8 Critical: Network, Low complexity, No privileges, No interaction, High C/I/A.

Use the calculator at [nvd.nist.gov/vuln-metrics/cvss/v3-calculator](https://nvd.nist.gov/vuln-metrics/cvss/v3-calculator).

---

## Recap

- ✅ Report structure: Executive Summary → Scope → Findings → Remediation → Appendices
- ✅ Each finding: title, severity, description, PoC, impact, fix, references
- ✅ CVSS 0–10: Critical (9+), High (7–8.9), Medium (4–6.9), Low (0.1–3.9)
- ✅ The report is your deliverable — write clearly for both technical and non-technical readers

**→ Section complete. Next: [05 Web Application Security](../05_web_application_security/README.md)**
