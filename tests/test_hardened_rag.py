from unittest.mock import MagicMock, patch

from langchain_core.documents import Document

from app.graph.edges import decide_to_generate, grade_generation_v_documents_and_question
from app.graph.nodes.generate import INSUFFICIENT_EVIDENCE_RESPONSE, generate_node
from app.graph.nodes.hallucination import hallucination_grader_node
from app.graph.nodes.transform_query import transform_query_node
from app.vectorstore.hybrid import SimpleBM25, reciprocal_rank_fusion
from app.vectorstore.ingestion import IngestionManager
from app.vectorstore.loader import load_file, split_documents


def test_transform_query_node_success() -> None:
    """Verifies that transform_query rewrites query into an optimized keyword query."""
    mock_llm_inst = MagicMock()
    mock_response = MagicMock()
    mock_response.content = "Project Helios solar panel energy capacity kW specifications"
    mock_llm_inst.invoke.return_value = mock_response

    with patch("app.graph.nodes.transform_query.get_llm", return_value=mock_llm_inst):
        state = {
            "question": "tell me about that solar project thing",
            "original_question": "tell me about that solar project thing",
            "query_rewrite_count": 0,
            "execution_time": {},
            "steps": [],
            "errors": [],
        }
        result = transform_query_node(state)

        assert result["question"] == "Project Helios solar panel energy capacity kW specifications"
        assert result["query_rewrite_count"] == 1
        assert "transform_query_node" in result["steps"]


def test_transform_query_node_fallback_on_error() -> None:
    """Verifies that transform_query gracefully falls back to the original question if LLM fails."""
    mock_llm_inst = MagicMock()
    mock_llm_inst.invoke.side_effect = Exception("LLM provider timeout")

    with patch("app.graph.nodes.transform_query.get_llm", return_value=mock_llm_inst):
        state = {
            "question": "What is the peak solar output?",
            "original_question": "What is the peak solar output?",
            "query_rewrite_count": 0,
            "execution_time": {},
            "steps": [],
            "errors": [],
        }
        result = transform_query_node(state)

        # Must fall back to question without raising
        assert result["question"] == "What is the peak solar output?"
        assert result["query_rewrite_count"] == 1
        assert "transform_query_node_failed" in result["steps"]


def test_decide_to_generate_query_rewrite_flow() -> None:
    """Verifies decision edge triggers query rewrite on first irrelevant retrieval attempt."""
    state_irrelevant = {
        "document_score": "Not Relevant",
        "documents": [],
        "query_rewrite_count": 0,
    }
    decision = decide_to_generate(state_irrelevant)
    assert decision == "transform_query"

    # After 1 rewrite, if still irrelevant, it falls back to web search
    state_still_irrelevant = {
        "document_score": "Not Relevant",
        "documents": [],
        "query_rewrite_count": 1,
    }
    decision_after_rewrite = decide_to_generate(state_still_irrelevant)
    assert decision_after_rewrite == "web_search"


def test_corrective_retrieval_on_insufficient_evidence() -> None:
    """Verifies that hallucination due to insufficient evidence triggers corrective web search."""
    state_insufficient = {
        "hallucination_score": "Hallucinated",
        "insufficient_evidence": True,
        "search_required": False,
        "retry_count": 0,
    }
    next_node = grade_generation_v_documents_and_question(state_insufficient)
    assert next_node == "web_search"

    # If web search was already tried, it falls back to generation retry or end
    state_search_already_done = {
        "hallucination_score": "Hallucinated",
        "insufficient_evidence": True,
        "search_required": True,
        "retry_count": 0,
    }
    next_node = grade_generation_v_documents_and_question(state_search_already_done)
    assert next_node == "generate"

    # Reaching max retries stops gracefully
    state_max_retries = {
        "hallucination_score": "Hallucinated",
        "retry_count": 3,
    }
    assert grade_generation_v_documents_and_question(state_max_retries) == "end"


def test_generation_node_abstention_on_empty_context() -> None:
    """Verifies generator outputs standard abstention message when no context exists."""
    state = {
        "question": "What is the secret launch date of Project Apollo?",
        "documents": [],
        "generation": "",
        "retry_count": 0,
        "sources": [],
        "execution_time": {},
        "steps": [],
        "errors": [],
    }
    result = generate_node(state)
    assert result["generation"] == INSUFFICIENT_EVIDENCE_RESPONSE
    assert result["insufficient_evidence"] is True
    assert "generate_node_abstained" in result["steps"]


def test_hallucination_grader_recognizes_abstention() -> None:
    """Verifies hallucination grader treats honest abstention as Grounded (avoiding infinite loops)."""
    state = {
        "question": "What is the quantum core speed?",
        "documents": [],
        "generation": INSUFFICIENT_EVIDENCE_RESPONSE,
        "execution_time": {},
        "steps": [],
    }
    result = hallucination_grader_node(state)
    assert result["hallucination_score"] == "Grounded"
    assert result["insufficient_evidence"] is True
    assert "hallucination_grader_abstained" in result["steps"]


def test_duplicate_document_detection_in_ingestion() -> None:
    """Verifies deduplication prevents indexing identical chunks repeatedly."""
    manager = IngestionManager(persist_directory=None)
    manager.vector_store.add_documents = MagicMock()

    doc_text = "This is a unique test chunk for deduplication verification."
    sample_docs = [Document(page_content=doc_text, metadata={"source": "test.txt"})]

    with patch("app.vectorstore.ingestion.load_file", return_value=sample_docs):
        # First ingestion
        count1 = manager.ingest_file("test.txt", chunk_size=100, chunk_overlap=20)
        assert count1 == 1
        assert manager.vector_store.add_documents.call_count == 1

        # Second ingestion of the same identical text must be skipped as a duplicate
        count2 = manager.ingest_file("test.txt", chunk_size=100, chunk_overlap=20)
        assert count2 == 0
        # Call count should not have increased
        assert manager.vector_store.add_documents.call_count == 1


def test_bm25_and_reciprocal_rank_fusion() -> None:
    """Verifies SimpleBM25 lexical scoring and Reciprocal Rank Fusion merging."""
    corpus = [
        Document(
            page_content="Helios solar panel peak capacity is 450kW.",
            metadata={"source": "helios.txt"},
        ),
        Document(
            page_content="Company employee vacation benefits and per diem meals.",
            metadata={"source": "hr.txt"},
        ),
        Document(
            page_content="Cybersecurity SOC2 AES-256 encryption policies.",
            metadata={"source": "sec.txt"},
        ),
    ]

    bm25 = SimpleBM25(corpus)
    matches = bm25.get_top_k("solar panel capacity", k=1)
    assert len(matches) == 1
    assert "helios.txt" in matches[0].metadata["source"]

    # Test Reciprocal Rank Fusion
    dense_list = [corpus[0], corpus[1]]
    sparse_list = [corpus[0], corpus[2]]
    fused = reciprocal_rank_fusion([dense_list, sparse_list], top_n=2)
    assert len(fused) == 2
    # corpus[0] appeared at rank 0 in both lists, so it must be top ranked in fused
    assert fused[0].metadata["source"] == "helios.txt"


def test_empty_document_and_split_handling(tmp_path) -> None:
    """Verifies that empty documents return empty document lists without raising errors."""
    empty_file = tmp_path / "empty.txt"
    empty_file.write_text("", encoding="utf-8")

    loaded = load_file(empty_file)
    assert loaded == []

    split = split_documents([])
    assert split == []
