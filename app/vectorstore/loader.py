import json
from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_core.documents import Document

# Attempt to load latest TextSplitter path, with fallback
try:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
except ImportError:
    from langchain.text_splitter import RecursiveCharacterTextSplitter  # type: ignore[no-redef]


def load_file(file_path: str | Path) -> list[Document]:
    """Loads a document from the local filesystem based on its extension.

    Supports TXT, MD, PDF, and JSON.

    Args:
        file_path: Absolute or relative path to the file.

    Returns:
        List of loaded Document objects.

    Raises:
        ValueError: If file format is unsupported.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    suffix = path.suffix.lower()

    if suffix in (".txt", ".md"):
        txt_loader = TextLoader(str(path), encoding="utf-8")
        return txt_loader.load()
    elif suffix == ".pdf":
        pdf_loader = PyPDFLoader(str(path))
        return pdf_loader.load()
    elif suffix == ".json":
        with open(path, encoding="utf-8") as f:
            data = json.load(f)

        documents = []
        # JSON can contain direct key-value pairs or structured content list
        if isinstance(data, list):
            for idx, item in enumerate(data):
                content = item.get("text") or item.get("content") or json.dumps(item)
                metadata = item.get("metadata") or {}
                metadata.setdefault("source", f"{path}#chunk{idx}")
                documents.append(Document(page_content=str(content), metadata=metadata))
        elif isinstance(data, dict):
            content = data.get("text") or data.get("content") or json.dumps(data)
            metadata = data.get("metadata") or {}
            metadata.setdefault("source", str(path))
            documents.append(Document(page_content=str(content), metadata=metadata))
        return documents
    else:
        raise ValueError(f"Unsupported file format: {suffix}")


def split_documents(
    documents: list[Document], chunk_size: int = 1000, chunk_overlap: int = 200
) -> list[Document]:
    """Splits loaded documents recursively into chunks.

    Args:
        documents: A list of Document objects.
        chunk_size: Maximum character length of each chunk.
        chunk_overlap: Overlap character count between adjacent chunks.

    Returns:
        A list of split/chunked Document objects.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        is_separator_regex=False,
    )
    return splitter.split_documents(documents)
