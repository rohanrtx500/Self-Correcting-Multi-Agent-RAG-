from unittest.mock import MagicMock, patch

from langchain_core.documents import Document

from app.graph.nodes.retrieve import retrieve_node
from app.vectorstore.ingestion import IngestionManager


@patch("app.vectorstore.chroma.get_embeddings")
def test_document_ingestion_and_retrieval(mock_get_emb: MagicMock, mock_embeddings) -> None:
    """Verifies that IngestionManager successfully chunks and loads text into Chroma."""
    mock_get_emb.return_value = mock_embeddings

    # Setup database manager (in-memory, by specifying mock or no persist dir)
    # We will use temporary directories or mock actual add_documents
    manager = IngestionManager(persist_directory=None)

    # Let's mock vector store add_documents to avoid writing actual sqlite files
    manager.vector_store.add_documents = MagicMock()

    # Ingest mock file details
    raw_docs = [
        Document(
            page_content="This is content about Project Helios solar specifications.",
            metadata={"source": "helios.txt"},
        )
    ]

    # Test splitting and mock embedding ingestion
    with patch("app.vectorstore.ingestion.load_file") as mock_load:
        mock_load.return_value = raw_docs
        chunks_count = manager.ingest_file("helios.txt", chunk_size=100, chunk_overlap=10)

    # Check chunks count and assert call occurred
    assert chunks_count > 0
    manager.vector_store.add_documents.assert_called_once()


@patch("app.graph.nodes.retrieve.get_retriever")
def test_retrieve_node(mock_get_retriever: MagicMock) -> None:
    """Verifies retrieval node execution and execution times tracking."""
    # Setup mock retriever response docs
    retrieved_docs = [
        Document(page_content="Mock doc 1 content.", metadata={"source": "doc1.txt"}),
        Document(page_content="Mock doc 2 content.", metadata={"source": "doc2.txt"}),
    ]

    mock_retriever = MagicMock()
    mock_retriever.invoke.return_value = retrieved_docs
    mock_get_retriever.return_value = mock_retriever

    state = {
        "question": "What is the solar panel output?",
        "documents": [],
        "retrieved_chunks": [],
        "execution_time": {},
        "steps": [],
        "errors": [],
    }

    result = retrieve_node(state)

    # Verify state updates
    assert len(result["documents"]) == 2
    assert result["retrieved_chunks"] == ["Mock doc 1 content.", "Mock doc 2 content."]
    assert "retrieve" in result["execution_time"]
    assert "retrieve_node" in result["steps"]
