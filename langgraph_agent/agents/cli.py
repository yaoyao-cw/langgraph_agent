"""Command-line interface entry point for the LangGraph agent."""
from __future__ import annotations

from typing import Any, Sequence

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from ..config import settings
from ..graph.builder import build_toolkit, create_agent
from ..prompts.system import build_system_prompt
from ..utils.console import (
    INFO_COLOR,
    RESET,
    clear_screen,
    print_divider,
    render_banner,
    user_prompt_label,
)


def build_llm(**overrides: Any) -> ChatOpenAI:
    """Construct the chat model used by the agent."""
    params = {
        "model": settings.agent_model,
        "api_key": settings.anthropic_api_key,
        "base_url": settings.anthropic_base_url,
        "max_tokens": 160000,
    }
    params.update(overrides)
    return ChatOpenAI(**params)


def run_cli(additional_tools: Sequence[Any] | None = None) -> None:
    """Run the interactive CLI application."""
    clear_screen()
    render_banner("LangGraph Test Generator", "AI-Powered Test Case Generation")
    print(f"{INFO_COLOR}Workspace: {settings.workspace}{RESET}")
    print(f"{INFO_COLOR}Type 'exit' to quit{RESET}\n")

    llm = build_llm()
    tools_list = build_toolkit(additional_tools)
    bound_llm = llm.bind_tools(tools_list)
    app = create_agent(bound_llm, tools_list)

    thread_id = "main_thread"
    config = {
        "configurable": {"thread_id": thread_id},
        "recursion_limit": 150,
    }

    state = {
        "messages": [SystemMessage(content=build_system_prompt())],
        "rounds_without_todo": 0,
        "pending_reminders": [],
    }

    while True:
        try:
            line = input(user_prompt_label())
        except (EOFError, KeyboardInterrupt):
            break

        if not line or line.strip().lower() in {"q", "quit", "exit"}:
            break

        print_divider()
        state["messages"].append(HumanMessage(content=line))

        try:
            for event in app.stream(state, config):
                for key, value in event.items():
                    if key == "__end__":
                        continue
                    if "messages" in value:
                        new_messages = [
                            m for m in value["messages"] if not isinstance(m, SystemMessage)
                        ]
                        state["messages"].extend(new_messages)
                    if "rounds_without_todo" in value:
                        state["rounds_without_todo"] = value["rounds_without_todo"]
                    if "pending_reminders" in value:
                        state["pending_reminders"] = value["pending_reminders"]
        except Exception as error:  # pragma: no cover - runtime guard
            print(f"{INFO_COLOR}Error: {error}{RESET}")

        print()


def main() -> None:
    run_cli()


if __name__ == "__main__":  # pragma: no cover - CLI execution
    main()
