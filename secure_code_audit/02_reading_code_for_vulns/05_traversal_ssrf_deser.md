# 02-5 · Path traversal, SSRF & deserialization

> **Level:** Beginner · **Prerequisites:** [02-4 Auth, secrets & crypto](04_auth_secrets_crypto.md)
> **Time:** 25 min · **Verified:** 2026-07-15

Three more source→sink flows. Each is safe with trusted input and dangerous with
user-controlled input — so each needs the [taint](../01_foundations/04_data_flow_and_taint.md)
lens.

---

## Path traversal (CWE-22)

The shape: user data in a filesystem path.

```python
# VULNERABLE
name = request.args.get("name")
with open("/var/data/" + name) as fh:    # name reaches open()
    return fh.read()
```

`name = ../../etc/passwd` escapes `/var/data/` and reads any file. Tell: user data
concatenated into a path passed to `open`, `send_file`, `os.remove`, etc.

**The fix — resolve and confine to a base directory:**

```python
from pathlib import Path
base = Path("/var/data").resolve()
target = (base / name).resolve()
if base not in target.parents and target != base:
    abort(403)                       # refuse anything outside base
return target.read_text()
```

Normalise first (`resolve()` collapses `..`), then verify the result is still under
`base`. Better yet, look the file up by an **id in an allow-list**, not by a
user-supplied name.

---

## Server-side request forgery (SSRF, CWE-918)

The shape: user controls the URL of an outbound request.

```python
# VULNERABLE
url = request.args.get("url")
return requests.get(url).text     # server fetches whatever the user names
```

The attacker makes *your server* the client: `url=http://169.254.169.254/…`
reaches cloud metadata (credentials!); `url=http://localhost:6379` hits internal
services behind your firewall. Tell: a user-influenced value in `requests.*`,
`urlopen`, an HTTP client, or a webhook fetch.

**The fix — allow-list, don't block-list:**

```python
from urllib.parse import urlparse
ALLOWED = {"api.partner.com", "cdn.example.com"}
host = urlparse(url).hostname
if host not in ALLOWED:
    abort(400)
```

Validate the **resolved host** against an allow-list, forbid internal ranges and
redirects. Block-lists (“reject 169.254.*”) are bypassable; allow-lists aren't.

---

## Insecure deserialization (CWE-502)

The shape: turning untrusted bytes back into objects with an unsafe loader.

```python
# VULNERABLE
obj = pickle.loads(request.get_data())        # pickle can construct ANY object → RCE
cfg = yaml.load(request.args.get("cfg"))       # yaml.load (no SafeLoader) can too
```

`pickle` and full-fat `yaml.load` can instantiate arbitrary classes and run code
during loading — a crafted payload = remote code execution. Tells: `pickle.loads`,
`yaml.load` without `SafeLoader`, `marshal`, `jsonpickle` on untrusted data.

**The fix — a safe format / loader:**

```python
import json, yaml
data = json.loads(raw)                 # JSON can't execute code
cfg = yaml.safe_load(text)             # safe_load builds only basic types
```

Prefer data-only formats (JSON) for untrusted input; if you must use YAML, use
`safe_load`. Never `pickle` data that crossed a trust boundary.

---

## Recap & next

- ✅ **Path traversal**: user path → `open()`; fix by `resolve()`-and-confine or an
  id allow-list.
- ✅ **SSRF**: user URL → outbound request; fix with a host **allow-list**, block
  internal ranges.
- ✅ **Insecure deserialization**: `pickle`/`yaml.load` on untrusted bytes → RCE;
  use **JSON / `safe_load`**.

## Exercise

The `/read` endpoint does `open("/var/data/" + name)`. A teammate "fixes" it with
`name = name.replace("../", "")`. Why is that still bypassable?

<details>
<summary>Solution</summary>

A single non-recursive `replace` is trivially bypassed — e.g. `....//` becomes
`../` after one removal, or absolute paths / encoded variants slip through. The
robust fix is to **normalise then verify containment** (`Path(base / name).resolve()`
must stay under `base`), or avoid user-supplied paths entirely with an
id → filename allow-list.

</details>

**→ Next: [02-6 · Access control & IDOR](06_access_control_idor.md)**
