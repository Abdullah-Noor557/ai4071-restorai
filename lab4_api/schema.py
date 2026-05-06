"""
Lab 4 Submission - schema.py

This file is the rubric-required deliverable. It re-exports the canonical
Pydantic models from ``app.api.schema`` so the submission folder stands on its
own while the implementation lives in the maintained package.

Defined models:
    - ChatRequest    (POST /chat, POST /stream body)
    - ChatResponse   (POST /chat response body)
    - StreamRequest  (alias of ChatRequest, used by /stream for OpenAPI clarity)
    - HealthResponse (GET /health response body)
    - ToolCallTrace  (one tool invocation in ChatResponse.tool_calls)

Validation rules enforced by Pydantic:
    * message    : 1..8000 chars, non-empty.
    * thread_id  : UUID OR ASCII slug (letters/digits/-_.), <= 128 chars.
    * status     : one of {completed, in_progress, interrupted, error}.
"""

from app.api.schema import (  # noqa: F401  (re-export)
    AgentStatus,
    ChatRequest,
    ChatResponse,
    HealthResponse,
    StreamRequest,
    ToolCallTrace,
)

__all__ = [
    "AgentStatus",
    "ChatRequest",
    "ChatResponse",
    "HealthResponse",
    "StreamRequest",
    "ToolCallTrace",
]
