# Section 03 · Request handling

> **Prerequisites:** [01 · Foundations](../01_foundations/README.md) · **Time:** ~2.5 h

Everything a client can send you, and how to handle it safely: the right **HTTP method and status code**, **JSON** payloads with validation, and **form data + file/image uploads** — the part that's easy to get insecure.

## Modules

| # | Module | The question it answers |
|---|--------|-------------------------|
| 03-1 | [HTTP methods & status codes](01_http_methods_status.md) | Which method and which code, and why it matters |
| 03-2 | [JSON APIs & validation](02_json_apis_validation.md) | How do I accept JSON and reject bad input properly? |
| 03-3 | [Forms, files & images](03_forms_files_images.md) | How do I handle form posts and uploads securely? |

## What you'll be able to do after this section

- Choose methods/status codes correctly (and know what idempotency buys you).
- Build a JSON endpoint that validates input and returns structured 422 errors.
- Accept form data and **image uploads** with type/size checks and safe filenames.

→ Start: **[03-1 · HTTP methods & status codes](01_http_methods_status.md)**
