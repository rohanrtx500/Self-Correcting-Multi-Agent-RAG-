from langchain_core.language_models.chat_models import BaseChatModel

from app.config import settings
from app.llm.gemini import get_gemini_llm
from app.llm.groq import get_groq_llm
from app.llm.openai import get_openai_llm


def get_llm(temperature: float = 0.0) -> BaseChatModel:
    """Factory function to retrieve the configured language model.

    Args:
        temperature: Controls randomness in LLM generation. Default is 0.0.

    Returns:
        An instance of BaseChatModel matching selection in configuration.

    Raises:
        ValueError: If provider name is unsupported.
        ImportError: If Ollama client cannot be imported.
    """
    provider = settings.LLM_PROVIDER.lower()

    if provider == "openai":
        return get_openai_llm(temperature=temperature)
    elif provider == "groq":
        return get_groq_llm(temperature=temperature)
    elif provider == "gemini":
        return get_gemini_llm(temperature=temperature)
    elif provider == "ollama":
        try:
            from langchain_community.chat_models import ChatOllama
        except ImportError as e:
            try:
                from langchain_community.chat_models.ollama import ChatOllama as FallbackOllama

                ChatOllama = FallbackOllama  # noqa: N806
            except ImportError:
                raise ImportError(
                    "ChatOllama is not available. Please install langchain-community or langchain-ollama."
                ) from e

        # Supports local execution via Ollama
        return ChatOllama(  # type: ignore[no-any-return]
            base_url=settings.OLLAMA_BASE_URL,
            model=settings.OLLAMA_MODEL,
            temperature=temperature,
        )
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")
