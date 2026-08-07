from unittest.mock import MagicMock, patch

from langchain_core.documents import Document

from app.graph.nodes.grade_documents import GradeDocument
from app.graph.router import RouteQuery
from app.graph.workflow_v1 import compile_workflow_v1


@patch("app.graph.nodes.router.get_router_chain")
@patch("app.graph.nodes.retrieve.get_retriever")
@patch("app.graph.nodes.grade_documents.get_llm")
def test_workflow_v1_vectorstore_path(
    mock_get_grader_llm: MagicMock,
    mock_get_retriever: MagicMock,
    mock_get_router_chain: MagicMock,
) -> None:
    """Verifies that vectorstore routing successfully traverses retrieve and grade nodes."""
    # 1. Mock Router -> returns vectorstore
    mock_router_chain = MagicMock()
    mock_router_chain.invoke.return_value = RouteQuery(datasource="vectorstore")
    mock_get_router_chain.return_value = mock_router_chain

    # 2. Mock Retriever -> returns a document
    mock_retriever = MagicMock()
    mock_retriever.invoke.return_value = [
        Document(
            page_content="Helios solar panels capacity is 450kW.",
            metadata={"source": "helios.md"},
        )
    ]
    mock_get_retriever.return_value = mock_retriever

    # 3. Mock Grader -> returns Relevant
    mock_grader_llm = MagicMock()
    mock_grader_chain = MagicMock()
    grade_val = GradeDocument(
        binary_score="Relevant",
        confidence=0.98,
        reasoning="Document is directly relevant.",
    )
    mock_grader_chain.return_value = grade_val
    mock_grader_chain.invoke.return_value = grade_val
    mock_grader_llm.with_structured_output.return_value = mock_grader_chain
    mock_get_grader_llm.return_value = mock_grader_llm

    # Compile workflow V1
    app_v1 = compile_workflow_v1()

    initial_state = {
        "question": "Acme solar output capacity?",
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

    # Run the compiled workflow
    result = app_v1.invoke(initial_state)

    # Assertions
    assert "router_node" in result["steps"]
    assert "retrieve_node" in result["steps"]
    assert "grade_documents_node" in result["steps"]
    assert result["document_score"] == "Relevant"
    assert len(result["documents"]) == 1
    assert result["documents"][0].page_content == "Helios solar panels capacity is 450kW."


@patch("app.graph.nodes.router.get_router_chain")
def test_workflow_v1_websearch_path(mock_get_router_chain: MagicMock) -> None:
    """Verifies that websearch routing directly exits the V1 workflow."""
    # Mock Router -> returns websearch
    mock_router_chain = MagicMock()
    mock_router_chain.invoke.return_value = RouteQuery(datasource="websearch")
    mock_get_router_chain.return_value = mock_router_chain

    app_v1 = compile_workflow_v1()

    initial_state = {
        "question": "What happened in the news yesterday?",
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

    result = app_v1.invoke(initial_state)

    # Assertions
    assert "router_node" in result["steps"]
    # In V1, we should bypass retrieve and grade nodes
    assert "retrieve_node" not in result["steps"]
    assert "grade_documents_node" not in result["steps"]
