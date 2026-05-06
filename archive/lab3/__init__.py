"""
RestorAI Lab 3: Multi-Agent System Package

This package contains the LangGraph implementation for RestorAI's
multi-agent furniture restoration system.

Modules:
- tools.py: Tool definitions with Pydantic validation
- graph.py: LangGraph state machine and agent nodes
- main.py: Execution script and CLI

Author: Abdullah Noor - 2022029
"""

__version__ = "1.0.0"
__author__ = "Abdullah Noor"
__student_id__ = "2022029"

from .tools import TOOLS, analyze_furniture_image, search_restoration_knowledge, search_web_for_products
from .graph import create_simple_restorai_graph, create_restorai_graph, run_restorai_agent

__all__ = [
    "TOOLS",
    "analyze_furniture_image",
    "search_restoration_knowledge",
    "search_web_for_products",
    "create_simple_restorai_graph",
    "create_restorai_graph",
    "run_restorai_agent"
]
