from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from loguru import logger

from app.graph.prompts import GENERATION_SYSTEM_PROMPT
from app.graph.state import AgentState
from app.llm.provider import get_llm
from app.utils.helpers import extract_document_sources, format_documents_to_string
from app.utils.logger import log_node_end, log_node_start
from app.utils.timing import time_block


def generate_node(state: AgentState) -> dict[str, Any]:
    """Generates an answer based on retrieved documents context.

    Args:
        state: The current graph state.

    Returns:
        Updated state containing generation response.
    """
    log_node_start("Generator")
    question = state["question"]
    documents = state.get("documents", [])
    retry_count = state.get("retry_count", 0)

    # Check if this is a retry loop
    is_retry = bool(state.get("generation"))
    if is_retry:
        retry_count += 1
        logger.info(f"Generating Response - Retry #{retry_count}")
    else:
        logger.info("Generating Response")

    # If we have no documents, we generate answer stating we don't have information
    context_str = ""
    if documents:
        context_str = format_documents_to_string(documents)
    else:
        context_str = "No relevant document contexts were found."

    try:
        with time_block() as timing:
            llm = get_llm(temperature=0.3)

            system_msg = SystemMessage(content=GENERATION_SYSTEM_PROMPT.format(context=context_str))
            human_msg = HumanMessage(content=f"Question: {question}")

            response = llm.invoke([system_msg, human_msg])
            generation = str(response.content)

        log_node_end("Generator", timing["duration"])

        # Extract sources from documents
        sources = extract_document_sources(documents)

        # Update execution times
        current_times = state.get("execution_time", {}).copy()
        current_times["generate"] = timing["duration"]

        return {
            "generation": generation,
            "retry_count": retry_count,
            "sources": sources,
            "execution_time": current_times,
            "steps": state.get("steps", [])
            + [f"generate_node_retry_{retry_count}" if is_retry else "generate_node"],
        }

    except Exception as e:
        logger.error(f"Generator Node error: {e}")
        current_errors = state.get("errors", []) + [f"Generator Error: {str(e)}"]
        current_times = state.get("execution_time", {}).copy()
        current_times["generate"] = 0.0
        return {
            "generation": "I encountered an error while generating the response.",
            "execution_time": current_times,
            "errors": current_errors,
            "steps": state.get("steps", []) + ["generate_node_failed"],
        }
