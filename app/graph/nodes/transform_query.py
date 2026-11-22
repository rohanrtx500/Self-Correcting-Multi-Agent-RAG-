from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from loguru import logger

from app.graph.prompts import QUERY_REWRITE_SYSTEM_PROMPT
from app.graph.state import AgentState
from app.llm.provider import get_llm
from app.utils.helpers import extract_text_content
from app.utils.logger import log_node_end, log_node_start
from app.utils.timing import time_block


def transform_query_node(state: AgentState) -> dict[str, Any]:
    """Transforms and reformulates the user question to optimize vector retrieval.

    Triggered when the initial retrieval yielded poor or irrelevant document chunks.

    Args:
        state: Current workflow state.

    Returns:
        Updated state with rewritten question and updated rewrite count.
    """
    log_node_start("Transform Query")
    original_question = state.get("original_question") or state["question"]
    current_question = state["question"]
    rewrite_count = state.get("query_rewrite_count", 0) + 1

    try:
        with time_block() as timing:
            logger.info(
                f"Rewriting query (Attempt #{rewrite_count}) for better retrieval relevance."
            )
            llm = get_llm(temperature=0.0)

            system_msg = SystemMessage(content=QUERY_REWRITE_SYSTEM_PROMPT)
            human_msg = HumanMessage(
                content=f"Original Question: {original_question}\nCurrent Query: {current_question}"
            )

            response = llm.invoke([system_msg, human_msg])
            rewritten_query = extract_text_content(response.content).strip()

            # Fallback if model returned empty
            if not rewritten_query:
                rewritten_query = current_question

        log_node_end("Transform Query", timing["duration"])
        logger.info(f"Optimized search query: [bold green]'{rewritten_query}'[/]")

        current_times = state.get("execution_time", {}).copy()
        current_times["transform_query"] = timing["duration"]

        return {
            "question": rewritten_query,
            "original_question": original_question,
            "query_rewrite_count": rewrite_count,
            "execution_time": current_times,
            "steps": state.get("steps", []) + ["transform_query_node"],
        }

    except Exception as e:
        logger.error(f"Transform Query Node error: {e}")
        current_errors = state.get("errors", []) + [f"Query Rewrite Error: {str(e)}"]
        current_times = state.get("execution_time", {}).copy()
        current_times["transform_query"] = 0.0

        return {
            "question": current_question,
            "original_question": original_question,
            "query_rewrite_count": rewrite_count,
            "execution_time": current_times,
            "errors": current_errors,
            "steps": state.get("steps", []) + ["transform_query_node_failed"],
        }
