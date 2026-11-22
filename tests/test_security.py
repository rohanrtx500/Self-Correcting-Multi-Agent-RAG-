from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app
from app.utils.security import (
    InMemoryRateLimiter,
    sanitize_filename,
    validate_and_canonicalize_path,
    validate_file_content,
)


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_sanitize_filename_traversal() -> None:
    """Verifies directory traversal sequences are stripped from uploaded filenames."""
    malicious_filename = "../../../etc/passwd.txt"
    safe_name = sanitize_filename(malicious_filename)
    assert ".." not in safe_name
    assert "/" not in safe_name
    assert "\\" not in safe_name
    assert safe_name.endswith(".txt")


def test_sanitize_filename_unsupported_extension() -> None:
    """Verifies that unauthorized file extensions are rejected."""
    with pytest.raises(Exception) as exc_info:
        sanitize_filename("malicious_script.exe")
    assert "Unsupported file type" in str(exc_info.value)


def test_validate_file_content_pdf_magic_bytes() -> None:
    """Verifies that PDF files must contain valid %PDF- magic header."""
    fake_pdf = b"This is not a real PDF file."
    with pytest.raises(Exception) as exc_info:
        validate_file_content(fake_pdf, ".pdf")
    assert "Missing %PDF- header" in str(exc_info.value)

    valid_pdf = b"%PDF-1.4 sample pdf content stream"
    # Should not raise
    validate_file_content(valid_pdf, ".pdf")


def test_validate_file_content_empty() -> None:
    """Verifies that zero-byte or whitespace-only files are rejected."""
    with pytest.raises(Exception) as exc_info:
        validate_file_content(b"", ".txt")
    assert "empty" in str(exc_info.value)


def test_validate_file_content_json() -> None:
    """Verifies that JSON files must contain valid JSON structures."""
    malformed_json = b"{not valid json"
    with pytest.raises(Exception) as exc_info:
        validate_file_content(malformed_json, ".json")
    assert "Invalid JSON" in str(exc_info.value)

    valid_json = b'{"key": "value"}'
    validate_file_content(valid_json, ".json")


def test_validate_and_canonicalize_path_traversal() -> None:
    """Verifies that path traversal escaping the allowed directory is blocked."""
    with pytest.raises(Exception) as exc_info:
        validate_and_canonicalize_path("C:/Windows/System32/calc.exe")
    assert exc_info.value.status_code in (400, 403)


def test_upload_endpoint_oversized_file(client: TestClient) -> None:
    """Verifies that uploads exceeding the size limit return HTTP 413 Payload Too Large."""
    # Temporarily set max upload size to 100 bytes
    original_size = settings.MAX_UPLOAD_SIZE_BYTES
    try:
        settings.MAX_UPLOAD_SIZE_BYTES = 100
        large_content = b"A" * 200
        response = client.post(
            "/upload",
            files={"file": ("test.txt", large_content, "text/plain")},
        )
        assert response.status_code == 413
        assert "exceeds maximum allowed upload size" in response.json()["detail"]
    finally:
        settings.MAX_UPLOAD_SIZE_BYTES = original_size


def test_upload_endpoint_unsupported_file_type(client: TestClient) -> None:
    """Verifies that uploading executable files returns HTTP 400 Bad Request."""
    response = client.post(
        "/upload",
        files={"file": ("script.sh", b"#!/bin/bash\necho test", "text/x-sh")},
    )
    assert response.status_code == 400
    assert "Unsupported file type" in response.json()["detail"]


def test_auth_enabled_rejects_missing_key(client: TestClient) -> None:
    """Verifies that sensitive endpoints reject requests when API key auth is enabled and key is missing."""
    original_auth = settings.API_KEY_AUTH_ENABLED
    original_key = settings.API_KEY
    try:
        settings.API_KEY_AUTH_ENABLED = True
        settings.API_KEY = "super-secret-key-12345"

        response = client.post(
            "/ingest",
            json={"path": "sample_documents/company_policy.txt"},
        )
        assert response.status_code == 401
        assert "Invalid or missing API key" in response.json()["detail"]

        # Now test with valid X-API-Key header
        with patch("app.main.validate_and_canonicalize_path") as mock_canon:
            with patch("app.main.IngestionManager") as mock_mgr_cls:
                mock_mgr = MagicMock()
                mock_mgr.ingest_file.return_value = 3
                mock_mgr_cls.return_value = mock_mgr
                mock_canon.return_value = MagicMock(is_dir=lambda: False)

                auth_response = client.post(
                    "/ingest",
                    json={"path": "sample_documents/company_policy.txt"},
                    headers={"X-API-Key": "super-secret-key-12345"},
                )
                assert auth_response.status_code == 200
    finally:
        settings.API_KEY_AUTH_ENABLED = original_auth
        settings.API_KEY = original_key


def test_rate_limiter() -> None:
    """Verifies sliding window rate limiter blocks requests exceeding the threshold."""
    limiter = InMemoryRateLimiter(requests_per_minute=3)
    client_ip = "192.168.1.100"

    assert limiter.is_allowed(client_ip) is True
    assert limiter.is_allowed(client_ip) is True
    assert limiter.is_allowed(client_ip) is True
    # 4th request in the same minute must be blocked
    assert limiter.is_allowed(client_ip) is False


def test_cors_headers(client: TestClient) -> None:
    """Verifies explicit CORS headers are returned for allowed origins."""
    response = client.options(
        "/query",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"
    assert response.headers.get("access-control-allow-credentials") == "true"

    vercel_response = client.options(
        "/query",
        headers={
            "Origin": "https://my-rag-app.vercel.app",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert vercel_response.status_code == 200
    assert (
        vercel_response.headers.get("access-control-allow-origin")
        == "https://my-rag-app.vercel.app"
    )
