import os
from typing import Any, cast

from langchain_core.embeddings import Embeddings
from pydantic import SecretStr

from app.config import settings

# Global cached embedding model singleton
_cached_embeddings: Embeddings | None = None


def get_embeddings() -> Embeddings:
    """Instantiates and returns the configured embedding model.

    Uses a cached singleton to avoid reloading transformer weights on every call.

    Returns:
        An instance of LangChain Embeddings.
    """
    global _cached_embeddings

    if _cached_embeddings is not None:
        return _cached_embeddings

    provider = settings.LLM_PROVIDER.lower()

    if provider == "ollama":
        try:
            from langchain_community.embeddings import OllamaEmbeddings
        except ImportError as e:
            try:
                from langchain_community.embeddings.ollama import OllamaEmbeddings
            except ImportError:
                raise ImportError(
                    "OllamaEmbeddings is not available. Please install langchain-community or langchain-ollama."
                ) from e
        _cached_embeddings = cast(
            Embeddings,
            OllamaEmbeddings(
                base_url=settings.OLLAMA_BASE_URL,
                model=settings.OLLAMA_MODEL,
            ),
        )
        return _cached_embeddings

    if (
        provider == "openai"
        and settings.OPENAI_API_KEY
        and "your-openai-api-key" not in settings.OPENAI_API_KEY
        and not settings.OPENAI_API_KEY.startswith("mock-")
    ):
        from langchain_openai import OpenAIEmbeddings

        _cached_embeddings = cast(
            Embeddings,
            OpenAIEmbeddings(
                api_key=SecretStr(settings.OPENAI_API_KEY),
            ),
        )
        return _cached_embeddings

    if provider == "gemini":
        gemini_key = settings.GEMINI_API_KEY or os.environ.get("GEMINI_API_KEY", "")
        if (
            gemini_key
            and "your-gemini-api-key" not in gemini_key
            and not gemini_key.startswith("mock-")
        ):
            try:
                from langchain_google_genai import GoogleGenerativeAIEmbeddings

                # Set in environ so Google SDK picks it up directly
                os.environ["GOOGLE_API_KEY"] = gemini_key

                kwargs: dict[str, Any] = {
                    "model": "models/text-embedding-004",
                    "google_api_key": SecretStr(gemini_key),
                }
                _cached_embeddings = cast(Embeddings, GoogleGenerativeAIEmbeddings(**kwargs))
                return _cached_embeddings
            except Exception as e:
                from loguru import logger

                logger.warning(f"Failed to initialize GoogleGenerativeAIEmbeddings: {e}")

    # Local CPU embeddings using sentence-transformers / HuggingFace if available
    try:
        from langchain_community.embeddings import HuggingFaceEmbeddings

        _cached_embeddings = cast(
            Embeddings,
            HuggingFaceEmbeddings(
                model_name="all-MiniLM-L6-v2",
                encode_kwargs={"batch_size": 64},
            ),
        )
        return _cached_embeddings
    except Exception:
        pass

    # If an OpenAI key is configured, fall back to OpenAI embeddings
    if (
        settings.OPENAI_API_KEY
        and "your-openai-api-key" not in settings.OPENAI_API_KEY
        and not settings.OPENAI_API_KEY.startswith("mock-")
    ):
        from langchain_openai import OpenAIEmbeddings

        _cached_embeddings = cast(
            Embeddings,
            OpenAIEmbeddings(
                api_key=SecretStr(settings.OPENAI_API_KEY),
            ),
        )
        return _cached_embeddings

    # Final fallback for offline environments or minimal CI containers without GPU/keys
    from langchain_core.embeddings import FakeEmbeddings

    _cached_embeddings = cast(Embeddings, FakeEmbeddings(size=384))
    return _cached_embeddings
