from pathlib import Path

from loguru import logger

from app.utils.timing import time_block
from app.vectorstore.chroma import get_vector_store
from app.vectorstore.loader import load_file, split_documents


class IngestionManager:
    """Manages document loading, chunking, and insertion into the vector database."""

    def __init__(self, persist_directory: str | None = None) -> None:
        """Initializes the IngestionManager.

        Args:
            persist_directory: Folder path to store ChromaDB files.
        """
        self.persist_directory = persist_directory
        self.vector_store = get_vector_store(persist_directory=self.persist_directory)

    def ingest_file(
        self,
        file_path: str | Path,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
    ) -> int:
        """Loads, splits, and embeds a single file into the vector store.

        Args:
            file_path: Path to the target document.
            chunk_size: Character limit per chunk.
            chunk_overlap: Characters shared between consecutive chunks.

        Returns:
            The number of chunks successfully ingested.
        """
        path = Path(file_path)
        logger.info(f"Ingesting file: {path.name}")

        try:
            with time_block() as timing:
                # 1. Load the document(s)
                raw_docs = load_file(path)
                logger.info(f"Loaded {len(raw_docs)} document pages/segments.")

                # 2. Split documents
                split_docs = split_documents(
                    raw_docs, chunk_size=chunk_size, chunk_overlap=chunk_overlap
                )
                logger.info(f"Split document into {len(split_docs)} chunks.")

                # 3. Add metadata details to check or search
                for idx, doc in enumerate(split_docs):
                    doc.metadata.setdefault("source", str(path))
                    doc.metadata.setdefault("title", path.stem)
                    doc.metadata.setdefault("chunk_index", idx)

                # 4. Insert chunks into Chroma DB
                if split_docs:
                    self.vector_store.add_documents(split_docs)

            logger.info(
                f"Successfully ingested {len(split_docs)} chunks from {path.name} in {timing['duration']:.3f}s."
            )
            return len(split_docs)

        except Exception as e:
            logger.error(f"Failed to ingest file {file_path}: {e}")
            raise e

    def ingest_directory(
        self,
        dir_path: str | Path,
        supported_extensions: tuple[str, ...] = (".txt", ".md", ".pdf", ".json"),
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
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

        for file_item in path.rglob("*"):
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
