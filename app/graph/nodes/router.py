from typing import Any

from loguru import logger

from app.graph.router import get_router_chain
from app.graph.state import AgentState
from app.utils.logger import log_node_end, log_node_start
from app.utils.timing import time_block


def router_node(state: AgentState) -> dict[str, Any]:
    """Invokes the question router to choose between vectorstore or websearch.

    Args:
        state: The current graph state.

    Returns:
        Updated state keys.
    """
    log_node_start("Router")
    question = state["question"]

    try:
        with time_block() as timing:
            router_chain = get_router_chain()
            decision = router_chain.invoke({"question": question})
            datasource = decision.datasource

        log_node_end("Router", timing["duration"])
        logger.info(f"Router Decision: [bold magenta]{datasource}[/]")

        # Update metadata dictionary
        current_metadata = state.get("metadata", {}).copy()
        current_metadata["router_decision"] = datasource

        # Update execution times
        current_times = state.get("execution_time", {}).copy()
        current_times["router"] = timing["duration"]

        return {
            "metadata": current_metadata,
            "execution_time": current_times,
            "steps": state.get("steps", []) + ["router_node"],
        }
    except Exception as e:
        logger.error(f"Router Node error: {e}")
        current_errors = state.get("errors", []) + [f"Router Error: {str(e)}"]
        # Fall back to vectorstore in case of exceptions
        current_metadata = state.get("metadata", {}).copy()
        current_metadata["router_decision"] = "vectorstore"
        return {
            "metadata": current_metadata,
            "errors": current_errors,
            "steps": state.get("steps", []) + ["router_node_fallback"],
        }
