"""
RestorAI - Lab 4 API Layer (FastAPI)

Endpoints
---------
GET   /            - service banner / OpenAPI link
GET   /health      - quick liveness + dependency check
POST  /chat        - synchronous RESTful chat (returns final answer)
POST  /stream      - Server-Sent Events stream of agent execution

Persistence
-----------
The LangGraph checkpointer is initialised exactly once at process startup via
FastAPI's `lifespan` context manager and reused for every request - so we never
pay the cost of reconnecting to the checkpoint store on the hot path.

Default backend: AsyncSqliteSaver writing to `CHECKPOINT_DB_PATH`
(defaults to ``./data/checkpoints.sqlite``). Inside the docker-compose stack
this path lives on a named volume so chat history survives container restarts.

Run locally:
    uvicorn app.api.main:app --host 0.0.0.0 --port 8000 --reload

Author: Abdullah Noor - 2022029
"""

from __future__ import annotations

import asyncio
import json
import os
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncIterator, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from app import __version__
from app.agent.graph import build_simple_graph
from app.api.schema import (
    AgentStatus,
    ChatRequest,
    ChatResponse,
    HealthResponse,
    StreamRequest,
    ToolCallTrace,
)


# ---------------------------------------------------------------------------
# Lifespan: build the checkpointer once and share it for the whole process
# ---------------------------------------------------------------------------

def _resolve_checkpoint_path() -> Path:
    raw = os.getenv("CHECKPOINT_DB_PATH", "./data/checkpoints.sqlite")
    p = Path(raw)
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Build the checkpointer + compiled graph at startup, dispose at shutdown.

    The checkpoint store is opened ONCE per process and reused for every
    request (Lab 4 Task 2 - Persistence over HTTP). Using a context manager
    ensures the SQLite connection is closed cleanly when uvicorn receives a
    SIGTERM (important for graceful container shutdowns).
    """
    db_path = _resolve_checkpoint_path()
    print(f"[lifespan] opening checkpoint store: {db_path}")

    async with AsyncSqliteSaver.from_conn_string(str(db_path)) as checkpointer:
        graph = build_simple_graph(checkpointer=checkpointer)
        app.state.checkpointer = checkpointer
        app.state.graph = graph
        app.state.checkpoint_path = str(db_path)
        print("[lifespan] graph compiled and ready")
        try:
            yield
        finally:
            print("[lifespan] shutting down")


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(
    title="RestorAI Agent API",
    description=(
        "REST + SSE interface for the RestorAI furniture-restoration LangGraph "
        "agent. Built for AI407L Lab 4 (API Layer)."
    ),
    version=__version__,
    lifespan=lifespan,
)

# Permissive CORS - the agent is consumed by browser-based demo clients.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sse(event: str, data: Any) -> str:
    """Format a single Server-Sent Event frame."""
    if not isinstance(data, str):
        data = json.dumps(data, ensure_ascii=False)
    return f"event: {event}\ndata: {data}\n\n"


def _trace_tool_call(tc: dict, result_preview: Optional[str] = None) -> ToolCallTrace:
    return ToolCallTrace(
        name=tc.get("name", "?"),
        args=tc.get("args", {}) or {},
        result_preview=(result_preview[:400] + "...") if result_preview and len(result_preview) > 400 else result_preview,
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/", include_in_schema=False)
async def root() -> dict:
    return {
        "service": "RestorAI Agent API",
        "version": __version__,
        "docs": "/docs",
        "endpoints": ["/health", "/chat (POST)", "/stream (POST)"],
    }


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Verify the checkpointer + knowledge base are reachable."""
    checkpointer_status = "ok" if getattr(app.state, "checkpointer", None) else "missing"

    kb_status = "ok"
    try:
        from app.agent.tools import _make_chroma_client
        client = _make_chroma_client()
        client.get_collection(name="restoration_knowledge")
    except Exception as exc:
        kb_status = f"error: {exc}"

    overall = "ok" if checkpointer_status == "ok" and kb_status == "ok" else "degraded"
    return HealthResponse(
        status=overall,
        checkpointer=checkpointer_status,
        knowledge_base=kb_status,
        version=__version__,
    )


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, request: Request) -> ChatResponse:
    """
    Synchronous chat endpoint.

    Bridges stateless HTTP and the stateful LangGraph by mapping
    ``req.thread_id`` to ``config.configurable.thread_id`` so the checkpointer
    can resume conversations across requests.
    """
    graph = getattr(request.app.state, "graph", None)
    if graph is None:
        raise HTTPException(status_code=503, detail="Graph not initialised")

    config = {"configurable": {"thread_id": req.thread_id}}
    initial_state = {"messages": [HumanMessage(content=req.message)]}

    started = time.perf_counter()
    answer_text = ""
    status: AgentStatus = "completed"
    tool_calls: list[ToolCallTrace] = []
    pending: dict[str, ToolCallTrace] = {}
    step_count = 0

    try:
        async for event in graph.astream(initial_state, config, stream_mode="values"):
            step_count += 1
            messages = event.get("messages", [])
            if not messages:
                continue
            last = messages[-1]

            if isinstance(last, AIMessage):
                if getattr(last, "tool_calls", None):
                    for tc in last.tool_calls:
                        trace = _trace_tool_call(tc)
                        tool_calls.append(trace)
                        if tc.get("id"):
                            pending[tc["id"]] = trace
                elif last.content:
                    answer_text = last.content
            elif isinstance(last, ToolMessage):
                tcid = getattr(last, "tool_call_id", None)
                if tcid and tcid in pending:
                    pending[tcid].result_preview = (
                        last.content[:400] + "..." if len(last.content) > 400 else last.content
                    )
    except Exception as exc:
        status = "error"
        answer_text = f"Internal agent error: {exc}"

    elapsed_ms = int((time.perf_counter() - started) * 1000)

    if not answer_text:
        # Graph ended without a final assistant message - mark as interrupted.
        status = "interrupted"
        answer_text = "(no answer produced - check tool outputs)"

    return ChatResponse(
        thread_id=req.thread_id,
        answer=answer_text,
        status=status,
        tool_calls=tool_calls,
        step_count=step_count,
        elapsed_ms=elapsed_ms,
    )


@app.post("/stream")
async def stream(req: StreamRequest, request: Request) -> StreamingResponse:
    """
    Server-Sent Events stream of LangGraph execution.

    Event types emitted:
        meta        -> { thread_id, started_at }
        node        -> { node, content }              (a graph node finished)
        tool_call   -> { name, args }                 (the agent requested a tool)
        tool_result -> { name, result_preview }       (a tool returned)
        token       -> { delta }                       (incremental answer chunks)
        done        -> { status, step_count, elapsed_ms }
        error       -> { message }
    """
    graph = getattr(request.app.state, "graph", None)
    if graph is None:
        raise HTTPException(status_code=503, detail="Graph not initialised")

    config = {"configurable": {"thread_id": req.thread_id}}
    initial_state = {"messages": [HumanMessage(content=req.message)]}

    async def event_generator() -> AsyncIterator[str]:
        started = time.perf_counter()
        step_count = 0
        last_emitted_len = 0
        status: AgentStatus = "completed"
        last_ai_text = ""

        yield _sse("meta", {"thread_id": req.thread_id, "started_at": time.time()})

        try:
            async for event in graph.astream(initial_state, config, stream_mode="values"):
                # Allow the client to disconnect cleanly.
                if await request.is_disconnected():
                    status = "interrupted"
                    break

                step_count += 1
                messages = event.get("messages", [])
                if not messages:
                    continue
                last = messages[-1]

                if isinstance(last, AIMessage):
                    if getattr(last, "tool_calls", None):
                        for tc in last.tool_calls:
                            yield _sse("tool_call", {"name": tc.get("name"), "args": tc.get("args", {})})
                            await asyncio.sleep(0)
                    elif last.content:
                        # Emit the new tail as a token delta for ChatGPT-like UX.
                        new_text = last.content
                        if new_text != last_ai_text:
                            delta = new_text[last_emitted_len:] if new_text.startswith(last_ai_text) else new_text
                            last_emitted_len = len(new_text)
                            last_ai_text = new_text
                            yield _sse("token", {"delta": delta})
                            yield _sse("node", {"node": "agent", "content_len": len(new_text)})
                            await asyncio.sleep(0)

                elif isinstance(last, ToolMessage):
                    preview = last.content if len(last.content) <= 400 else last.content[:400] + "..."
                    yield _sse("tool_result", {"name": last.name, "result_preview": preview})
                    await asyncio.sleep(0)

            elapsed_ms = int((time.perf_counter() - started) * 1000)
            yield _sse("done", {"status": status, "step_count": step_count, "elapsed_ms": elapsed_ms})

        except Exception as exc:
            yield _sse("error", {"message": str(exc)})
            yield _sse("done", {"status": "error", "step_count": step_count})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # disable buffering on nginx-style proxies
        },
    )
