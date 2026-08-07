from loguru import logger

from app.config import settings
from app.graph.state import AgentState


def route_question(state: AgentState) -> str:
    """Routes the question to web search or vectorstore.

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
    """Determines whether to generate an answer or perform a web search.

    Args:
        state: The current graph state.

    Returns:
        Next node name: "generate" or "web_search".
    """
    logger.info("--- DECIDING TO GENERATE ---")

    # If any document is relevant, we proceed to generation
    if state.get("document_score") == "Relevant" and state.get("documents"):
        logger.info("Decision: Context is relevant, proceeding to generation.")
        return "generate"
    else:
        # All documents were filtered out as irrelevant, fallback to web search
        logger.info("Decision: Context is not relevant or empty, proceeding to Web Search.")
        return "web_search"


def grade_generation_v_documents_and_question(state: AgentState) -> str:
    """Determines whether the generation is grounded and answers the question.

    Args:
        state: The current graph state.

    Returns:
        Next node name: "generate" (to retry), "web_search" (fallback), or "end".
    """
    logger.info("--- EVALUATING GENERATION (SELF-RAG) ---")

    hallucination = state.get("hallucination_score")
    retry_count = state.get("retry_count", 0)

    # Check for hallucination
    if hallucination == "Hallucinated":
        if retry_count < settings.MAX_RETRIES:
            logger.warning(
                f"Generation contains hallucinations! Retry #{retry_count + 1} of {settings.MAX_RETRIES}."
            )
            return "generate"
        else:
            logger.error(
                f"Generation contains hallucinations, but reached max retries ({settings.MAX_RETRIES}). Stopping gracefully."
            )
            return "end"

    # No hallucination found (grounded answer)
    logger.info("Generation is fully grounded in retrieved evidence.")

    # Optional: Verify if the answer actually addresses the question
    # In simple self-rag systems, we can check this using an LLM or exit
    # We will exit to END if grounded
    return "end"
