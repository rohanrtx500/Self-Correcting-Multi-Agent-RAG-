from langgraph.graph import END, StateGraph

from app.graph.edges import (
    decide_to_generate,
    grade_generation_v_documents_and_question,
    route_question,
)
from app.graph.nodes.generate import generate_node
from app.graph.nodes.grade_documents import grade_documents_node
from app.graph.nodes.hallucination import hallucination_grader_node
from app.graph.nodes.retrieve import retrieve_node
from app.graph.nodes.router import router_node
from app.graph.nodes.transform_query import transform_query_node
from app.graph.nodes.web_search import web_search_node
from app.graph.state import AgentState


def get_graph() -> StateGraph:
    """Configures, registers, and compiles the multi-agent state graph.

    Includes dynamic routing, relevance grading, query reformulation,
    hallucination detection, and bounded corrective retrieval loops.

    Returns:
        Configured LangGraph StateGraph workflow.
    """
    # 1. Initialize StateGraph with the AgentState schema
    workflow = StateGraph(AgentState)

    # 2. Register all independent agent nodes
    workflow.add_node("router", router_node)
    workflow.add_node("retrieve", retrieve_node)
    workflow.add_node("grade_documents", grade_documents_node)
    workflow.add_node("transform_query", transform_query_node)
    workflow.add_node("web_search", web_search_node)
    workflow.add_node("generate", generate_node)
    workflow.add_node("hallucination_grader", hallucination_grader_node)

    # 3. Configure the execution path flow
    # Flow starts at the Router node
    workflow.set_entry_point("router")

    # Router decides to retrieve documents or perform web search
    workflow.add_conditional_edges(
        "router",
        route_question,
        {
            "retrieve": "retrieve",
            "web_search": "web_search",
        },
    )

    # Retrieval flows directly to Document Relevance grading
    workflow.add_edge("retrieve", "grade_documents")

    # Grading determines whether to proceed to generation, rewrite query, or fallback to web search
    workflow.add_conditional_edges(
        "grade_documents",
        decide_to_generate,
        {
            "generate": "generate",
            "transform_query": "transform_query",
            "web_search": "web_search",
        },
    )

    # Query transformation loops back to Retrieve with rewritten query
    workflow.add_edge("transform_query", "retrieve")

    # Web search results lead directly to response generation
    workflow.add_edge("web_search", "generate")

    # Generation output flows directly to hallucination verification
    workflow.add_edge("generate", "hallucination_grader")

    # Hallucination grader loops back to generate, triggers corrective web search, or exits to END
    workflow.add_conditional_edges(
        "hallucination_grader",
        grade_generation_v_documents_and_question,
        {
            "generate": "generate",
            "web_search": "web_search",
            "end": END,
        },
    )

    return workflow
