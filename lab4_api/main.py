"""
Lab 4 Submission - main.py

Entry-point for the rubric. Re-exports the FastAPI ``app`` from
``app.api.main`` and provides a ``__main__`` block for the typical
``python lab4_api/main.py`` workflow used during the demo.

For production / docker the canonical command remains:
    uvicorn app.api.main:app --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

from app.api.main import app  # noqa: F401  (re-export the FastAPI instance)

__all__ = ["app"]


def _run_dev_server() -> None:
    import os
    import uvicorn

    host = os.getenv("API_HOST", "127.0.0.1")
    port = int(os.getenv("API_PORT", "8000"))

    uvicorn.run("app.api.main:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    _run_dev_server()
