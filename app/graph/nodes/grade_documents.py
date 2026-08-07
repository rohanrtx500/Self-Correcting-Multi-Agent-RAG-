from concurrent.futures import ThreadPoolExecutor
from typing import Any, Literal, cast

from langchain_core.prompts import ChatPromptTemplate
from loguru import logger
from pydantic import BaseModel, Field

from app.graph.prompts import DOCUMENT_GRADER_SYSTEM_PROMPT
from app.graph.state import AgentState
from app.llm.provider import get_llm
from app.utils.logger import log_node_end, log_node_start
from app.utils.timing import time_block


class GradeDocument(BaseModel):
    """Pydantic model for grading document relevance."""

    binary_score: Literal["Relevant", "Not Relevant"] = Field(
        ...,
        description="Document is relevant to the question ('Relevant' or 'Not Relevant')",
    )
    confidence: float = Field(
        ...,
        description="Confidence score for the decision, between 0.0 and 1.0",
    )
    reasoning: str = Field(
        ...,
        description="Detailed explanation explaining why the document is relevant or not relevant to the question",
    )


def grade_documents_node(state: AgentState) -> dict[str, Any]:
    """Filters retrieved documents using an LLM relevance critic.

    Runs relevance grading concurrently for all chunks.

    Args:
        state: The current graph state.

    Returns:
        Updated state keys containing filtered documents list.
    """
    log_node_start("Document Relevance Grader")
    question = state["question"]
    documents = state.get("documents", [])

    if not documents:
        logger.warning("No documents to grade.")
        return {
            "documents": [],
            "document_score": "Not Relevant",
            "steps": state.get("steps", []) + ["grade_documents_empty"],
        }

    try:
        with time_block() as timing:
            logger.info("Grading Documents Relevance")
            llm = get_llm(temperature=0.0)
            structured_grader = llm.with_structured_output(GradeDocument)

            prompt = ChatPromptTemplate.from_messages(
                [
                    ("system", DOCUMENT_GRADER_SYSTEM_PROMPT),
                    ("human", "Question: {question}\n\nDocument: {document_content}"),
                ]
            )
            grader_chain = prompt | structured_grader

            # Local helper to grade a single document (executed in a thread)
            def grade_single_doc(item: tuple[int, Any]) -> tuple[Any, GradeDocument]:
                idx, doc = item
                result = cast(
                    GradeDocument,
                    grader_chain.invoke(
                        {"question": question, "document_content": doc.page_content}
                    ),
                )
                return doc, result

            # Run grading concurrently in a thread pool
            with ThreadPoolExecutor() as executor:
                graded_results = list(executor.map(grade_single_doc, enumerate(documents)))

            filtered_documents = []
            relevant_count = 0

            # Process graded results
            for idx, (doc, res) in enumerate(graded_results):
                grade = res.binary_score
                confidence = res.confidence
                reasoning = res.reasoning

                logger.debug(
                    f"Doc #{idx+1} graded: {grade} (confidence: {confidence:.2f} | Reasoning: {reasoning})"
                )

                if grade == "Relevant":
                    filtered_documents.append(doc)
                    relevant_count += 1

            # Decide on overall document score
            doc_score = "Relevant" if relevant_count > 0 else "Not Relevant"

        log_node_end("Document Relevance Grader", timing["duration"])
        logger.info(
            f"Documents Grading completed: {relevant_count}/{len(documents)} Relevant. Result: [bold cyan]{doc_score}[/]"
        )

        current_times = state.get("execution_time", {}).copy()
        current_times["grade_documents"] = timing["duration"]

        return {
            "documents": filtered_documents,
            "document_score": doc_score,
            "execution_time": current_times,
            "steps": state.get("steps", []) + ["grade_documents_node"],
        }

    except Exception as e:
        logger.error(f"Grade Documents Node error: {e}")
        current_errors = state.get("errors", []) + [f"Grade Documents Error: {str(e)}"]
        # Fallback: keep all documents
        return {
            "documents": documents,
            "document_score": "Relevant",
            "errors": current_errors,
            "steps": state.get("steps", []) + ["grade_documents_node_fallback"],
        }
