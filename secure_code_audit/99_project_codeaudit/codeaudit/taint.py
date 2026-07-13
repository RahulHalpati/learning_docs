"""A tiny intraprocedural taint tracker.

Syntactic rules (rules.py) can't tell `cur.execute(q)` where `q` is a constant
from where `q` came from user input. Taint analysis answers exactly that: does
data from a **source** (user input) reach a **sink** (a dangerous operation)
without being sanitised?

This implementation is deliberately simple so you can read it in one sitting:

* It works **within a single function** (intraprocedural) — it doesn't follow
  calls into other functions.
* It's roughly **flow-insensitive**: once a name is tainted in a function it
  stays tainted. That over-approximates (some false positives) but rarely misses
  a real flow, which is the safer bias for a security tool.

Its limits are the whole point of module 03-4 — and the reason bandit/semgrep
exist. Sources: function parameters, `input()`, and anything touching `request`.
Sinks: SQL `execute`, `open` (path traversal), outbound HTTP (SSRF).
"""

from __future__ import annotations

import ast

from .finding import Finding
from .rules import call_name

# sink call name (last attribute) -> (rule_id, severity, cwe, message)
_SINKS_BY_SUFFIX = {
    "execute": ("CA201", "high", "CWE-89", "User input reaches SQL execute() — SQL injection."),
    "executemany": ("CA201", "high", "CWE-89", "User input reaches SQL execute() — SQL injection."),
    "executescript": ("CA201", "high", "CWE-89", "User input reaches SQL execute() — SQL injection."),
    "open": ("CA202", "medium", "CWE-22", "User input reaches open() — path traversal."),
}
_HTTP_SINKS = {
    "requests.get", "requests.post", "requests.put", "requests.delete",
    "requests.head", "requests.patch", "requests.request", "urlopen",
}


def _is_source(node: ast.AST) -> bool:
    """A leaf that introduces taint on its own."""
    if isinstance(node, ast.Call) and call_name(node) == "input":
        return True
    if isinstance(node, ast.Name) and node.id == "request":   # flask request global
        return True
    return False


def _expr_is_tainted(node: ast.AST, tainted: set[str]) -> bool:
    """True if the expression reads a tainted name or contains a source."""
    for sub in ast.walk(node):
        if isinstance(sub, ast.Name) and sub.id in tainted:
            return True
        if _is_source(sub):
            return True
    return False


class TaintAnalyzer:
    def __init__(self, tree: ast.Module, filename: str, lines: list[str]):
        self.tree = tree
        self.filename = filename
        self.lines = lines
        self.findings: list[Finding] = []

    # -- public entry ------------------------------------------------------- #
    def analyze(self) -> list[Finding]:
        funcs = [n for n in ast.walk(self.tree)
                 if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
        for fn in funcs:
            tainted = {a.arg for a in fn.args.args + fn.args.kwonlyargs}
            tainted -= {"self", "cls"}
            self._process(fn.body, tainted)
        top = [s for s in self.tree.body
               if not isinstance(s, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))]
        self._process(top, set())
        return self.findings

    # -- ordered walk ------------------------------------------------------- #
    def _process(self, stmts: list[ast.stmt], tainted: set[str]) -> None:
        for stmt in stmts:
            self._check_leaf_expressions(stmt, tainted)

            if isinstance(stmt, ast.Assign):
                is_tainted = self._expr_is_tainted(stmt.value, tainted)
                for tgt in stmt.targets:
                    if isinstance(tgt, ast.Name):
                        (tainted.add if is_tainted else tainted.discard)(tgt.id)

            # recurse into nested blocks (but not nested function scopes)
            for fieldname in ("body", "orelse", "finalbody"):
                block = getattr(stmt, fieldname, None)
                if isinstance(block, list) and block and isinstance(block[0], ast.stmt):
                    self._process(
                        [s for s in block
                         if not isinstance(s, (ast.FunctionDef, ast.AsyncFunctionDef))],
                        tainted,
                    )
            for handler in getattr(stmt, "handlers", []):
                self._process(handler.body, tainted)

    def _check_leaf_expressions(self, stmt: ast.stmt, tainted: set[str]) -> None:
        """Check sinks only in the expressions evaluated at THIS statement."""
        exprs: list[ast.AST] = []
        if isinstance(stmt, ast.Assign):
            exprs.append(stmt.value)
        elif isinstance(stmt, ast.Expr):
            exprs.append(stmt.value)
        elif isinstance(stmt, ast.Return) and stmt.value is not None:
            exprs.append(stmt.value)
        elif isinstance(stmt, (ast.If, ast.While)):
            exprs.append(stmt.test)
        elif isinstance(stmt, ast.For):
            exprs.append(stmt.iter)
        elif isinstance(stmt, (ast.With, ast.AsyncWith)):
            exprs.extend(item.context_expr for item in stmt.items)
        for expr in exprs:
            self._check_expr_sinks(expr, tainted)

    def _expr_is_tainted(self, node: ast.AST, tainted: set[str]) -> bool:
        return _expr_is_tainted(node, tainted)

    def _check_expr_sinks(self, expr: ast.AST, tainted: set[str]) -> None:
        for sub in ast.walk(expr):
            if not isinstance(sub, ast.Call):
                continue
            name = call_name(sub)
            suffix = name.split(".")[-1]
            spec = None
            if suffix in _SINKS_BY_SUFFIX:
                spec = _SINKS_BY_SUFFIX[suffix]
            elif name in _HTTP_SINKS or suffix == "urlopen":
                spec = ("CA203", "medium", "CWE-918",
                        "User input reaches an outbound HTTP request — SSRF.")
            if spec and self._call_has_tainted_arg(sub, tainted):
                rule_id, severity, cwe, message = spec
                line = getattr(sub, "lineno", 0)
                snippet = self.lines[line - 1].strip() if 0 < line <= len(self.lines) else ""
                self.findings.append(
                    Finding(rule_id, severity, message, self.filename, line, snippet, cwe)
                )

    def _call_has_tainted_arg(self, call: ast.Call, tainted: set[str]) -> bool:
        for arg in call.args:
            if self._expr_is_tainted(arg, tainted):
                return True
        for kw in call.keywords:
            if self._expr_is_tainted(kw.value, tainted):
                return True
        return False


def find_taint(tree: ast.Module, filename: str, lines: list[str]) -> list[Finding]:
    return TaintAnalyzer(tree, filename, lines).analyze()
