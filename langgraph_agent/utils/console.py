"""Console utilities for rendering output consistently."""
from __future__ import annotations

import re
import sys
import threading
import time
from typing import Iterable


RESET = "\x1b[0m"
PRIMARY_COLOR = "\x1b[38;2;120;200;255m"
ACCENT_COLOR = "\x1b[38;2;150;140;255m"
INFO_COLOR = "\x1b[38;2;110;110;110m"
PROMPT_COLOR = "\x1b[38;2;120;200;255m"
TODO_PENDING_COLOR = "\x1b[38;2;176;176;176m"
TODO_PROGRESS_COLOR = "\x1b[38;2;120;200;255m"
TODO_COMPLETED_COLOR = "\x1b[38;2;34;139;34m"
DIVIDER = "\n"

MD_BOLD = re.compile(r"\*\*(.+?)\*\*")
MD_CODE = re.compile(r"`([^`]+)`")
MD_HEADING = re.compile(r"^(#{1,6})\s*(.+)$", re.MULTILINE)
MD_BULLET = re.compile(r"^\s*[-\*]\s+", re.MULTILINE)


def clear_screen() -> None:
    if sys.stdout.isatty():
        sys.stdout.write("\033c")
        sys.stdout.flush()


def render_banner(title: str, subtitle: str | None = None) -> None:
    print(f"{PRIMARY_COLOR}{title}{RESET}")
    if subtitle:
        print(f"{ACCENT_COLOR}{subtitle}{RESET}")
    print()


def user_prompt_label() -> str:
    return f"{ACCENT_COLOR}{RESET} {PROMPT_COLOR}User{RESET}{INFO_COLOR} >> {RESET}"


def print_divider() -> None:
    print(DIVIDER, end="")


def format_markdown(text: str) -> str:
    if not text or text.lstrip().startswith("\x1b"):
        return text

    def bold_repl(match: re.Match[str]) -> str:
        return f"\x1b[1m{match.group(1)}\x1b[0m"

    def code_repl(match: re.Match[str]) -> str:
        return f"\x1b[38;2;255;214;102m{match.group(1)}\x1b[0m"

    def heading_repl(match: re.Match[str]) -> str:
        return f"\x1b[1m{match.group(2)}\x1b[0m"

    formatted = MD_BOLD.sub(bold_repl, text)
    formatted = MD_CODE.sub(code_repl, formatted)
    formatted = MD_HEADING.sub(heading_repl, formatted)
    formatted = MD_BULLET.sub("• ", formatted)
    return formatted


def pretty_tool_line(kind: str, title: str | None) -> None:
    body = f"{kind}({title})…" if title else kind
    glow = f"{ACCENT_COLOR}\x1b[1m"
    print(f"{glow}⏺ {body}{RESET}")


def pretty_sub_line(text: str) -> None:
    lines = text.splitlines() or [""]
    for line in lines:
        print(f"  ⎿ {format_markdown(line)}")


class Spinner:
    def __init__(self, label: str = "Waiting for model") -> None:
        self.label = label
        self.frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        self.color = "\x1b[38;2;255;229;92m"
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if not sys.stdout.isatty() or self._thread is not None:
            return
        self._stop.clear()

        def run() -> None:
            start_ts = time.time()
            index = 0
            while not self._stop.is_set():
                elapsed = time.time() - start_ts
                frame = self.frames[index % len(self.frames)]
                styled = f"{self.color}{frame} {self.label} ({elapsed:.1f}s)\x1b[0m"
                sys.stdout.write("\r" + styled)
                sys.stdout.flush()
                index += 1
                time.sleep(0.08)

        self._thread = threading.Thread(target=run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if self._thread is None:
            return
        self._stop.set()
        self._thread.join(timeout=1)
        self._thread = None
        try:
            sys.stdout.write("\r\x1b[2K")
            sys.stdout.flush()
        except Exception:  # pragma: no cover - defensive clear
            pass


def pretty_tool_output(title: str, lines: Iterable[str]) -> None:
    pretty_tool_line(title, None)
    for line in lines:
        pretty_sub_line(line)


__all__ = [
    "Spinner",
    "clear_screen",
    "format_markdown",
    "pretty_sub_line",
    "pretty_tool_line",
    "print_divider",
    "render_banner",
    "user_prompt_label",
    "RESET",
    "ACCENT_COLOR",
    "INFO_COLOR",
    "TODO_PENDING_COLOR",
    "TODO_PROGRESS_COLOR",
    "TODO_COMPLETED_COLOR",
]
