# 04-2 · FastAPI Endpoint

> **Level:** Beginner · **Prerequisites:** [04-1 CLI](01_cli.md)
> **Time:** 20 min · **Verified:** FastAPI 0.136.1, TestClient, fake model

---

## The API

`POST /generate` takes a job posting and returns the full proposal result as JSON.

```bash
# start the server
uvicorn proposal_agent.api:app --reload

# call it
curl -X POST http://localhost:8000/generate \
     -H "Content-Type: application/json" \
     -d '{"job_text": "Build a FastAPI backend with Postgres."}'
```

Response:

```json
{
  "proposal": "Hi — I build exactly this...",
  "analysis": "Stack: FastAPI, Postgres. Budget: healthy...",
  "fit": "HIGH fit — best project: Typed Python SDK...",
  "review": "APPROVED",
  "approved": true,
  "revisions": 1,
  "path": ["analyzer", "matcher", "writer", "reviewer"]
}
```

---

## The code

```python
# proposal_agent/api.py

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from .graph import generate_proposal

app = FastAPI(title="Proposal Agent API", version="1.0.0")


class GenerateRequest(BaseModel):
    job_text: str
    max_revisions: int = 2


class GenerateResponse(BaseModel):
    proposal: str
    analysis: str
    fit: str
    review: str
    approved: bool
    revisions: int
    path: list[str]


@app.post("/generate", response_model=GenerateResponse)
def generate(req: GenerateRequest) -> GenerateResponse:
    if not req.job_text.strip():
        raise HTTPException(status_code=422, detail="job_text must not be empty")

    final = generate_proposal(req.job_text, max_revisions=req.max_revisions)

    return GenerateResponse(
        proposal=final.get("proposal", ""),
        analysis=final.get("analysis", ""),
        fit=final.get("fit", ""),
        review=final.get("review", ""),
        approved=bool(final.get("approved")),
        revisions=int(final.get("revisions", 0)),
        path=final.get("log", []),
    )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
```

### Design notes

- **Pydantic models for I/O** — FastAPI validates the request body automatically.
  If `job_text` is missing, FastAPI returns a 422 before your handler runs.
- **Manual empty check** — Pydantic doesn't validate that a string is non-empty by
  default. The explicit `if not req.job_text.strip()` catches whitespace-only inputs.
- **Response model** — `response_model=GenerateResponse` makes FastAPI serialize and
  document the output shape automatically.
- **Thin handler** — the handler delegates everything to `generate_proposal()`. The
  API knows nothing about LangGraph; it just calls the same function the CLI calls.

---

## Tests (verified, 4 passing)

```python
# tests/test_api.py

import os
import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("PROPOSAL_LLM", "fake")

from proposal_agent.api import app

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_generate_returns_proposal():
    r = client.post("/generate", json={"job_text": "Build a FastAPI backend."})
    assert r.status_code == 200
    body = r.json()
    assert body["proposal"]
    assert isinstance(body["revisions"], int)
    assert "analyzer" in body["path"]


def test_generate_rejects_empty_job():
    r = client.post("/generate", json={"job_text": "   "})
    assert r.status_code == 422


def test_generate_max_revisions_param():
    r = client.post("/generate", json={"job_text": "Need a REST API.", "max_revisions": 0})
    assert r.status_code == 200
    assert r.json()["revisions"] <= 1
```

```bash
PROPOSAL_LLM=fake pytest tests/test_api.py -v
```

```
tests/test_api.py::test_health                    PASSED
tests/test_api.py::test_generate_returns_proposal PASSED
tests/test_api.py::test_generate_rejects_empty_job PASSED
tests/test_api.py::test_generate_max_revisions_param PASSED

4 passed in 2.28s
```

---

## Interactive docs

FastAPI auto-generates Swagger UI at `http://localhost:8000/docs` — open it to
test the endpoint in the browser without writing curl commands.

---

## Exercise

Add a `POST /generate/stream` endpoint that streams each agent's output using
Server-Sent Events (FastAPI `StreamingResponse`).

<details>
<summary>Approach</summary>

```python
from fastapi.responses import StreamingResponse
import json

@app.post("/generate/stream")
def generate_stream(req: GenerateRequest):
    def event_stream():
        graph = build_graph()
        for event in graph.stream(
            {"job_text": req.job_text, "revisions": 0, "max_revisions": req.max_revisions},
            config={"configurable": {"thread_id": "stream"}},
        ):
            node_name = list(event.keys())[0]
            data = {"node": node_name, "output": event[node_name]}
            yield f"data: {json.dumps(data)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
```

</details>

---

**Next → [03 Streamlit UI](03_streamlit_ui.md)**
