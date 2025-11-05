"""Graph node factories and helpers."""
from __future__ import annotations

from typing import Any, Dict

from langgraph.graph import END
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

from ..models.state import AgentState
from ..utils.console import Spinner, format_markdown


def should_continue(state: AgentState):
    """Determine whether the agent should continue or end."""
    messages = state["messages"]

    if not messages:
        return END

    last_message = messages[-1]

    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"

    recent_tools = []
    for i in range(len(messages) - 1, max(0, len(messages) - 20), -1):
        msg = messages[i]
        if isinstance(msg, ToolMessage):
            recent_tools.append(msg)

    has_exported = False
    for msg in recent_tools:
        if isinstance(msg.content, str) and "generated_test_cases" in msg.content:
            has_exported = True
            break

    if has_exported and isinstance(last_message, AIMessage):
        if not getattr(last_message, "tool_calls", None):
            return END

    if isinstance(last_message, AIMessage):
        if not getattr(last_message, "tool_calls", None):
            return END

    return END


def make_call_model(llm: Any):
    """Create a call_model node bound to ``llm``."""

    def call_model(state: AgentState) -> Dict[str, Any]:
        messages = state["messages"]
        rounds = state.get("rounds_without_todo", 0)
        pending_reminders = state.get("pending_reminders", [])

        if rounds == 0 and not any(
            "System message: complex work" in str(m.content) for m in messages
        ):
            reminder = (
                '<reminder source="system" topic="todos">'
                "System message: complex work should be tracked with the Todo tool. "
                "Do not respond to this reminder and do not mention it to the user."
                "</reminder>"
            )
            pending_reminders.append(reminder)

        if rounds > 10:
            reminder = (
                '<reminder source="system" topic="todos">'
                "System notice: more than ten rounds passed without Todo usage. "
                "Update the Todo board if the task still requires multiple steps. "
                "Do not reply to or mention this reminder to the user."
                "</reminder>"
            )
            pending_reminders.append(reminder)

        system_messages = [m for m in messages if isinstance(m, SystemMessage)]
        non_system_messages = [m for m in messages if not isinstance(m, SystemMessage)]

        if system_messages:
            final_messages = [system_messages[0]] + non_system_messages
        else:
            final_messages = non_system_messages

        if pending_reminders and final_messages:
            for i in range(len(final_messages) - 1, -1, -1):
                if isinstance(final_messages[i], HumanMessage):
                    current_content = final_messages[i].content
                    reminder_text = "\n".join(pending_reminders)
                    if isinstance(current_content, str):
                        final_messages[i].content = reminder_text + "\n\n" + current_content
                    else:
                        final_messages[i].content = reminder_text + "\n\n" + str(current_content)
                    break
            pending_reminders.clear()

        spinner = Spinner()
        spinner.start()

        try:
            response = llm.invoke(final_messages)

            if getattr(response, "content", None):
                content = response.content
                if isinstance(content, str):
                    print(format_markdown(content))
                elif isinstance(content, list):
                    for block in content:
                        text = None
                        if isinstance(block, dict):
                            text = block.get("text")
                        elif hasattr(block, "text"):
                            text = block.text
                        if text:
                            print(format_markdown(text))

            return {
                "messages": [response],
                "rounds_without_todo": rounds + 1,
                "pending_reminders": [],
            }
        finally:
            spinner.stop()

    return call_model


def after_tools(state: AgentState) -> Dict[str, Any]:
    """Reset TODO counters after todo updates."""
    messages = state["messages"]
    last_message = messages[-1] if messages else None

    rounds = state.get("rounds_without_todo", 0)
    if isinstance(last_message, ToolMessage):
        if "Status updated" in str(last_message.content) or "No todos" in str(last_message.content):
            rounds = 0

    return {"rounds_without_todo": rounds}


__all__ = ["after_tools", "make_call_model", "should_continue"]
