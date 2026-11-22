import asyncio
import os
import time
import uuid
from collections.abc import AsyncGenerator, Awaitable, Callable
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, File, HTTPException, Request, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger
from starlette.responses import Response

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
from app.utils.logger import get_request_id, set_request_id, setup_logger
from app.utils.security import (
    check_rate_limit,
    sanitize_filename,
    validate_and_canonicalize_path,
    validate_file_content,
    verify_api_key,
)
from app.vectorstore.chroma import get_vector_store
from app.vectorstore.ingestion import IngestionManager

# --- Global Metrics Tracking ---
START_TIME = time.time()
queries_processed = 0
total_latency = 0.0
error_count = 0


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Handles application startup and shutdown events."""
    # 1. Initialize Loguru Rich Logging configurations
    setup_logger(settings.LOG_LEVEL)
    logger.info("Initializing Self-Correcting RAG API Service...")
    logger.info(f"Active Environment: [bold cyan]{settings.ENVIRONMENT}[/]")
    logger.info(f"Configured LLM Provider: [bold cyan]{settings.LLM_PROVIDER}[/]")
    logger.info(f"Allowed Ingestion Directory: [bold cyan]{settings.ALLOWED_INGESTION_DIR}[/]")

    # Ensure required directories exist
    os.makedirs(settings.ALLOWED_INGESTION_DIR, exist_ok=True)
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

    # 2. Check Database connectivity and pre-warm embedding model in memory
    try:
        store = get_vector_store()
        count = store._collection.count()
        logger.info(f"Vector Database connected. Current collection count: {count}")

        from app.vectorstore.embeddings import get_embeddings

        embeddings = get_embeddings()
        await asyncio.to_thread(embeddings.embed_query, "warmup")
        logger.info("Embedding model pre-warmed in memory.")
    except Exception as e:
        logger.error(f"Vector Database connection warning at startup: {e}")

    yield
    logger.info("Shutting down API Service...")


app = FastAPI(
    title="TrustFlow - Self-Correcting RAG Service",
    description="Enterprise-grade RAG pipeline using LangGraph, grading decisions, Tavily search, and hallucination correction loops.",
    version="1.0.0",
    lifespan=lifespan,
)


# Structured request correlation ID middleware
@app.middleware("http")
async def request_id_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    req_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:16]
    set_request_id(req_id)
    response = await call_next(request)
    response.headers["X-Request-ID"] = req_id
    return response


# Global sanitized error handlers to prevent internal path/exception leaks
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    req_id = get_request_id()
    logger.warning(f"HTTP {exc.status_code} on {request.method} {request.url.path}: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "request_id": req_id},
        headers={"X-Request-ID": req_id},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    global error_count
    error_count += 1
    req_id = get_request_id()
    logger.exception(
        f"Unhandled server error on {request.method} {request.url.path} [Request ID: {req_id}]"
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal server error occurred.", "request_id": req_id},
        headers={"X-Request-ID": req_id},
    )


# Configure CORS using explicit trusted origins and regex for deployed domains
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_origin_regex=settings.CORS_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Compile LangGraph Workflow
graph = get_graph().compile()


@app.post(
    "/query",
    response_model=QueryResponse,
    tags=["RAG Query"],
    dependencies=[Depends(check_rate_limit)],
)
@app.post(
    "/api/v1/query",
    response_model=QueryResponse,
    tags=["RAG Query"],
    dependencies=[Depends(check_rate_limit)],
)
async def run_query(request: QueryRequest) -> QueryResponse:
    """Executes the agentic self-correcting RAG workflow for a user question."""
    global queries_processed, total_latency, error_count
    logger.info(f"Received query request: '{request.question}'")

    start_perf = time.perf_counter()

    try:
        initial_state = {
            "question": request.question,
            "original_question": request.question,
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
            "query_rewrite_count": 0,
            "grounding_reason": "",
            "insufficient_evidence": False,
            "sources": [],
            "web_results": [],
            "errors": [],
        }

        # Run State Graph
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
        web_results = result.get("web_results", [])

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
            web_results=web_results,
            errors=errors,
        )

    except HTTPException:
        raise
    except Exception as e:
        error_count += 1
        logger.error(f"Error processing query: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Pipeline execution encountered an error: {str(e)}",
        ) from e


@app.post(
    "/ingest",
    response_model=IngestionResponse,
    tags=["Document Ingestion"],
    dependencies=[Depends(verify_api_key), Depends(check_rate_limit)],
)
async def ingest_document(request: IngestionRequest) -> IngestionResponse:
    """Ingests file or directory documents from the allowed ingestion directory into the vector database."""
    logger.info(f"Received ingestion request for path: {request.path}")

    # Validate canonical path and ensure it stays within allowed boundary
    target_path = validate_and_canonicalize_path(
        request.path, allowed_base_dir=settings.ALLOWED_INGESTION_DIR
    )

    try:
        manager = IngestionManager()

        if target_path.is_dir():
            count = await asyncio.to_thread(
                manager.ingest_directory,
                dir_path=target_path,
                chunk_size=request.chunk_size,
                chunk_overlap=request.chunk_overlap,
            )
            msg = f"Directory ingestion completed. Added {count} chunks to the vector database."
        else:
            count = await asyncio.to_thread(
                manager.ingest_file,
                file_path=target_path,
                chunk_size=request.chunk_size,
                chunk_overlap=request.chunk_overlap,
            )
            msg = f"File ingestion completed. Added {count} chunks to the vector database."

        return IngestionResponse(success=True, message=msg, chunks_count=count)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ingestion failed for {request.path}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Document ingestion failed: {str(e)}",
        ) from e


@app.post(
    "/upload",
    response_model=IngestionResponse,
    tags=["Document Ingestion"],
    dependencies=[Depends(verify_api_key), Depends(check_rate_limit)],
)
@app.post(
    "/api/v1/upload",
    response_model=IngestionResponse,
    tags=["Document Ingestion"],
    dependencies=[Depends(verify_api_key), Depends(check_rate_limit)],
)
async def upload_document(file: UploadFile = File(...)) -> IngestionResponse:  # noqa: B008
    """Uploads a file document, validates content and size, saves it securely, and ingests it into ChromaDB."""
    logger.info(f"Received file upload attempt: {file.filename}")

    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file must have a valid filename.",
        )

    # 1. Sanitize filename and generate server-side unique name (prevents path traversal)
    safe_filename = sanitize_filename(file.filename)
    ext = Path(safe_filename).suffix.lower()

    # 2. Stream read with bounded upload size limit to prevent memory exhaustion (DoS)
    chunks: list[bytes] = []
    total_bytes = 0
    chunk_size = 65536  # 64 KB

    while True:
        chunk = await file.read(chunk_size)
        if not chunk:
            break
        total_bytes += len(chunk)
        if total_bytes > settings.MAX_UPLOAD_SIZE_BYTES:
            max_mb = settings.MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail=f"File exceeds maximum allowed upload size of {max_mb}MB.",
            )
        chunks.append(chunk)

    contents = b"".join(chunks)

    # 3. Validate content types, magic headers, and text encodings
    validate_file_content(contents, ext)

    # 4. Save file to dedicated upload directory
    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)
    save_path = upload_dir / safe_filename

    try:
        with open(save_path, "wb") as f:
            f.write(contents)

        manager = IngestionManager()
        count = await asyncio.to_thread(manager.ingest_file, save_path)
        msg = f"File '{file.filename}' uploaded and ingested successfully. Added {count} chunks to vector DB."
        return IngestionResponse(success=True, message=msg, chunks_count=count)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to process upload '{file.filename}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"File upload and ingestion failed: {str(e)}",
        ) from e


@app.get("/health", response_model=HealthStatus, tags=["Monitoring"])
@app.get("/api/v1/health", response_model=HealthStatus, tags=["Monitoring"])
@app.get("/api/v1/status", response_model=HealthStatus, tags=["Monitoring"])
async def check_health() -> HealthStatus:
    """Returns application health and subsystem dependency indicators."""
    db_connected = False
    details: dict[str, str] = {
        "api": "healthy",
        "llm_provider": settings.LLM_PROVIDER,
    }

    try:
        store = get_vector_store()
        store._collection.count()
        db_connected = True
        details["database"] = "connected"
    except Exception as e:
        logger.warning(f"Health check DB connection check failed: {e}")
        details["database"] = "disconnected"

    # Distinguish overall application health from dependency status
    overall_status = "healthy" if db_connected else "degraded"

    return HealthStatus(
        status=overall_status,
        llm_provider=settings.LLM_PROVIDER,
        database_connected=db_connected,
        details=details,
    )


@app.get("/metrics", response_model=MetricsPayload, tags=["Monitoring"])
@app.get("/api/v1/metrics", response_model=MetricsPayload, tags=["Monitoring"])
async def check_metrics() -> MetricsPayload:
    """Retrieves operational latency, requests counts, and error metrics."""
    uptime = time.time() - START_TIME
    avg_latency = (total_latency / queries_processed) if queries_processed > 0 else 0.0

    return MetricsPayload(
        uptime_seconds=uptime,
        queries_processed=queries_processed,
        average_query_latency=avg_latency,
        error_count=error_count,
    )
