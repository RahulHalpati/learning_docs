# 03-2 · AST basics

> **Level:** Beginner · **Prerequisites:** [03-1 How SAST works](01_how_sast_works.md)
> **Time:** 25 min · **Verified:** 2026-07-15 (Python 3.10.12)

Time to touch the tree. The `ast` module turns source into nodes you can inspect —
this is the raw material every rule works on.

---

## Parse and look

```python
import ast

tree = ast.parse("eval(x)")
print(ast.dump(tree, indent=2))
```

Real output:

```
Module(
  body=[
    Expr(
      value=Call(
        func=Name(id='eval', ctx=Load()),
        args=[Name(id='x', ctx=Load())],
        keywords=[]))],
  type_ignores=[])
```

Read it top-down: a `Module` contains an `Expr` (an expression statement), whose
`value` is a `Call`. The call's `func` is `Name(id='eval')` and its `args` are
`[Name(id='x')]`. **That structure is exactly what a rule matches.**

> Tip: keep [Python AST docs](https://docs.python.org/3/library/ast.html) or the
> `ast.dump` output open while writing rules — you match what you see there.

---

## Walk the tree with NodeVisitor

`ast.NodeVisitor` walks every node; define `visit_<NodeType>` to handle a kind of
node. To find every function call:

```python
import ast

class CallFinder(ast.NodeVisitor):
    def visit_Call(self, node):
        # node.func is what's being called; node.lineno is where
        print("call at line", node.lineno, "->", ast.dump(node.func))
        self.generic_visit(node)     # keep descending into children!

CallFinder().visit(ast.parse("print(eval(x))"))
```

**The one gotcha:** always call `self.generic_visit(node)` (or the walker stops at
that node and misses nested calls — here, the `eval` inside `print(...)`).

---

## Naming the callee

Rules constantly ask "what is being called?" A call's `func` is a `Name`
(`eval`) or an `Attribute` (`os.system`, `hashlib.md5`). Your tool has one helper
that flattens either into a dotted string — this is straight from
[`codeaudit/rules.py`](../99_project_codeaudit/codeaudit/rules.py):

```python
def call_name(node: ast.Call) -> str:
    func = node.func
    parts = []
    while isinstance(func, ast.Attribute):   # os.system → walk .system then .os
        parts.append(func.attr)
        func = func.value
    if isinstance(func, ast.Name):
        parts.append(func.id)
    return ".".join(reversed(parts))
```

| Code | `call_name` returns |
|---|---|
| `eval(x)` | `"eval"` |
| `os.system(x)` | `"os.system"` |
| `hashlib.md5(x)` | `"hashlib.md5"` |
| `cur.execute(q)` | `"execute"` (receiver is a variable → just the method) |

Now a rule is trivial: `if call_name(node) == "eval": report(...)`.

---

## Line numbers and keywords

Two more things rules need, both on the node:

- **`node.lineno`** — 1-based line, for the finding location and the code snippet.
- **`node.keywords`** — the `kwarg=value` pairs. To check `shell=True`:

```python
def keyword_is_true(call, name):
    for kw in call.keywords:
        if kw.arg == name and isinstance(kw.value, ast.Constant) and kw.value.value is True:
            return True
    return False
```

That's every AST primitive the whole tool uses. The rules in 03-3 are just these
pieces combined.

---

## Recap & next

- ✅ `ast.parse(src)` → a tree; `ast.dump()` shows its shape (match what you see).
- ✅ `ast.NodeVisitor` + `visit_Call` walks nodes — **always `generic_visit`** to
  recurse.
- ✅ `call_name()` flattens `Name`/`Attribute` to a dotted string; `node.lineno`
  and `node.keywords` give location and kwargs.

## Exercise

Write a NodeVisitor that prints the name and line of every function *defined* in a
file (hint: `visit_FunctionDef`, `node.name`).

<details>
<summary>Solution</summary>

```python
import ast

class DefFinder(ast.NodeVisitor):
    def visit_FunctionDef(self, node):
        print(f"{node.lineno}: def {node.name}")
        self.generic_visit(node)

DefFinder().visit(ast.parse(open("samples/vulnerable_app/app.py").read()))
```

Prints each route handler (`login`, `search`, `ping`, …) with its line number.

</details>

**→ Next: [03-3 · Writing detection rules](03_writing_detection_rules.md)**
