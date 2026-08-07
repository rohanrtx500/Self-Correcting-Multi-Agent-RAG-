from unittest.mock import MagicMock, patch

from langchain_core.documents import Document

from app.graph.nodes.grade_documents import GradeDocument, grade_documents_node


@patch("app.graph.nodes.grade_documents.get_llm")
def test_grade_documents_relevant(mock_get_llm: MagicMock) -> None:
    """Tests document grader node when all documents are relevant."""
    # Mock LLM with structured output returning Relevant
    mock_llm_inst = MagicMock()
    mock_structured_chain = MagicMock()
    grade_val = GradeDocument(
        binary_score="Relevant",
        confidence=0.95,
        reasoning="The document discusses solar panels peak output which matches the query.",
    )
    mock_structured_chain.return_value = grade_val
    mock_structured_chain.invoke.return_value = grade_val
    mock_llm_inst.with_structured_output.return_value = mock_structured_chain
    mock_get_llm.return_value = mock_llm_inst

    state = {
        "question": "What is Project Helios?",
        "documents": [
            Document(page_content="Helios specifications...", metadata={"source": "spec.md"})
        ],
        "document_score": "",
        "execution_time": {},
        "steps": [],
        "errors": [],
    }

    result = grade_documents_node(state)

    assert result["document_score"] == "Relevant"
    assert len(result["documents"]) == 1
    assert "grade_documents_node" in result["steps"]


@patch("app.graph.nodes.grade_documents.get_llm")
def test_grade_documents_irrelevant(mock_get_llm: MagicMock) -> None:
    """Tests document grader filtering out irrelevant chunks."""
    # Mock LLM returning Not Relevant
    mock_llm_inst = MagicMock()
    mock_structured_chain = MagicMock()
    grade_val = GradeDocument(
        binary_score="Not Relevant",
        confidence=0.88,
        reasoning="The document is about vacation policies and is not relevant to solar panels.",
    )
    mock_structured_chain.return_value = grade_val
    mock_structured_chain.invoke.return_value = grade_val
    mock_llm_inst.with_structured_output.return_value = mock_structured_chain
    mock_get_llm.return_value = mock_llm_inst

    state = {
        "question": "What is Project Helios?",
        "documents": [
            Document(
                page_content="Employee vacation policies...", metadata={"source": "vacation.txt"}
            )
        ],
        "document_score": "",
        "execution_time": {},
        "steps": [],
        "errors": [],
    }

    result = grade_documents_node(state)

    assert result["document_score"] == "Not Relevant"
    assert len(result["documents"]) == 0
    assert "grade_documents_node" in result["steps"]
