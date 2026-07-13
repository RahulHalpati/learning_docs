# Section 07 · Testing

> **Prerequisites:** Sections [03](../03_the_sync_client/README.md)–[06](../06_async_client/README.md).
> **Time:** ~2–3 hours.

An SDK without tests is a liability — every change risks silently breaking someone's production code. But testing an SDK has a special challenge: it's *defined* by making HTTP calls, and you can't hit the real API in your test suite (it's slow, flaky, rate-limited, and might require secrets). The answer is to **mock the HTTP layer**: with `respx`, you tell the test "when the SDK calls this URL, return this response," and now your tests are **fast, deterministic, and offline** — yet exercise the real client code end to end.

## Modules

| # | Module | The question it answers |
|---|--------|------------------------|
| 01 | [Testing with respx](01_testing_with_respx.md) | How do I test HTTP code without a network? |
| 02 | [Fixtures, async tests & coverage](02_fixtures_and_coverage.md) | How do I keep tests clean, test async, and measure what's covered? |

## What you'll be able to do after this section

- Mock httpx requests with `respx` to test the real client offline and deterministically.
- Test the hard paths: error mapping, retries-then-success, pagination across pages, auth headers.
- Use fixtures for shared data, test the async client with `pytest-asyncio`, and read a coverage report to find gaps.

→ Start: **[01 · Testing with respx](01_testing_with_respx.md)**
