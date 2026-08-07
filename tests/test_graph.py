from unittest.mock import MagicMock, patch

from langchain_core.documents import Document

from app.graph.graph import get_graph
from app.graph.nodes.grade_documents import GradeDocument
from app.graph.nodes.hallucination import GradeHallucinations
from app.graph.router import RouteQuery


@patch("app.graph.nodes.router.get_router_chain")
@patch("app.graph.nodes.retrieve.get_retriever")
@patch("app.graph.nodes.grade_documents.get_llm")
@patch("app.graph.nodes.generate.get_llm")
@patch("app.graph.nodes.hallucination.get_llm")
def test_full_graph_integration_flow(
    mock_halluc_llm: MagicMock,
    mock_gen_llm: MagicMock,
    mock_grade_llm: MagicMock,
    mock_retrieve: MagicMock,
    mock_router: MagicMock,
) -> None:
    """Verifies the complete RAG graph pipeline workflow end-to-end.

    Traces execution paths from router through vector store retrieval,
    relevance grading, answer generation, and hallucination scoring.
    """
    # 1. Mock Router
    mock_router_chain = MagicMock()
    mock_router_chain.invoke.return_value = RouteQuery(datasource="vectorstore")
    mock_router.return_value = mock_router_chain

    # 2. Mock Retriever
    mock_retriever = MagicMock()
    mock_retriever.invoke.return_value = [
        Document(
            page_content="Helios has a solar panels peak output of 450kW.",
            metadata={"source": "helios.txt"},
        )
    ]
    mock_retrieve.return_value = mock_retriever

    # 3. Mock Grader (Relevant)
    mock_grade_llm_inst = MagicMock()
    mock_grade_chain = MagicMock()
    grade_val = GradeDocument(
        binary_score="Relevant",
        confidence=0.98,
        reasoning="Directly details the solar panels capacity.",
    )
    mock_grade_chain.return_value = grade_val
    mock_grade_chain.invoke.return_value = grade_val
    mock_grade_llm_inst.with_structured_output.return_value = mock_grade_chain
    mock_grade_llm.return_value = mock_grade_llm_inst

    # 4. Mock Generator
    mock_gen_llm_inst = MagicMock()
    mock_gen_response = MagicMock()
    mock_gen_response.content = "Project Helios solar panel capacity is 450kW."
    mock_gen_llm_inst.invoke.return_value = mock_gen_response
    mock_gen_llm.return_value = mock_gen_llm_inst

    # 5. Mock Hallucination Grader (Grounded)
    mock_halluc_llm_inst = MagicMock()
    mock_halluc_chain = MagicMock()
    halluc_val = GradeHallucinations(
        grounded=True,
        confidence=0.97,
        reasoning="Grounded in context.",
    )
    mock_halluc_chain.return_value = halluc_val
    mock_halluc_chain.invoke.return_value = halluc_val
    mock_halluc_llm_inst.with_structured_output.return_value = mock_halluc_chain
    mock_halluc_llm.return_value = mock_halluc_llm_inst

    # 6. Compile and execute graph
    compiled_graph = get_graph().compile()

    initial_state = {
        "question": "What is the solar panel capacity?",
        "documents": [],
        "retrieved_chunks": [],
        "search_required": False,
        "generation": "",
        "hallucination_score": "Grounded",
        "document_score": "Relevant",
        "steps": [],
        "metadata": {},
        "execution_time": {},
        "retry_count": 0,
        "sources": [],
        "web_results": [],
        "errors": [],
    }

    # Execute workflow run
    result = compiled_graph.invoke(initial_state)

    # 7. Perform Assertions on workflow trace steps and outputs
    assert result["generation"] == "Project Helios solar panel capacity is 450kW."
    assert "helios.txt" in result["sources"]
    assert result["hallucination_score"] == "Grounded"
    assert result["document_score"] == "Relevant"

    # Verify transition path steps were recorded
    steps = result["steps"]
    assert "router_node" in steps
    assert "retrieve_node" in steps
    assert "grade_documents_node" in steps
    assert "generate_node" in steps
    assert "hallucination_grader_node" in steps
