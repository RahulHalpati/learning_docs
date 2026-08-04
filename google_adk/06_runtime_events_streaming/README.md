# Section 06 · Runtime, events & streaming

> **Prerequisites:** [01 · Foundations](../01_foundations/README.md) · **Time:** ~90 min

How agents actually *run*. Runners drive agents and emit **events**; you can **stream** those (including token-by-token and the bidirectional **Live API**); and `adk api_server` exposes an agent over HTTP.

## Modules

| # | Module | The question it answers |
|---|--------|-------------------------|
| 06-1 | [Runners & events](01_runners_and_events.md) | How does a runner drive an agent, and what's in the event stream? |
| 06-2 | [Streaming & Live](02_streaming_and_live.md) | How do I stream partial output, and what is the Live API? |
| 06-3 | [API server & clients](03_api_server_and_clients.md) | How do I serve an agent over HTTP and call it? |

## What you'll be able to do after this section

- Drive agents with `Runner`/`InMemoryRunner` and read `Event` objects.
- Stream partial responses; understand the bidirectional Live API and its offline limits.
- Serve an agent with `adk api_server` and call its endpoints.

→ Start: **[06-1 · Runners & events](01_runners_and_events.md)**
