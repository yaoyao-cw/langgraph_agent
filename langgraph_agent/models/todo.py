"""Todo models and helpers."""
from __future__ import annotations

from typing import Dict, List, Set

from pydantic import BaseModel, Field

from ..config import settings
from ..utils.console import (
    RESET,
    TODO_COMPLETED_COLOR,
    TODO_PENDING_COLOR,
    TODO_PROGRESS_COLOR,
)


class TodoItem(BaseModel):
    id: str = Field(description="Unique identifier for the todo item.")
    content: str = Field(description="Short description of the work to be done.")
    status: str = Field(description="Current status of the todo item.")
    active_form: str = Field(alias="activeForm", description="Primary tool used for this step.")

    class Config:
        allow_population_by_field_name = True


class TodoManager:
    """Manage a constrained TODO list shared across the agent session."""

    def __init__(self) -> None:
        self.items: List[TodoItem] = []

    def update(self, items: List[Dict[str, str]]) -> str:
        if not isinstance(items, list):
            raise ValueError("Todo items must be a list")

        cleaned: List[TodoItem] = []
        seen_ids: Set[str] = set()
        in_progress = 0

        for index, raw in enumerate(items):
            if not isinstance(raw, dict):
                raise ValueError("Each todo must be an object")

            todo_id = str(raw.get("id") or index + 1)
            if todo_id in seen_ids:
                raise ValueError(f"Duplicate todo id: {todo_id}")
            seen_ids.add(todo_id)

            content = str(raw.get("content") or "").strip()
            if not content:
                raise ValueError("Todo content cannot be empty")

            status = str(raw.get("status") or settings.todo_statuses[0]).lower()
            if status not in settings.todo_statuses:
                raise ValueError(
                    f"Status must be one of {', '.join(settings.todo_statuses)}"
                )

            if status == "in_progress":
                in_progress += 1

            active_form = str(raw.get("activeForm") or "").strip()
            if not active_form:
                raise ValueError("Todo activeForm cannot be empty")

            cleaned.append(
                TodoItem(
                    id=todo_id,
                    content=content,
                    status=status,
                    activeForm=active_form,
                )
            )

            if len(cleaned) > 20:
                raise ValueError("Todo list is limited to 20 items")

        if in_progress > 1:
            raise ValueError("Only one task can be in_progress at a time")

        self.items = cleaned
        return self.render()

    def render(self) -> str:
        if not self.items:
            return f"{TODO_PENDING_COLOR}☐ No todos yet{RESET}"

        lines: List[str] = []
        for todo in self.items:
            mark = "☒" if todo.status == "completed" else "☐"
            lines.append(self._decorate_line(mark, todo))
        return "\n".join(lines)

    def stats(self) -> Dict[str, int]:
        return {
            "total": len(self.items),
            "completed": sum(todo.status == "completed" for todo in self.items),
            "in_progress": sum(todo.status == "in_progress" for todo in self.items),
        }

    def _decorate_line(self, mark: str, todo: TodoItem) -> str:
        status = todo.status
        text = f"{mark} {todo.content}"

        if status == "completed":
            return f"{TODO_COMPLETED_COLOR}\x1b[9m{text}{RESET}"
        if status == "in_progress":
            return f"{TODO_PROGRESS_COLOR}{text}{RESET}"
        return f"{TODO_PENDING_COLOR}{text}{RESET}"


__all__ = ["TodoItem", "TodoManager"]
