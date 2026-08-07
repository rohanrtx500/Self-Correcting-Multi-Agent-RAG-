from typing import Literal

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from loguru import logger

from app.graph.nodes.grade_documents import grade_documents_node
from app.graph.nodes.retrieve import retrieve_node
from app.graph.nodes.router import router_node
from app.graph.state import AgentState


def route_question_v1(state: AgentState) -> Literal["retrieve", "end"]:
    """Routes the query based on the router decision metadata.

    Since web search is not implemented in V1, websearch routes directly to END.

    Args:
        state: The current workflow state.

    Returns:
        Next node name to execute.
    """
    decision = state.get("metadata", {}).get("router_decision")
    logger.info(f"Transition check - Router Decision: {decision}")

    if decision == "websearch":
        logger.info("Routing decision: websearch -> END (direct bypass in V1)")
        return "end"

    logger.info("Routing decision: vectorstore -> Retrieve")
    return "retrieve"


def compile_workflow_v1() -> CompiledStateGraph:
    """Compiles the incremental workflow V1: Router -> Retriever -> Grader."""
    workflow = StateGraph(AgentState)

    # Add V1 active nodes
    workflow.add_node("router", router_node)
    workflow.add_node("retrieve", retrieve_node)
    workflow.add_node("grade_documents", grade_documents_node)

    # Establish connections
    workflow.add_edge(START, "router")

    # Conditional routing after router decision
    workflow.add_conditional_edges(
        "router",
        route_question_v1,
        {
            "retrieve": "retrieve",
            "end": END,
        },
    )

    # Retrieve leads directly to Document Grader
    workflow.add_edge("retrieve", "grade_documents")

    # Document Grader leads to END
    workflow.add_edge("grade_documents", END)

    return workflow.compile()
