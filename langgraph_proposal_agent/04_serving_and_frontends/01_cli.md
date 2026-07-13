# 04-1 · CLI

> **Level:** Beginner · **Prerequisites:** [03-2 Memory & streaming](../03_assembling_the_graph/02_memory_and_streaming.md)
> **Time:** 10 min · **Verified:** Python 3.10, fake model

---

## Usage

```bash
# from the 99_project_proposal_agent/ directory

# pass a file
PROPOSAL_LLM=fake python -m proposal_agent.cli data/sample_jobs/fastapi_backend.txt

# pipe from stdin
cat data/sample_jobs/rag_chatbot.txt | PROPOSAL_LLM=fake python -m proposal_agent.cli

# real LLM (needs Ollama running)
PROPOSAL_LLM=ollama python -m proposal_agent.cli data/sample_jobs/fastapi_backend.txt
```

## Output (fake model)

```
============================================================
PATH     : analyzer -> matcher -> writer -> reviewer
REVISIONS: 1
APPROVED : True
============================================================
Hi — I build exactly this. I recently shipped a typed Python/FastAPI API...
[draft]. Happy to start this week.
```

---

## The code

```python
# proposal_agent/cli.py

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
```

The CLI is intentionally thin — it only handles I/O. All the agent logic lives in
`graph.generate_proposal()`, which is also what the FastAPI endpoint and Streamlit
app call.

---

## Exercise

Add a `--thread-id` flag so users can resume a previous conversation thread:

```bash
python -m proposal_agent.cli job.txt --thread-id my-client-123
```

<details>
<summary>Hint</summary>

Use `argparse` or `sys.argv` parsing. Pass the thread_id to `generate_proposal()`:

```python
import argparse

def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument("file", nargs="?")
    parser.add_argument("--thread-id", default="default")
    args = parser.parse_args(argv)

    job_text = Path(args.file).read_text() if args.file else sys.stdin.read()
    final = generate_proposal(job_text, thread_id=args.thread_id)
    ...
```

</details>

---

**Next → [02 FastAPI endpoint](02_fastapi_endpoint.md)**
