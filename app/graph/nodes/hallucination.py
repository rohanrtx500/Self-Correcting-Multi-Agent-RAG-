from typing import Any, Literal, cast

from langchain_core.prompts import ChatPromptTemplate
from loguru import logger
from pydantic import BaseModel, Field

from app.graph.prompts import HALLUCINATION_GRADER_SYSTEM_PROMPT
from app.graph.state import AgentState
from app.llm.provider import get_llm
from app.utils.helpers import format_documents_to_string
from app.utils.logger import log_node_end, log_node_start
from app.utils.timing import time_block


class GradeHallucinations(BaseModel):
    """Pydantic model for grading factual hallucination in the generation."""

    grounded: bool = Field(
        ...,
        description="True if the generated answer is fully grounded in and supported by the context, False if it contains hallucinations or unsupported facts.",
    )
    confidence: float = Field(
        ...,
        description="Confidence score for the decision, between 0.0 and 1.0",
    )
    reasoning: str = Field(
        ...,
        description="Detailed explanation explaining why the generation is grounded or hallucinated.",
    )
    issue_type: Literal["none", "unsupported_generation", "insufficient_evidence"] = Field(
        default="none",
        description="Primary reason if ungrounded: 'unsupported_generation' or 'insufficient_evidence'.",
    )


def hallucination_grader_node(state: AgentState) -> dict[str, Any]:
    """Evaluates the generation to detect hallucinations against retrieved documents.

    Distinguishes unsupported generation from insufficient evidence.

    Args:
        state: The current graph state.

    Returns:
        Updated state keys containing the hallucination score and reason.
    """
    log_node_start("Hallucination Grader")
    generation = state.get("generation", "")
    documents = state.get("documents", [])

    if not generation:
        logger.warning("No generation to grade.")
        return {
            "hallucination_score": "Hallucinated",
            "grounding_reason": "Empty generation response.",
            "steps": state.get("steps", []) + ["hallucination_grader_empty"],
        }

    # Guardrail: If model explicitly and honestly abstained due to lack of evidence, consider it grounded
    abstention_phrases = (
        "insufficient evidence",
        "cannot find the answer",
        "insufficient information",
        "no relevant document contexts",
    )
    if any(phrase in generation.lower() for phrase in abstention_phrases):
        logger.info("Generation is an explicit abstention. Marking as Grounded.")
        return {
            "hallucination_score": "Grounded",
            "grounding_reason": "Model correctly abstained due to insufficient context.",
            "insufficient_evidence": True,
            "steps": state.get("steps", []) + ["hallucination_grader_abstained"],
        }

    # Format retrieved document context
    context_str = format_documents_to_string(documents) if documents else "No context available."

    try:
        with time_block() as timing:
            logger.info("Evaluating Generation for Hallucinations (Self-RAG)")
            llm = get_llm(temperature=0.0)
            structured_grader = llm.with_structured_output(GradeHallucinations)

            prompt = ChatPromptTemplate.from_messages(
                [
                    ("system", HALLUCINATION_GRADER_SYSTEM_PROMPT),
                    (
                        "human",
                        "Documents Context:\n{context}\n\nGenerated Answer:\n{generation}",
                    ),
                ]
            )
            grader_chain = prompt | structured_grader

            result = cast(
                GradeHallucinations,
                grader_chain.invoke({"context": context_str, "generation": generation}),
            )
            grade = "Grounded" if result.grounded else "Hallucinated"
            explanation = result.reasoning
            confidence = result.confidence
            issue = getattr(result, "issue_type", "unsupported_generation")

        log_node_end("Hallucination Grader", timing["duration"])
        logger.info(f"Hallucination Score: {grade} (confidence: {confidence:.2f} | Issue: {issue})")
        logger.debug(f"Grader Explanation: {explanation}")

        current_times = state.get("execution_time", {}).copy()
        current_times["hallucination_grader"] = timing["duration"]

        return {
            "hallucination_score": grade,
            "grounding_reason": explanation,
            "insufficient_evidence": issue == "insufficient_evidence",
            "execution_time": current_times,
            "steps": state.get("steps", []) + ["hallucination_grader_node"],
        }

    except Exception as e:
        logger.error(f"Hallucination Grader Node error: {e}")
        current_errors = state.get("errors", []) + [f"Hallucination Grader Error: {str(e)}"]
        # Fallback: Guardrail against treating failed grader as fatal hallucination if confident generation
        return {
            "hallucination_score": "Grounded",  # Fail-open with warning log rather than infinite error loop
            "grounding_reason": f"Grader evaluation failed: {e}",
            "errors": current_errors,
            "steps": state.get("steps", []) + ["hallucination_grader_fallback"],
        }
