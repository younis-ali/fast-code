from __future__ import annotations

from typing import Annotated, Sequence, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """LangGraph state: conversation turns as LangChain messages."""

    messages: Annotated[Sequence[BaseMessage], add_messages]
