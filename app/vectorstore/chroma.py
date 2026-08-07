from langchain_chroma import Chroma
from langchain_core.vectorstores import VectorStoreRetriever

from app.config import settings
from app.vectorstore.embeddings import get_embeddings

# --- Globals for caching Chroma instances ---
_vector_store: Chroma | None = None
_default_retriever: VectorStoreRetriever | None = None


def get_vector_store(persist_directory: str | None = None) -> Chroma:
    """Retrieves or creates a ChromaDB vector store instance.

    Uses a cached singleton if no custom persist_directory is specified.

    Args:
        persist_directory: Custom folder path to store database files.
            If None, uses settings.CHROMA_PERSIST_DIRECTORY.

    Returns:
        An instance of Chroma vector store.
    """
    global _vector_store

    # Bypass cache if custom persist directory is provided (e.g. during testing)
    if persist_directory is not None:
        embeddings = get_embeddings()
        return Chroma(
            collection_name=settings.CHROMA_COLLECTION_NAME,
            embedding_function=embeddings,
            persist_directory=persist_directory,
        )

    # Return cached singleton instance
    if _vector_store is None:
        directory = settings.CHROMA_PERSIST_DIRECTORY
        embeddings = get_embeddings()
        _vector_store = Chroma(
            collection_name=settings.CHROMA_COLLECTION_NAME,
            embedding_function=embeddings,
            persist_directory=directory,
        )
    return _vector_store


def get_retriever(
    persist_directory: str | None = None,
    search_type: str = "similarity",
    k: int = 4,
    fetch_k: int = 20,
    lambda_mult: float = 0.5,
) -> VectorStoreRetriever:
    """Configures and returns the retriever interface of the vector store.

    Uses a cached default retriever instance if parameters match default settings.

    Args:
        persist_directory: Custom folder path for the vector store database.
        search_type: Search algorithm to use ("similarity" or "mmr").
        k: Number of documents to retrieve.
        fetch_k: Number of documents to pass to MMR algorithm.
        lambda_mult: Diversity factor for MMR search.

    Returns:
        VectorStoreRetriever config.
    """
    global _default_retriever

    # Use cache only for default parameter configurations
    is_default = persist_directory is None and search_type == "similarity" and k == 4

    if not is_default:
        vector_store = get_vector_store(persist_directory=persist_directory)
        search_kwargs: dict = {"k": k}
        if search_type == "mmr":
            search_kwargs.update({"fetch_k": fetch_k, "lambda_mult": lambda_mult})
        return vector_store.as_retriever(
            search_type=search_type,
            search_kwargs=search_kwargs,
        )

    if _default_retriever is None:
        vector_store = get_vector_store()
        _default_retriever = vector_store.as_retriever(
            search_type="similarity",
            search_kwargs={"k": 4},
        )
    return _default_retriever
