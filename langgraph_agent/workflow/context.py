"""Shared mutable context for the agent workflow."""
from __future__ import annotations

from ..models.todo import TodoManager

TODO_BOARD = TodoManager()
AGENT_STATE = {"rounds_without_todo": 0}


__all__ = ["TODO_BOARD", "AGENT_STATE"]
