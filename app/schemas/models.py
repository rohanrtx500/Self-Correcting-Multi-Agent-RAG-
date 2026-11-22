from typing import Any

from pydantic import BaseModel, Field, field_validator


# --- QUERY ENDPOINTS ---
class QueryRequest(BaseModel):
    """Payload to submit a query to the agentic RAG pipeline."""

    question: str = Field(
        ...,
        description="The question to be answered by the self-correcting RAG pipeline.",
        examples=["What are the architectural specifications for Project Helios?"],
        min_length=1,
        max_length=2000,
    )

    @field_validator("question")
    @classmethod
    def validate_question(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Question cannot be empty or whitespace only.")
        return cleaned


class QueryResponse(BaseModel):
    """The structured response from the self-correcting RAG pipeline."""

    question: str = Field(..., description="The original question queried.")
    answer: str = Field(..., description="The final grounded answer synthesized by the LLM.")
    sources: list[str] = Field(
        ...,
        description="Unique source links, paths, or web URLs referenced in the answer.",
    )
    steps: list[str] = Field(
        ...,
        description="List of nodes in the state graph traversed to reach the response.",
    )
    execution_time: dict[str, float] = Field(
        ...,
        description="Timing breakdown in seconds for each node execution.",
    )
    search_required: bool = Field(
        ...,
        description="Indicates if the system fell back to web search.",
    )
    retry_count: int = Field(
        ...,
        description="Number of retries triggered during hallucination grading loops.",
    )
    retrieved_chunks: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Retrieved document chunks and metadata.",
    )
    web_results: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Web search results from Tavily.",
    )
    errors: list[str] = Field(default_factory=list, description="Any warnings or errors.")


# --- INGESTION ENDPOINTS ---
class IngestionRequest(BaseModel):
    """Payload to request local document ingestion."""

    path: str = Field(
        ...,
        description="Absolute or relative file path or directory path to ingest.",
        examples=["sample_documents/company_policy.txt"],
        min_length=1,
        max_length=500,
    )
    chunk_size: int = Field(
        default=1000,
        ge=100,
        le=8000,
        description="Maximum length of characters per text segment chunk.",
    )
    chunk_overlap: int = Field(
        default=200,
        ge=0,
        le=2000,
        description="Character overlap size between consecutive chunks.",
    )

    @field_validator("path")
    @classmethod
    def validate_path(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Path cannot be empty or whitespace only.")
        return cleaned


class IngestionResponse(BaseModel):
    """The outcome status of the document ingestion request."""

    success: bool = Field(..., description="True if ingestion completed without system failures.")
    message: str = Field(..., description="User-facing explanation of the ingestion task.")
    chunks_count: int = Field(..., description="Total count of text chunks added to vector store.")


# --- SYSTEM STATES ---
class HealthStatus(BaseModel):
    """Health check response containing active providers and status."""

    status: str = Field(
        ..., description="API system health state: healthy, degraded, or unhealthy."
    )
    llm_provider: str = Field(
        ..., description="Active LLM provider (OpenAI, Groq, Ollama, Gemini)."
    )
    database_connected: bool = Field(
        ...,
        description="Indicates if Chroma database connection is functional.",
    )
    details: dict[str, str] = Field(
        default_factory=dict,
        description="Health diagnostics per subsystem.",
    )


class MetricsPayload(BaseModel):
    """Internal latency and performance monitoring stats."""

    uptime_seconds: float = Field(..., description="FastAPI web application running uptime.")
    queries_processed: int = Field(..., description="Total count of processed query requests.")
    average_query_latency: float = Field(
        ...,
        description="Average execution duration of the query pipeline in seconds.",
    )
    error_count: int = Field(
        default=0,
        description="Total count of failed queries or runtime errors.",
    )


# --- KNOWLEDGE BASE / DOCUMENT MODELS ---
class DocumentItem(BaseModel):
    """Metadata summary of an ingested document in the knowledge base."""

    title: str = Field(..., description="Document filename or display title.")
    source: str = Field(..., description="Source path or filename identifier.")
    chunk_count: int = Field(..., description="Total chunks indexed for this document.")
    preview: str = Field(default="", description="Snippet preview of the document content.")


class KnowledgeBaseResponse(BaseModel):
    """List of all documents stored in the vector database knowledge base."""

    total_chunks: int = Field(..., description="Total chunks in the vector collection.")
    total_documents: int = Field(
        ..., description="Total unique documents in the vector collection."
    )
    collection_name: str = Field(..., description="Active vector collection name.")
    documents: list[DocumentItem] = Field(
        default_factory=list, description="List of unique documents indexed."
    )


class DocumentDeleteResponse(BaseModel):
    """Response after deleting a document from the vector store."""

    success: bool = Field(..., description="Whether the deletion succeeded.")
    message: str = Field(..., description="Status message detailing how many chunks were deleted.")
    deleted_chunks: int = Field(default=0, description="Number of chunks removed.")
