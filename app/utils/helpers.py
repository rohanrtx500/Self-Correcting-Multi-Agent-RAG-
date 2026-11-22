from collections.abc import Sequence
from typing import Any

from langchain_core.documents import Document


def extract_text_content(content: Any) -> str:
    """Safely extracts clean string text from LangChain message content (str or list of blocks).

    Handles multimodal models like Google Gemini that return content as a list of dicts.

    Args:
        content: Raw content from BaseMessage.content.

    Returns:
        Clean concatenated text string.
    """
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and "text" in block:
                parts.append(str(block["text"]))
            elif hasattr(block, "text"):
                parts.append(str(block.text))
        return "".join(parts)
    return str(content)


def format_documents_to_string(documents: Sequence[Document]) -> str:
    """Formats a sequence of Documents into a single structured string for LLM prompts.

    Args:
        documents: A sequence of LangChain Document objects.

    Returns:
        A string formatted with document markers and contents.
    """
    formatted_docs = []
    for i, doc in enumerate(documents, 1):
        source = doc.metadata.get("source", "Unknown")
        title = doc.metadata.get("title", f"Document {i}")
        content = doc.page_content.strip()
        formatted_docs.append(
            f"--- DOCUMENT {i} (Title: {title} | Source: {source}) ---\n{content}"
        )
    return "\n\n".join(formatted_docs)


def extract_document_sources(documents: Sequence[Document]) -> list[str]:
    """Extracts unique source metadata locations from documents.

    Args:
        documents: A list of Document objects.

    Returns:
        A list of unique source identifiers (e.g., file paths, URLs).
    """
    sources = set()
    for doc in documents:
        source = doc.metadata.get("source")
        if source:
            sources.add(str(source))
    return sorted(list(sources))


def clean_web_results(results: list[dict[str, Any]]) -> list[Document]:
    """Cleans raw web search responses and wraps them into standard Document formats.

    Args:
        results: List of Tavily results dictionary.

    Returns:
        List of formatted Document objects.
    """
    cleaned_docs = []
    for idx, res in enumerate(results):
        title = res.get("title", f"Web Search Result {idx}")
        url = res.get("url", "N/A")
        content = res.get("content", "")

        # Wrap in Document format expected by the state and nodes
        cleaned_docs.append(
            Document(
                page_content=content,
                metadata={
                    "source": url,
                    "title": title,
                    "type": "web_search",
                },
            )
        )
    return cleaned_docs
