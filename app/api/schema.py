"""
Lab 4 - Pydantic schemas (the contract between client and agent).

Defines:
    ChatRequest     - body for POST /chat and POST /stream
    ChatResponse    - body returned by POST /chat
    StreamRequest   - alias of ChatRequest (kept explicit for OpenAPI docs)
    AgentStatus     - enum-style string literal for the current run status
    HealthResponse  - body returned by GET /health

All identifiers, message lengths and thread IDs are validated server-side so
the FastAPI layer rejects malformed input *before* it hits the LangGraph runtime.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Literal, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator


AgentStatus = Literal["completed", "in_progress", "interrupted", "error"]


class ChatRequest(BaseModel):
    """Incoming user message + conversation thread identifier."""

    model_config = ConfigDict(json_schema_extra={
        "examples": [{
            "message": "I have a vintage walnut table with water rings. Help me restore it..",
            "thread_id": "550e8400-e29b-41d4-a716-446655440000",
        }],
    })


    message: str = Field(
        ...,
        min_length=1,
        max_length=8000,
        description="User message / instruction to the agent.",
    )
    thread_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description=(
            "Conversation thread ID. Reuse the same value to continue an existing "
            "conversation; provide a new value (or omit to auto-generate a UUID) to start fresh."
        ),
    )

    @field_validator("thread_id")
    @classmethod
    def _validate_thread_id(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("thread_id cannot be empty")
        if len(v) > 128:
            raise ValueError("thread_id must be <= 128 characters")
        # Accept either a UUID or any short identifier (so demos can use 'demo-1').
        try:
            UUID(v)
            return v
        except (ValueError, AttributeError):
            pass
        # Allow simple ASCII slugs as a friendly alternative.
        if not all(ch.isalnum() or ch in "-_." for ch in v):
            raise ValueError(
                "thread_id must be a UUID or contain only alphanumeric, '-', '_' or '.' characters"
            )
        return v


class StreamRequest(ChatRequest):
    """Alias used by the streaming endpoint - kept distinct for OpenAPI clarity."""


class ToolCallTrace(BaseModel):
    """Information about a tool the agent used while answering."""
    name: str
    args: dict
    result_preview: Optional[str] = Field(
        default=None,
        description="First ~400 chars of the tool's response (truncated for UI display).",
    )


class ChatResponse(BaseModel):
    """Final answer + run metadata returned by POST /chat."""

    model_config = ConfigDict(json_schema_extra={
        "examples": [{
            "thread_id": "550e8400-e29b-41d4-a716-446655440000",
            "answer": "RESTORATION PLAN: ...",
            "status": "completed",
            "tool_calls": [],
            "step_count": 3,
            "elapsed_ms": 4821,
            "timestamp": "2026-05-04T16:54:00Z",
        }],
    })

    thread_id: str = Field(..., description="Echoes the thread_id from the request.")
    answer: str = Field(..., description="Final agent answer (the restoration plan).")
    status: AgentStatus = Field(..., description="Run outcome.")
    tool_calls: List[ToolCallTrace] = Field(
        default_factory=list,
        description="Tools the agent invoked while producing the answer.",
    )
    step_count: int = Field(
        default=0, ge=0, description="Number of LangGraph events emitted during this run."
    )
    elapsed_ms: int = Field(
        default=0, ge=0, description="Wall-clock duration of the run, in milliseconds."
    )
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class HealthResponse(BaseModel):
    """Returned by GET /health - verifies the API + checkpointer + KB are reachable."""
    status: Literal["ok", "degraded"]
    checkpointer: str
    knowledge_base: str
    version: str
