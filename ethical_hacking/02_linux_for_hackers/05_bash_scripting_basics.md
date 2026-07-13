# 02-5 · Bash Scripting Basics

> **Level:** Beginner · **Prerequisites:** [02-4 Process & service management](04_process_and_service_management.md)
> **Time:** ~1.5 hours · **Verified:** 2026-06-25

> ⚠️ **LEGAL REMINDER:** Run all scripts against the lab network only.

---

## Why this matters

As a Python developer you already know how to write scripts. Bash scripting lets you automate recon and repetitive tasks at the shell level — no imports, no virtual environments, just run it. Most CTF challenges and real pentests involve writing small bash scripts to automate scanning, extract data, or chain tools together.

---

## Variables, conditionals, loops

```bash
#!/bin/bash
# recon.sh — scan a host and save results

TARGET="10.0.0.20"
OUTPUT_DIR="/shared/recon"

mkdir -p "$OUTPUT_DIR"

echo "Scanning $TARGET..."
nmap -sV -T4 "$TARGET" -oN "$OUTPUT_DIR/nmap_$TARGET.txt"
echo "Done. Results in $OUTPUT_DIR/nmap_$TARGET.txt"
```

Run it:
```bash
chmod +x recon.sh
./recon.sh
```

### Conditionals

```bash
if ping -c 1 10.0.0.20 &>/dev/null; then
    echo "Host is up"
else
    echo "Host is down"
fi
```

### Loops

```bash
# Scan a range of hosts
for ip in 10.0.0.{10..40}; do
    if ping -c 1 -W 1 "$ip" &>/dev/null; then
        echo "$ip is up"
    fi
done
```

---

## Your first recon script

```bash
#!/bin/bash
# quick_recon.sh — mini pentest toolkit

TARGET=${1:-"10.0.0.20"}   # use first argument, default to DVWA
OUTDIR="/shared/$(echo $TARGET | tr '.' '_')"
mkdir -p "$OUTDIR"

echo "[*] Quick recon of $TARGET"
echo "[*] Results → $OUTDIR"

# 1. Ping check
if ping -c 2 -W 1 "$TARGET" &>/dev/null; then
    echo "[+] Host is up"
else
    echo "[-] Host is down — exiting"
    exit 1
fi

# 2. Port scan
echo "[*] Running nmap..."
nmap -sV -T4 --top-ports 100 "$TARGET" -oN "$OUTDIR/ports.txt"

# 3. HTTP banner if port 80 is open
if grep -q "80/tcp.*open" "$OUTDIR/ports.txt"; then
    echo "[*] Port 80 open — grabbing HTTP headers"
    curl -sI "http://$TARGET/" > "$OUTDIR/http_headers.txt"
    echo "[+] HTTP headers saved"
fi

echo "[+] Recon complete. Check $OUTDIR/"
```

Run it against both lab targets:
```bash
chmod +x quick_recon.sh
./quick_recon.sh 10.0.0.20
./quick_recon.sh 10.0.0.30:5000
```

---

## Recap & next

- ✅ Variables: `NAME="value"` — quote always to handle spaces
- ✅ Conditionals: `if command; then ... fi` — tests exit code (0=success)
- ✅ Loops: `for x in list; do ... done` — brace expansion `{1..10}` generates ranges
- ✅ `$1` is the first argument; `${1:-default}` provides a fallback

**Self-check:** Your script needs to try all ports from 8000 to 8100 on a target with curl. Write the one-liner.

<details>
<summary>Answer</summary>

```bash
for port in {8000..8100}; do
    curl -s -o /dev/null -w "%{http_code} $port\n" "http://10.0.0.30:$port/" 2>/dev/null | grep -v "^000"
done
```

`-w "%{http_code}"` prints the HTTP status code. `-o /dev/null` discards the response body. Filtering `000` removes timeouts (connection refused).

</details>

---

## Exercise

Write a script `host_sweep.sh` that takes a /24 network (e.g. `10.0.0`) as an argument and prints all live hosts. Save results to `/shared/live_hosts.txt`.

<details>
<summary>Solution</summary>

```bash
#!/bin/bash
NETWORK=${1:-"10.0.0"}
OUTPUT="/shared/live_hosts.txt"
> "$OUTPUT"   # clear the file

echo "[*] Sweeping $NETWORK.0/24..."

for i in $(seq 1 254); do
    ip="$NETWORK.$i"
    if ping -c 1 -W 1 "$ip" &>/dev/null; then
        echo "$ip" | tee -a "$OUTPUT"
    fi
done

echo "[+] Found $(wc -l < $OUTPUT) live hosts. Results in $OUTPUT"
```

Usage: `./host_sweep.sh 10.0.0`

</details>

---

**→ Section complete. Next: [03 Essential Tools](../03_essential_tools/README.md)**
