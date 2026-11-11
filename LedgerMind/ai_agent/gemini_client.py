
import os
from functools import lru_cache

from google import genai
from google.genai import types

# Load .env locally when python-dotenv is installed.
# Production deployments should use environment variables.
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


DEFAULT_MODEL = "gemini-3.8-flash"


def get_model_name() -> str:
    """Return the configured Gemini model name."""
    return os.getenv("GEMINI_MODEL", DEFAULT_MODEL).strip()


@lru_cache(maxsize=1)
def get_gemini_client():
    """
    Create and reuse one Gemini API client.

    API credentials must come from environment variables.
    Never hardcode API keys in this file.
    """
    api_key = (
        os.getenv("GEMINI_API_KEY")
        or os.getenv("GOOGLE_API_KEY")
    )

    if not api_key:
        raise RuntimeError(
            "Gemini API key is missing. "
            "Configure GEMINI_API_KEY in your environment."
        )

    return genai.Client(api_key=api_key)


def generate_text(
    prompt: str,
    system_instruction: str | None = None,
    temperature: float = 0.2,
    max_output_tokens: int = 2048,
) -> str:
    """Generate a text response using Gemini."""

    if not prompt or not prompt.strip():
        raise ValueError("Prompt cannot be empty.")

    if not 0 <= temperature <= 2:
        raise ValueError("Temperature must be between 0 and 2.")

    if max_output_tokens < 1:
        raise ValueError("max_output_tokens must be positive.")

    config = types.GenerateContentConfig(
        temperature=temperature,
        max_output_tokens=max_output_tokens,
        system_instruction=system_instruction,
    )

    response = get_gemini_client().models.generate_content(
        model=get_model_name(),
        contents=prompt,
        config=config,
    )

    if not response.text:
        raise RuntimeError(
            "Gemini returned an empty response."
        )

    return response.text.strip()

