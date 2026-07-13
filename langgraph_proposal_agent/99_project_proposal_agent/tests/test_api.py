"""FastAPI endpoint tests — offline, deterministic (fake model via env var)."""

import os
import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("PROPOSAL_LLM", "fake")

from proposal_agent.api import app  # noqa: E402  (import after env var set)

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_generate_returns_proposal():
    r = client.post("/generate", json={"job_text": "Build a FastAPI backend."})
    assert r.status_code == 200
    body = r.json()
    assert body["proposal"]           # non-empty string
    assert isinstance(body["revisions"], int)
    assert isinstance(body["approved"], bool)
    assert "analyzer" in body["path"]
    assert "writer" in body["path"]


def test_generate_rejects_empty_job():
    r = client.post("/generate", json={"job_text": "   "})
    assert r.status_code == 422


def test_generate_max_revisions_param():
    r = client.post("/generate", json={"job_text": "Need a REST API.", "max_revisions": 0})
    assert r.status_code == 200
    # with max_revisions=0, loop exits immediately after first review
    assert r.json()["revisions"] <= 1
