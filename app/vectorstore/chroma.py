from typing import Any

from langchain_chroma import Chroma
from langchain_core.documents import Document
from loguru import logger

from app.config import settings
from app.vectorstore.embeddings import get_embeddings
from app.vectorstore.hybrid import HybridRetriever, SimpleBM25

# --- Globals for caching Chroma and hybrid instances ---
_vector_store: Chroma | None = None
_default_retriever: Any = None
_bm25_index: SimpleBM25 | None = None


def _resolve_collection_name() -> str:
    """Returns provider-specific collection name to prevent vector dimension collisions."""
    provider = settings.LLM_PROVIDER.lower()
    base_name = settings.CHROMA_COLLECTION_NAME
    if base_name.startswith("test_"):
        return base_name
    if provider == "gemini":
        return f"{base_name}_gemini"
    elif provider == "openai":
        return f"{base_name}_openai"
    return base_name


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

    collection = _resolve_collection_name()

    # Bypass cache if custom persist directory is provided (e.g. during testing)
    if persist_directory is not None:
        embeddings = get_embeddings()
        return Chroma(
            collection_name=collection,
            embedding_function=embeddings,
            persist_directory=persist_directory,
        )

    # Return cached singleton instance
    if _vector_store is None:
        directory = settings.CHROMA_PERSIST_DIRECTORY
        embeddings = get_embeddings()
        _vector_store = Chroma(
            collection_name=collection,
            embedding_function=embeddings,
            persist_directory=directory,
        )
    return _vector_store


def update_bm25_index(documents: list[Document]) -> None:
    """Updates the global BM25 keyword index with newly ingested documents."""
    global _bm25_index
    if not documents:
        return

    if _bm25_index is None or not _bm25_index.corpus:
        _bm25_index = SimpleBM25(documents)
    else:
        # Combine existing corpus with new documents
        combined = _bm25_index.corpus + documents
        _bm25_index = SimpleBM25(combined)


def get_retriever(
    persist_directory: str | None = None,
    search_type: str = "similarity",
    k: int | None = None,
    fetch_k: int = 20,
    lambda_mult: float = 0.5,
) -> Any:
    """Configures and returns the retriever interface of the vector store.

    Integrates hybrid search (dense embeddings + BM25 keyword search) when enabled.

    Args:
        persist_directory: Custom folder path for the vector store database.
        search_type: Search algorithm to use ("similarity" or "mmr").
        k: Number of documents to retrieve. Defaults to settings.RETRIEVAL_TOP_K.
        fetch_k: Number of documents to pass to MMR algorithm.
        lambda_mult: Diversity factor for MMR search.

    Returns:
        A retriever runnable (VectorStoreRetriever or HybridRetriever).
    """
    global _default_retriever, _bm25_index

    top_k = k if k is not None else settings.RETRIEVAL_TOP_K

    # Use cache only for default parameter configurations
    is_default = (
        persist_directory is None
        and search_type == "similarity"
        and (k is None or k == settings.RETRIEVAL_TOP_K)
    )

    if not is_default:
        vector_store = get_vector_store(persist_directory=persist_directory)
        search_kwargs: dict[str, Any] = {"k": top_k}
        if search_type == "mmr":
            search_kwargs.update({"fetch_k": fetch_k, "lambda_mult": lambda_mult})
        base_retriever = vector_store.as_retriever(
            search_type=search_type,
            search_kwargs=search_kwargs,
        )
        if settings.HYBRID_SEARCH_ENABLED and _bm25_index is not None:
            return HybridRetriever(base_retriever, bm25=_bm25_index, top_k=top_k)
        return base_retriever

    if _default_retriever is None:
        vector_store = get_vector_store()
        base_retriever = vector_store.as_retriever(
            search_type="similarity",
            search_kwargs={"k": top_k},
        )

        # Attempt to warm up BM25 index from existing Chroma collection items if available
        if _bm25_index is None and settings.HYBRID_SEARCH_ENABLED:
            try:
                raw = vector_store._collection.get()
                raw_docs = raw.get("documents") if raw else None
                if raw and raw_docs:
                    corpus = [
                        Document(
                            page_content=doc,
                            metadata=(
                                (raw.get("metadatas") or [{}])[i] if raw.get("metadatas") else {}
                            ),
                        )
                        for i, doc in enumerate(raw_docs)
                    ]
                    _bm25_index = SimpleBM25(corpus)
                    logger.debug(f"Preloaded BM25 index with {len(corpus)} existing vector chunks.")
            except Exception as e:
                logger.debug(f"Could not preload BM25 index from Chroma: {e}")

        if settings.HYBRID_SEARCH_ENABLED and _bm25_index is not None:
            _default_retriever = HybridRetriever(base_retriever, bm25=_bm25_index, top_k=top_k)
        else:
            _default_retriever = base_retriever

    return _default_retriever
