from langchain_core.language_models.chat_models import BaseChatModel
from pydantic import SecretStr

from app.config import settings


def get_gemini_llm(temperature: float = 0.0) -> BaseChatModel:
    """Instantiates and returns the Gemini LLM client.

    Attempts using ChatGoogleGenerativeAI if available, or falls back to
    Google's official OpenAI-compatible endpoint interface.

    Args:
        temperature: Controls randomness in LLM generation. Default is 0.0.

    Returns:
        An instance of BaseChatModel configured for Google Gemini.
    """
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(  # type: ignore[no-any-return]
            google_api_key=SecretStr(settings.GEMINI_API_KEY),
            model=settings.GEMINI_MODEL,
            temperature=temperature,
            max_retries=3,
        )
    except ImportError:
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            api_key=SecretStr(settings.GEMINI_API_KEY),
            model=settings.GEMINI_MODEL,
            temperature=temperature,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
            max_retries=3,
        )
