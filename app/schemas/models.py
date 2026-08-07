from pydantic import BaseModel, Field


# --- QUERY ENDPOINTS ---
class QueryRequest(BaseModel):
    """Payload to submit a query to the agentic RAG pipeline."""

    question: str = Field(
        ...,
        description="The question to be answered by the self-correcting RAG pipeline.",
        examples=["What are the architectural specifications for Project Helios?"],
    )


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
    retrieved_chunks: list[dict] = Field(
        default_factory=list,
        description="Retrieved document chunks and metadata.",
    )
    errors: list[str] = Field(default_factory=list, description="Any warnings or errors.")


# --- INGESTION ENDPOINTS ---
class IngestionRequest(BaseModel):
    """Payload to request local document ingestion."""

    path: str = Field(
        ...,
        description="Absolute or relative file path or directory path to ingest.",
        examples=["D:/Projects-Personal/self-correcting-multi-agent-rag/sample_documents/"],
    )
    chunk_size: int = Field(
        default=1000,
        description="Maximum length of characters per text segment chunk.",
    )
    chunk_overlap: int = Field(
        default=200,
        description="Character overlap size between consecutive chunks.",
    )


class IngestionResponse(BaseModel):
    """The outcome status of the document ingestion request."""

    success: bool = Field(..., description="True if ingestion completed without system failures.")
    message: str = Field(..., description="User-facing explanation of the ingestion task.")
    chunks_count: int = Field(..., description="Total count of text chunks added to vector store.")


# --- SYSTEM STATES ---
class HealthStatus(BaseModel):
    """Health check response containing active providers and status."""

    status: str = Field(..., description="API system health state. Typically 'healthy'.")
    llm_provider: str = Field(..., description="Active LLM provider (OpenAI, Groq, Ollama).")
    database_connected: bool = Field(
        ...,
        description="Indicates if Chroma database connection is functional.",
    )


class MetricsPayload(BaseModel):
    """Internal latency and performance monitoring stats."""

    uptime_seconds: float = Field(..., description="FastAPI web application running uptime.")
    queries_processed: int = Field(..., description="Total count of processed query requests.")
    average_query_latency: float = Field(
        ...,
        description="Average execution duration of the query pipeline in seconds.",
    )
