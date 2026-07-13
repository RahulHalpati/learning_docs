"""Pattern-based detection rules, each an ``ast.NodeVisitor``.

A rule walks one file's AST and appends a Finding wherever it sees a dangerous
shape. These are *syntactic* rules — they match the structure of the code, not
the flow of data (that's taint.py). Syntactic rules are cheap, easy to read, and
catch a surprising amount; their weakness is context (a rule can't tell a
constant from user input). We accept that here and let taint.py cover flow.

Add a rule by subclassing ``Rule`` and appending it to ``ALL_RULES`` at the
bottom. That's the whole extension model — it's what module 03-3 walks through.
"""

from __future__ import annotations

import ast

from .finding import Finding


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def call_name(node: ast.Call) -> str:
    """Best-effort dotted name of what's being called.

    ``eval(...)``            -> "eval"
    ``os.system(...)``       -> "os.system"
    ``hashlib.md5(...)``     -> "hashlib.md5"
    ``cur.execute(...)``     -> "execute"   (receiver is a variable, unknown)
    """
    func = node.func
    parts = []
    while isinstance(func, ast.Attribute):
        parts.append(func.attr)
        func = func.value
    if isinstance(func, ast.Name):
        parts.append(func.id)
    return ".".join(reversed(parts))


def keyword_is_true(node: ast.Call, name: str) -> bool:
    for kw in node.keywords:
        if kw.arg == name and isinstance(kw.value, ast.Constant) and kw.value.value is True:
            return True
    return False


def get_keyword(node: ast.Call, name: str):
    for kw in node.keywords:
        if kw.arg == name:
            return kw.value
    return None


class Rule(ast.NodeVisitor):
    """Base class: subclasses set id/severity/cwe and override visit_* methods."""

    id = ""
    severity = "medium"
    cwe = ""

    def __init__(self, filename: str, source_lines: list[str]):
        self.filename = filename
        self.lines = source_lines
        self.findings: list[Finding] = []

    def report(self, node: ast.AST, message: str) -> None:
        line = getattr(node, "lineno", 0)
        snippet = self.lines[line - 1].strip() if 0 < line <= len(self.lines) else ""
        self.findings.append(
            Finding(self.id, self.severity, message, self.filename, line, snippet, self.cwe)
        )


# --------------------------------------------------------------------------- #
# the rules
# --------------------------------------------------------------------------- #
class DangerousCallRule(Rule):
    """eval / exec / os.system — arbitrary code or command execution."""

    id, severity, cwe = "CA101", "critical", "CWE-95"
    _NAMES = {"eval", "exec", "os.system"}

    def visit_Call(self, node: ast.Call):
        name = call_name(node)
        if name in self._NAMES:
            self.report(node, f"Dangerous call to `{name}()` — arbitrary code/command execution risk.")
        self.generic_visit(node)


class ShellTrueRule(Rule):
    """subprocess.* with shell=True — command injection if any arg is user-controlled."""

    id, severity, cwe = "CA102", "high", "CWE-78"

    def visit_Call(self, node: ast.Call):
        name = call_name(node)
        if name.startswith("subprocess.") and keyword_is_true(node, "shell"):
            self.report(node, f"`{name}(..., shell=True)` — shell command injection risk.")
        self.generic_visit(node)


class WeakHashRule(Rule):
    """hashlib.md5 / sha1 — broken for passwords or integrity."""

    id, severity, cwe = "CA103", "medium", "CWE-327"
    _WEAK = {"hashlib.md5", "hashlib.sha1", "md5", "sha1"}

    def visit_Call(self, node: ast.Call):
        if call_name(node) in self._WEAK:
            self.report(node, "Weak hash (MD5/SHA1) — unsuitable for passwords or integrity.")
        self.generic_visit(node)


class InsecureDeserializationRule(Rule):
    """pickle.loads / yaml.load without SafeLoader — code execution on load."""

    id, severity, cwe = "CA104", "high", "CWE-502"

    def visit_Call(self, node: ast.Call):
        name = call_name(node)
        if name in ("pickle.loads", "pickle.load", "cPickle.loads"):
            self.report(node, f"`{name}()` deserialises untrusted data — remote code execution risk.")
        elif name in ("yaml.load",):
            loader = get_keyword(node, "Loader")
            safe = loader is not None and (
                (isinstance(loader, ast.Attribute) and "Safe" in loader.attr)
                or (isinstance(loader, ast.Name) and "Safe" in loader.id)
            )
            if not safe:
                self.report(node, "`yaml.load()` without SafeLoader — code execution risk; use `yaml.safe_load`.")
        self.generic_visit(node)


class FlaskDebugRule(Rule):
    """app.run(debug=True) — the Werkzeug debugger is an RCE console if exposed."""

    id, severity, cwe = "CA105", "high", "CWE-489"

    def visit_Call(self, node: ast.Call):
        if call_name(node).endswith("run") and keyword_is_true(node, "debug"):
            self.report(node, "`debug=True` — exposes the interactive debugger (RCE) in production.")
        self.generic_visit(node)


class HardcodedSecretRule(Rule):
    """A string literal assigned to a secret-looking name."""

    id, severity, cwe = "CA106", "medium", "CWE-798"
    _NAMES = ("password", "passwd", "pwd", "secret", "secret_key",
              "api_key", "apikey", "token", "access_key")

    def visit_Assign(self, node: ast.Assign):
        if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
            for target in node.targets:
                name = target.id if isinstance(target, ast.Name) else getattr(target, "attr", "")
                low = name.lower()
                if any(k in low for k in self._NAMES) and len(node.value.value) >= 4:
                    self.report(node, f"Hardcoded secret in `{name}` — move it to an environment variable.")
        self.generic_visit(node)


class SqlStringBuildRule(Rule):
    """.execute(<f-string or concatenation>) — classic SQL injection shape."""

    id, severity, cwe = "CA107", "high", "CWE-89"
    _SINKS = {"execute", "executemany", "executescript"}

    def visit_Call(self, node: ast.Call):
        if call_name(node).split(".")[-1] in self._SINKS and node.args:
            arg = node.args[0]
            if self._is_built_string(arg):
                self.report(node, "SQL built with string formatting/concatenation — use parameterised queries.")
        self.generic_visit(node)

    @staticmethod
    def _is_built_string(node: ast.AST) -> bool:
        if isinstance(node, ast.JoinedStr):        # f"... {x} ..."
            return True
        if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Mod)):  # "..." + x  or  "..." % x
            return True
        if isinstance(node, ast.Call) and call_name(node).endswith("format"):        # "...".format(x)
            return True
        return False


ALL_RULES = [
    DangerousCallRule,
    ShellTrueRule,
    WeakHashRule,
    InsecureDeserializationRule,
    FlaskDebugRule,
    HardcodedSecretRule,
    SqlStringBuildRule,
]
