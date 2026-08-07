from unittest.mock import MagicMock, patch

from langchain_core.documents import Document

from app.graph.nodes.generate import generate_node


@patch("app.graph.nodes.generate.get_llm")
def test_generate_node_first_attempt(mock_get_llm: MagicMock) -> None:
    """Tests generating a response from context for the first time."""
    # Setup mock LLM response
    mock_llm_inst = MagicMock()
    mock_response = MagicMock()
    mock_response.content = "Answer about Helios solar system [1]."
    mock_llm_inst.invoke.return_value = mock_response
    mock_get_llm.return_value = mock_llm_inst

    state = {
        "question": "What is the solar panel capacity?",
        "documents": [
            Document(
                page_content="Helios solar panel output is 450kW.",
                metadata={"source": "helios.txt"},
            )
        ],
        "generation": "",
        "retry_count": 0,
        "sources": [],
        "execution_time": {},
        "steps": [],
        "errors": [],
    }

    result = generate_node(state)

    assert result["generation"] == "Answer about Helios solar system [1]."
    assert result["sources"] == ["helios.txt"]
    assert result["retry_count"] == 0
    assert "generate_node" in result["steps"]


@patch("app.graph.nodes.generate.get_llm")
def test_generate_node_retry_loop(mock_get_llm: MagicMock) -> None:
    """Tests generating response during a self-correction retry loop."""
    mock_llm_inst = MagicMock()
    mock_response = MagicMock()
    mock_response.content = "Regenerated corrected answer [1]."
    mock_llm_inst.invoke.return_value = mock_response
    mock_get_llm.return_value = mock_llm_inst

    state = {
        "question": "What is the solar panel capacity?",
        "documents": [
            Document(
                page_content="Helios solar panel output is 450kW.",
                metadata={"source": "helios.txt"},
            )
        ],
        # Represents an existing answer which was marked as hallucinated
        "generation": "An incorrect hallucinated statement.",
        "retry_count": 0,
        "sources": [],
        "execution_time": {},
        "steps": [],
        "errors": [],
    }

    result = generate_node(state)

    assert result["generation"] == "Regenerated corrected answer [1]."
    assert result["sources"] == ["helios.txt"]
    assert result["retry_count"] == 1
    assert "generate_node_retry_1" in result["steps"]
