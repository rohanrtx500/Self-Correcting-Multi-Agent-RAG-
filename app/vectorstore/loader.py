import json
from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_core.documents import Document

# Attempt to load latest TextSplitter path, with fallback
try:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
except ImportError:
    from langchain.text_splitter import RecursiveCharacterTextSplitter  # type: ignore[no-redef]


def _load_json_file(path: Path) -> list[Document]:
    """Helper to parse and extract Documents from a JSON file."""
    with open(path, encoding="utf-8") as f:
        content = f.read().strip()
        if not content:
            return []
        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            raise ValueError(f"Malformed JSON file: {e}") from e

    documents: list[Document] = []
    if isinstance(data, list):
        for idx, item in enumerate(data):
            if not item:
                continue
            content_val = (
                item.get("text")
                or item.get("content")
                or (json.dumps(item) if not isinstance(item, str) else item)
            )
            if not str(content_val).strip():
                continue
            metadata = item.get("metadata") if isinstance(item, dict) else {}
            metadata = metadata or {}
            metadata.setdefault("source", f"{path}#item{idx}")
            documents.append(Document(page_content=str(content_val), metadata=metadata))
    elif isinstance(data, dict):
        content_val = data.get("text") or data.get("content") or json.dumps(data)
        if str(content_val).strip():
            metadata = data.get("metadata") or {}
            metadata.setdefault("source", str(path))
            documents.append(Document(page_content=str(content_val), metadata=metadata))
    return documents


def load_file(file_path: str | Path) -> list[Document]:
    """Loads a document from the local filesystem based on its extension.

    Supports TXT, MD, PDF, and JSON.

    Args:
        file_path: Absolute or relative path to the file.

    Returns:
        List of loaded Document objects.

    Raises:
        FileNotFoundError: If file does not exist.
        ValueError: If file format is unsupported or file is empty/corrupt.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    # Check for empty file
    if path.stat().st_size == 0:
        return []

    suffix = path.suffix.lower()

    if suffix in (".txt", ".md"):
        txt_loader = TextLoader(str(path), encoding="utf-8")
        docs = txt_loader.load()
        return [doc for doc in docs if doc.page_content.strip()]
    elif suffix == ".pdf":
        try:
            pdf_loader = PyPDFLoader(str(path))
            docs = pdf_loader.load()
            return [doc for doc in docs if doc.page_content.strip()]
        except Exception:
            try:
                import pypdf

                reader = pypdf.PdfReader(str(path))
                fallback_docs = []
                for i, page in enumerate(reader.pages):
                    page_text = page.extract_text() or ""
                    if page_text.strip():
                        fallback_docs.append(
                            Document(
                                page_content=page_text,
                                metadata={"source": str(path), "page": i + 1},
                            )
                        )
                return fallback_docs
            except ImportError as ie:
                raise ValueError(
                    "PDF processing requires `pypdf`. Please run: pip install pypdf"
                ) from ie
    elif suffix == ".json":
        return _load_json_file(path)
    else:
        raise ValueError(f"Unsupported file format: {suffix}")


def split_documents(
    documents: list[Document],
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
) -> list[Document]:
    """Splits loaded documents recursively into chunks.

    Args:
        documents: A list of Document objects.
        chunk_size: Maximum character length of each chunk.
        chunk_overlap: Overlap character count between adjacent chunks.

    Returns:
        A list of split/chunked Document objects.
    """
    if not documents:
        return []

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        is_separator_regex=False,
    )
    return splitter.split_documents(documents)
