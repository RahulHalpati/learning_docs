# Section 01 · Foundations

> **Prerequisites:** [00 · Introduction](../00_introduction.md). Comfortable with Python.
> **Time:** ~2–3 hours.

Before writing a single line of the SDK, you need three things clear in your head: **what an SDK actually does for the person who installs it**, **the HTTP/REST vocabulary** every API client speaks, and **why the obvious way to call an API falls apart** as soon as the code is more than a script. That last one is the motivation engine for the whole course — every later section exists to fix a problem you'll create on purpose here.

## Modules

| # | Module | The question it answers |
|---|--------|------------------------|
| 01 | [What is an SDK](01_what_is_an_sdk.md) | What value does a client library add, and what are its parts? |
| 02 | [HTTP & REST refresher](02_http_and_rest_refresher.md) | What exactly am I wrapping? (methods, status codes, JSON, auth) |
| 03 | [The naive client & its problems](03_the_naive_client_and_its_problems.md) | Why isn't a plain `httpx.get` good enough? |

## What you'll be able to do after this section

- Explain, to a teammate, what an SDK gives users that raw HTTP calls don't.
- Read an API's HTTP traffic: methods, status codes, headers, query params, JSON bodies.
- Point at concrete pain in a naive client (scattered auth, dict access, no error types, no retries) and name the SDK feature that solves each.

→ Start: **[01 · What is an SDK](01_what_is_an_sdk.md)**
