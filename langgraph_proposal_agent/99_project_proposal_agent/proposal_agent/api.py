"""FastAPI endpoint: POST /generate  →  proposal JSON.

    uvicorn proposal_agent.api:app --reload
    curl -X POST http://localhost:8000/generate \
         -H "Content-Type: application/json" \
         -d '{"job_text": "Build a FastAPI backend with Postgres."}'
"""

from __future__ import annotations

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
