"""
RestorAI Agent Package - LangGraph state machine + tools.

Public exports:
- TOOLS                          : list of LangChain tools used by the agent
- create_simple_restorai_graph   : single-agent ReAct graph with checkpointer override
- create_hitl_simple_restorai_graph : same graph with human-in-the-loop on order_products
- run_restorai_agent             : convenience runner used in CLI/demo modes
"""

from .tools import (
    TOOLS,
    analyze_furniture_image,
    search_restoration_knowledge,
    search_web_for_products,
    order_products,
    KnowledgeBase,
)
from .graph import (
    AgentState,
    SimpleAgentState,
    build_simple_graph,
    build_hitl_graph,
    create_simple_restorai_graph,
    create_hitl_simple_restorai_graph,
    run_restorai_agent,
)

__all__ = [
    "TOOLS",
    "analyze_furniture_image",
    "search_restoration_knowledge",
    "search_web_for_products",
    "order_products",
    "KnowledgeBase",
    "AgentState",
    "SimpleAgentState",
    "build_simple_graph",
    "build_hitl_graph",
    "create_simple_restorai_graph",
    "create_hitl_simple_restorai_graph",
    "run_restorai_agent",
]
