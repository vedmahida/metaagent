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



