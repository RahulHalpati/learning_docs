# 04-2 · semgrep & custom rules

> **Level:** Intermediate · **Prerequisites:** [04-1 bandit](01_bandit.md)
> **Time:** 25 min · **Verified:** 2026-07-15 (rule syntax; semgrep is an optional install)

Where bandit ships fixed Python rules, **semgrep** lets you write rules in a
pattern language that looks like the code you're matching — across many languages.
It's the tool teams reach for when they need *custom*, org-specific rules.

> semgrep is a larger install (`pip install semgrep`) and wasn't run in the
> verified environment; the commands and rule below are standard, documented usage.

---

## Run the community rules

```bash
pip install semgrep
semgrep --config auto samples/vulnerable_app        # curated rulesets, auto-selected
semgrep --config p/python samples/vulnerable_app    # the Python ruleset
```

`--config auto` pulls maintained rulesets from the semgrep registry (OWASP, CWE
top-25, framework-specific). You get bandit-class coverage plus a lot more, with
no rules to write.

---

## The killer feature: pattern-is-code rules

A semgrep rule matches source using code with **metavariables** (`$X`). To flag
`eval` on anything:

```yaml
# eval.yml
rules:
  - id: dangerous-eval
    languages: [python]
    severity: ERROR
    message: eval() on dynamic input — arbitrary code execution (CWE-95).
    pattern: eval(...)
```

```bash
semgrep --config eval.yml samples/vulnerable_app
```

Compare that to the AST-visitor version you wrote in
[03-3](../03_static_analysis_with_ast/03_writing_detection_rules.md): semgrep's
`pattern: eval(...)` expresses the same thing as `call_name(node) == "eval"`, but
declaratively — no `NodeVisitor`, no `generic_visit`. Under the hood it's still
parsing to a tree and matching structure; you're just describing the shape instead
of coding the walk.

---

## A taint rule (source → sink, declaratively)

semgrep can express the taint analysis you hand-built, too:

```yaml
rules:
  - id: sql-injection-taint
    languages: [python]
    severity: ERROR
    message: User input reaches execute() — SQL injection (CWE-89).
    mode: taint
    pattern-sources:
      - pattern: flask.request.$ANY
    pattern-sinks:
      - pattern: $CURSOR.execute(...)
```

That's your entire `taint.py` — sources, sinks, propagation — in a dozen lines,
maintained by someone else. Writing your own first is what makes this readable
rather than magical.

---

## When to use which

| Need | Reach for |
|---|---|
| Fast, zero-config Python security scan | **bandit** |
| Custom / org-specific rules, multi-language, taint | **semgrep** |
| Deep interprocedural analysis, security research | **CodeQL** |
| Understanding *how they work* / a tiny embeddable check | **your `codeaudit`** |

---

## Recap & next

- ✅ **semgrep** matches with **code-like patterns + metavariables** (`$X`), across
  languages — declarative versions of your AST rules.
- ✅ Its **`mode: taint`** expresses source→sink flow in a few lines — the same idea
  as your `taint.py`.
- ✅ Use **bandit** for quick Python scans, **semgrep** for custom/multi-language
  rules, **CodeQL** for deep analysis.

## Exercise

Write a semgrep rule that flags `subprocess.*(..., shell=True)` (your CA102).
Match the keyword argument.

<details>
<summary>Solution</summary>

```yaml
rules:
  - id: subprocess-shell-true
    languages: [python]
    severity: ERROR
    message: subprocess with shell=True — command injection (CWE-78).
    patterns:
      - pattern: subprocess.$FN(..., shell=True, ...)
```

`--config` it against `samples/vulnerable_app`; it should hit the `/ping`
`check_output(..., shell=True)` line.

</details>

**→ Next: [04-3 · Dependency scanning (SCA)](03_dependency_scanning_sca.md)**
