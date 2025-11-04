"""General-purpose text helpers."""
from __future__ import annotations


def clamp_text(text: str, limit: int) -> str:
    """Clamp ``text`` to at most ``limit`` characters."""
    if len(text) <= limit:
        return text
    remaining = len(text) - limit
    return text[:limit] + f"\n\n...<truncated {remaining} chars>"


__all__ = ["clamp_text"]
