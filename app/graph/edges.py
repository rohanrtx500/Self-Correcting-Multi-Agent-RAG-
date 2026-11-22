from loguru import logger

from app.config import settings
from app.graph.state import AgentState


def route_question(state: AgentState) -> str:
    """Routes the initial question to web search or vectorstore.

    Args:
        state: The current graph state.

    Returns:
        Next node name: "web_search" or "retrieve".
    """
    logger.info("--- ROUTING QUESTION ---")
    datasource = state.get("metadata", {}).get("router_decision")

    if datasource == "websearch":
        logger.info("Router Decision: Route to Web Search")
        return "web_search"
    else:
        logger.info("Router Decision: Route to Vector Store Retrieval")
        return "retrieve"


def decide_to_generate(state: AgentState) -> str:
    """Determines whether to generate an answer, rewrite the query, or fallback to web search.

    If document relevance is poor:
    1. First tries rewriting the query to perform another retrieval attempt.
    2. If the query has already been rewritten and documents remain irrelevant,
       falls back to web search.

    Args:
        state: The current graph state.

    Returns:
        Next node name: "generate", "transform_query", or "web_search".
    """
    logger.info("--- DECIDING TO GENERATE OR RETRY ---")

    # If any document is relevant, proceed directly to generation
    if state.get("document_score") == "Relevant" and state.get("documents"):
        logger.info("Decision: Context is relevant, proceeding to answer generation.")
        return "generate"

    # Relevance is poor or documents list is empty
    rewrite_count = state.get("query_rewrite_count", 0)
    if rewrite_count < 1:
        logger.warning(
            f"Decision: Context is not relevant. Rewriting query for improved retrieval (Rewrite attempt #{rewrite_count + 1})."
        )
        return "transform_query"

    # Context is still irrelevant after query transformation; fallback to web search
    logger.warning(
        "Decision: Context remains irrelevant after query rewrite. Falling back to Web Search."
    )
    return "web_search"


def grade_generation_v_documents_and_question(state: AgentState) -> str:
    """Determines whether the generation is grounded and answers the question.

    Handles corrective retrieval when evidence is insufficient, or regenerated
    synthesis when generation is unsupported.

    Args:
        state: The current graph state.

    Returns:
        Next node name: "generate" (retry), "web_search" (corrective retrieval), or "end".
    """
    logger.info("--- EVALUATING GENERATION (SELF-RAG) ---")

    hallucination = state.get("hallucination_score")
    retry_count = state.get("retry_count", 0)
    insufficient_evidence = state.get("insufficient_evidence", False)
    search_already_performed = state.get("search_required", False)

    # If generation lacks evidence and external web search has not been performed yet,
    # trigger corrective Web Search regardless of whether model explicitly abstained
    if insufficient_evidence and not search_already_performed:
        logger.warning(
            f"Generation lacks evidence! Initiating corrective Web Search (Retry #{retry_count + 1} of {settings.MAX_RETRIES})."
        )
        return "web_search"

    # Check for hallucination
    if hallucination == "Hallucinated":
        if retry_count < settings.MAX_RETRIES:
            logger.warning(
                f"Generation contains unsupported claims! Regenerating answer (Retry #{retry_count + 1} of {settings.MAX_RETRIES})."
            )
            return "generate"
        else:
            logger.error(
                f"Reached max retry limit ({settings.MAX_RETRIES}). Stopping gracefully with current response."
            )
            return "end"

    # No hallucination found (grounded answer or honest abstention)
    logger.info("Generation verified as grounded in available evidence.")
    return "end"
