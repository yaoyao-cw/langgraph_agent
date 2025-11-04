"""Configuration objects and constants for the LangGraph agent."""
from __future__ import annotations

from pathlib import Path
from typing import Tuple

from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    """Runtime configuration for the LangGraph agent.

    Values can be overridden through environment variables with the
    ``LANGGRAPH_AGENT_`` prefix or via a local ``.env`` file.
    """

    anthropic_base_url: str = Field(
        default="https://dashscope.aliyuncs.com/compatible-mode/v1",
        description="Base URL for Anthropic compatible APIs.",
    )
    anthropic_api_key: str = Field(
        default="sk-e300801ecaf3456aaa8365eaf0bd0710",
        description="API key used for Anthropic compatible endpoints.",
    )
    agent_model: str = Field(
        default="qwen3-max-2025-09-23",
        description="Model identifier used for language model invocations.",
    )
    workspace: Path = Field(
        default_factory=lambda: Path.cwd(),
        description="Workspace root where all file operations should occur.",
    )
    max_tool_result_chars: int = Field(
        default=100_000,
        description="Maximum number of characters returned from a tool call.",
    )
    todo_statuses: Tuple[str, str, str] = Field(
        default=("pending", "in_progress", "completed"),
        description="Allowed statuses for TODO items.",
    )

    class Config:
        env_prefix = "LANGGRAPH_AGENT_"
        env_file = ".env"
        case_sensitive = False


settings = Settings()
