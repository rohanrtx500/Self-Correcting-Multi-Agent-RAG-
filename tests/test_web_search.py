from unittest.mock import MagicMock, patch

from app.graph.nodes.web_search import web_search_node
from app.graph.state import AgentState


@patch("app.graph.nodes.web_search.TavilyClient")
def test_web_search_success(mock_tavily_client_class: MagicMock) -> None:
    """Verifies that web_search_node executes search and appends results to state."""
    # Setup mock Tavily search response
    mock_tavily_instance = MagicMock()
    mock_tavily_client_class.return_value = mock_tavily_instance

    mock_search_response = {
        "results": [
            {
                "title": "NASA Mars Helios Rover",
                "url": "https://nasa.gov/helios-rover",
                "content": "Helios Rover is a new autonomous vehicle powered by solar panels.",
            }
        ]
    }
    mock_tavily_instance.search.return_value = mock_search_response

    initial_state: AgentState = {
        "question": "What is NASA's Helios Rover?",
        "documents": [],
        "retrieved_chunks": [],
        "search_required": False,
        "generation": "",
        "hallucination_score": "",
        "document_score": "",
        "steps": [],
        "metadata": {},
        "execution_time": {},
        "retry_count": 0,
        "sources": [],
        "web_results": [],
        "errors": [],
    }

    # Run the node
    result = web_search_node(initial_state)

    # Assertions
    mock_tavily_instance.search.assert_called_once_with(
        query="What is NASA's Helios Rover?", max_results=4, include_raw_content=False
    )
    assert result["search_required"] is True
    assert "web_search_node" in result["steps"]
    assert len(result["documents"]) == 1
    assert (
        result["documents"][0].page_content
        == "Helios Rover is a new autonomous vehicle powered by solar panels."
    )
    assert result["documents"][0].metadata["source"] == "https://nasa.gov/helios-rover"
    assert result["documents"][0].metadata["title"] == "NASA Mars Helios Rover"
    assert len(result["web_results"]) == 1
    assert result["web_results"][0]["url"] == "https://nasa.gov/helios-rover"


@patch("app.graph.nodes.web_search.TavilyClient")
def test_web_search_failure(mock_tavily_client_class: MagicMock) -> None:
    """Verifies that web_search_node logs failures and fails gracefully without crashing."""
    mock_tavily_instance = MagicMock()
    mock_tavily_client_class.return_value = mock_tavily_instance
    mock_tavily_instance.search.side_effect = Exception("API connection timed out")

    initial_state: AgentState = {
        "question": "What is NASA's Helios Rover?",
        "documents": [],
        "retrieved_chunks": [],
        "search_required": False,
        "generation": "",
        "hallucination_score": "",
        "document_score": "",
        "steps": [],
        "metadata": {},
        "execution_time": {},
        "retry_count": 0,
        "sources": [],
        "web_results": [],
        "errors": [],
    }

    result = web_search_node(initial_state)

    # Assertions
    assert "web_search_node_failed" in result["steps"]
    assert len(result["errors"]) == 1
    assert "API connection timed out" in result["errors"][0]
