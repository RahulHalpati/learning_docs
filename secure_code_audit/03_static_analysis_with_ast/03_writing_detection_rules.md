# 03-3 · Writing detection rules

> **Level:** Beginner · **Prerequisites:** [03-2 AST basics](02_ast_basics.md)
> **Time:** 30 min · **Verified:** 2026-07-15

Now the payoff: turn the AST primitives into real rules. This is
[`codeaudit/rules.py`](../99_project_codeaudit/codeaudit/rules.py) — read it
alongside this module.

---

## The Finding and the Rule base

Every detection produces a `Finding` ([`finding.py`](../99_project_codeaudit/codeaudit/finding.py)):

```python
@dataclass
class Finding:
    rule_id: str      # "CA101"
    severity: str     # critical | high | medium | low | info
    message: str
    file: str
    line: int
    snippet: str = ""
    cwe: str = ""
```

Rules subclass a small base that's a `NodeVisitor` plus a `report()` helper that
grabs the source line for the snippet:

```python
class Rule(ast.NodeVisitor):
    id = ""; severity = "medium"; cwe = ""

    def __init__(self, filename, source_lines):
        self.filename = filename
        self.lines = source_lines
        self.findings = []

    def report(self, node, message):
        line = getattr(node, "lineno", 0)
        snippet = self.lines[line - 1].strip() if 0 < line <= len(self.lines) else ""
        self.findings.append(
            Finding(self.id, self.severity, message, self.filename, line, snippet, self.cwe))
```

---

## A rule is a class with a `visit_` method

The whole "dangerous call" rule — `eval`, `exec`, `os.system`:

```python
class DangerousCallRule(Rule):
    id, severity, cwe = "CA101", "critical", "CWE-95"
    _NAMES = {"eval", "exec", "os.system"}

    def visit_Call(self, node):
        if call_name(node) in self._NAMES:
            self.report(node, f"Dangerous call to `{call_name(node)}()` — arbitrary code/command execution risk.")
        self.generic_visit(node)
```

That's it. Match the shape, call `report`, keep descending. Each other rule is the
same idea:

| Rule | id | Matches |
|---|---|---|
| `DangerousCallRule` | CA101 | `call_name` in {eval, exec, os.system} |
| `ShellTrueRule` | CA102 | `subprocess.*` **and** `keyword_is_true(node, "shell")` |
| `WeakHashRule` | CA103 | `call_name` in {hashlib.md5, hashlib.sha1, …} |
| `InsecureDeserializationRule` | CA104 | `pickle.loads`; or `yaml.load` without a Safe loader kwarg |
| `FlaskDebugRule` | CA105 | a `.run(...)` call with `debug=True` |
| `HardcodedSecretRule` | CA106 | `visit_Assign`: string literal → a secret-y name |
| `SqlStringBuildRule` | CA107 | `.execute(<f-string / concat / .format>)` |

---

## Two rules that read a different node type

Not every rule visits `Call`. **Hardcoded secrets** visit assignments:

```python
class HardcodedSecretRule(Rule):
    id, severity, cwe = "CA106", "medium", "CWE-798"
    _NAMES = ("password", "secret", "secret_key", "api_key", "token", ...)

    def visit_Assign(self, node):
        if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
            for target in node.targets:
                name = target.id if isinstance(target, ast.Name) else getattr(target, "attr", "")
                if any(k in name.lower() for k in self._NAMES) and len(node.value.value) >= 4:
                    self.report(node, f"Hardcoded secret in `{name}` — move it to an environment variable.")
        self.generic_visit(node)
```

And **SQL string building** inspects the *shape of the argument* to `.execute`:

```python
@staticmethod
def _is_built_string(node):
    if isinstance(node, ast.JoinedStr):                                   # f"...{x}..."
        return True
    if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Mod)):  # "..." + x / "..." % x
        return True
    if isinstance(node, ast.Call) and call_name(node).endswith("format"): # "...".format(x)
        return True
    return False
```

---

## The extension model: append to `ALL_RULES`

The scanner runs every class in one list:

```python
ALL_RULES = [DangerousCallRule, ShellTrueRule, WeakHashRule,
             InsecureDeserializationRule, FlaskDebugRule,
             HardcodedSecretRule, SqlStringBuildRule]
```

Adding a rule = write a `Rule` subclass, append it here. The scanner
([`scanner.py`](../99_project_codeaudit/codeaudit/scanner.py)) instantiates each per
file and collects the findings:

```python
for rule_cls in ALL_RULES:
    rule = rule_cls(filename, lines)
    rule.visit(tree)
    findings.extend(rule.findings)
```

Run it and see all seven fire on the sample app:

```bash
python -m codeaudit.cli samples/vulnerable_app --min-severity high
# 🟠 HIGH CA102 ... shell=True ...
# 🟠 HIGH CA107 ... SQL built with string formatting ...
# ...
```

---

## Recap & next

- ✅ A rule is a `Rule` subclass with a `visit_<Node>` method that calls `report()`.
- ✅ Most visit `Call`; some visit `Assign` (secrets) or inspect an **argument's
  shape** (SQL building).
- ✅ Register a rule by appending it to **`ALL_RULES`** — that's the whole
  extension model.

## Exercise

Write rule **CA108** that flags `requests.get(..., verify=False)` (disabled TLS
verification, CWE-295). Add it to `ALL_RULES` and test it.

<details>
<summary>Solution</summary>

```python
class TlsVerifyOffRule(Rule):
    id, severity, cwe = "CA108", "medium", "CWE-295"
    def visit_Call(self, node):
        name = call_name(node)
        if name.startswith("requests.") and _keyword_is_false(node, "verify"):
            self.report(node, "TLS verification disabled (verify=False) — MITM risk.")
        self.generic_visit(node)
```

where `_keyword_is_false` mirrors `keyword_is_true` but checks `value is False`.
Append `TlsVerifyOffRule` to `ALL_RULES`; test with
`scan_source("import requests\nrequests.get(u, verify=False)")` → expect `CA108`.

</details>

**→ Next: [03-4 · Simple taint tracking](04_simple_taint_tracking.md)**
