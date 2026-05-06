"""
Lab 4 - End-to-end API test client.

Exercises every endpoint of the RestorAI FastAPI service:

    GET    /
    GET    /health
    POST   /chat       (synchronous)
    POST   /stream     (Server-Sent Events)

Why a Python client instead of plain curl?
    * Windows powershell ``curl`` is an alias for Invoke-WebRequest which
      buffers the response - it cannot show SSE deltas as they arrive.
    * The test client uses ``httpx`` which streams the response correctly.

Run:
    python lab4_api/test_api.py            # default: http://127.0.0.1:8000
    python lab4_api/test_api.py --base http://localhost:8000
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from uuid import uuid4

import httpx


def banner(title: str) -> None:
    print()
    print("=" * 70)
    print(title)
    print("=" * 70)


def test_root(base: str) -> None:
    banner("TEST 1 - GET /")
    r = httpx.get(f"{base}/", timeout=10)
    print(f"status: {r.status_code}")
    print(json.dumps(r.json(), indent=2))
    assert r.status_code == 200


def test_health(base: str) -> None:
    banner("TEST 2 - GET /health")
    r = httpx.get(f"{base}/health", timeout=15)
    print(f"status: {r.status_code}")
    print(json.dumps(r.json(), indent=2))
    assert r.status_code == 200
    assert r.json()["status"] in {"ok", "degraded"}


def test_chat(base: str, thread_id: str) -> None:
    banner("TEST 3 - POST /chat (synchronous)")
    payload = {
        "message": (
            "I have water ring damage on an oak coffee table. "
            "Give me a short restoration plan."
        ),
        "thread_id": thread_id,
    }
    print("> request:")
    print(json.dumps(payload, indent=2))
    started = time.perf_counter()
    r = httpx.post(f"{base}/chat", json=payload, timeout=120)
    elapsed = time.perf_counter() - started

    print(f"\n> http {r.status_code} in {elapsed:.2f}s")
    body = r.json()
    print(json.dumps({
        "thread_id": body.get("thread_id"),
        "status": body.get("status"),
        "step_count": body.get("step_count"),
        "elapsed_ms": body.get("elapsed_ms"),
        "tool_calls": [t["name"] for t in body.get("tool_calls", [])],
        "answer_preview": (body.get("answer") or "")[:600] + "...",
    }, indent=2))
    assert r.status_code == 200
    assert body["status"] in {"completed", "interrupted"}


def test_persistence(base: str, thread_id: str) -> None:
    banner("TEST 4 - Persistence over HTTP (same thread_id)")
    payload = {
        "message": "Based on what we just discussed, give me only the shopping list as bullet points.",
        "thread_id": thread_id,
    }
    print("> reusing thread_id:", thread_id)
    r = httpx.post(f"{base}/chat", json=payload, timeout=120)
    body = r.json()
    print(json.dumps({
        "thread_id": body.get("thread_id"),
        "status": body.get("status"),
        "answer_preview": (body.get("answer") or "")[:400] + "...",
    }, indent=2))
    assert r.status_code == 200


def test_stream(base: str, thread_id: str) -> None:
    banner("TEST 5 - POST /stream (Server-Sent Events)")
    payload = {
        "message": "Briefly explain the safety precautions for chemical strippers.",
        "thread_id": thread_id,
    }
    print("> request:")
    print(json.dumps(payload, indent=2))
    print("\n> SSE events:")
    with httpx.stream("POST", f"{base}/stream", json=payload, timeout=120) as r:
        assert r.status_code == 200
        for line in r.iter_lines():
            if not line:
                continue
            print("  " + line)


def main() -> int:
    parser = argparse.ArgumentParser(description="RestorAI API smoke test")
    parser.add_argument("--base", default="http://127.0.0.1:8000",
                        help="Base URL of the running API.")
    parser.add_argument("--skip-stream", action="store_true",
                        help="Skip the SSE streaming test (e.g. when capturing logs).")
    args = parser.parse_args()

    thread_id = str(uuid4())

    try:
        test_root(args.base)
        test_health(args.base)
        test_chat(args.base, thread_id)
        test_persistence(args.base, thread_id)
        if not args.skip_stream:
            test_stream(args.base, thread_id)
    except AssertionError as exc:
        print(f"\nASSERTION FAILED: {exc}", file=sys.stderr)
        return 1
    except httpx.HTTPError as exc:
        print(f"\nHTTP ERROR: {exc}", file=sys.stderr)
        return 1

    banner("ALL TESTS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
