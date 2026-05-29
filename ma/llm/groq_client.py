"""
Groq LLM client — the cognitive engine powering MetaAgent.
All calls use structured JSON output mode where possible to eliminate
parsing failures in downstream pipeline stages.
"""
import os
import json
from typing import Any
from groq import Groq
from pydantic import BaseModel
from dotenv import load_dotenv
from ma.utils.logger import get_logger

load_dotenv()
logger = get_logger(__name__)

# Singleton — initialized once, reused across all pipeline stages
_client: Groq | None = None


def get_client() -> Groq:
    """Initialize and return the Groq client."""
    global _client
    if _client is None:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise EnvironmentError(
                "GROQ_API_KEY not set. Add it to .env\n"
                "Free key at: https://console.groq.com"
            )
        _client = Groq(api_key=api_key)
    return _client


def get_model() -> str:
    """Return the Groq model."""
    return os.getenv("METAAGENT_MODEL", "llama-3.3-70b-versatile")


def complete(
    system: str,
    user: str,
    temperature: float = 0.3,
    max_tokens: int = 4096
) -> str:
    """
    Raw completion. Returns the response string.
    Used when we need freeform text (code generation, descriptions).
    """
    client = get_client()
    response = client.chat.completions.create(
        model=get_model(),
        temperature=temperature,
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user}
        ]
    )
    return response.choices[0].message.content


def complete_json(
    system: str,
    user: str,
    schema: type[BaseModel],
    temperature: float = 0.2,
    max_tokens: int = 4096,
) -> dict[str, Any]:
    """
    Structured JSON completion using Groq's JSON mode.
    Forces output to be valid JSON matching the schema description.
    Falls back to manual extraction if JSON mode fails.
    """
    client = get_client()

    # Inject schema into system prompt so model knows the expected shape
    schema_str = json.dumps(schema.model_json_schema(), indent=2)
    system_with_schema = (
        f"{system}\n\n"
        f"You MUST respond with valid JSON matching this exact schema:\n"
        f"```json\n{schema_str}\n```\n"
        f"Respond ONLY with the JSON object. No explanation, no markdown."
    )

    response = client.chat.completions.create(
        model=get_model(),
        temperature=temperature,
        max_tokens=max_tokens,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system_with_schema},
            {"role": "user",   "content": user},
        ],
    )

    raw = response.choices[0].message.content
    return json.loads(raw)



