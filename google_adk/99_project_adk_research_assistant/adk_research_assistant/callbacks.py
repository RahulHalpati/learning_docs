"""A simple guardrail callback for the capstone."""
from google.adk.models.llm_response import LlmResponse
from google.genai import types

BLOCKED = ("password", "credit card", "ssn")


def safety_guard(callback_context, llm_request):
    """Block requests mentioning sensitive credentials (before_model_callback).

    Returns None to proceed, or an LlmResponse to short-circuit the model call.
    """
    text = str(llm_request.contents).lower()
    if any(term in text for term in BLOCKED):
        return LlmResponse(content=types.Content(
            role="model",
            parts=[types.Part(text="I can't help with sensitive credentials.")]))
    return None
