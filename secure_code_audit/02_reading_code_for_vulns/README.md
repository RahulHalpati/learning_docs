# 02 · Reading code for vulnerabilities (manual review)

The durable skill: finding bugs with your eyes. Tools automate the patterns you
learn here — but the logic flaws only a human can see start here too. Every module
audits real code from the bundled sample app.

| # | Module | Vulnerability classes |
|---|---|---|
| 02-1 | [The review workflow](01_the_review_workflow.md) | How to approach a codebase cold |
| 02-2 | [Injection](02_injection.md) | SQL (CWE-89), command (CWE-78), code (CWE-95) |
| 02-3 | [XSS, SSTI & output](03_xss_ssti_and_output.md) | XSS (CWE-79), SSTI (CWE-1336) |
| 02-4 | [Auth, secrets & crypto](04_auth_secrets_crypto.md) | Secrets (CWE-798), weak crypto (CWE-327) |
| 02-5 | [Traversal, SSRF & deserialization](05_traversal_ssrf_deser.md) | CWE-22, CWE-918, CWE-502 |
| 02-6 | [Access control & IDOR](06_access_control_idor.md) | Broken access control (CWE-284/639) |

**Next → [02-1 · The review workflow](01_the_review_workflow.md)**
