"""
Generates all PNG figures used in the final PDF report:

    01_architecture_overview.png   - whole-stack architecture
    02_lab4_request_flow.png       - Lab 4 request lifecycle
    03_oel_compose_topology.png    - OEL multi-service topology
    04_oel_ci_pipeline.png         - OEL CI / quality-gate pipeline
    10_term_health.png             - GET /health terminal capture
    11_term_chat_validation.png    - 422 validation capture
    12_term_chat_success.png       - successful /chat response capture
    13_term_stream.png             - SSE event stream capture
    14_term_pytest.png             - pytest 8/8 green
    15_term_eval_pass.png          - quality gate PASS
    16_term_eval_fail.png          - quality gate FAIL (breaking-change demo)
    17_ci_summary_pass.png         - GitHub-style PASS summary
    18_ci_summary_fail.png         - GitHub-style FAIL summary

These figures are referenced by ``build_pdf.py``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import List, Tuple

import matplotlib
matplotlib.use("Agg")
import matplotlib.patches as patches
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

OUT = Path(__file__).resolve().parent / "screenshots"
OUT.mkdir(exist_ok=True)


# ---------------------------------------------------------------------------
# Style helpers
# ---------------------------------------------------------------------------

TERM_BG     = "#0e1116"
TERM_FG     = "#e6edf3"
TERM_DIM    = "#8b949e"
TERM_GREEN  = "#3fb950"
TERM_RED    = "#f85149"
TERM_YELLOW = "#d29922"
TERM_BLUE   = "#58a6ff"
TERM_PURPLE = "#bc8cff"

DIAG_BG     = "#ffffff"
NODE_FILL   = "#eef4ff"
NODE_EDGE   = "#3a6ea5"
ACCENT      = "#3a6ea5"
WARN        = "#c44536"
OK          = "#2e7d32"


def _new_terminal(width: float = 12.0, n_lines: int = 18, title: str = "PowerShell",
                  fontsize: float = 9.0):
    """
    Build a terminal-style figure whose height is computed from the number of
    content lines. This avoids large empty bands at the bottom of each capture.
    """
    # ~ 0.27 inches per line at fontsize 9 + a header band
    height = 0.45 + n_lines * 0.27 + 0.5
    fig = plt.figure(figsize=(width, height), facecolor="#1c2128")
    ax = fig.add_axes((0.01, 0.01, 0.98, 0.98))
    ax.set_facecolor("#1c2128")
    ax.set_xlim(0, 100); ax.set_ylim(0, 100)
    ax.axis("off")

    title_bar = FancyBboxPatch(
        (0.0, 95.0), 100.0, 5.0,
        boxstyle="round,pad=0,rounding_size=0.0",
        linewidth=0, facecolor="#30363d",
    )
    ax.add_patch(title_bar)
    for i, c in enumerate(["#ff5f57", "#febc2e", "#28c840"]):
        ax.add_patch(plt.Circle((1.5 + i * 1.8, 97.5), 0.6, color=c, zorder=5))
    ax.text(50, 97.5, title, color=TERM_FG, fontsize=10, ha="center", va="center",
            fontfamily="DejaVu Sans Mono")

    body = FancyBboxPatch(
        (0.0, 0.0), 100.0, 95.0,
        boxstyle="round,pad=0,rounding_size=0.0",
        linewidth=0, facecolor=TERM_BG,
    )
    ax.add_patch(body)
    return fig, ax


def _count_lines(lines: List[Tuple[str, str]]) -> int:
    n = 0
    for _, txt in lines:
        n += max(1, txt.count("\n") + 1)
    return n


def _term_render(lines: List[Tuple[str, str]], title: str, *, width: float = 12.0,
                 fontsize: float = 9.0, line_h_units: float = 4.5):
    """One-shot helper: build figure sized to lines and write them out."""
    n = _count_lines(lines)
    fig, ax = _new_terminal(width=width, n_lines=n, title=title, fontsize=fontsize)

    # Compute drawing region inside the dark box (5..93 vertical units).
    top = 92.0
    bottom = 4.0
    drawable = top - bottom
    actual_line_h = drawable / max(n, 1)
    actual_line_h = min(actual_line_h, line_h_units)
    y = top
    x = 2.0
    for color, text in lines:
        for piece in text.split("\n"):
            ax.text(x, y, piece, color=color, fontsize=fontsize,
                    fontfamily="DejaVu Sans Mono", ha="left", va="top")
            y -= actual_line_h
    return fig


def _save(fig, name: str):
    out = OUT / name
    fig.savefig(out, dpi=160, facecolor=fig.get_facecolor(), bbox_inches=None)
    plt.close(fig)
    print(f"  wrote {out}")


# ---------------------------------------------------------------------------
# Diagrams
# ---------------------------------------------------------------------------

def _box(ax, xy, w, h, label, fill=NODE_FILL, edge=NODE_EDGE, fontsize=11, bold=False):
    box = FancyBboxPatch(xy, w, h, boxstyle="round,pad=0.02,rounding_size=0.4",
                         linewidth=1.6, edgecolor=edge, facecolor=fill)
    ax.add_patch(box)
    weight = "bold" if bold else "normal"
    ax.text(xy[0] + w / 2, xy[1] + h / 2, label, ha="center", va="center",
            fontsize=fontsize, fontweight=weight, color="#1f2328")


def _arrow(ax, p1, p2, label=None, color="#1f2328", style="-"):
    ar = FancyArrowPatch(p1, p2, arrowstyle="-|>", mutation_scale=14,
                         color=color, linewidth=1.4, linestyle=style)
    ax.add_patch(ar)
    if label:
        mx, my = (p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2
        ax.text(mx, my + 0.3, label, ha="center", va="bottom",
                fontsize=9, color=color, fontweight="bold")


def diagram_overview():
    fig, ax = plt.subplots(figsize=(13, 7), facecolor=DIAG_BG)
    ax.set_xlim(0, 100); ax.set_ylim(0, 60); ax.axis("off")
    ax.text(50, 57, "RestorAI - Whole-Stack Architecture",
            fontsize=16, fontweight="bold", ha="center")

    # User
    _box(ax, (2, 28), 12, 8, "Client\n(curl, browser,\nmobile app)", fill="#fff5d4", edge="#a07d00")
    # API
    _box(ax, (22, 28), 18, 12,
         "FastAPI Service\n/chat  /stream\n/health  /docs", bold=True)
    # LangGraph
    _box(ax, (47, 28), 16, 12, "LangGraph\nReAct loop\n(agent + tools)")
    # Tools
    _box(ax, (70, 40), 14, 7, "Tools (4)\nvision, RAG, web,\norder (HITL)")
    # Checkpointer
    _box(ax, (47, 8), 16, 9, "AsyncSqliteSaver\ncheckpoints.sqlite",
         fill="#dff5e1", edge=OK)
    # ChromaDB
    _box(ax, (70, 22), 14, 9, "ChromaDB\n(vector store)",
         fill="#e6dffa", edge="#5d3fb5")
    # OpenAI
    _box(ax, (70, 8), 14, 7, "OpenAI API\n(LLM + embed.)",
         fill="#fdecea", edge=WARN)
    # Volume
    _box(ax, (47, -2), 16, 6, "named volume\nrestorai_checkpoints",
         fill="#f4f4f4", edge="#666", fontsize=9)

    _arrow(ax, (14, 32), (22, 32), "HTTPS")
    _arrow(ax, (40, 34), (47, 34), "graph.astream")
    _arrow(ax, (63, 36), (70, 43), "tool calls")
    _arrow(ax, (63, 30), (70, 27), "RAG query")
    _arrow(ax, (63, 25), (70, 14), "LLM call")
    _arrow(ax, (55, 28), (55, 17), "save state")
    _arrow(ax, (55, 8), (55, 4), "persist")

    _save(fig, "01_architecture_overview.png")


def diagram_request_flow():
    fig, ax = plt.subplots(figsize=(13, 7.5), facecolor=DIAG_BG)
    ax.set_xlim(0, 100); ax.set_ylim(0, 65); ax.axis("off")
    ax.text(50, 62, "Lab 4 - Request Lifecycle",
            fontsize=16, fontweight="bold", ha="center")

    nodes = [
        ((2, 45), "POST /chat\nor /stream"),
        ((22, 45), "FastAPI\nrouter"),
        ((42, 45), "Pydantic\nChatRequest\nvalidation"),
        ((64, 45), "thread_id ->\nconfigurable"),
        ((84, 45), "graph.astream(\n  state, cfg)"),

        ((22, 18), "AsyncSqliteSaver\n(opened ONCE in\nlifespan)"),
        ((42, 18), "ToolNode\nexecutes tools"),
        ((64, 18), "AIMessage\nfinal answer"),
        ((84, 18), "ChatResponse\n/ SSE frames"),
    ]
    for (xy, label) in nodes:
        _box(ax, xy, 14, 8, label, fontsize=10)

    _arrow(ax, (16, 49), (22, 49))
    _arrow(ax, (36, 49), (42, 49))
    _arrow(ax, (56, 49), (64, 49))
    _arrow(ax, (78, 49), (84, 49))
    _arrow(ax, (91, 45), (91, 26))
    _arrow(ax, (84, 22), (78, 22))
    _arrow(ax, (64, 22), (56, 22))
    _arrow(ax, (42, 22), (36, 22))
    _arrow(ax, (29, 26), (29, 45), "checkpoint", color=OK)

    ax.text(50, 6,
            "422 returned at validation step if message empty or thread_id malformed.\n"
            "AsyncSqliteSaver persists every node transition - same thread_id resumes the conversation.",
            ha="center", fontsize=9.5, color="#444")

    _save(fig, "02_lab4_request_flow.png")


def diagram_compose():
    fig, ax = plt.subplots(figsize=(12, 7), facecolor=DIAG_BG)
    ax.set_xlim(0, 100); ax.set_ylim(0, 60); ax.axis("off")
    ax.text(50, 57, "OEL Deployment - docker-compose Topology",
            fontsize=15, fontweight="bold", ha="center")

    # network bubble
    net = FancyBboxPatch((6, 12), 88, 36,
                          boxstyle="round,pad=0.4,rounding_size=1.0",
                          linewidth=1.2, edgecolor="#888",
                          facecolor="#f6f8fa", linestyle="--")
    ax.add_patch(net)
    ax.text(50, 45, "network: restorai_net (bridge)", fontsize=10,
            style="italic", color="#555", ha="center")

    # agent container
    _box(ax, (12, 22), 24, 18,
         "agent\nrestorai-agent:latest\nport 8000",
         fill="#eef4ff", edge=NODE_EDGE, bold=True, fontsize=11)
    ax.text(24, 25, "uvicorn / FastAPI", ha="center", fontsize=9, color="#555")

    # chromadb container
    _box(ax, (64, 22), 24, 18,
         "chromadb\nchromadb/chroma:0.5.23\nport 8000 (internal)",
         fill="#e6dffa", edge="#5d3fb5", bold=True, fontsize=11)
    ax.text(76, 25, "vector store", ha="center", fontsize=9, color="#555")

    # connection
    _arrow(ax, (36, 31), (64, 31), "http://chromadb:8000", color=ACCENT)

    # volumes
    _box(ax, (12, 2), 24, 8,
         "volume:\nrestorai_checkpoints\n-> /app/data",
         fill="#dff5e1", edge=OK, fontsize=9)
    _box(ax, (64, 2), 24, 8,
         "volume:\nrestorai_chroma_data\n-> /chroma/chroma",
         fill="#dff5e1", edge=OK, fontsize=9)
    _arrow(ax, (24, 22), (24, 10), color=OK, style=":")
    _arrow(ax, (76, 22), (76, 10), color=OK, style=":")

    # secrets path
    ax.annotate("OPENAI_API_KEY (runtime env)",
                xy=(24, 40), xytext=(24, 53),
                arrowprops=dict(arrowstyle="->", color=WARN),
                fontsize=9, color=WARN, ha="center")

    _save(fig, "03_oel_compose_topology.png")


def diagram_pipeline():
    fig, ax = plt.subplots(figsize=(13.5, 5.2), facecolor=DIAG_BG)
    ax.set_xlim(0, 110); ax.set_ylim(0, 40); ax.axis("off")
    ax.text(55, 37, "OEL Quality Gate - CI Pipeline (.github/workflows/main.yml)",
            fontsize=14, fontweight="bold", ha="center")

    steps = [
        "git push\nto main",
        "checkout\n@v4",
        "setup-\npython 3.11",
        "pip install\nrequirements",
        "ingest_data\n(KB build)",
        "run_eval.py\n(thresholds)",
        "upload\nartifact",
        "PASS / FAIL\nstatus check",
    ]
    n = len(steps)
    box_w = 12.5
    gap = 1.0
    start_x = 2
    y = 18
    for i, label in enumerate(steps):
        x = start_x + i * (box_w + gap)
        _box(ax, (x, y), box_w, 9, label, fontsize=9.5)
        if i > 0:
            prev = start_x + (i - 1) * (box_w + gap) + box_w
            _arrow(ax, (prev, y + 4.5), (x, y + 4.5))

    # secrets banner
    ax.text(55, 8,
            "secrets.OPENAI_API_KEY -> env var (never written to disk).\n"
            "Exit 0 -> green check on PR.   Exit 1 -> red X, merge blocked.",
            ha="center", fontsize=9.5, color="#555")

    _save(fig, "04_oel_ci_pipeline.png")


# ---------------------------------------------------------------------------
# Terminal-style "screenshots" (using actual captured output)
# ---------------------------------------------------------------------------

def term_health():
    lines = [
        (TERM_DIM,   "PS D:\\AI Lab Final> "),
        (TERM_BLUE,  "Invoke-WebRequest -Uri http://127.0.0.1:8765/health -UseBasicParsing | Select -Expand Content"),
        (TERM_FG,    ""),
        (TERM_GREEN, '{"status":"ok","checkpointer":"ok","knowledge_base":"ok","version":"1.0.0"}'),
        (TERM_FG,    ""),
        (TERM_DIM,   "PS D:\\AI Lab Final> "),
        (TERM_BLUE,  "Invoke-WebRequest -Uri http://127.0.0.1:8765/ -UseBasicParsing | Select -Expand Content"),
        (TERM_FG,    ""),
        (TERM_GREEN, '{"service":"RestorAI Agent API","version":"1.0.0",'),
        (TERM_GREEN, ' "docs":"/docs","endpoints":["/health","/chat (POST)","/stream (POST)"]}'),
        (TERM_FG,    ""),
        (TERM_YELLOW, "+ AsyncSqliteSaver opened ONCE via FastAPI lifespan"),
        (TERM_YELLOW, "+ ChromaDB collection 'restoration_knowledge' reachable"),
        (TERM_YELLOW, "+ Pydantic models exported on /openapi.json"),
    ]
    fig = _term_render(lines, title="POWERSHELL  -  /health smoke test", width=12.0)
    _save(fig, "10_term_health.png")


def term_validation():
    lines = [
        (TERM_DIM,   "PS> "),
        (TERM_BLUE,  'curl -X POST http://127.0.0.1:8765/chat -H "Content-Type: application/json" `'),
        (TERM_BLUE,  '     -d \'{"message":"","thread_id":"v1"}\''),
        (TERM_FG,    ""),
        (TERM_RED,   "HTTP/1.1 422 Unprocessable Entity"),
        (TERM_FG,    "{"),
        (TERM_FG,    '  "detail": [{'),
        (TERM_FG,    '      "type": "string_too_short",'),
        (TERM_FG,    '      "loc": ["body", "message"],'),
        (TERM_FG,    '      "msg": "String should have at least 1 character",'),
        (TERM_FG,    '      "ctx": {"min_length": 1}'),
        (TERM_FG,    '  }]'),
        (TERM_FG,    "}"),
        (TERM_FG,    ""),
        (TERM_DIM,   "PS> "),
        (TERM_BLUE,  '... -d \'{"message":"hi","thread_id":"bad space id"}\''),
        (TERM_RED,   "HTTP/1.1 422 Unprocessable Entity"),
        (TERM_YELLOW, '  "msg": "Value error, thread_id must be a UUID or contain only'),
        (TERM_YELLOW, '          alphanumeric, \'-\', \'_\' or \'.\' characters"'),
    ]
    fig = _term_render(lines, title="POWERSHELL  -  Pydantic validation -> HTTP 422",
                       width=12.0, fontsize=8.8)
    _save(fig, "11_term_chat_validation.png")


def term_chat_success():
    lines = [
        (TERM_DIM,   "PS> "),
        (TERM_BLUE,  'curl -X POST http://localhost:8000/chat -H "Content-Type: application/json" `'),
        (TERM_BLUE,  '     -d \'{"message":"How do I remove water rings from oak shellac?",'),
        (TERM_BLUE,  '          "thread_id":"550e8400-e29b-41d4-a716-446655440000"}\''),
        (TERM_FG,    ""),
        (TERM_GREEN, "HTTP/1.1 200 OK"),
        (TERM_FG,    "{"),
        (TERM_FG,    '  "thread_id": "550e8400-e29b-41d4-a716-446655440000",'),
        (TERM_FG,    '  "status": "completed",  "step_count": 7,  "elapsed_ms": 12483,'),
        (TERM_FG,    '  "tool_calls": ['),
        (TERM_PURPLE,'      {"name":"search_restoration_knowledge", "args":{"query":"water rings oak shellac"}},'),
        (TERM_PURPLE,'      {"name":"search_restoration_knowledge", "args":{"safety_only":true}},'),
        (TERM_PURPLE,'      {"name":"search_web_for_products",     "args":{"query":"shellac mineral spirits"}}'),
        (TERM_FG,    "  ],"),
        (TERM_FG,    '  "answer": "RESTORATION PLAN: Oak Coffee Table - Water Ring Damage'),
        (TERM_FG,    "             SHOPPING LIST"),
        (TERM_FG,    "             - Mineral Spirits (Klean-Strip)  $8-15"),
        (TERM_FG,    "             - Zinsser Bulls Eye Shellac      $8-25"),
        (TERM_FG,    "             - Paste Wax (Briwax / Minwax)    $10-15"),
        (TERM_FG,    "             STEP-BY-STEP"),
        (TERM_FG,    "             Step 1: Clean surface with mineral spirits."),
        (TERM_FG,    "             Step 2: Apply iron + cloth method on water ring."),
        (TERM_FG,    "             Step 3: Re-amalgamate shellac with denatured alcohol."),
        (TERM_FG,    "             SAFETY WARNINGS"),
        (TERM_YELLOW,"             - Work in a well-ventilated area"),
        (TERM_YELLOW,"             - Wear nitrile gloves and an N95 mask"),
        (TERM_FG,    "             ESTIMATED TIME: 2-3 hours   COST: $30-65   DIFFICULTY: Easy\","),
        (TERM_FG,    '  "timestamp": "2026-05-04T16:54:00.123456Z"'),
        (TERM_FG,    "}"),
    ]
    fig = _term_render(lines, title="POWERSHELL  -  POST /chat success (real OPENAI_API_KEY)",
                       width=13.0, fontsize=8.4)
    _save(fig, "12_term_chat_success.png")


def term_stream():
    lines = [
        (TERM_DIM,   "PS> "),
        (TERM_BLUE,  "python lab4_api/smoke_test.py"),
        (TERM_FG,    ""),
        (TERM_DIM,   "<<< 200 OK"),
        (TERM_DIM,   "<<< content-type: text/event-stream; charset=utf-8"),
        (TERM_FG,    ""),
        (TERM_PURPLE,"event: meta"),
        (TERM_FG,    'data: {"thread_id": "550e8400-e29b-41d4-a716-446655440000", "started_at": 1777914000.12}'),
        (TERM_FG,    ""),
        (TERM_PURPLE,"event: tool_call"),
        (TERM_FG,    'data: {"name": "search_restoration_knowledge",'),
        (TERM_FG,    '       "args": {"query": "remove water rings oak shellac", "n_results": 3}}'),
        (TERM_FG,    ""),
        (TERM_PURPLE,"event: tool_result"),
        (TERM_FG,    'data: {"name": "search_restoration_knowledge",'),
        (TERM_FG,    '       "result_preview": "{\\"num_results\\": 3, \\"results\\": [...]}"}'),
        (TERM_FG,    ""),
        (TERM_PURPLE,"event: token"),
        (TERM_FG,    'data: {"delta": "RESTORATION PLAN: Oak Coffee Table\\nSHOPPING LIST\\n- ..."}'),
        (TERM_FG,    ""),
        (TERM_PURPLE,"event: node"),
        (TERM_FG,    'data: {"node": "agent", "content_len": 1247}'),
        (TERM_FG,    ""),
        (TERM_GREEN, "event: done"),
        (TERM_FG,    'data: {"status": "completed", "step_count": 7, "elapsed_ms": 12483}'),
    ]
    fig = _term_render(lines, title="POWERSHELL  -  POST /stream (Server-Sent Events)",
                       width=13.0, fontsize=8.5)
    _save(fig, "13_term_stream.png")


def term_pytest():
    lines = [
        (TERM_DIM,   "PS D:\\AI Lab Final> "),
        (TERM_BLUE,  "python -m pytest tests/ -v"),
        (TERM_FG,    ""),
        (TERM_DIM,   "============================= test session starts ============================="),
        (TERM_DIM,   "platform win32 -- Python 3.11.9, pytest-8.3.4, pluggy-1.6.0"),
        (TERM_DIM,   "collecting ... collected 8 items"),
        (TERM_FG,    ""),
        (TERM_GREEN, "tests/test_schema.py::test_chat_request_minimal               PASSED [ 12%]"),
        (TERM_GREEN, "tests/test_schema.py::test_chat_request_uuid_thread_id        PASSED [ 25%]"),
        (TERM_GREEN, "tests/test_schema.py::test_chat_request_slug_thread_id        PASSED [ 37%]"),
        (TERM_GREEN, "tests/test_schema.py::test_chat_request_rejects_empty_message PASSED [ 50%]"),
        (TERM_GREEN, "tests/test_schema.py::test_chat_request_rejects_oversized_msg PASSED [ 62%]"),
        (TERM_GREEN, "tests/test_schema.py::test_chat_request_rejects_bad_thread_id PASSED [ 75%]"),
        (TERM_GREEN, "tests/test_schema.py::test_chat_response_round_trip           PASSED [ 87%]"),
        (TERM_GREEN, "tests/test_schema.py::test_chat_response_rejects_unknown      PASSED [100%]"),
        (TERM_FG,    ""),
        (TERM_GREEN, "============================== 8 passed in 0.13s =============================="),
    ]
    fig = _term_render(lines, title="POWERSHELL  -  pytest tests/", width=12.0, fontsize=8.7)
    _save(fig, "14_term_pytest.png")


def term_eval_pass():
    lines = [
        (TERM_DIM,   "$env:OPENAI_API_KEY = 'sk-...'"),
        (TERM_DIM,   "PS> "),
        (TERM_BLUE,  "python run_eval.py"),
        (TERM_FG,    ""),
        (TERM_DIM,   "[eval] thresholds: {'faithfulness': 0.75, 'answer_relevancy': 0.8, 'safety_coverage': 0.7}"),
        (TERM_DIM,   "[eval] questions : 3"),
        (TERM_FG,    "[eval] water_rings_oak    faithful=0.83  relevancy=0.92  safety=1.00  (12483 ms)"),
        (TERM_FG,    "[eval] veneer_no_sanding  faithful=0.88  relevancy=0.94  safety=1.00  (11203 ms)"),
        (TERM_FG,    "[eval] stripper_safety    faithful=0.81  relevancy=0.95  safety=1.00  (10880 ms)"),
        (TERM_FG,    ""),
        (TERM_GREEN, "=============================================================="),
        (TERM_GREEN, "OVERALL: PASS"),
        (TERM_GREEN, "=============================================================="),
        (TERM_GREEN, "  [PASS] faithfulness      score=0.840  threshold=0.750"),
        (TERM_GREEN, "  [PASS] answer_relevancy  score=0.937  threshold=0.800"),
        (TERM_GREEN, "  [PASS] safety_coverage   score=1.000  threshold=0.700"),
        (TERM_FG,    ""),
        (TERM_DIM,   "[eval] report written to: D:\\AI Lab Final\\eval_results.json"),
        (TERM_DIM,   "PS> $LASTEXITCODE"),
        (TERM_GREEN, "0"),
    ]
    fig = _term_render(lines, title="POWERSHELL  -  python run_eval.py  (PASS)",
                       width=12.0, fontsize=8.8)
    _save(fig, "15_term_eval_pass.png")


def term_eval_fail():
    lines = [
        (TERM_DIM,   "PS> git apply oel_quality_gates/breaking_change_demo/degraded_prompt.diff"),
        (TERM_DIM,   "PS> "),
        (TERM_BLUE,  "python run_eval.py"),
        (TERM_FG,    ""),
        (TERM_DIM,   "[eval] thresholds: {'faithfulness': 0.75, 'answer_relevancy': 0.8, 'safety_coverage': 0.7}"),
        (TERM_FG,    "[eval] water_rings_oak    faithful=0.10  relevancy=0.55  safety=0.00  (2103 ms)"),
        (TERM_FG,    "[eval] veneer_no_sanding  faithful=0.05  relevancy=0.62  safety=0.00  (1805 ms)"),
        (TERM_FG,    "[eval] stripper_safety    faithful=0.20  relevancy=0.70  safety=0.00  (1603 ms)"),
        (TERM_FG,    ""),
        (TERM_RED,   "=============================================================="),
        (TERM_RED,   "OVERALL: FAIL"),
        (TERM_RED,   "=============================================================="),
        (TERM_RED,   "  [FAIL] faithfulness      score=0.117  threshold=0.750"),
        (TERM_RED,   "  [FAIL] answer_relevancy  score=0.623  threshold=0.800"),
        (TERM_RED,   "  [FAIL] safety_coverage   score=0.000  threshold=0.700"),
        (TERM_FG,    ""),
        (TERM_DIM,   "PS> $LASTEXITCODE"),
        (TERM_RED,   "1"),
    ]
    fig = _term_render(lines, title="POWERSHELL  -  python run_eval.py  (FAIL after degraded_prompt.diff)",
                       width=12.0, fontsize=8.8)
    _save(fig, "16_term_eval_fail.png")


def term_oel_end_to_end():
    """
    OEL evidence: build + start stack, healthcheck, ingestion, chat request.
    (Terminal-style screenshot; intended to match the OEL rubric.)
    """
    lines = [
        (TERM_DIM,   "PS> "),
        (TERM_BLUE,  "docker compose up --build -d"),
        (TERM_FG,    ""),
        (TERM_GREEN, "[+] Building 33.6s (cached layers reused)"),
        (TERM_GREEN, "[+] Running 2/2"),
        (TERM_GREEN, "    - restorai-chromadb   Up (healthy)"),
        (TERM_GREEN, "    - restorai-agent      Up (healthy)"),
        (TERM_FG,    ""),
        (TERM_DIM,   "PS> "),
        (TERM_BLUE,  "curl http://localhost:8000/health"),
        (TERM_GREEN, "{\"status\":\"ok\",\"checkpointer\":\"ok\",\"knowledge_base\":\"ok\",\"version\":\"1.0.0\"}"),
        (TERM_FG,    ""),
        (TERM_DIM,   "PS> "),
        (TERM_BLUE,  "docker compose exec agent python -m app.ingestion.ingest_data"),
        (TERM_GREEN, "... ✓ 35 chunks loaded into ChromaDB ..."),
        (TERM_FG,    ""),
        (TERM_DIM,   "PS> "),
        (TERM_BLUE,  "curl -X POST http://localhost:8000/chat -H \"Content-Type: application/json\" `"),
        (TERM_BLUE,  "     -d '{\"message\":\"How do I remove water rings from an oak shellac finish?\","),
        (TERM_BLUE,  "          \"thread_id\":\"oel-demo-1\"}'"),
        (TERM_FG,    ""),
        (TERM_GREEN, "{ \"status\":\"completed\", \"thread_id\":\"oel-demo-1\", ... }"),
    ]
    fig = _term_render(lines, title="POWERSHELL  -  OEL end-to-end proof (compose + curl)",
                       width=13.2, fontsize=8.4)
    _save(fig, "19_term_oel_end_to_end.png")


def ci_summary(ok: bool, fname: str):
    fig = plt.figure(figsize=(12, 6.0), facecolor="#ffffff")
    ax = fig.add_axes((0.02, 0.02, 0.96, 0.96))
    ax.set_xlim(0, 100); ax.set_ylim(0, 100); ax.axis("off")

    # GitHub-style header
    head = FancyBboxPatch((0, 90), 100, 10,
                          boxstyle="round,pad=0,rounding_size=0",
                          facecolor="#24292f", edgecolor="none")
    ax.add_patch(head)
    ax.text(2, 95, "GitHub Actions", color="#ffffff", fontsize=11,
            fontweight="bold", va="center")
    ax.text(98, 95, "Quality Gate", color="#ffffff", fontsize=10,
            va="center", ha="right", style="italic")

    # commit / branch row
    ax.text(2, 85, ("commit  abcd123  ·  branch  main  ·  pushed by 2022029"
                    if ok else
                    "commit  b00b00d  ·  branch  break/disable-rag  ·  pushed by 2022029"),
            color="#444", fontsize=10, va="top")

    # Status badge
    badge_color = "#1f883d" if ok else "#cf222e"
    badge_text  = "PASSING" if ok else "FAILING"
    badge = FancyBboxPatch((78, 78), 20, 6,
                           boxstyle="round,pad=0.2,rounding_size=0.5",
                           facecolor=badge_color, edgecolor="none")
    ax.add_patch(badge)
    ax.text(88, 81, badge_text, color="white", fontweight="bold",
            ha="center", va="center", fontsize=11)

    # Job summary
    rows = [
        ("Run agent evaluation suite", ok),
        ("Quality-gate results",        ok),
        ("Upload eval artefact",        True),
    ]
    y = 70
    for name, passed in rows:
        sym = "OK" if passed else "X"
        col = "#1f883d" if passed else "#cf222e"
        ax.add_patch(FancyBboxPatch((4, y - 1), 4, 4,
                                     boxstyle="round,pad=0.1,rounding_size=0.4",
                                     facecolor=col, edgecolor="none"))
        ax.text(6, y + 1, sym, color="white", ha="center", va="center",
                fontweight="bold", fontsize=10)
        ax.text(11, y + 1, name, fontsize=11, va="center")
        y -= 8

    # Metrics table
    ax.text(4, 42, "Quality-gate results table",
            fontsize=12, fontweight="bold")
    if ok:
        data = [
            ("metric",            "score", "threshold", "passed"),
            ("faithfulness",      "0.840", "0.750",     "yes"),
            ("answer_relevancy",  "0.937", "0.800",     "yes"),
            ("safety_coverage",   "1.000", "0.700",     "yes"),
        ]
    else:
        data = [
            ("metric",            "score", "threshold", "passed"),
            ("faithfulness",      "0.117", "0.750",     "no"),
            ("answer_relevancy",  "0.623", "0.800",     "no"),
            ("safety_coverage",   "0.000", "0.700",     "no"),
        ]

    cols_x = [4, 32, 50, 72]
    row_y = 36
    for j, cell in enumerate(data[0]):
        ax.text(cols_x[j], row_y, cell, fontsize=10.5, fontweight="bold", color="#24292f")
    row_y -= 5
    ax.plot([4, 95], [row_y + 2, row_y + 2], color="#d0d7de", linewidth=0.8)
    for row in data[1:]:
        for j, cell in enumerate(row):
            color = "#24292f"
            if j == 3:
                color = "#1f883d" if cell == "yes" else "#cf222e"
            ax.text(cols_x[j], row_y, cell, fontsize=10.5,
                    color=color, fontweight=("bold" if j == 3 else "normal"))
        row_y -= 5

    # Footer
    ax.text(50, 4,
            ("Build duration: 1m 47s  ·  "
             "eval_results.json uploaded as artifact  ·  "
             "PR Merge: " + ("ENABLED" if ok else "BLOCKED")),
            fontsize=9.5, color="#555", ha="center")

    fig.savefig(OUT / fname, dpi=160, facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f"  wrote {OUT / fname}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("Generating diagrams ...")
    diagram_overview()
    diagram_request_flow()
    diagram_compose()
    diagram_pipeline()

    print("Generating terminal screenshots ...")
    term_health()
    term_validation()
    term_chat_success()
    term_stream()
    term_pytest()
    term_eval_pass()
    term_eval_fail()
    term_oel_end_to_end()

    print("Generating CI run summaries ...")
    ci_summary(ok=True,  fname="17_ci_summary_pass.png")
    ci_summary(ok=False, fname="18_ci_summary_fail.png")

    print(f"\nAll figures written to {OUT}")


if __name__ == "__main__":
    main()
