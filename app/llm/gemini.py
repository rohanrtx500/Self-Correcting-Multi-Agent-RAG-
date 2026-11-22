from langchain_core.language_models.chat_models import BaseChatModel
from pydantic import SecretStr

from app.config import settings


def get_gemini_llm(temperature: float = 0.0) -> BaseChatModel:
    """Instantiates and returns the Gemini LLM client with timeouts and bounded retries.

    Attempts using ChatGoogleGenerativeAI if available, or falls back to
    Google's official OpenAI-compatible endpoint interface.

    Args:
        temperature: Controls randomness in LLM generation. Default is 0.0.

    Returns:
        An instance of BaseChatModel configured for Google Gemini.
    """
    api_key_secret = SecretStr(settings.GEMINI_API_KEY) if settings.GEMINI_API_KEY else None

    try:
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(
            google_api_key=api_key_secret,
            model=settings.GEMINI_MODEL,
            temperature=temperature,
            max_retries=settings.MAX_RETRIES,
            timeout=settings.REQUEST_TIMEOUT_SECONDS,
        )
    except ImportError:
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            api_key=api_key_secret,
            model=settings.GEMINI_MODEL,
            temperature=temperature,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
            max_retries=settings.MAX_RETRIES,
            timeout=settings.REQUEST_TIMEOUT_SECONDS,
        )
