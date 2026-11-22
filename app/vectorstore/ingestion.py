import hashlib
from pathlib import Path
from typing import Any

from langchain_core.documents import Document
from loguru import logger

from app.config import settings
from app.utils.timing import time_block
from app.vectorstore.chroma import get_vector_store, update_bm25_index
from app.vectorstore.loader import load_file, split_documents


def sanitize_metadata(metadata: dict[str, Any]) -> dict[str, str | int | float | bool]:
    """Ensures metadata values are valid scalar types accepted by ChromaDB.

    ChromaDB rejects None, nested lists, or dictionaries in metadata.
    """
    clean_meta: dict[str, str | int | float | bool] = {}
    for k, v in metadata.items():
        if v is None:
            continue
        if isinstance(v, (str, int, float, bool)):
            clean_meta[k] = v
        else:
            clean_meta[k] = str(v)
    return clean_meta


def compute_content_hash(text: str) -> str:
    """Computes a SHA-256 hash of text content for duplicate detection."""
    return hashlib.sha256(text.strip().encode("utf-8")).hexdigest()


# Global in-memory cache for indexed hashes to eliminate repeated disk deserialization
_global_indexed_hashes: set[str] | None = None


class IngestionManager:
    """Manages document loading, deduplication, chunking, and insertion into the vector database."""

    def __init__(self, persist_directory: str | None = None) -> None:
        """Initializes the IngestionManager.

        Args:
            persist_directory: Folder path to store ChromaDB files.
        """
        self.persist_directory = persist_directory
        self.vector_store = get_vector_store(persist_directory=self.persist_directory)
        self._indexed_hashes: set[str] = set()
        self._load_existing_hashes()

    def _load_existing_hashes(self) -> None:
        """Preloads existing chunk hashes from ChromaDB to avoid duplicate indexing."""
        global _global_indexed_hashes

        # Use memory cache for default persist directory
        if self.persist_directory is None and _global_indexed_hashes is not None:
            self._indexed_hashes = _global_indexed_hashes
            return

        try:
            if hasattr(self.vector_store, "_collection"):
                existing = self.vector_store._collection.get(include=["metadatas"])
                existing_metas = existing.get("metadatas") if existing else None
                if existing and existing_metas is not None:
                    for meta in existing_metas:
                        if meta and isinstance(meta, dict) and "content_hash" in meta:
                            self._indexed_hashes.add(str(meta["content_hash"]))
                if self.persist_directory is None:
                    _global_indexed_hashes = self._indexed_hashes
                logger.debug(
                    f"Loaded {len(self._indexed_hashes)} existing hashes for deduplication."
                )
        except Exception as e:
            logger.debug(f"Could not preload existing hashes from vector store: {e}")

    def ingest_file(
        self,
        file_path: str | Path,
        chunk_size: int | None = None,
        chunk_overlap: int | None = None,
    ) -> int:
        """Loads, splits, deduplicates, and embeds a single file into the vector store.

        Args:
            file_path: Path to the target document.
            chunk_size: Character limit per chunk. Defaults to settings.CHUNK_SIZE.
            chunk_overlap: Shared characters between chunks. Defaults to settings.CHUNK_OVERLAP.

        Returns:
            The number of chunks successfully ingested.
        """
        path = Path(file_path)
        logger.info(f"Ingesting file: {path.name}")

        size = chunk_size if chunk_size is not None else settings.CHUNK_SIZE
        overlap = chunk_overlap if chunk_overlap is not None else settings.CHUNK_OVERLAP
        if overlap >= size:
            overlap = max(0, size // 5)

        try:
            with time_block() as timing:
                # 1. Load the document(s)
                raw_docs = load_file(path)
                if not raw_docs:
                    logger.warning(f"File {path.name} contained no text content to ingest.")
                    return 0

                logger.info(f"Loaded {len(raw_docs)} document pages/segments.")

                # 2. Split documents into chunks
                split_docs = split_documents(raw_docs, chunk_size=size, chunk_overlap=overlap)
                logger.info(f"Split document into {len(split_docs)} raw chunks.")

                # 3. Deduplicate chunks using content hashing
                unique_docs: list[Document] = []
                for idx, doc in enumerate(split_docs):
                    content = doc.page_content.strip()
                    if not content:
                        continue

                    chunk_hash = compute_content_hash(content)
                    if chunk_hash in self._indexed_hashes:
                        logger.debug(f"Skipping duplicate chunk {idx} of {path.name}.")
                        continue

                    self._indexed_hashes.add(chunk_hash)

                    # Build rich, sanitized metadata
                    meta = doc.metadata.copy()
                    meta.setdefault("source", str(path))
                    meta.setdefault("title", path.stem)
                    meta.setdefault("chunk_index", idx)
                    meta["content_hash"] = chunk_hash
                    meta["doc_id"] = f"{path.stem}_{idx}"

                    doc.metadata = sanitize_metadata(meta)
                    unique_docs.append(doc)

                # 4. Insert chunks into Chroma DB
                if unique_docs:
                    self.vector_store.add_documents(unique_docs)
                    # Update hybrid BM25 index with fresh documents
                    update_bm25_index(unique_docs)
                else:
                    logger.info(f"All chunks from {path.name} were duplicates or empty; 0 added.")
                    return 0

            logger.info(
                f"Successfully ingested {len(unique_docs)} chunks from {path.name} in {timing['duration']:.3f}s."
            )
            return len(unique_docs)

        except Exception as e:
            logger.error(f"Failed to ingest file {file_path}: {e}")
            raise e

    def ingest_directory(
        self,
        dir_path: str | Path,
        supported_extensions: tuple[str, ...] = (".txt", ".md", ".pdf", ".json"),
        chunk_size: int | None = None,
        chunk_overlap: int | None = None,
    ) -> int:
        """Walks a directory and ingests all supported documents.

        Args:
            dir_path: Directory path to scan.
            supported_extensions: File extensions to ingest.
            chunk_size: Size of each text chunk.
            chunk_overlap: Overlap size between chunks.

        Returns:
            Total count of chunks ingested across all files.
        """
        path = Path(dir_path)
        if not path.is_dir():
            raise NotADirectoryError(f"{dir_path} is not a valid directory.")

        total_chunks = 0
        logger.info(f"Scanning directory: {path}")

        for file_item in sorted(path.rglob("*")):
            if file_item.is_file() and file_item.suffix.lower() in supported_extensions:
                try:
                    chunks_count = self.ingest_file(
                        file_item, chunk_size=chunk_size, chunk_overlap=chunk_overlap
                    )
                    total_chunks += chunks_count
                except Exception as e:
                    logger.warning(f"Skipping file {file_item.name} due to ingestion error: {e}")

        logger.info(f"Directory ingestion completed. Total chunks added: {total_chunks}")
        return total_chunks
