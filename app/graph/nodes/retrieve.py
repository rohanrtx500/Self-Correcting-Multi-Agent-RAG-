from typing import Any

from loguru import logger

from app.graph.state import AgentState
from app.utils.logger import log_node_end, log_node_start
from app.utils.timing import time_block
from app.vectorstore.chroma import get_retriever


def retrieve_node(state: AgentState) -> dict[str, Any]:
    """Retrieves documents from the vector database.

    Args:
        state: The current graph state.

    Returns:
        Updated state keys containing retrieved documents.
    """
    log_node_start("Retrieve")
    question = state["question"]

    try:
        with time_block() as timing:
            logger.info("Retrieving Documents from Vector Database")
            # Create the retriever using configuration defaults
            retriever = get_retriever()
            documents = retriever.invoke(question)

        log_node_end("Retrieve", timing["duration"])
        logger.info(f"Retrieved {len(documents)} Chunks")

        # Update execution times
        current_times = state.get("execution_time", {}).copy()
        current_times["retrieve"] = timing["duration"]

        return {
            "documents": documents,
            "retrieved_chunks": [doc.page_content for doc in documents],
            "execution_time": current_times,
            "steps": state.get("steps", []) + ["retrieve_node"],
        }
    except Exception as e:
        logger.error(f"Retrieve Node error: {e}")
        current_errors = state.get("errors", []) + [f"Retrieve Error: {str(e)}"]
        current_times = state.get("execution_time", {}).copy()
        current_times["retrieve"] = 0.0
        return {
            "documents": [],
            "retrieved_chunks": [],
            "execution_time": current_times,
            "errors": current_errors,
            "steps": state.get("steps", []) + ["retrieve_node_failed"],
        }
