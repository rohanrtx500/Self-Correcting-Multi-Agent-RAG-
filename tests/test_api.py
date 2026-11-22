from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client() -> TestClient:
    """Fixture returning a FastAPI TestClient."""
    return TestClient(app)


@patch("app.main.get_vector_store")
def test_health_endpoint(mock_get_store: MagicMock, client: TestClient) -> None:
    """Verifies health check endpoint returns 200 with service indicators."""
    mock_store = MagicMock()
    mock_store._collection.count.return_value = 10
    mock_get_store.return_value = mock_store

    response = client.get("/health")
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["status"] == "healthy"
    assert json_data["database_connected"] is True
    assert json_data["llm_provider"] in ("openai", "groq", "ollama", "gemini")


@patch("app.main.get_vector_store")
def test_health_endpoint_db_failure(mock_get_store: MagicMock, client: TestClient) -> None:
    """Verifies health check handles DB lookup errors gracefully and flags status."""
    mock_get_store.side_effect = Exception("Chroma connection refused")

    response = client.get("/health")
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["status"] == "degraded"
    assert json_data["database_connected"] is False


def test_metrics_endpoint(client: TestClient) -> None:
    """Verifies metrics checks report active query processing counts."""
    response = client.get("/metrics")
    assert response.status_code == 200
    json_data = response.json()
    assert "uptime_seconds" in json_data
    assert "queries_processed" in json_data
    assert "average_query_latency" in json_data


@patch("app.main.graph.ainvoke")
def test_query_endpoint(mock_graph_invoke: MagicMock, client: TestClient) -> None:
    """Verifies RAG query endpoint returns answers, steps, and execution times."""
    mock_graph_invoke.return_value = {
        "generation": "Project Helios peak output is 450kW.",
        "sources": ["helios.md"],
        "steps": ["router_node", "retrieve_node", "grade_documents_node", "generate_node"],
        "execution_time": {"retrieve": 0.05, "generate": 0.45},
        "search_required": False,
        "retry_count": 0,
        "errors": [],
    }

    query_payload = {"question": "What is the peak output?"}
    response = client.post("/query", json=query_payload)

    assert response.status_code == 200
    json_data = response.json()
    assert json_data["question"] == "What is the peak output?"
    assert json_data["answer"] == "Project Helios peak output is 450kW."
    assert "helios.md" in json_data["sources"]
    assert "generate_node" in json_data["steps"]
    assert json_data["search_required"] is False
    assert json_data["retry_count"] == 0
    assert "execution_time" in json_data


@patch("app.main.IngestionManager")
@patch("os.path.exists")
def test_ingest_endpoint_file(
    mock_exists: MagicMock, mock_ingestion_manager_class: MagicMock, client: TestClient
) -> None:
    """Verifies document ingestion processes paths successfully and returns chunk metrics."""
    mock_exists.return_value = True

    # Setup mock manager instance
    mock_manager = MagicMock()
    mock_manager.ingest_file.return_value = 5
    mock_ingestion_manager_class.return_value = mock_manager

    ingest_payload = {"path": "sample_documents/company_policy.txt", "chunk_size": 1000}
    response = client.post("/ingest", json=ingest_payload)

    assert response.status_code == 200
    json_data = response.json()
    assert json_data["success"] is True
    assert json_data["chunks_count"] == 5
    assert "File ingestion completed" in json_data["message"]


def test_ingest_endpoint_nonexistent_path(client: TestClient) -> None:
    """Verifies ingestion rejects invalid paths with a 400 Bad Request error."""
    ingest_payload = {"path": "invalid/path/to/docs", "chunk_size": 1000}
    response = client.post("/ingest", json=ingest_payload)
    assert response.status_code == 400
    assert "does not exist" in response.json()["detail"]
