"""Command line: turn a job posting into a proposal.

    python -m proposal_agent.cli data/sample_jobs/fastapi_backend.txt
    cat job.txt | python -m proposal_agent.cli        # read from stdin

Set the LLM with the PROPOSAL_LLM env var (ollama | anthropic | openai | fake).
"""

from __future__ import annotations

import sys
from pathlib import Path

from .graph import generate_proposal


def main(argv: list[str]) -> None:
    if argv:
        job_text = Path(argv[0]).read_text(encoding="utf-8")
    else:
        job_text = sys.stdin.read()

    if not job_text.strip():
        print("No job text provided. Pass a file path or pipe text via stdin.")
        raise SystemExit(1)

    final = generate_proposal(job_text)

    print("=" * 60)
    print("PATH     :", " -> ".join(final.get("log", [])))
    print("REVISIONS:", final.get("revisions"))
    print("APPROVED :", final.get("approved"))
    print("=" * 60)
    print(final["proposal"])


if __name__ == "__main__":
    main(sys.argv[1:])
