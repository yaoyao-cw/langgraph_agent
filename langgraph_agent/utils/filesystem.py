"""Filesystem helpers constrained to the configured workspace."""
from __future__ import annotations

from pathlib import Path

from ..config import settings


class WorkspacePathError(ValueError):
    """Raised when an attempted file access escapes the workspace."""


def safe_path(path_value: str) -> Path:
    """Resolve ``path_value`` inside the configured workspace.

    Args:
        path_value: Relative path provided by the user or a tool call.

    Returns:
        A normalized absolute :class:`~pathlib.Path` inside the workspace.
    """

    abs_path = (settings.workspace / str(path_value or "")).resolve()
    try:
        abs_path.relative_to(settings.workspace)
    except ValueError as exc:  # pragma: no cover - defensive branch
        raise WorkspacePathError("Path escapes workspace") from exc
    return abs_path


__all__ = ["WorkspacePathError", "safe_path"]
