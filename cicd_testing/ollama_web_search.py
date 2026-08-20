"""
Give qwen2.5-coder:14b (or any tool-calling model) live web access via Ollama.

Setup on your machine:
    pip install ollama ddgs

Run:
    python ollama_web_search.py
"""

import ollama
from ddgs import DDGS


def web_search(query: str, max_results: int = 5) -> str:
    """Search the web and return a short summary of results."""
    with DDGS() as ddgs:
        results = list(ddgs.text(query, max_results=max_results))
    if not results:
        return "No results found."
    lines = []
    for r in results:
        lines.append(f"- {r['title']}: {r['body']} ({r['href']})")
    return "\n".join(lines)


# Tool schema the model can call
tools = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the internet for current, real-time information.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query",
                    }
                },
                "required": ["query"],
            },
        },
    }
]

available_functions = {"web_search": web_search}


def chat_with_web_access(prompt: str, model: str = "qwen2.5-coder:14b"):
    messages = [{"role": "user", "content": prompt}]

    response = ollama.chat(model=model, messages=messages, tools=tools)

    # If model decided to call a tool
    if response["message"].get("tool_calls"):
        messages.append(response["message"])
        for tool_call in response["message"]["tool_calls"]:
            fn_name = tool_call["function"]["name"]
            fn_args = tool_call["function"]["arguments"]
            print(f"[calling tool: {fn_name}({fn_args})]")

            fn = available_functions[fn_name]
            result = fn(**fn_args)

            messages.append(
                {
                    "role": "tool",
                    "content": result,
                }
            )

        # Get final answer using tool results
        final_response = ollama.chat(model=model, messages=messages)
        return final_response["message"]["content"]

    return response["message"]["content"]


if __name__ == "__main__":
    question = input("Ask something (needs current info to trigger search): ")
    answer = chat_with_web_access(question)
    print("\n--- Answer ---")
    print(answer)