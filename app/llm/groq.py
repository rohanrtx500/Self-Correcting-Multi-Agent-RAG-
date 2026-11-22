from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from app.config import settings


def get_groq_llm(temperature: float = 0.0) -> ChatOpenAI:
    """Instantiates and returns the Groq client via ChatOpenAI interface with timeouts.

    Args:
        temperature: Controls randomness in LLM generation. Default is 0.0.

    Returns:
        An instance of ChatOpenAI pointing to Groq's endpoint.
    """
    return ChatOpenAI(
        api_key=SecretStr(settings.GROQ_API_KEY) if settings.GROQ_API_KEY else None,
        model=settings.GROQ_MODEL,
        temperature=temperature,
        base_url="https://api.groq.com/openai/v1",
        timeout=settings.REQUEST_TIMEOUT_SECONDS,
        max_retries=settings.MAX_RETRIES,
    )
