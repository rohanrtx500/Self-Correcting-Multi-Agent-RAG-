import os
from typing import Any

from loguru import logger
from tavily import TavilyClient

from app.config import settings
from app.graph.state import AgentState
from app.utils.helpers import clean_web_results
from app.utils.logger import log_node_end, log_node_start
from app.utils.timing import time_block


def web_search_node(state: AgentState) -> dict[str, Any]:
    """Performs an external web search using Tavily API to retrieve fallback context.

    Args:
        state: The current graph state.

    Returns:
        Updated state containing newly retrieved documents.
    """
    log_node_start("Web Search")
    question = state["question"]
    documents = list(state.get("documents") or [])

    api_key = settings.TAVILY_API_KEY or os.environ.get("TAVILY_API_KEY", "")

    if not api_key or "your-tavily-api-key" in api_key:
        logger.info("TAVILY_API_KEY not configured. Skipping external web search fallback.")
        current_times = state.get("execution_time", {}).copy()
        current_times["web_search"] = 0.0
        return {
            "documents": documents,
            "web_results": [],
            "search_required": True,
            "execution_time": current_times,
            "steps": state.get("steps", []) + ["web_search_skipped"],
        }

    try:
        with time_block() as timing:
            logger.info(f"Searching Web for query: '{question}'")
            tavily_client = TavilyClient(api_key=api_key)

            response = tavily_client.search(
                query=question,
                max_results=4,
                include_raw_content=False,
            )

            search_results = response.get("results", [])
            logger.debug(f"Raw Tavily results count: {len(search_results)}")

            web_docs = clean_web_results(search_results)
            documents.extend(web_docs)

        log_node_end("Web Search", timing["duration"])
        logger.info(f"Web Search found {len(web_docs)} results.")

        current_times = state.get("execution_time", {}).copy()
        current_times["web_search"] = timing["duration"]

        return {
            "documents": documents,
            "web_results": search_results,
            "search_required": True,
            "execution_time": current_times,
            "steps": state.get("steps", []) + ["web_search_node"],
        }

    except Exception as e:
        logger.error(f"Web Search Node error: {e}")
        current_errors = state.get("errors", []) + [f"Web Search Error: {str(e)}"]
        current_times = state.get("execution_time", {}).copy()
        current_times["web_search"] = 0.0
        return {
            "search_required": True,
            "execution_time": current_times,
            "errors": current_errors,
            "steps": state.get("steps", []) + ["web_search_node_failed"],
        }
