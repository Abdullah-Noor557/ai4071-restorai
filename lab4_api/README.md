# Lab 4 - The API Layer (FastAPI & LangServe-style)

**Author**: Abdullah Noor (2022029)
**Course**: AI407L
**Prerequisites**: Lab 3 (Reasoning Loop) + Lab 5 (Persistence)

This folder is the **submission package** for Lab 4. The implementation lives
in the maintained `app/api/` package one level up; the files in this folder
are the rubric-required deliverables and a reproducible test harness.

```
lab4_api/
├── README.md              <- this file
├── schema.py              <- re-exports app/api/schema.py (Pydantic models)
├── main.py                <- re-exports app/api/main.py (FastAPI app)
├── smoke_test.py          <- end-to-end tester (writes api_test_results.txt)
├── test_api.py            <- minimal one-shot client used during the demo
└── api_test_results.txt   <- captured output of a successful run + curl appendix
```

---

## Mandatory tasks - where to look

### Task 1 - Endpoint Design & Schema Validation

`schema.py` (re-exporting `app/api/schema.py`) defines:

| Model            | Used by              | Notes                                    |
|------------------|----------------------|------------------------------------------|
| `ChatRequest`    | POST `/chat`, `/stream` | `message` (1-8000 chars) + `thread_id` (UUID or slug, <=128 chars) |
| `ChatResponse`   | POST `/chat`         | `answer`, `status`, `tool_calls`, `step_count`, `elapsed_ms`, `timestamp` |
| `StreamRequest`  | POST `/stream`       | alias of `ChatRequest`, kept distinct for OpenAPI |
| `HealthResponse` | GET  `/health`       | dependency check                         |
| `AgentStatus`    | string literal       | `completed | in_progress | interrupted | error` |

Tests 4 and 5 in `api_test_results.txt` show the API rejecting an empty
`message` and a malformed `thread_id` with HTTP 422.

### Task 2 - Persistence over HTTP

The checkpointer is **opened once** in `app/api/main.py::lifespan`:

```python
async with AsyncSqliteSaver.from_conn_string(str(db_path)) as checkpointer:
    graph = build_simple_graph(checkpointer=checkpointer)
    app.state.checkpointer = checkpointer
    app.state.graph = graph
    yield
```

The endpoint maps the request's `thread_id` onto LangGraph's
`config.configurable.thread_id`:

```python
config = {"configurable": {"thread_id": req.thread_id}}
async for event in graph.astream(initial_state, config, stream_mode="values"):
    ...
```

So any number of HTTP requests that share the same `thread_id` continue the
**same** conversation. Tests 6 and 7 in `api_test_results.txt` reuse the
same `thread_id` to demonstrate this.

The checkpoint database lives at `CHECKPOINT_DB_PATH` (default
`./data/checkpoints.sqlite`). In the `oel_deployment/` Docker stack this
path is on a named volume, so chats survive container restarts.

### Task 3 - Streaming Responses (Server-Sent Events)

`POST /stream` returns `text/event-stream` and emits these SSE frames:

| Event         | When                                               |
|---------------|----------------------------------------------------|
| `meta`        | first frame, contains `thread_id` + `started_at`   |
| `tool_call`   | the agent requested a tool                         |
| `tool_result` | a tool returned (preview, truncated to 400 chars)  |
| `token`       | incremental answer text (for ChatGPT-like UX)      |
| `node`        | a graph node finished (with `content_len`)         |
| `done`        | terminal frame: `status`, `step_count`, `elapsed_ms` |
| `error`       | exception encountered during the run                |

Implementation:

```python
async def event_generator():
    yield _sse("meta", {"thread_id": req.thread_id, "started_at": time.time()})
    async for event in graph.astream(initial_state, config, stream_mode="values"):
        ...
        yield _sse("token", {"delta": delta})
    yield _sse("done", {"status": status, "step_count": step_count, ...})

return StreamingResponse(event_generator(), media_type="text/event-stream", ...)
```

Frontends can consume this directly with the browser `EventSource` API.

---

## How to run

```powershell
# from the repo root
$env:OPENAI_API_KEY = "sk-..."             # required
$env:GOOGLE_API_KEY = "..."                # optional (vision)
$env:CHECKPOINT_DB_PATH = "$PWD\data\checkpoints.sqlite"

# start the API
python -m uvicorn app.api.main:app --host 0.0.0.0 --port 8000

# in another terminal, run the smoke test against the live API
python lab4_api/smoke_test.py
```

The interactive Swagger UI is available at <http://localhost:8000/docs>.

---

## Submission checklist

- [x] `schema.py` - Pydantic models for `ChatRequest` and `ChatResponse`
- [x] `main.py` - FastAPI app hosting `POST /chat` and `POST /stream`
- [x] `api_test_results.txt` - output of a successful curl-equivalent run
