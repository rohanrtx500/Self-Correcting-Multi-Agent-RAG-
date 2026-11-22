import os

from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from app.config import settings


def get_openai_llm(temperature: float = 0.0) -> ChatOpenAI:
    """Instantiates and returns the ChatOpenAI client with timeouts and bounded retries.

    Args:
        temperature: Controls randomness in LLM generation. Default is 0.0.

    Returns:
        An instance of ChatOpenAI configured with active settings.
    """
    api_key = settings.OPENAI_API_KEY or os.environ.get("OPENAI_API_KEY") or "mock-openai-key"
    return ChatOpenAI(
        api_key=SecretStr(api_key),
        model=settings.OPENAI_MODEL,
        temperature=temperature,
        timeout=settings.REQUEST_TIMEOUT_SECONDS,
        max_retries=settings.MAX_RETRIES,
    )
