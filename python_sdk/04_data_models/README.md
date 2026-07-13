# Section 04 · Data models

> **Prerequisites:** [Section 03 · The sync client](../03_the_sync_client/README.md).
> **Time:** ~2–3 hours.

The client works, but it hands back raw dicts — the naive client's "dicts not types" problem (`p["weihgt"]` → runtime `KeyError`). This section fixes it with **Pydantic models**: methods return typed objects (`Pokemon`) whose fields autocomplete in your editor and are validated on the way in. Then we make sure that type information actually *reaches your users* by shipping a `py.typed` marker — the difference between an SDK that's typed for you and one that's typed for everyone.

## Modules

| # | Module | The question it answers |
|---|--------|------------------------|
| 01 | [Response models with Pydantic](01_response_models_pydantic.md) | How do I turn JSON dicts into typed, validated objects? |
| 02 | [Typing & py.typed](02_typing_and_py_typed.md) | How do my users' type checkers see my types? |

## What you'll be able to do after this section

- Define Pydantic models that parse and validate API responses, ignoring unknown fields safely.
- Return typed objects from resource methods so users get autocomplete and `.field` access.
- Add type hints across the public API and ship a `py.typed` marker so downstream type checkers use them.

→ Start: **[01 · Response models with Pydantic](01_response_models_pydantic.md)**
