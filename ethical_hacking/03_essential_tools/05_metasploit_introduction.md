# 03-5 · Metasploit Introduction

> **Level:** Beginner · **Prerequisites:** [03-4 Burp Suite basics](04_burp_suite_basics.md)
> **Time:** ~1 hour · **Verified:** 2026-06-25 (Metasploit Framework 6.x)

> ⚠️ **LEGAL REMINDER:** Only use Metasploit against systems you own or have explicit written authorisation to test. This module covers the interface and auxiliary modules only — no exploitation of real CVEs.

---

## Why this matters

Metasploit is the most widely used exploitation framework in the world. Understanding it is required for any pentesting role — and it's tested in every major certification (OSCP, eJPT, CEH). This module teaches the interface and auxiliary scanners; full exploitation is covered in Section 04.

---

## Start Metasploit

```bash
# Inside the attacker container (Metasploit is not in the Dockerfile — install if needed)
# Or run on your Kali host machine:
msfconsole
```

You'll see the Metasploit banner and the `msf6 >` prompt.

---

## The core workflow: search, use, set, run

```
msf6 > search portscan
msf6 > use auxiliary/scanner/portscan/tcp
msf6 auxiliary(scanner/portscan/tcp) > show options
msf6 auxiliary(scanner/portscan/tcp) > set RHOSTS 10.0.0.0/24
msf6 auxiliary(scanner/portscan/tcp) > set PORTS 80,443,5000
msf6 auxiliary(scanner/portscan/tcp) > run
```

**Workflow explanation:**
1. `search` — find modules by keyword
2. `use` — load a module
3. `show options` — see what you need to configure
4. `set` — set required options (RHOSTS=target, LHOST=your IP, PORT=port, etc.)
5. `run` (or `exploit`) — execute

---

## Module types

| Type | Path prefix | Purpose |
|---|---|---|
| **Auxiliary** | `auxiliary/` | Scanners, fuzzers, information gathering — no payload |
| **Exploit** | `exploit/` | Run a CVE-based exploit against a vulnerability |
| **Payload** | `payload/` | What runs on the target after exploitation (reverse shell, meterpreter) |
| **Post** | `post/` | Post-exploitation: privilege escalation, persistence, pivoting |

**For beginners: start with auxiliary modules.** They're safe, informative, and don't require finding actual vulnerabilities.

---

## Useful auxiliary scanners (practice in the lab)

```
auxiliary/scanner/portscan/tcp         # TCP port scanner
auxiliary/scanner/http/http_version    # detect web server versions
auxiliary/scanner/http/dir_scanner     # brute-force directories
auxiliary/scanner/http/http_login      # HTTP login brute-force
auxiliary/scanner/mysql/mysql_version  # MySQL version detection
```

---

## Verified: HTTP version scan of the lab

```
msf6 > use auxiliary/scanner/http/http_version
msf6 auxiliary(scanner/http/http_version) > set RHOSTS 10.0.0.20 10.0.0.30
msf6 auxiliary(scanner/http/http_version) > run

[*] 10.0.0.20:80 Apache/2.4.57 (Debian)
[*] 10.0.0.30:5000 Werkzeug/3.0.1 Python/3.11.6
[*] Scanned 2 of 2 hosts (100% complete)
```

Same information as nmap's `-sV`, but from Metasploit's database — stored in the MSF workspace for later use.

---

## Recap & next

- ✅ `search`, `use`, `show options`, `set`, `run` — the universal Metasploit workflow
- ✅ Auxiliary modules = scanning, no exploitation; safe to run in the lab
- ✅ Module types: auxiliary (scan), exploit (attack), payload (what runs), post (after access)

**Self-check:** What is the difference between an exploit module and an auxiliary module? When would you use each?

<details>
<summary>Answer</summary>

An **exploit module** combines a vulnerability and a payload — it attacks a specific CVE and, if successful, executes code on the target (e.g., opens a reverse shell). An **auxiliary module** is just a tool: a scanner, a brute-forcer, a version detector. Use auxiliaries for information gathering; use exploits when you've identified a specific vulnerability and want to verify it. In real pentests, start with auxiliaries to map the surface, then move to targeted exploits.

</details>

---

**→ Section complete. Next: [04 Ethical Hacking Methodology](../04_ethical_hacking_methodology/README.md)**
