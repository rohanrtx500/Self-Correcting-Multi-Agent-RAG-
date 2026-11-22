import os
import sys
from collections.abc import Generator
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from langchain_core.embeddings import Embeddings

# Add project root directory to path to support package importing during test run
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)


# Custom Mock Embeddings class
class MockEmbeddings(Embeddings):

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [[0.1] * 1536 for _ in texts]

    def embed_query(self, text: str) -> list[float]:
        return [0.1] * 1536


@pytest.fixture(scope="session", autouse=True)
def set_env_variables() -> None:
    """Configures environment variables for testing."""
    os.environ["LLM_PROVIDER"] = "openai"
    os.environ["OPENAI_API_KEY"] = "mock-testing-key"
    os.environ["TAVILY_API_KEY"] = "mock-testing-key"
    os.environ["CHROMA_PERSIST_DIRECTORY"] = "./test_chroma_db"
    os.environ["CHROMA_COLLECTION_NAME"] = "test_collection"


@pytest.fixture(autouse=True)
def mock_global_embeddings(monkeypatch: pytest.MonkeyPatch) -> None:
    """Globally mocks embeddings to isolate tests from network calls and GPU/model dependencies."""
    mock_emb = MockEmbeddings()
    monkeypatch.setattr("app.vectorstore.embeddings.get_embeddings", lambda: mock_emb)
    monkeypatch.setattr("app.vectorstore.chroma.get_embeddings", lambda: mock_emb)


@pytest.fixture
def mock_embeddings() -> MockEmbeddings:
    """Fixture providing MockEmbeddings."""
    return MockEmbeddings()


@pytest.fixture
def mock_llm() -> MagicMock:
    """Fixture providing a mock language model client."""
    mock_client = MagicMock()

    # Mock invoke returning a default AI message
    mock_response = MagicMock()
    mock_response.content = "Mocked LLM Generation Response."
    mock_client.invoke.return_value = mock_response

    # Mock with_structured_output returning a mock structured chain
    mock_structured_chain = MagicMock()
    mock_client.with_structured_output.return_value = mock_structured_chain

    return mock_client


@pytest.fixture
def mock_tavily() -> Generator[MagicMock, None, None]:
    """Mock-patches TavilyClient search method."""
    with patch("app.graph.nodes.web_search.TavilyClient") as mock_class:
        mock_instance = MagicMock()
        mock_instance.search.return_value = {
            "results": [
                {
                    "title": "Mock Web Search Result",
                    "url": "https://example.com/mock",
                    "content": "This is mocked content from a web search result.",
                }
            ]
        }
        mock_class.return_value = mock_instance
        yield mock_instance
