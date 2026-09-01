# 05-1 · Testing with Floci

> **Level:** Intermediate · **Prerequisites:** [03-2 The linkstash-cloud stack](../04_iac_with_opentofu/02_the_capstone_stack.md)
> **Time:** 25 min · **Verified:** 2026-09-01 (7 tests passing)

The reason many teams adopt Floci: you can write **integration tests that
exercise real AWS API calls** — not mocks — against ephemeral infra, for free. Your
tests run the same code path as production.

---

## The capstone's tests

[`tests/test_storage.py`](../99_project_linkstash_cloud/tests/test_storage.py)
hits real boto3 against Floci:

```python
pytestmark = pytest.mark.skipif(
    not os.environ.get("AWS_ENDPOINT_URL"),
    reason="set AWS_ENDPOINT_URL and apply infra first",
)

def test_put_and_get(store):
    store.put("t-get", "https://example.org")
    assert store.get("t-get") == "https://example.org"

def test_put_emits_event(store):
    store.drain_events()
    store.put("t-evt", "https://example.net")
    assert any("created:t-evt" in e for e in store.drain_events())
```

Verified:

```
$ python -m pytest -q
.......                                          [100%]
7 passed in 0.35s
```

The `skipif` guard means the suite **skips cleanly** when Floci isn't
configured (so a plain `pytest` on a laptop without it doesn't fail) and **runs**
when `AWS_ENDPOINT_URL` is set — locally or in CI.

---

## Floci vs moto (mocks)

Two ways to test AWS code without real AWS:

| | Floci | moto |
|---|---|---|
| What | a running emulator (container) | an in-process Python mock |
| Fidelity | high — real API server, cross-service | good for single-service unit tests |
| Speed | fast (local container) | fastest (no container) |
| Multi-service flows | ✅ (S3 + DynamoDB + SQS together) | awkward |
| Non-Python tools (OpenTofu, CLI) | ✅ works against it | ✗ Python-only |

Rule of thumb: **moto for fast Python unit tests** of one service; **Floci for
integration tests** spanning services, or when OpenTofu/CLI are in the loop (like
the capstone). They coexist happily.

---

## Keeping tests isolated

Tests share one Floci, so avoid cross-test interference:

- **Unique keys per test** (`t-get`, `t-evt`) so tests don't collide.
- **Drain/clean state** where order matters — the event test calls
  `drain_events()` first to clear the queue.
- **Ephemeral by default** — a fresh `docker run` starts empty, so CI gets a clean
  slate every run (05-2).

For strict isolation you can create per-test buckets/tables/queues with random
names, or restart Floci between test files.

---

## Recap & next

- ✅ Floci enables **real integration tests** (actual boto3 calls) against
  ephemeral AWS — 7 passing in the capstone.
- ✅ Guard with **`skipif AWS_ENDPOINT_URL`** so the suite skips without Floci
  and runs with it.
- ✅ **moto** = fast in-process mocks for unit tests; **Floci** = integration
  tests across services / with OpenTofu/CLI.

**Self-check:** Why does the capstone's test suite `skipif not AWS_ENDPOINT_URL`
instead of always running?

<details>
<summary>Answer</summary>

So the suite **doesn't fail on a machine without Floci** (a plain `pytest`
skips those integration tests). When the Floci environment *is* configured
(`AWS_ENDPOINT_URL` set — locally or in CI), the same tests run for real. It makes
integration tests opt-in by environment rather than a hard dependency of every test
run.

</details>

**→ Next: [05-2 · Floci in CI](02_floci_in_ci.md)**
