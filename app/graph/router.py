from typing import Literal

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable
from pydantic import BaseModel, Field

from app.graph.prompts import ROUTER_SYSTEM_PROMPT
from app.llm.provider import get_llm


class RouteQuery(BaseModel):
    """Route a user query to the most appropriate datasource."""

    datasource: Literal["vectorstore", "websearch"] = Field(
        ...,
        description="Given a user question choose to route it to websearch or vectorstore.",
    )


def get_router_chain() -> Runnable:
    """Configures and returns the router chain using structured outputs.

    Returns:
        A LangChain Runnable that outputs a RouteQuery Pydantic object.
    """
    llm = get_llm(temperature=0.0)

    # Use native structured outputs
    structured_llm = llm.with_structured_output(RouteQuery)

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", ROUTER_SYSTEM_PROMPT),
            ("human", "{question}"),
        ]
    )

    return prompt | structured_llm
