# Section 02 · LangChain core

> **Prerequisites:** [Section 01 · Foundations](../01_foundations/README.md).
> **Time:** ~5–7 hours.

A RAG pipeline is a *chain* of steps: build a prompt → call the LLM → parse the answer, often with memory of the conversation. This section teaches those building blocks and the glue that connects them — **LCEL**, the `|` pipe operator that is the defining feature of modern LangChain. Master this and the RAG chain in Section 03 will read like plain English.

> ⚠️ This is exactly where old tutorials go wrong: they use `LLMChain`, `SequentialChain`, and `ConversationChain`, which **don't exist in LangChain 1.x**. We use LCEL and `RunnableWithMessageHistory` instead — the current, supported way.

## Modules

| # | Module | The question it answers |
|---|--------|------------------------|
| 01 | [Prompts & messages](01_prompts_and_messages.md) | How do I build the text I send the LLM, with variables? |
| 02 | [LCEL chains](02_lcel_chains.md) | How do I connect steps with the `\|` pipe? |
| 03 | [Output parsers & structured output](03_output_parsers_and_structured.md) | How do I turn the reply into clean text or data? |
| 04 | [Memory & message history](04_memory_message_history.md) | How does my app remember earlier turns?  ·  ⚪ *optional / appendix* |

## What you'll be able to do after this section

- Write reusable prompt templates with variables and roles.
- Compose `prompt | llm | parser` chains with LCEL and call `.invoke()`.
- Get clean strings, lists, or JSON/objects out of an LLM.
- Add conversation memory with `RunnableWithMessageHistory`.

→ Start: **[01 · Prompts & messages](01_prompts_and_messages.md)**
