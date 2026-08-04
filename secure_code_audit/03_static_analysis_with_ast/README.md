# 03 · Static analysis with AST (build your own)

Now you build the scanner. By the end of this section you'll understand every line
of `codeaudit` — how it parses code, matches dangerous patterns, and tracks taint
from source to sink.

| # | Module | You'll build |
|---|---|---|
| 03-1 | [How SAST works](01_how_sast_works.md) | The mental model: source → tokens → AST → rules |
| 03-2 | [AST basics](02_ast_basics.md) | Parse code and walk it with `ast.NodeVisitor` |
| 03-3 | [Writing detection rules](03_writing_detection_rules.md) | The real `rules.py` — one rule at a time |
| 03-4 | [Simple taint tracking](04_simple_taint_tracking.md) | The real `taint.py` — source→sink flow |

**Next → [03-1 · How SAST works](01_how_sast_works.md)**
