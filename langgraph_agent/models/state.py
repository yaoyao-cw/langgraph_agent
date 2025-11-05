"""State models used by the LangGraph workflow."""
from __future__ import annotations

from operator import add
from typing import Annotated, List, TypedDict


class AgentState(TypedDict):
    """Shared agent state used by LangGraph."""

    messages: Annotated[List, add]
    rounds_without_todo: int
    pending_reminders: List[str]


__all__ = ["AgentState"]
