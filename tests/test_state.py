from langchain_core.documents import Document

from app.graph.state import AgentState


def test_agent_state_initialization() -> None:
    """Verifies that AgentState TypedDict can be initialized with correct types."""
    # Create a valid state dictionary matching the AgentState TypedDict keys
    state: AgentState = {
        "question": "What is the battery storage capacity?",
        "documents": [
            Document(
                page_content="LFP battery capacity is 1.2MWh.", metadata={"source": "helios.txt"}
            )
        ],
        "retrieved_chunks": ["LFP battery capacity is 1.2MWh."],
        "search_required": False,
        "generation": "The battery storage capacity is 1.2MWh.",
        "hallucination_score": "Grounded",
        "document_score": "Relevant",
        "steps": ["retrieve", "grade", "generate"],
        "metadata": {"test_key": "test_value"},
        "execution_time": {"retrieve": 0.05, "generate": 0.45},
        "retry_count": 0,
        "sources": ["helios.txt"],
        "web_results": [],
        "errors": [],
    }

    # Perform assertions to ensure values are tracked and structured correctly
    assert state["question"] == "What is the battery storage capacity?"
    assert len(state["documents"]) == 1
    assert state["documents"][0].page_content == "LFP battery capacity is 1.2MWh."
    assert state["search_required"] is False
    assert state["generation"] == "The battery storage capacity is 1.2MWh."
    assert state["retry_count"] == 0
    assert "retrieve" in state["steps"]
    assert state["metadata"]["test_key"] == "test_value"
    assert state["execution_time"]["retrieve"] == 0.05
    assert len(state["errors"]) == 0


def test_agent_state_updates() -> None:
    """Verifies state transition updates mimic LangGraph reducer behaviors."""
    # Initialize basic state
    state: AgentState = {
        "question": "Acme Corp meal allowance?",
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

    # Simulate Retrieve Node update
    retrieve_update = {
        "documents": [Document(page_content="Daily per diem meal allowance is $75.")],
        "retrieved_chunks": ["Daily per diem meal allowance is $75."],
        "steps": state["steps"] + ["retrieve_node"],
    }
    state.update(retrieve_update)  # type: ignore[typeddict-item]

    # Verify updates took effect
    assert len(state["documents"]) == 1
    assert state["retrieved_chunks"] == ["Daily per diem meal allowance is $75."]
    assert state["steps"] == ["retrieve_node"]

    # Simulate Generator Node update with retry count increment
    generate_update = {
        "generation": "The daily meal allowance is $75.",
        "retry_count": state["retry_count"] + 1,
        "steps": state["steps"] + ["generate_node"],
    }
    state.update(generate_update)  # type: ignore[typeddict-item]

    assert state["generation"] == "The daily meal allowance is $75."
    assert state["retry_count"] == 1
    assert state["steps"] == ["retrieve_node", "generate_node"]
