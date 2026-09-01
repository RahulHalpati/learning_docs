# 03: Output parsers & structured output

> **Level:** Intermediate · **Prerequisites:** [02 · LCEL chains](02_lcel_chains.md)
> **Time:** ~1 hour · **Verified:** 2026-06-15 (langchain-core 1.3.2)

## Why this matters

An LLM returns an `AIMessage` full of free text. Your *program* usually wants something cleaner: a plain string, a list, or structured data with fields. **Output parsers** are the last link in a chain that convert the model's reply into what your code can use. In RAG you'll at least use `StrOutputParser`; for anything that feeds another system (APIs, databases) you'll want structured output.

## `StrOutputParser` — just give me the text

You've already used it. It pulls `.content` out of the `AIMessage` so the chain returns a `str`:

```python
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
chain = llm | StrOutputParser()
print(repr(chain.invoke("hi")))      # 'Hello! How can I help you today?'  (a str, not an AIMessage)
```

This is the default ending for text-answer chains, including RAG.

## `CommaSeparatedListOutputParser` — get a list

When you ask the model for a list, this parser turns the comma-separated reply into a Python list:

```python
from langchain_core.output_parsers import CommaSeparatedListOutputParser

parser = CommaSeparatedListOutputParser()
print(parser.parse("apple, banana, cherry"))
```

**Output (real run):**

```text
['apple', 'banana', 'cherry']
```

Parsers also provide **format instructions** (`parser.get_format_instructions()`) you can insert into your prompt, telling the model exactly how to format its reply so the parser succeeds.

## JSON output — get structured data

For data with fields, ask the model for JSON and parse it with `JsonOutputParser`:

```python
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
prompt = ChatPromptTemplate.from_template(
    "Return ONLY a JSON object with keys name, language, years for a fictional developer. {request}"
)

chain = prompt | llm | JsonOutputParser()
out = chain.invoke({"request": "give me a profile"})
print("parsed:", out, "| type:", type(out).__name__, "| years+1:", out["years"] + 1)
```

**Output (representative — your wording will differ):**

```text
parsed: {'name': 'Ada Lin', 'language': 'Python', 'years': 5} | type: dict | years+1: 6
```

The reply is now a real Python `dict` you can index and compute with — not a string you'd have to hand-parse.

```mermaid
flowchart LR
    L[LLM reply<br/>'{...}' text] --> JP[JsonOutputParser] --> D["dict<br/>out['years'] works"]
```

## `.with_structured_output()` — the robust way (real models)

Hand-writing "please reply in JSON" and hoping is fragile. Modern chat models support **`.with_structured_output(Schema)`**, which makes the model return data matching a schema you define (often via a Pydantic model), validated for you:

```python
from pydantic import BaseModel, Field

class Profile(BaseModel):
    name: str = Field(description="the person's name")
    language: str
    years: int = Field(description="years of experience")

# With a real model (Ollama/hosted) that supports tool/structured output:
# structured_llm = llm.with_structured_output(Profile)
# result = structured_llm.invoke("Ada has used Python for 5 years.")
# result  ->  Profile(name='Ada', language='Python', years=5)
```

This needs a real model with structured-output support, so it's **not run here** — but it's the production-grade choice: you get a typed `Profile` object, validated, instead of trusting raw text. Use `JsonOutputParser` when your model lacks the feature; prefer `.with_structured_output()` when it's available.

## Which parser when?

| You want | Use |
|----------|-----|
| plain answer text (most RAG) | `StrOutputParser` |
| a list of items | `CommaSeparatedListOutputParser` |
| structured data, simple model | `JsonOutputParser` (+ format instructions in the prompt) |
| structured data, capable model | `.with_structured_output(PydanticModel)` |

## Recap & next

- ✅ **Output parsers** are the final chain link that turns the `AIMessage` into usable data.
- ✅ `StrOutputParser` → clean `str` (the RAG default); `CommaSeparatedListOutputParser` → `list`; `JsonOutputParser` → `dict`.
- ✅ Parsers can supply **format instructions** for the prompt so the model formats correctly.
- ✅ For robust structured data on a capable model, prefer **`.with_structured_output(Schema)`** (validated objects).
- ✅ Self-check: what does `StrOutputParser` extract, and when would you choose `.with_structured_output` over `JsonOutputParser`?

→ Next: **[04 · Memory & message history](04_memory_message_history.md)** — making a chain remember the conversation.

## Exercises

1. **Parse a list.** Build `prompt | llm | CommaSeparatedListOutputParser()` with a prompt asking for exactly three colours, comma-separated. Invoke and confirm you get a 3-element Python list.

<details><summary>Solution</summary>

```python
from langchain_core.output_parsers import CommaSeparatedListOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
prompt = ChatPromptTemplate.from_template("Name 3 colours as a comma-separated list, nothing else.")
chain = prompt | llm | CommaSeparatedListOutputParser()
print(chain.invoke({}))   # e.g. ['red', 'green', 'blue']
```

The chain output is a `list`, ready to iterate — no manual `.split(",")`.
</details>

2. **JSON to computation.** Using `JsonOutputParser` and a prompt that asks for a JSON object with integer `items` and `price` keys, build a chain and compute `items * price` from the result.

<details><summary>Solution</summary>

```python
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
prompt = ChatPromptTemplate.from_template(
    "Return ONLY a JSON object with integer keys items and price for a small order.")
out = (prompt | llm | JsonOutputParser()).invoke({})
print(out["items"] * out["price"])   # e.g. 30
```

Because the parser returns a real `dict`, you index fields and do arithmetic directly — the payoff of structured output over a raw string.
</details>

3. **Why format instructions?** A teammate's `JsonOutputParser` keeps failing because the model wraps JSON in prose ("Sure! Here's the JSON: ..."). What's the fix?

<details><summary>Solution</summary>

Insert the parser's **format instructions** into the prompt: `parser.get_format_instructions()` returns text telling the model to output *only* valid JSON in the expected shape. Add it to the prompt template so the model stops adding prose. (On a capable model, `.with_structured_output()` sidesteps the issue entirely by constraining the output format.)
</details>
