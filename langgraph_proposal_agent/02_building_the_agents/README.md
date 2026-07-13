# Section 02 · Building the Agents

Build the four agents one at a time. Each module is self-contained: concept, code,
verified output, unit test.

| Module | Agent | What it does |
|---|---|---|
| [01 Shared state](01_shared_state.md) | — | The `ProposalState` TypedDict that flows through all 4 agents |
| [02 Analyzer](02_analyzer.md) | Agent 1 | Extract tech stack, budget, timeline, red flags |
| [03 Profile Matcher](03_profile_matcher.md) | Agent 2 | Score job vs your portfolio, pick best project |
| [04 Proposal Writer](04_proposal_writer.md) | Agent 3 | Draft the proposal using analysis + match |
| [05 Reviewer](05_reviewer.md) | Agent 4 | Approve or send revision notes |

**→ Start: [01 Shared state](01_shared_state.md)**
