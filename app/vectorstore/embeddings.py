from langchain_core.embeddings import Embeddings

from app.config import settings


def get_embeddings() -> Embeddings:
    """Instantiates and returns the configured embedding model.

    Returns:
        An instance of LangChain Embeddings.
    """
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
        return OllamaEmbeddings(
            base_url=settings.OLLAMA_BASE_URL,
            model=settings.OLLAMA_MODEL,
        )

    if (
        provider == "openai"
        and settings.OPENAI_API_KEY
        and "your-openai-api-key" not in settings.OPENAI_API_KEY
        and settings.OPENAI_API_KEY != "mock-openai-key"
    ):
        from langchain_openai import OpenAIEmbeddings
        from pydantic import SecretStr

        return OpenAIEmbeddings(
            api_key=SecretStr(settings.OPENAI_API_KEY),
        )

    # Free, high-performance local embeddings for Gemini or fallback
    try:
        from langchain_community.embeddings import HuggingFaceEmbeddings

        return HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    except Exception:
        from langchain_openai import OpenAIEmbeddings
        from pydantic import SecretStr

        return OpenAIEmbeddings(
            api_key=SecretStr(settings.OPENAI_API_KEY),
        )
