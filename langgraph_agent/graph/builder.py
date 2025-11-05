"""Utilities for assembling the LangGraph agent."""
from __future__ import annotations

from typing import Any, List, Sequence

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode

from ..models.state import AgentState
from ..tools.system import bash, edit_text, read_file, write_file
from ..tools.test_generation import (
    apply_inferred_outputs,
    bind_language_model,
    execute_strategies,
    export_test_cases,
    extract_covered_combinations,
    get_test_results,
    infer_outputs_with_ai,
    initialize_test_gen,
)
from ..tools.todo import todo_write
from .nodes import after_tools, make_call_model, should_continue


def build_toolkit(additional_tools: Sequence[Any] | None = None) -> List[Any]:
    """Return the default toolkit, optionally extended with ``additional_tools``."""
    base_tools = [
        bash,
        read_file,
        write_file,
        edit_text,
        todo_write,
        initialize_test_gen,
        extract_covered_combinations,
        execute_strategies,
        infer_outputs_with_ai,
        apply_inferred_outputs,
        export_test_cases,
        get_test_results,
    ]
    if additional_tools:
        base_tools.extend(additional_tools)
    return base_tools


def create_agent(llm: Any, tools_list: Sequence[Any]):
    """Create the LangGraph agent application and configured tool list."""
    bind_language_model(llm)

    workflow = StateGraph(AgentState)
    workflow.add_node("agent", make_call_model(llm))
    workflow.add_node("tools", ToolNode(tools_list))
    workflow.add_node("after_tools", after_tools)

    workflow.set_entry_point("agent")

    workflow.add_conditional_edges(
        "agent",
        should_continue,
        {
            "tools": "tools",
            END: END,
        },
    )

    workflow.add_edge("tools", "after_tools")
    workflow.add_edge("after_tools", "agent")

    memory = MemorySaver()
    app = workflow.compile(checkpointer=memory)

    return app


__all__ = ["build_toolkit", "create_agent"]
