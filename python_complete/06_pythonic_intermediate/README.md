# Section 06 · Pythonic Intermediate

> **Level:** Intermediate → Advanced · **Prerequisites:** [Section 04 (OOP)](../04_oop/README.md), [Section 05 (errors)](../05_exceptions_and_errors/README.md)
> **Time:** ~6 hours · **Verified:** 2026-06-04 (Python 3.12.13)

You can already write correct Python. This section is about writing **idiomatic, efficient, elegant** Python — the features that make experienced developers nod. Iterators and generators let you process huge or infinite streams without exhausting memory; decorators let you add behaviour without touching a function's body; context managers guarantee clean-up; and advanced typing makes large codebases maintainable. These also power the tools you'll use next: async builds on iterators, FastAPI's dependency injection builds on decorators and context managers.

## Modules

| # | Module | You'll learn to… |
|---|--------|------------------|
| 01 | [Iterators & iterables](01_iterators_and_iterables.md) | Understand the protocol behind every `for` loop |
| 02 | [Generators](02_generators.md) | Produce values lazily with `yield`; handle infinite streams |
| 03 | [Decorators](03_decorators.md) | Wrap functions to add logging, timing, retries, caching |
| 04 | [Context managers](04_context_managers.md) | Guarantee setup/cleanup with `with` and `@contextmanager` |
| 05 | [Advanced typing](05_advanced_typing.md) | Generics, `Protocol`, `TypedDict`, and friends |

→ Start: **[01 · Iterators & iterables](01_iterators_and_iterables.md)**
