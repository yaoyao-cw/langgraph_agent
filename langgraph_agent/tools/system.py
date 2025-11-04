"""System-level tools such as bash, read, and write."""
from __future__ import annotations

import subprocess
from typing import Optional

from langchain_core.tools import tool

from ..config import settings
from ..utils.console import pretty_sub_line, pretty_tool_line
from ..utils.filesystem import safe_path
from ..utils.text import clamp_text


@tool
def bash(command: str, timeout_ms: int = 30000) -> str:
    """Execute a shell command inside the project workspace."""
    if not command:
        raise ValueError("missing bash.command")
    if any(token in command for token in ["rm -rf /", "shutdown", "reboot", "sudo "]):
        raise ValueError("blocked dangerous command")

    pretty_tool_line("Bash", command)

    proc = subprocess.run(
        command,
        cwd=str(settings.workspace),
        shell=True,
        capture_output=True,
        text=True,
        timeout=timeout_ms / 1000.0,
    )
    output = "\n".join(
        part for part in [proc.stdout, proc.stderr] if part
    ).strip()
    result = clamp_text(output or "(no output)", settings.max_tool_result_chars)

    pretty_sub_line(clamp_text(result, 2000))
    return result


@tool
def read_file(
    path: str,
    start_line: Optional[int] = None,
    end_line: Optional[int] = None,
    max_chars: int = 100000,
) -> str:
    """Read a UTF-8 text file within the workspace."""
    pretty_tool_line("Read", path)

    fp = safe_path(path)
    text = fp.read_text("utf-8")
    lines = text.split("\n")

    start = max(1, start_line or 1) - 1 if start_line else 0
    end = len(lines) if end_line is None or end_line < 0 else max(start, end_line)

    slice_text = "\n".join(lines[start:end])
    result = clamp_text(slice_text, max_chars)

    pretty_sub_line(clamp_text(result, 2000))
    return result


@tool
def write_file(path: str, content: str, mode: str = "overwrite") -> str:
    """Create or overwrite a UTF-8 text file."""
    pretty_tool_line("Write", path)

    fp = safe_path(path)
    fp.parent.mkdir(parents=True, exist_ok=True)

    if mode == "append" and fp.exists():
        with fp.open("a", encoding="utf-8") as handle:
            handle.write(content)
    else:
        fp.write_text(content, encoding="utf-8")

    byte_len = len(content.encode("utf-8"))
    result = f"wrote {byte_len} bytes to {fp.relative_to(settings.workspace)}"

    pretty_sub_line(result)
    return result


@tool
def edit_text(
    path: str,
    action: str,
    find: Optional[str] = None,
    replace: Optional[str] = None,
    insert_after: Optional[int] = None,
    new_text: Optional[str] = None,
    range_start: Optional[int] = None,
    range_end: Optional[int] = None,
) -> str:
    """Apply small, precise edits to a text file."""
    pretty_tool_line("Edit", f"{action} {path}")

    fp = safe_path(path)
    text = fp.read_text("utf-8")

    if action == "replace":
        if not find:
            raise ValueError("edit_text.replace missing find")
        replaced = text.replace(find, replace or "")
        fp.write_text(replaced, encoding="utf-8")
        result = f"replace done ({len(replaced.encode('utf-8'))} bytes)"

    elif action == "insert":
        line_number = insert_after if insert_after is not None else -1
        rows = text.split("\n")
        idx = max(-1, min(len(rows) - 1, line_number))
        rows[idx + 1 : idx + 1] = [new_text or ""]
        updated = "\n".join(rows)
        fp.write_text(updated, encoding="utf-8")
        result = f"inserted after line {line_number}"

    elif action == "delete_range":
        if range_start is None or range_end is None or range_end < range_start:
            raise ValueError("edit_text.delete_range invalid range")
        rows = text.split("\n")
        updated = "\n".join([*rows[:range_start], *rows[range_end:]])
        fp.write_text(updated, encoding="utf-8")
        result = f"deleted lines [{range_start}, {range_end})"

    else:
        raise ValueError(f"unsupported edit_text.action: {action}")

    pretty_sub_line(result)
    return result


__all__ = ["bash", "read_file", "write_file", "edit_text"]
