# Section 05 · Web Application Security

> The deepest section and the one most relevant to real-world work. Web apps are the #1
> attack surface in modern pentesting. Every module here includes hands-on exercises
> against the local lab (DVWA + vuln-flask).

> ⚠️ **LEGAL REMINDER:** All exercises target the local Docker lab only. Never test against live applications without written permission and a defined scope.

| Module | What you'll learn | Time |
|---|---|---|
| [01 How web apps work](01_how_web_apps_work.md) | Front-end/back-end, HTTP flow, cookies, sessions, same-origin policy | ~1 h |
| [02 OWASP Top 10 overview](02_owasp_top_10_overview.md) | All 10 categories, real CVEs, which ones you'll practice | ~1.5 h |
| [03 SQL injection](03_sql_injection.md) | Manual SQLi, sqlmap, blind SQLi, parameterised query fix — against vuln-flask | ~2 h |
| [04 Cross-site scripting (XSS)](04_cross_site_scripting_xss.md) | Reflected, stored, DOM-based; cookie theft demo; CSP fix — against DVWA | ~1.5 h |
| [05 Authentication attacks](05_authentication_attacks.md) | Default creds, hydra brute-force, session fixation — against both targets | ~1.5 h |
| [06 IDOR & access control](06_idor_and_access_control.md) | Forced browsing, IDOR, parameter tampering — against vuln-flask | ~1 h |
| [07 Security headers & TLS](07_security_headers_and_tls.md) | HSTS, CSP, X-Frame-Options, mixed content — nikto + Burp verification | ~1.5 h |

**→ Start: [01 How web apps work](01_how_web_apps_work.md)**
