from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from loguru import logger

from app.graph.prompts import GENERATION_SYSTEM_PROMPT
from app.graph.state import AgentState
from app.llm.provider import get_llm
from app.utils.helpers import (
    extract_document_sources,
    extract_text_content,
    format_documents_to_string,
)
from app.utils.logger import log_node_end, log_node_start
from app.utils.timing import time_block

INSUFFICIENT_EVIDENCE_RESPONSE = (
    "Based on the available documentation, there is insufficient evidence to answer this question."
)


def generate_node(state: AgentState) -> dict[str, Any]:
    """Generates a grounded answer based strictly on retrieved documents context.

    Args:
        state: The current graph state.

    Returns:
        Updated state containing generation response.
    """
    log_node_start("Generator")
    question = state.get("original_question") or state["question"]
    documents = state.get("documents", [])
    retry_count = state.get("retry_count", 0)

    # Check if this is a retry loop
    is_retry = bool(state.get("generation"))
    if is_retry:
        retry_count += 1
        logger.info(f"Generating Response - Retry #{retry_count}")
    else:
        logger.info("Generating Response")

    # If there are no documents, return strict abstention directly
    if not documents:
        logger.info("No documents provided for generation. Abstaining with standard message.")
        current_times = state.get("execution_time", {}).copy()
        current_times["generate"] = 0.0
        return {
            "generation": INSUFFICIENT_EVIDENCE_RESPONSE,
            "retry_count": retry_count,
            "sources": [],
            "insufficient_evidence": True,
            "execution_time": current_times,
            "steps": state.get("steps", []) + ["generate_node_abstained"],
        }

    context_str = format_documents_to_string(documents)

    try:
        with time_block() as timing:
            llm = get_llm(temperature=0.2)

            system_msg = SystemMessage(content=GENERATION_SYSTEM_PROMPT.format(context=context_str))

            prompt_content = f"Question: {question}"
            if is_retry and state.get("grounding_reason"):
                prompt_content += (
                    f"\n\n[CORRECTION GUIDANCE]: Your previous attempt was flagged: {state['grounding_reason']}. "
                    f"Ensure every statement is directly quoted or substantiated by <<<DOCUMENT_CONTEXT>>>."
                )

            human_msg = HumanMessage(content=prompt_content)

            response = llm.invoke([system_msg, human_msg])
            generation = extract_text_content(response.content)

        log_node_end("Generator", timing["duration"])

        # Extract verified sources from documents
        sources = extract_document_sources(documents)

        current_times = state.get("execution_time", {}).copy()
        current_times["generate"] = timing["duration"]

        return {
            "generation": generation,
            "retry_count": retry_count,
            "sources": sources,
            "insufficient_evidence": False,
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
