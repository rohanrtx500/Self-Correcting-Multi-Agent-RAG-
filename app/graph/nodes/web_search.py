from typing import Any

from loguru import logger
from tavily import TavilyClient

from app.config import settings
from app.graph.state import AgentState
from app.utils.helpers import clean_web_results
from app.utils.logger import log_node_end, log_node_start
from app.utils.timing import time_block


def web_search_node(state: AgentState) -> dict[str, Any]:
    """Performs a web search using Tavily API to retrieve external documents.

    Args:
        state: The current graph state.

    Returns:
        Updated state containing newly retrieved documents.
    """
    log_node_start("Web Search")
    question = state["question"]

    documents = list(state.get("documents") or [])

    try:
        with time_block() as timing:
            logger.info(f"Searching Web for query: '{question}'")
            # Instantiate Tavily client
            tavily_client = TavilyClient(api_key=settings.TAVILY_API_KEY)

            # Perform the search query
            response = tavily_client.search(
                query=question,
                max_results=4,
                include_raw_content=False,
            )

            # Retrieve results list
            search_results = response.get("results", [])
            logger.debug(f"Raw Tavily results count: {len(search_results)}")

            # Parse results to Document format
            web_docs = clean_web_results(search_results)

            # Append new web documents
            documents.extend(web_docs)

        log_node_end("Web Search", timing["duration"])
        logger.info(f"Web Search found {len(web_docs)} results.")

        # Update execution times
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
        # In case of API failure, do not append anything but proceed
        current_times = state.get("execution_time", {}).copy()
        current_times["web_search"] = 0.0
        return {
            "execution_time": current_times,
            "errors": current_errors,
            "steps": state.get("steps", []) + ["web_search_node_failed"],
        }
