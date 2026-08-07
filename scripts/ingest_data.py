import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables before importing app configurations
load_dotenv()

# Add project root directory to path to support package importing
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

from loguru import logger

from app.vectorstore.ingestion import IngestionManager


def main() -> None:
    """CLI Entry point for data ingestion."""
    parser = argparse.ArgumentParser(
        description="Ingest text, markdown, PDF or JSON files into ChromaDB persistent vector store."
    )
    parser.add_argument(
        "--path",
        type=str,
        default="sample_documents",
        help="Path to the file or directory containing files to ingest.",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=1000,
        help="Max character size per document chunk.",
    )
    parser.add_argument(
        "--chunk-overlap",
        type=int,
        default=200,
        help="Overlap character count between consecutive chunks.",
    )

    args = parser.parse_args()

    # Resolve absolute path
    target_path = Path(args.path)
    if not target_path.is_absolute():
        target_path = Path(project_root) / target_path

    if not target_path.exists():
        logger.error(f"Target path does not exist: {target_path}")
        sys.exit(1)

    logger.info("Initializing Ingestion Manager...")
    manager = IngestionManager()

    try:
        if target_path.is_dir():
            logger.info(f"Starting directory ingestion from: {target_path}")
            count = manager.ingest_directory(
                dir_path=target_path,
                chunk_size=args.chunk_size,
                chunk_overlap=args.chunk_overlap,
            )
            logger.info(f"Directory ingestion success. Total chunks added: {count}")
        else:
            logger.info(f"Starting file ingestion from: {target_path}")
            count = manager.ingest_file(
                file_path=target_path,
                chunk_size=args.chunk_size,
                chunk_overlap=args.chunk_overlap,
            )
            logger.info(f"File ingestion success. Chunks added: {count}")

    except Exception as e:
        logger.error(f"Ingestion failed with error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
