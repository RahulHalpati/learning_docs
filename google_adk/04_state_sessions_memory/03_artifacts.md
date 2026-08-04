# 04-3 · Artifacts

> **Level:** Intermediate · **Prerequisites:** [04-1 · Sessions & state](01_sessions_and_state.md)
> **Time:** 20 min · **Verified:** 2026-07-21 (google-adk 2.5.0)

## Why this matters

State is for structured values; **artifacts** are for *binary blobs* — a generated PDF, an image, an audio clip, a CSV. The **ArtifactService** stores them by filename with versioning, so agents and tools can produce and retrieve files without stuffing bytes into state.

---

## Save and load

```python
import asyncio
from google.adk.artifacts import InMemoryArtifactService
from google.genai import types

async def main():
    svc = InMemoryArtifactService()
    artifact = types.Part(inline_data=types.Blob(mime_type="text/plain",
                                                 data=b"report contents"))

    version = await svc.save_artifact(app_name="app", user_id="u", session_id="s1",
                                      filename="report.txt", artifact=artifact)
    print("saved version:", version)

    loaded = await svc.load_artifact(app_name="app", user_id="u", session_id="s1",
                                     filename="report.txt")
    print("loaded:", loaded.inline_data.data.decode())
    print("keys:", await svc.list_artifact_keys(app_name="app", user_id="u", session_id="s1"))

asyncio.run(main())
```

**Output (real run):**
```
saved version: 0
loaded: report contents
keys: ['report.txt']
```

Each save returns a **version** (0, 1, 2, …) — saving `report.txt` again keeps the old version and adds a new one, so you have history. `list_artifact_keys` enumerates a session's files.

---

## From inside a tool or callback

In practice you save artifacts through the context, which routes to the service automatically:

```python
# in a tool:
#   await tool_context.save_artifact("chart.png", types.Part(inline_data=...))
#   img = await tool_context.load_artifact("chart.png")
```

So a "generate a report" tool produces `report.pdf` as an artifact, and a later step (or the user) loads it — the bytes never bloat the session state.

> **Tip:** Use `user:`-prefixed filenames (e.g. `user:profile.png`) for artifacts that should persist across a user's sessions, mirroring the state prefixes from [04-1](01_sessions_and_state.md). `InMemoryArtifactService` is for dev; GCS-backed services persist in production.

---

## State vs memory vs artifacts

| Store | For | Example |
|-------|-----|---------|
| **state** | structured values in a conversation | `draft`, `score` |
| **memory** | searchable knowledge across sessions | "user is vegetarian" |
| **artifacts** | binary files | `report.pdf`, `chart.png` |

Three stores, three jobs — don't put a PDF in state or a scalar in artifacts.

---

## Recap & next

- ✅ `ArtifactService` stores binary blobs by filename, with versioning.
- ✅ `save_artifact` returns a version; `load_artifact`/`list_artifact_keys` retrieve.
- ✅ Save via `tool_context`/`callback_context` in real agents; `user:` filenames persist per user.
- ✅ Self-check: which of state / memory / artifacts holds a generated chart image?

→ Next: **[04-4 · Callbacks](04_callbacks.md)**

## Exercises

1. Save two versions of `notes.txt` and confirm the returned versions are `0` then `1`.

<details>
<summary>Solution</summary>

Call `save_artifact(..., filename="notes.txt", ...)` twice with different bytes; the first returns `0`, the second `1`. `load_artifact` returns the latest unless you request a specific version.
</details>
