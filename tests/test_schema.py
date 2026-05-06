"""
Pure-Pydantic schema tests. No network, no LLM, no chromadb - safe to run in CI
in under a second.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.api.schema import ChatRequest, ChatResponse, AgentStatus  # noqa: F401


def test_chat_request_minimal():
    req = ChatRequest(message="hello")
    assert req.message == "hello"
    assert len(req.thread_id) >= 8  # auto-generated UUID


def test_chat_request_uuid_thread_id():
    tid = "550e8400-e29b-41d4-a716-446655440000"
    req = ChatRequest(message="hi", thread_id=tid)
    assert req.thread_id == tid


def test_chat_request_slug_thread_id():
    req = ChatRequest(message="hi", thread_id="demo-1.run_42")
    assert req.thread_id == "demo-1.run_42"


def test_chat_request_rejects_empty_message():
    with pytest.raises(ValidationError):
        ChatRequest(message="")


def test_chat_request_rejects_oversized_message():
    with pytest.raises(ValidationError):
        ChatRequest(message="x" * 10_000)


def test_chat_request_rejects_bad_thread_id():
    with pytest.raises(ValidationError):
        ChatRequest(message="hi", thread_id="bad space id")


def test_chat_response_round_trip():
    r = ChatResponse(
        thread_id="demo",
        answer="ok",
        status="completed",
        tool_calls=[],
        step_count=3,
        elapsed_ms=42,
    )
    dumped = r.model_dump_json()
    assert "completed" in dumped


def test_chat_response_rejects_unknown_status():
    with pytest.raises(ValidationError):
        ChatResponse(
            thread_id="demo",
            answer="ok",
            status="not-a-status",  # type: ignore[arg-type]
        )
