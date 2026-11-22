from langchain_core.embeddings import Embeddings

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
        _cached_embeddings = OllamaEmbeddings(
            base_url=settings.OLLAMA_BASE_URL,
            model=settings.OLLAMA_MODEL,
        )
        return _cached_embeddings

    if (
        provider == "openai"
        and settings.OPENAI_API_KEY
        and "your-openai-api-key" not in settings.OPENAI_API_KEY
        and settings.OPENAI_API_KEY != "mock-openai-key"
    ):
        from langchain_openai import OpenAIEmbeddings
        from pydantic import SecretStr

        _cached_embeddings = OpenAIEmbeddings(
            api_key=SecretStr(settings.OPENAI_API_KEY),
        )
        return _cached_embeddings

    # Free, high-performance local embeddings for Gemini or fallback
    try:
        import importlib
        import os

        torch_mod = importlib.import_module("torch")
        # Maximize CPU tensor parallelism across cores
        threads = min(8, os.cpu_count() or 4)
        torch_mod.set_num_threads(threads)
    except Exception:
        pass

    try:
        from langchain_community.embeddings import HuggingFaceEmbeddings

        _cached_embeddings = HuggingFaceEmbeddings(
            model_name="all-MiniLM-L6-v2",
            encode_kwargs={"batch_size": 64},
        )
        return _cached_embeddings
    except Exception:
        from langchain_openai import OpenAIEmbeddings
        from pydantic import SecretStr

        _cached_embeddings = OpenAIEmbeddings(
            api_key=SecretStr(settings.OPENAI_API_KEY),
        )
        return _cached_embeddings
