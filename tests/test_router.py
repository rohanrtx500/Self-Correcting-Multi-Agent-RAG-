from unittest.mock import MagicMock, patch

from app.graph.nodes.router import router_node
from app.graph.router import RouteQuery


@patch("app.graph.nodes.router.get_router_chain")
def test_router_node_vectorstore(mock_get_router: MagicMock) -> None:
    """Verifies that router node correctly writes vectorstore routing to metadata."""
    # Configure mock chain response
    mock_chain = MagicMock()
    mock_chain.invoke.return_value = RouteQuery(datasource="vectorstore")
    mock_get_router.return_value = mock_chain

    # Initialize sample state
    state = {
        "question": "What is the solar panel capacity of Helios?",
        "metadata": {},
        "execution_time": {},
        "steps": [],
        "errors": [],
    }

    # Execute router node
    result = router_node(state)

    # Verify decision metadata
    assert result["metadata"]["router_decision"] == "vectorstore"
    assert "router" in result["execution_time"]
    assert "router_node" in result["steps"]


@patch("app.graph.nodes.router.get_router_chain")
def test_router_node_websearch(mock_get_router: MagicMock) -> None:
    """Verifies that router node correctly writes websearch routing to metadata."""
    mock_chain = MagicMock()
    mock_chain.invoke.return_value = RouteQuery(datasource="websearch")
    mock_get_router.return_value = mock_chain

    state = {
        "question": "Who won the World Cup in 2026?",
        "metadata": {},
        "execution_time": {},
        "steps": [],
        "errors": [],
    }

    result = router_node(state)

    assert result["metadata"]["router_decision"] == "websearch"
    assert "router" in result["execution_time"]
    assert "router_node" in result["steps"]
