from unittest.mock import MagicMock, patch

from langchain_core.documents import Document

from app.graph.nodes.hallucination import GradeHallucinations, hallucination_grader_node


@patch("app.graph.nodes.hallucination.get_llm")
def test_hallucination_grader_grounded(mock_get_llm: MagicMock) -> None:
    """Tests grading an answer which is fully supported by the context."""
    mock_llm_inst = MagicMock()
    mock_structured_chain = MagicMock()
    grade_val = GradeHallucinations(
        grounded=True,
        confidence=0.99,
        reasoning="Every claim matches facts in the documents.",
    )
    mock_structured_chain.return_value = grade_val
    mock_structured_chain.invoke.return_value = grade_val
    mock_llm_inst.with_structured_output.return_value = mock_structured_chain
    mock_get_llm.return_value = mock_llm_inst

    state = {
        "question": "What is the solar panel capacity?",
        "documents": [
            Document(
                page_content="Helios solar panel output is 450kW.",
                metadata={"source": "helios.txt"},
            )
        ],
        "generation": "Helios solar panel output is 450kW.",
        "hallucination_score": "",
        "execution_time": {},
        "steps": [],
        "errors": [],
    }

    result = hallucination_grader_node(state)

    assert result["hallucination_score"] == "Grounded"
    assert "hallucination_grader_node" in result["steps"]


@patch("app.graph.nodes.hallucination.get_llm")
def test_hallucination_grader_hallucinated(mock_get_llm: MagicMock) -> None:
    """Tests grading an answer containing unsupported assertions (hallucinations)."""
    mock_llm_inst = MagicMock()
    mock_structured_chain = MagicMock()
    grade_val = GradeHallucinations(
        grounded=False,
        confidence=0.92,
        reasoning="The answer claims a capacity of 1000kW, but source says 450kW.",
    )
    mock_structured_chain.return_value = grade_val
    mock_structured_chain.invoke.return_value = grade_val
    mock_llm_inst.with_structured_output.return_value = mock_structured_chain
    mock_get_llm.return_value = mock_llm_inst

    state = {
        "question": "What is the solar panel capacity?",
        "documents": [
            Document(
                page_content="Helios solar panel output is 450kW.",
                metadata={"source": "helios.txt"},
            )
        ],
        "generation": "Helios solar panel output is 1000kW.",
        "hallucination_score": "",
        "execution_time": {},
        "steps": [],
        "errors": [],
    }

    result = hallucination_grader_node(state)

    assert result["hallucination_score"] == "Hallucinated"
    assert "hallucination_grader_node" in result["steps"]
