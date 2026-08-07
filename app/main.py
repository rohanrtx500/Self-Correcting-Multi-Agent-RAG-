import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.config import settings
from app.graph.graph import get_graph
from app.schemas.models import (
    HealthStatus,
    IngestionRequest,
    IngestionResponse,
    MetricsPayload,
    QueryRequest,
    QueryResponse,
)
from app.utils.logger import setup_logger
from app.vectorstore.chroma import get_vector_store
from app.vectorstore.ingestion import IngestionManager

# --- Global Metrics Tracking ---
START_TIME = time.time()
queries_processed = 0
total_latency = 0.0


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Handles application startup and shutdown events."""
    # 1. Initialize Loguru Rich Logging configurations
    setup_logger(settings.LOG_LEVEL)
    logger.info("Initializing Self-Correcting RAG API Service...")

    # 2. Check Database connectivity
    try:
        store = get_vector_store()
        # Ping collection count to verify it works
        count = store._collection.count()
        logger.info(f"Vector Database connected. Current collection count: {count}")
    except Exception as e:
        logger.error(f"Vector Database connection failure: {e}")

    yield
    logger.info("Shutting down API Service...")


app = FastAPI(
    title="TrustFlow - Self-Correcting RAG Service",
    description="Enterprise-grade RAG pipeline using LangGraph, grading decisions, Tavily search, and hallucination correction loops.",
    version="1.0.0",
    lifespan=lifespan,
)

# Enable CORS for local dashboards and cross-origin debugging
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Compile LangGraph Workflow
graph = get_graph().compile()


@app.post("/query", response_model=QueryResponse, tags=["RAG Query"])
async def run_query(request: QueryRequest) -> QueryResponse:
    """Executes the agentic self-correcting RAG workflow for a user question."""
    global queries_processed, total_latency
    logger.info(f"Received query request: '{request.question}'")

    start_perf = time.perf_counter()

    try:
        # Initialize default state inputs
        initial_state = {
            "question": request.question,
            "documents": [],
            "retrieved_chunks": [],
            "search_required": False,
            "generation": "",
            "hallucination_score": "Grounded",
            "document_score": "Relevant",
            "steps": [],
            "metadata": {},
            "execution_time": {},
            "retry_count": 0,
            "sources": [],
            "web_results": [],
            "errors": [],
        }

        # Run State Graph (synchronously or asynchronously)
        result = await graph.ainvoke(initial_state)

        # Measure latency
        elapsed = time.perf_counter() - start_perf
        queries_processed += 1
        total_latency += elapsed

        # Extract values
        answer = result.get("generation", "")
        sources = result.get("sources", [])
        steps = result.get("steps", [])
        execution_times = result.get("execution_time", {})
        search_required = result.get("search_required", False)
        retry_count = result.get("retry_count", 0)
        errors = result.get("errors", [])

        # Format document chunks for frontend inspector
        raw_docs = result.get("documents", [])
        retrieved_chunks = [
            {"page_content": doc.page_content, "metadata": doc.metadata} for doc in raw_docs
        ]

        logger.info(f"Query processed successfully in {elapsed:.3f}s. Steps: {steps}")

        return QueryResponse(
            question=request.question,
            answer=answer,
            sources=sources,
            steps=steps,
            execution_time=execution_times,
            search_required=search_required,
            retry_count=retry_count,
            retrieved_chunks=retrieved_chunks,
            errors=errors,
        )

    except Exception as e:
        logger.error(f"Error processing query: {e}")
        raise HTTPException(
            status_code=500, detail=f"Pipeline execution encountered an error: {str(e)}"
        ) from e


@app.post("/ingest", response_model=IngestionResponse, tags=["Document Ingestion"])
async def ingest_document(request: IngestionRequest) -> IngestionResponse:
    """Ingests file or directory documents into the vector database."""
    logger.info(f"Received ingestion request for path: {request.path}")

    try:
        manager = IngestionManager()
        import os

        if not os.path.exists(request.path):
            raise HTTPException(
                status_code=400, detail=f"The specified path does not exist: {request.path}"
            )

        if os.path.isdir(request.path):
            count = manager.ingest_directory(
                dir_path=request.path,
                chunk_size=request.chunk_size,
                chunk_overlap=request.chunk_overlap,
            )
            msg = f"Directory ingestion completed. Added {count} chunks to the vector database."
        else:
            count = manager.ingest_file(
                file_path=request.path,
                chunk_size=request.chunk_size,
                chunk_overlap=request.chunk_overlap,
            )
            msg = f"File ingestion completed. Added {count} chunks to the vector database."

        return IngestionResponse(success=True, message=msg, chunks_count=count)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ingestion failed: {e}")
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}") from e


@app.post("/upload", response_model=IngestionResponse, tags=["Document Ingestion"])
async def upload_document(file: UploadFile = File(...)) -> IngestionResponse:  # noqa: B008
    """Uploads a file document, saves it locally, and ingests it into the vector database."""
    logger.info(f"Received file upload: {file.filename}")
    if not file.filename:
        raise HTTPException(status_code=400, detail="Uploaded file must have a valid filename.")

    import os

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in [".txt", ".md", ".pdf", ".json"]:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Supported file types: .pdf, .txt, .md, .json",
        )

    upload_dir = os.path.join(settings.BASE_DIR, "uploaded_documents")
    os.makedirs(upload_dir, exist_ok=True)
    save_path = os.path.join(upload_dir, file.filename)

    try:
        contents = await file.read()
        with open(save_path, "wb") as f:
            f.write(contents)

        manager = IngestionManager()
        count = manager.ingest_file(save_path)
        msg = f"File '{file.filename}' uploaded & ingested successfully. Added {count} chunks to vector DB."
        return IngestionResponse(success=True, message=msg, chunks_count=count)
    except Exception as e:
        logger.error(f"Failed to process upload '{file.filename}': {e}")
        raise HTTPException(status_code=500, detail=f"Upload processing failed: {str(e)}") from e


@app.get("/health", response_model=HealthStatus, tags=["Monitoring"])
async def check_health() -> HealthStatus:
    """Returns database connection and service health status."""
    db_connected = False
    try:
        store = get_vector_store()
        # Verify collection count queries are responsive
        store._collection.count()
        db_connected = True
    except Exception as e:
        logger.warning(f"Health check DB connection check failed: {e}")

    return HealthStatus(
        status="healthy",
        llm_provider=settings.LLM_PROVIDER,
        database_connected=db_connected,
    )


@app.get("/metrics", response_model=MetricsPayload, tags=["Monitoring"])
async def check_metrics() -> MetricsPayload:
    """Retrieves operational latency and requests counts metrics."""
    uptime = time.time() - START_TIME
    avg_latency = (total_latency / queries_processed) if queries_processed > 0 else 0.0

    return MetricsPayload(
        uptime_seconds=uptime,
        queries_processed=queries_processed,
        average_query_latency=avg_latency,
    )
