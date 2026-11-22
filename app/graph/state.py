from typing import Any, TypedDict

from langchain_core.documents import Document


class AgentState(TypedDict, total=False):
    """The state representation of our self-correcting RAG workflow.

    Tracks data flow, decisions, timings, retries, and errors.
    """

    question: str
    original_question: str
    documents: list[Document]
    retrieved_chunks: list[str]
    search_required: bool
    generation: str
    hallucination_score: str  # "Grounded" or "Hallucinated"
    document_score: str  # "Relevant" or "Not Relevant"
    steps: list[str]
    metadata: dict[str, Any]
    execution_time: dict[str, float]
    retry_count: int
    query_rewrite_count: int
    grounding_reason: str
    insufficient_evidence: bool
    sources: list[str]
    web_results: list[dict[str, Any]]
    errors: list[str]
