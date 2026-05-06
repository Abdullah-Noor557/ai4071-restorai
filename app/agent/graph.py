"""
RestorAI - LangGraph state machine.

Implements the ReAct loop (Reason -> Act -> Loop) used by all submission
artifacts (Lab 3 CLI, Lab 4 API, OEL evaluation harness).

Public factories:
    build_simple_graph(checkpointer=None)       -> compiled StateGraph
    build_hitl_graph(checkpointer=None)         -> compiled StateGraph (with HITL)
    create_simple_restorai_graph()              -> backward-compat (MemorySaver)
    create_hitl_simple_restorai_graph()         -> backward-compat (MemorySaver)

Author: Abdullah Noor - 2022029
"""

from __future__ import annotations

import json
import operator
from typing import Annotated, Any, Literal, Optional, Sequence, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode

from .tools import TOOLS


# ---------------------------------------------------------------------------
# State definitions
# ---------------------------------------------------------------------------

class AgentState(TypedDict):
    """Full multi-agent state (used by the legacy 3-agent workflow)."""
    messages: Annotated[Sequence[BaseMessage], operator.add]
    current_agent: str
    vision_analysis: str
    restoration_plan: str
    final_output: str
    image_path: str


class SimpleAgentState(TypedDict):
    """Minimal state used by the single-agent ReAct graph (Lab 4)."""
    messages: Annotated[Sequence[BaseMessage], operator.add]


# ---------------------------------------------------------------------------
# System prompt for the unified agent
# ---------------------------------------------------------------------------

UNIFIED_SYSTEM_PROMPT = """You are RestorAI, an expert furniture restoration assistant.

YOUR CAPABILITIES (tools):
1. analyze_furniture_image     - Analyse uploaded furniture images (skip if no image given).
2. search_restoration_knowledge - RAG over the curated restoration knowledge base.
3. search_web_for_products      - Find product / retailer / price info.
4. order_products               - HIGH-RISK. Only call when the user explicitly asks to order/buy.

WORKFLOW:
1. Identify damage / material from the user's description (or vision tool if image supplied).
2. Use search_restoration_knowledge for techniques.
3. Use search_restoration_knowledge with safety_only=True for any chemical / aggressive method.
4. Use search_web_for_products to build a shopping list.
5. ONLY if the user explicitly asked to order/buy items, call order_products.

OUTPUT FORMAT - return a complete restoration plan with:
RESTORATION PLAN: [Description]

SHOPPING LIST
-------------
- [Product] - $X-Y (Retailers)

STEP-BY-STEP INSTRUCTIONS
-------------------------
Step 1: ...

SAFETY WARNINGS
---------------
- ...

ESTIMATED TIME: X hours
ESTIMATED COST: $X-Y
DIFFICULTY: Easy/Medium/Hard

RULES:
- Always ground recommendations in knowledge-base results, not assumptions.
- Always check safety_only=True before recommending chemical or aggressive methods.
- If material is veneer, include the constraint NO SANDING.
- Do NOT ask the user for an image if they already described the problem in text.
"""


# ---------------------------------------------------------------------------
# Conditional router shared by both graphs
# ---------------------------------------------------------------------------

def should_continue(state: SimpleAgentState) -> Literal["tools", "end"]:
    """Route to tools if the latest message has tool_calls, else end."""
    messages = state["messages"]
    if not messages:
        return "end"
    last = messages[-1]
    if hasattr(last, "tool_calls") and last.tool_calls:
        return "tools"
    return "end"


# ---------------------------------------------------------------------------
# Single-agent ReAct graph (used by Lab 3 demo, Lab 4 API and OEL eval)
# ---------------------------------------------------------------------------

def _make_agent_node(model_name: str = "gpt-4o-mini"):
    """Factory for the agent reasoning node."""
    llm = ChatOpenAI(model=model_name, temperature=0)
    llm_with_tools = llm.bind_tools(TOOLS)

    def agent_node(state: SimpleAgentState):
        messages = [{"role": "system", "content": UNIFIED_SYSTEM_PROMPT}] + list(state["messages"])
        response = llm_with_tools.invoke(messages)
        return {"messages": [response]}

    return agent_node


def build_simple_graph(
    checkpointer: Optional[BaseCheckpointSaver] = None,
    model_name: str = "gpt-4o-mini",
):
    """
    Build the canonical single-agent ReAct graph.

    Args:
        checkpointer: optional checkpointer (e.g. SqliteSaver). When omitted a
                      fresh MemorySaver is used. The API layer injects a long-
                      lived SqliteSaver via FastAPI lifespan.
        model_name:   OpenAI chat model.
    """
    workflow: StateGraph = StateGraph(SimpleAgentState)

    workflow.add_node("agent", _make_agent_node(model_name=model_name))
    workflow.add_node("tools", ToolNode(TOOLS))
    workflow.set_entry_point("agent")
    workflow.add_conditional_edges("agent", should_continue, {"tools": "tools", "end": END})
    workflow.add_edge("tools", "agent")

    return workflow.compile(checkpointer=checkpointer or MemorySaver())


def create_simple_restorai_graph():
    """Backward-compatible alias used by the Lab 3 CLI."""
    return build_simple_graph()


# ---------------------------------------------------------------------------
# HITL variant - human approval gate before order_products
# ---------------------------------------------------------------------------

def build_hitl_graph(checkpointer: Optional[BaseCheckpointSaver] = None):
    workflow: StateGraph = StateGraph(SimpleAgentState)
    workflow.add_node("agent", _make_agent_node())

    tool_map = {t.name: t for t in TOOLS}

    def hitl_tools_node(state: SimpleAgentState):
        messages = list(state["messages"])
        last = messages[-1]
        out_messages: list[BaseMessage] = []

        for tc in getattr(last, "tool_calls", []) or []:
            name = tc.get("name")
            args = tc.get("args", {}) or {}
            tcid = tc.get("id", "hitl_tool_call")

            if name == "order_products":
                print("\n" + "=" * 70)
                print("HITL SAFETY INTERRUPT: High-risk tool requested")
                print("=" * 70)
                print(f"Tool: {name}")
                print("Proposed args:")
                print(json.dumps(args, indent=2))
                print("\nChoose: [A]pprove / [E]dit JSON args / [C]ancel")
                choice = input("Your choice (A/E/C): ").strip().lower()

                if choice == "c":
                    out_messages.append(ToolMessage(
                        content=json.dumps({"ok": False, "cancelled": True}),
                        name=name, tool_call_id=tcid,
                    ))
                    continue

                if choice == "e":
                    edited = input("Paste edited JSON args: ").strip()
                    try:
                        args = json.loads(edited)
                    except Exception as exc:
                        out_messages.append(ToolMessage(
                            content=json.dumps({"ok": False, "error": f"Invalid JSON: {exc}"}),
                            name=name, tool_call_id=tcid,
                        ))
                        continue

                tool_obj = tool_map.get(name)
                result = tool_obj.invoke(args) if tool_obj else json.dumps({"ok": False, "error": "Tool not found"})
                out_messages.append(ToolMessage(content=str(result), name=name, tool_call_id=tcid))
                continue

            # regular tool
            tool_obj = tool_map.get(name)
            result = tool_obj.invoke(args) if tool_obj else json.dumps({"ok": False, "error": "Tool not found"})
            out_messages.append(ToolMessage(content=str(result), name=name, tool_call_id=tcid))

        return {"messages": out_messages}

    workflow.add_node("tools", hitl_tools_node)
    workflow.set_entry_point("agent")
    workflow.add_conditional_edges("agent", should_continue, {"tools": "tools", "end": END})
    workflow.add_edge("tools", "agent")

    return workflow.compile(checkpointer=checkpointer or MemorySaver())


def create_hitl_simple_restorai_graph():
    """Backward-compatible alias used by the Lab 3 CLI HITL demo."""
    return build_hitl_graph()


# ---------------------------------------------------------------------------
# CLI helper kept for Lab 3 compatibility
# ---------------------------------------------------------------------------

def run_restorai_agent(image_path: str, user_query: Optional[str] = None, use_simple: bool = True):
    """Run the agent end-to-end and print streaming output (used by Lab 3 main.py)."""
    print("\n" + "=" * 70)
    print("RestorAI Agent System")
    print("=" * 70)

    app = build_simple_graph()
    if not user_query:
        user_query = f"Please analyze this furniture image and create a restoration plan: {image_path}"

    initial_state = {"messages": [HumanMessage(content=user_query)]}
    config: dict[str, Any] = {"configurable": {"thread_id": "restorai_session_1"}}

    final_state = None
    for event in app.stream(initial_state, config, stream_mode="values"):
        messages = event.get("messages", [])
        if messages:
            last = messages[-1]
            if isinstance(last, AIMessage):
                if getattr(last, "tool_calls", None):
                    for tc in last.tool_calls:
                        print(f"  -> tool: {tc['name']} args={tc['args']}")
                elif last.content:
                    print(f"  agent: {last.content[:200]}...")
            elif isinstance(last, ToolMessage):
                print(f"  <- tool result ({len(last.content)} chars)")
        final_state = event

    print("=" * 70)
    return final_state
