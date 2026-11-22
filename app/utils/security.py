import json
import os
import re
import secrets
import time
import uuid
from collections import defaultdict
from pathlib import Path
from threading import Lock

from fastapi import Header, HTTPException, Request, status
from loguru import logger

from app.config import settings

# Supported extensions and their MIME checks
ALLOWED_EXTENSIONS = {".txt", ".md", ".pdf", ".json"}


def validate_and_canonicalize_path(
    input_path: str | Path,
    allowed_base_dir: str | Path | None = None,
) -> Path:
    """Resolves and validates a canonical file path, ensuring it stays within the allowed directory.

    Args:
        input_path: File or directory path provided by user.
        allowed_base_dir: Directory to which access must be restricted.
            Defaults to settings.ALLOWED_INGESTION_DIR or settings.BASE_DIR.

    Returns:
        Canonical resolved Path.

    Raises:
        HTTPException: If the path does not exist, attempts directory traversal,
            or escapes the allowed directory boundary.
    """
    if not input_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The specified path cannot be empty.",
        )

    base_dir = (
        Path(allowed_base_dir).resolve()
        if allowed_base_dir
        else Path(settings.ALLOWED_INGESTION_DIR).resolve()
    )
    project_root = Path(settings.BASE_DIR).resolve()

    target = Path(input_path)
    if not target.is_absolute():
        candidate_base = (base_dir / target).resolve()
        candidate_root = (project_root / target).resolve()
        if os.path.exists(str(candidate_base)):
            resolved_path = candidate_base
        elif os.path.exists(str(candidate_root)):
            resolved_path = candidate_root
        else:
            resolved_path = candidate_base
    else:
        resolved_path = target.resolve()

    # Verify that resolved path exists using os.path.exists
    if not os.path.exists(str(resolved_path)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"The specified path does not exist: {input_path}",
        )

    # Security check: Ensure resolved path is strictly within base_dir or project_root
    is_safe = False
    try:
        resolved_path.relative_to(base_dir)
        is_safe = True
    except ValueError:
        try:
            resolved_path.relative_to(project_root)
            is_safe = True
        except ValueError:
            is_safe = False

    if not is_safe:
        logger.warning(
            f"Security path traversal attempt blocked: {input_path} (resolved: {resolved_path}, allowed: {base_dir})"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: The specified path is outside the allowed ingestion directory.",
        )

    return resolved_path


def sanitize_filename(filename: str) -> str:
    """Sanitizes a client-provided filename and generates a secure server-side unique name.

    Args:
        filename: Raw client filename.

    Returns:
        Secure server-side unique filename with UUID prefix.
    """
    if not filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file must have a valid filename.",
        )

    # Strip any directory path components to prevent path traversal
    base_name = Path(filename).name
    # Strip null bytes and non-printable characters
    base_name = base_name.replace("\x00", "").strip()

    # Extract extension
    ext = Path(base_name).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type '{ext}'. Supported types: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    stem = Path(base_name).stem
    # Replace non-alphanumeric chars (except dash and underscore) with underscore
    safe_stem = re.sub(r"[^a-zA-Z0-9_\-]", "_", stem)[:64]
    if not safe_stem:
        safe_stem = "doc"

    # Prepend UUID to guarantee server-side uniqueness
    unique_prefix = uuid.uuid4().hex[:12]
    return f"{unique_prefix}_{safe_stem}{ext}"


def validate_file_content(content: bytes, ext: str) -> None:
    """Validates that file content matches its declared extension and is non-empty.

    Args:
        content: Raw file bytes.
        ext: File extension (e.g. '.pdf', '.txt').

    Raises:
        HTTPException: If file is empty, malformed, or content does not match extension.
    """
    if not content or len(content.strip()) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded file is empty.",
        )

    ext = ext.lower()

    if ext == ".pdf":
        # Check PDF magic bytes (%PDF-)
        if not content.startswith(b"%PDF-"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid PDF file: Missing %PDF- header signature.",
            )
    elif ext == ".json":
        try:
            text = content.decode("utf-8")
            data = json.loads(text)
            if not isinstance(data, (dict, list)):
                raise ValueError("JSON root must be an object or array.")
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid JSON file content: {e}",
            ) from e
    elif ext in (".txt", ".md"):
        # Check text decodability and check for binary null bytes
        if b"\x00" in content:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid text file: File contains binary data / null bytes.",
            )
        try:
            content.decode("utf-8")
        except UnicodeDecodeError:
            try:
                content.decode("latin-1")
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid text encoding in {ext} file: {e}",
                ) from e


class InMemoryRateLimiter:
    """Thread-safe sliding window rate limiter."""

    def __init__(self, requests_per_minute: int = 60) -> None:
        self.requests_per_minute = requests_per_minute
        self.window_seconds = 60.0
        self.requests: dict[str, list[float]] = defaultdict(list)
        self.lock = Lock()

    def is_allowed(self, client_id: str) -> bool:
        """Checks if a request from client_id is allowed under the rate limit."""
        now = time.time()
        window_start = now - self.window_seconds

        with self.lock:
            client_requests = self.requests[client_id]
            # Prune requests outside the current window
            self.requests[client_id] = [ts for ts in client_requests if ts > window_start]

            if len(self.requests[client_id]) >= self.requests_per_minute:
                return False

            self.requests[client_id].append(now)
            return True


# Global rate limiter instance
rate_limiter = InMemoryRateLimiter(requests_per_minute=settings.RATE_LIMIT_PER_MINUTE)


async def check_rate_limit(request: Request) -> None:
    """FastAPI dependency to enforce rate limits per client IP."""
    client_ip = request.client.host if request.client else "unknown"
    if not rate_limiter.is_allowed(client_ip):
        logger.warning(f"Rate limit exceeded for client IP: {client_ip}")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please wait before making more requests.",
        )


async def verify_api_key(
    x_api_key: str | None = Header(None, alias="X-API-Key"),
    authorization: str | None = Header(None, alias="Authorization"),
) -> None:
    """FastAPI dependency to verify API keys when authentication is enabled.

    Supports 'X-API-Key' header or 'Authorization: Bearer <key>'.
    """
    if not settings.API_KEY_AUTH_ENABLED:
        return

    expected_key = settings.API_KEY
    if not expected_key:
        logger.error("API_KEY_AUTH_ENABLED is True but API_KEY is not configured in settings.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication service misconfigured on the server.",
        )

    provided_key: str | None = None
    if x_api_key:
        provided_key = x_api_key
    elif authorization and authorization.lower().startswith("bearer "):
        provided_key = authorization[7:].strip()

    if not provided_key or not secrets.compare_digest(provided_key, expected_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key.",
            headers={"WWW-Authenticate": "ApiKey"},
        )
