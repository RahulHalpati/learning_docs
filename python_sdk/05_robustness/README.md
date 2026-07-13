# Section 05 · Robustness

> **Prerequisites:** [Section 03 · The sync client](../03_the_sync_client/README.md), [Section 04 · Data models](../04_data_models/README.md).
> **Time:** ~4–5 hours.

This is the section that turns a working client into a *production* one. We close the remaining naive-client problems all at once: cryptic errors become a **typed exception hierarchy**; one network blip stops being fatal thanks to **retries with backoff**; multi-page lists become a single `for` loop via **pagination**; and we lock down **timeouts, logging, and config** so the SDK never hangs and is debuggable. Every one of these slots into the single `_request` funnel from Section 03 — written once, applied to every call.

## Modules

| # | Module | The question it answers |
|---|--------|------------------------|
| 01 | [The error hierarchy](01_error_hierarchy.md) | How do I turn bad statuses into specific, catchable exceptions? |
| 02 | [Retries & backoff](02_retries_and_backoff.md) | How do I survive transient failures without hammering the server? |
| 03 | [Pagination](03_pagination.md) | How do I let users iterate huge lists with one `for` loop? |
| 04 | [Timeouts, logging & config](04_timeouts_logging_config.md) | How do I prevent hangs and make the SDK debuggable & configurable? |

## What you'll be able to do after this section

- Design an exception hierarchy (`PokeError → APIError → NotFoundError/…`) and map HTTP statuses onto it.
- Add retries with exponential backoff to the request funnel, retrying only what's safe to retry.
- Provide pagination iterators that walk `next` links transparently — sync now, async later.
- Set sane default timeouts, add opt-in logging, and expose clean configuration knobs.

→ Start: **[01 · The error hierarchy](01_error_hierarchy.md)**
