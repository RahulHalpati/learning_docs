# Section 01 · Foundations

> **Prerequisites:** [00 · Introduction](../00_introduction.md) · **Time:** ~2 h

The three things every Flask app does: **run**, **route a URL to a function**, and **read a request / return a response**. Everything later is built on these.

## Modules

| # | Module | The question it answers |
|---|--------|-------------------------|
| 01-1 | [Your first app](01_first_app.md) | How do I create and run a Flask app? |
| 01-2 | [Routing & URL variables](02_routing_and_variables.md) | How do URLs map to functions, with typed variable parts? |
| 01-3 | [Request & response](03_request_and_response.md) | How do I read input and control what goes back? |

## What you'll be able to do after this section

- Create an app, define routes, and run it with `flask run --debug`.
- Use variable rules (`<int:id>`, `<path:p>`) and build URLs with `url_for`.
- Read query args, headers, and JSON bodies; return dicts, tuples, or `make_response`.

→ Start: **[01-1 · Your first app](01_first_app.md)**
