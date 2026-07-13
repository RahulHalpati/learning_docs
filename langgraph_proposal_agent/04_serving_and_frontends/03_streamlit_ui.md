# 04-3 · Streamlit UI

> **Level:** Beginner · **Prerequisites:** [04-2 FastAPI endpoint](02_fastapi_endpoint.md)
> **Time:** 20 min · **Verified:** Streamlit 1.45.0, AppTest, Python 3.10

---

## Run it

```bash
cd 99_project_proposal_agent
PROPOSAL_LLM=fake streamlit run app_streamlit.py
```

Open `http://localhost:8501` in your browser, paste a job posting, and click
**Generate proposal**.

---

## The code (~60 lines)

```python
# app_streamlit.py

import streamlit as st
from proposal_agent.graph import generate_proposal

st.set_page_config(page_title="Proposal Agent", page_icon="✍️", layout="wide")
st.title("✍️ Freelance Proposal Generator")
st.caption("Paste a job posting → 4 AI agents write you a personalised proposal.")

with st.sidebar:
    st.header("Settings")
    max_revisions = st.slider("Max revisions", min_value=0, max_value=5, value=2)
    st.markdown("**LLM:** set `PROPOSAL_LLM` env var  \n`ollama` · `anthropic` · `openai` · `fake`")

job_text = st.text_area("Job posting", height=200, placeholder="Paste the full job description here…")

if st.button("Generate proposal", type="primary", disabled=not job_text.strip()):
    with st.spinner("Agents are working…"):
        final = generate_proposal(job_text.strip(), max_revisions=max_revisions)

    path = " → ".join(final.get("log", []))
    approved = final.get("approved", False)
    revisions = final.get("revisions", 0)

    col1, col2, col3 = st.columns(3)
    col1.metric("Agent path", path)
    col2.metric("Revisions", revisions)
    col3.metric("Approved", "✅ Yes" if approved else "⚠️ No")

    st.divider()

    tab_proposal, tab_analysis, tab_fit, tab_review = st.tabs(
        ["Proposal", "Analysis", "Fit", "Review notes"]
    )

    with tab_proposal:
        proposal = final.get("proposal", "")
        st.text_area("Copy-paste ready proposal", value=proposal, height=400)
        st.download_button("Download .txt", data=proposal, file_name="proposal.txt")

    with tab_analysis:
        st.markdown(final.get("analysis", "_no analysis_"))

    with tab_fit:
        st.markdown(final.get("fit", "_no fit assessment_"))

    with tab_review:
        if approved:
            st.success("Reviewer approved the proposal.")
        else:
            st.warning("Reviewer requested changes but max revisions reached.")
        st.markdown(final.get("review", "") or "_no review notes_")
```

### UI breakdown

| Component | Purpose |
|---|---|
| `st.sidebar` with `st.slider` | Let users tweak `max_revisions` without touching code |
| `st.text_area` | Big input box for the job posting |
| `st.button(disabled=...)` | Greys out the button if the input is empty |
| `st.spinner` | Shows "Agents are working…" while the graph runs |
| `st.metric` | Shows path / revisions / approved at a glance |
| `st.tabs` | Organises proposal, analysis, fit, and review in tabs |
| `st.download_button` | One click to save the proposal as a `.txt` file |

---

## Automated test

```python
# verify the UI starts and renders without crashing

from streamlit.testing.v1 import AppTest

def test_streamlit_app_loads():
    at = AppTest.from_file("app_streamlit.py")
    at.run()
    assert not at.exception
    assert len(at.text_area) >= 1   # job posting input is rendered
```

```bash
PROPOSAL_LLM=fake pytest tests/test_streamlit.py -v   # if you add this file
```

---

## Exercise

Add a **second sidebar section** that lets users type a custom tone (e.g. "warm and
conversational", "technical and detailed") and passes it to `generate_proposal()`.

<details>
<summary>Hint</summary>

In the sidebar:

```python
tone = st.text_input("Proposal tone", value="confident and direct")
```

Then pass it when calling the graph. You'll need to expose `tone` in `generate_proposal()`:

```python
# in graph.py
def generate_proposal(job_text, *, max_revisions=2, thread_id="default", tone=None, **kwargs):
    graph = build_graph(tone=tone, **kwargs)
    ...
```

And in the app:

```python
final = generate_proposal(job_text.strip(), max_revisions=max_revisions, tone=tone)
```

</details>

---

**Next → [05-1 Prompts & template](../05_quality_and_shipping/01_prompts_and_template.md)**
