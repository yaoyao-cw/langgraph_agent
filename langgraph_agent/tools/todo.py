"""Todo management tool integration."""
from __future__ import annotations

from typing import Any, Dict, List

from langchain_core.tools import tool

from ..utils.console import pretty_sub_line, pretty_tool_line
from ..workflow.context import AGENT_STATE, TODO_BOARD


@tool
def todo_write(items: List[Dict[str, Any]]) -> str:
    """Update the shared todo list."""
    pretty_tool_line("Update Todos", "{ params.todo }")

    board_view = TODO_BOARD.update(items)
    AGENT_STATE["rounds_without_todo"] = 0
    stats = TODO_BOARD.stats()

    if stats["total"] == 0:
        summary = "No todos have been created."
    else:
        summary = (
            f"Status updated: {stats['completed']} completed, "
            f"{stats['in_progress']} in progress."
        )

    result = board_view + ("\n\n" + summary if summary else "")
    pretty_sub_line(result)
    return result


__all__ = ["todo_write"]
