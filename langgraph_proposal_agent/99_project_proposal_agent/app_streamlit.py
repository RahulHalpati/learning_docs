"""Streamlit UI for the Proposal Agent.

    streamlit run app_streamlit.py
"""

from __future__ import annotations

import streamlit as st

from proposal_agent.graph import generate_proposal

st.set_page_config(page_title="Proposal Agent", page_icon="✍️", layout="wide")

st.title("✍️ Freelance Proposal Generator")
st.caption("Paste a job posting → 4 AI agents write you a personalized proposal.")

with st.sidebar:
    st.header("Settings")
    max_revisions = st.slider("Max revisions", min_value=0, max_value=5, value=2)
    st.markdown("---")
    st.markdown(
        "**LLM:** set `PROPOSAL_LLM` env var  \n"
        "`ollama` · `anthropic` · `openai` · `fake`"
    )

job_text = st.text_area(
    "Job posting",
    height=200,
    placeholder="Paste the full job description here…",
)

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
        review = final.get("review", "")
        if approved:
            st.success("Reviewer approved the proposal.")
        else:
            st.warning("Reviewer requested changes but max revisions reached.")
        st.markdown(review or "_no review notes_")
