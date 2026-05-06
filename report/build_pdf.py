"""
Build the final PDF report:
    AI407L_Final_Report_2022029_Abdullah_Noor.pdf

Sections:
    Cover                           - student details, course, date, signature line
    Table of Contents
    1. Executive Summary
    2. Lab 4 - The API Layer
        2.1 Architecture
        2.2 Task 1 - Endpoint design & schema validation
        2.3 Task 2 - Persistence over HTTP
        2.4 Task 3 - Streaming responses (SSE)
        2.5 Verification
    3. OEL - Industrial Packaging & Deployment
        3.1 Multi-stage Dockerfile
        3.2 docker-compose topology
        3.3 Secret-free image
        3.4 End-to-end evidence
    4. OEL - Automated Quality Gates
        4.1 CI-ready evaluation script
        4.2 Pipeline configuration
        4.3 Versioned thresholds
        4.4 Breaking-change demonstration
    5. Project Reorganisation
    6. How To Run
    Appendix A - File listing

Run:
    python report/build_pdf.py
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import List

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    Image,
    KeepTogether,
    PageBreak,
    PageTemplate,
    Paragraph,
    Preformatted,
    Spacer,
    Table,
    TableStyle,
)


REPO        = Path(__file__).resolve().parent.parent
SHOTS       = Path(__file__).resolve().parent / "screenshots"
OUT_PDF     = REPO / "AI407L_Final_Report_2022029_Abdullah_Noor.pdf"

PAGE_W, PAGE_H = A4
MARGIN_LR = 1.8 * cm
MARGIN_TB = 2.0 * cm

ACCENT       = colors.HexColor("#3a6ea5")
ACCENT_DARK  = colors.HexColor("#1f3f63")
SUBTLE       = colors.HexColor("#5a6675")
RULE         = colors.HexColor("#cdd5e0")
CODE_BG      = colors.HexColor("#f4f6fa")
CODE_BORDER  = colors.HexColor("#cdd5e0")
PASS_GREEN   = colors.HexColor("#1f883d")
FAIL_RED     = colors.HexColor("#cf222e")


# ---------------------------------------------------------------------------
# Stylesheet
# ---------------------------------------------------------------------------

base = getSampleStyleSheet()

S = {
    "title": ParagraphStyle(
        "title", parent=base["Title"],
        fontName="Helvetica-Bold", fontSize=24, leading=28,
        textColor=ACCENT_DARK, alignment=TA_CENTER, spaceAfter=8,
    ),
    "subtitle": ParagraphStyle(
        "subtitle", parent=base["Normal"],
        fontName="Helvetica", fontSize=13, leading=16,
        textColor=SUBTLE, alignment=TA_CENTER, spaceAfter=18,
    ),
    "h1": ParagraphStyle(
        "h1", parent=base["Heading1"],
        fontName="Helvetica-Bold", fontSize=18, leading=22,
        textColor=ACCENT_DARK, spaceBefore=14, spaceAfter=8,
    ),
    "h2": ParagraphStyle(
        "h2", parent=base["Heading2"],
        fontName="Helvetica-Bold", fontSize=13.5, leading=17,
        textColor=ACCENT, spaceBefore=12, spaceAfter=4,
    ),
    "h3": ParagraphStyle(
        "h3", parent=base["Heading3"],
        fontName="Helvetica-Bold", fontSize=11.5, leading=14,
        textColor=ACCENT_DARK, spaceBefore=8, spaceAfter=2,
    ),
    "body": ParagraphStyle(
        "body", parent=base["BodyText"],
        fontName="Helvetica", fontSize=10.5, leading=14,
        alignment=TA_JUSTIFY, spaceAfter=6,
    ),
    "tight": ParagraphStyle(
        "tight", parent=base["BodyText"],
        fontName="Helvetica", fontSize=10.0, leading=12.5,
        alignment=TA_LEFT, spaceAfter=4,
    ),
    "code": ParagraphStyle(
        "code", parent=base["Code"],
        fontName="Courier", fontSize=8.6, leading=10.8,
        backColor=CODE_BG, borderColor=CODE_BORDER, borderWidth=0.5,
        borderPadding=4, leftIndent=2, rightIndent=2, spaceAfter=8,
    ),
    "caption": ParagraphStyle(
        "caption", parent=base["Italic"],
        fontName="Helvetica-Oblique", fontSize=9, leading=11,
        textColor=SUBTLE, alignment=TA_CENTER, spaceBefore=2, spaceAfter=10,
    ),
    "footer": ParagraphStyle(
        "footer", parent=base["Normal"],
        fontName="Helvetica", fontSize=8.5, leading=10,
        textColor=SUBTLE, alignment=TA_CENTER,
    ),
}


# ---------------------------------------------------------------------------
# Page template (running header / footer)
# ---------------------------------------------------------------------------

def _page_decoration(canvas, doc):
    canvas.saveState()

    # Header line + title (skip the first / cover page)
    if doc.page > 1:
        canvas.setStrokeColor(RULE)
        canvas.setLineWidth(0.4)
        canvas.line(MARGIN_LR, PAGE_H - MARGIN_TB + 14,
                    PAGE_W - MARGIN_LR, PAGE_H - MARGIN_TB + 14)
        canvas.setFont("Helvetica", 8.5)
        canvas.setFillColor(SUBTLE)
        canvas.drawString(MARGIN_LR, PAGE_H - MARGIN_TB + 18,
                           "AI407L - Final Report")
        canvas.drawRightString(PAGE_W - MARGIN_LR, PAGE_H - MARGIN_TB + 18,
                                "Abdullah Noor / 2022029")

    # Footer
    canvas.setStrokeColor(RULE)
    canvas.setLineWidth(0.4)
    canvas.line(MARGIN_LR, MARGIN_TB - 16,
                PAGE_W - MARGIN_LR, MARGIN_TB - 16)
    canvas.setFont("Helvetica", 8.5)
    canvas.setFillColor(SUBTLE)
    canvas.drawString(MARGIN_LR, MARGIN_TB - 28,
                      "RestorAI - Furniture Restoration Multi-Agent System")
    canvas.drawRightString(PAGE_W - MARGIN_LR, MARGIN_TB - 28,
                            f"Page {doc.page}")
    canvas.restoreState()


# ---------------------------------------------------------------------------
# Convenience wrappers
# ---------------------------------------------------------------------------

def P(text: str, style: str = "body") -> Paragraph:
    return Paragraph(text, S[style])


def code_block(text: str) -> Preformatted:
    # Strip leading/trailing blank lines, keep indentation.
    return Preformatted(text.strip("\n"), S["code"])


def screenshot(filename: str, caption: str, *,
               width: float = 16.5, max_height: float = 12.5) -> List:
    """
    Insert a centred screenshot capped to (width, max_height) cm. Image
    dimensions are computed from the source PNG so we always preserve the
    aspect ratio - no squishing, no upscaling beyond the source resolution.
    """
    from PIL import Image as PILImage
    src = SHOTS / filename
    with PILImage.open(src) as im:
        nat_w, nat_h = im.size

    aspect = nat_w / nat_h
    target_w = width * cm
    target_h = target_w / aspect
    if target_h > max_height * cm:
        target_h = max_height * cm
        target_w = target_h * aspect

    img = Image(str(src), width=target_w, height=target_h)
    img.hAlign = "CENTER"
    return [Spacer(0, 4), img, P(caption, "caption")]


_CELL_BODY = ParagraphStyle(
    "_cell_body", parent=base["BodyText"],
    fontName="Helvetica", fontSize=9.7, leading=12,
    alignment=TA_LEFT, spaceAfter=0, spaceBefore=0,
)
_CELL_HEAD = ParagraphStyle(
    "_cell_head", parent=base["BodyText"],
    fontName="Helvetica-Bold", fontSize=10, leading=12,
    textColor=colors.white, alignment=TA_LEFT, spaceAfter=0, spaceBefore=0,
)


def _wrap_cell(value, header: bool = False):
    """Wrap a string cell in a Paragraph so long text reflows inside its column."""
    if isinstance(value, str):
        return Paragraph(value, _CELL_HEAD if header else _CELL_BODY)
    return value


def info_table(rows: List[List[str]], col_widths=None) -> Table:
    wrapped = []
    for r, row in enumerate(rows):
        wrapped.append([_wrap_cell(v, header=(r == 0)) for v in row])

    t = Table(wrapped, colWidths=col_widths, hAlign="LEFT")
    t.setStyle(TableStyle([
        ("BACKGROUND",  (0, 0), (-1, 0),  ACCENT),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f6f8fc")]),
        ("BOX",         (0, 0), (-1, -1), 0.5, RULE),
        ("INNERGRID",   (0, 0), (-1, -1), 0.25, RULE),
        ("VALIGN",      (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING",(0, 0), (-1, -1), 5),
        ("TOPPADDING",  (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 4),
    ]))
    return t


_CELL_PASS = ParagraphStyle(
    "_cell_pass", parent=_CELL_BODY,
    fontName="Helvetica-Bold", textColor=PASS_GREEN, alignment=TA_CENTER,
)
_CELL_FAIL = ParagraphStyle(
    "_cell_fail", parent=_CELL_BODY,
    fontName="Helvetica-Bold", textColor=FAIL_RED, alignment=TA_CENTER,
)


def ok_fail_table(rows: List[List[str]], col_widths=None) -> Table:
    """Table whose last column is colour-coded yes/no/OK/FAIL."""
    new_rows = []
    for r, row in enumerate(rows):
        if r == 0:
            new_rows.append(row)
            continue
        last = row[-1]
        cell_lc = last.lower()
        if cell_lc.startswith("y") or cell_lc.startswith("p") or "ok" in cell_lc:
            colored = Paragraph(last, _CELL_PASS)
        elif cell_lc.startswith("n") or cell_lc.startswith("f"):
            colored = Paragraph(last, _CELL_FAIL)
        else:
            colored = last
        new_rows.append(list(row[:-1]) + [colored])
    return info_table(new_rows, col_widths=col_widths)


# ---------------------------------------------------------------------------
# Cover
# ---------------------------------------------------------------------------

def cover() -> List:
    flow: List = [Spacer(0, 3.5 * cm)]
    flow.append(P("AI407L - AI Lab", "subtitle"))
    flow.append(P("Final Lab Report", "title"))
    flow.append(P(
        "Lab 4 - The API Layer (FastAPI &amp; LangServe)<br/>"
        "OEL - Industrial Packaging &amp; Automated Quality Gates",
        "subtitle"))
    flow.append(Spacer(0, 0.7 * cm))

    # Decorative bar
    bar = Table([[""]], colWidths=[16.5 * cm], rowHeights=[0.18 * cm])
    bar.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), ACCENT)]))
    bar.hAlign = "CENTER"
    flow.append(bar)
    flow.append(Spacer(0, 1.4 * cm))

    info = info_table([
        ["Field",          "Value"],
        ["Student Name",   "Abdullah Noor"],
        ["Roll Number",    "2022029"],
        ["Course",         "AI407L - AI Lab"],
        ["Project",        "RestorAI - Furniture Restoration Multi-Agent System"],
        ["Submission",     "Lab 4 + OEL (Deployment Packaging & Quality Gates)"],
        ["Date",           datetime.now().strftime("%d %B %Y")],
        ["Repository",     "AI Lab Final/  (local)  - see README.md at root"],
    ], col_widths=[5.2 * cm, 11.3 * cm])
    info.hAlign = "CENTER"
    flow.append(info)

    flow.append(Spacer(0, 1.5 * cm))
    flow.append(P(
        "<b>Project goal.</b> Transform the local LangGraph furniture-restoration "
        "agent (Lab 3 / Mid-exam) into a productionised web service: expose it "
        "behind a streaming REST API (Lab 4), package it as a reproducible "
        "container stack (OEL Task 1), and protect it with a CI quality gate "
        "that blocks deployment of degraded agents (OEL Task 2).",
        "body"))
    flow.append(Spacer(0, 0.4 * cm))
    flow.append(P(
        "<b>This report</b> walks through what was built, how each rubric outcome "
        "is satisfied, and includes screenshots of the running system.",
        "body"))

    flow.append(PageBreak())
    return flow


# ---------------------------------------------------------------------------
# TOC (manual - reportlab's built-in TOC needs two passes)
# ---------------------------------------------------------------------------

def toc() -> List:
    flow: List = [P("Table of Contents", "h1")]
    rows = [
        ["1.", "Executive Summary"],
        ["2.", "Lab 4 - The API Layer"],
        ["",   "    2.1 Architecture"],
        ["",   "    2.2 Task 1 - Endpoint design & schema validation"],
        ["",   "    2.3 Task 2 - Persistence over HTTP"],
        ["",   "    2.4 Task 3 - Streaming responses (SSE)"],
        ["",   "    2.5 Verification"],
        ["3.", "OEL - Industrial Packaging & Deployment"],
        ["",   "    3.1 Multi-stage Dockerfile"],
        ["",   "    3.2 docker-compose topology"],
        ["",   "    3.3 Secret-free image"],
        ["",   "    3.4 End-to-end evidence"],
        ["4.", "OEL - Automated Quality Gates"],
        ["",   "    4.1 CI-ready evaluation script"],
        ["",   "    4.2 Pipeline configuration"],
        ["",   "    4.3 Versioned thresholds"],
        ["",   "    4.4 Breaking-change demonstration"],
        ["5.", "Project Reorganisation"],
        ["6.", "How To Run"],
        ["A.", "Appendix - File listing"],
    ]
    t = Table(rows, colWidths=[1.5 * cm, 14 * cm])
    t.setStyle(TableStyle([
        ("FONT",        (0, 0), (-1, -1), "Helvetica", 11),
        ("FONT",        (0, 0), (0, -1),  "Helvetica-Bold", 11),
        ("TEXTCOLOR",   (0, 0), (0, -1),  ACCENT_DARK),
        ("VALIGN",      (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 3),
    ]))
    flow.append(t)
    flow.append(PageBreak())
    return flow


# ---------------------------------------------------------------------------
# Section 1 - Executive Summary
# ---------------------------------------------------------------------------

def sec_summary() -> List:
    f: List = []
    f.append(P("1. Executive Summary", "h1"))
    f.append(P(
        "RestorAI is a furniture-restoration AI agent that walks a user from a "
        "free-text or photographic description of their damaged piece to a "
        "complete restoration plan, shopping list and safety constraints. "
        "Earlier labs built the knowledge base (Lab 2), reasoning loop (Lab 3) "
        "and persistent state with human-in-the-loop gating (Lab 5 / Mid-exam). "
        "This submission packages those pieces for production.",
        "body"))

    f.append(P("Deliverables in this submission", "h2"))
    f.append(ok_fail_table([
        ["Submission",                                "Folder",                "Status"],
        ["Lab 4 - API Layer",                         "lab4_api/",             "OK"],
        ["OEL Task 1 - Industrial Packaging",         "oel_deployment/",       "OK"],
        ["OEL Task 2 - Automated Quality Gates",      "oel_quality_gates/",    "OK"],
        ["Project re-organisation (clean structure)", "app/, archive/, ...",   "OK"],
        ["Final report (this document)",              "report/",               "OK"],
    ]))

    f.append(P("Architecture in one picture", "h2"))
    f += screenshot("01_architecture_overview.png",
                    "Figure 1 - End-to-end RestorAI architecture. The FastAPI "
                    "service is the new piece for Lab 4; ChromaDB and "
                    "AsyncSqliteSaver are the two services that the OEL "
                    "compose stack runs alongside the agent.")

    f.append(P("Rubric coverage at a glance", "h2"))
    f.append(ok_fail_table([
        ["Rubric outcome",                                    "Where it is satisfied", "Status"],
        ["Lab 4 / Task 1 - schema.py with Pydantic",          "app/api/schema.py",     "OK"],
        ["Lab 4 / Task 2 - Persistence over HTTP",            "app/api/main.py::lifespan", "OK"],
        ["Lab 4 / Task 3 - Streaming via SSE",                "app/api/main.py::stream",   "OK"],
        ["OEL - Reproducible container image",                "Dockerfile (multi-stage)",  "OK"],
        ["OEL - Secret-free image",                           ".dockerignore + compose env", "OK"],
        ["OEL - Multi-service orchestration",                 "docker-compose.yml",        "OK"],
        ["OEL - End-to-end test evidence",                    "oel_deployment/REPORT.md",  "OK"],
        ["OEL - CI-ready evaluation script",                  "run_eval.py + app/eval/",   "OK"],
        ["OEL - Pipeline on every push",                      ".github/workflows/main.yml","OK"],
        ["OEL - Versioned thresholds (>= 2 metrics)",         "eval_thresholds.json (3)",  "OK"],
        ["OEL - Breaking-change demonstration",               "oel_quality_gates/breaking_change_demo/", "OK"],
    ]))

    f.append(PageBreak())
    return f


# ---------------------------------------------------------------------------
# Section 2 - Lab 4
# ---------------------------------------------------------------------------

def sec_lab4() -> List:
    f: List = []
    f.append(P("2. Lab 4 - The API Layer", "h1"))
    f.append(P(
        "Lab 4 wraps the LangGraph agent in a FastAPI service so any "
        "client (mobile app, web UI, curl, another microservice) can drive "
        "the agent over HTTP. Three rubric tasks are addressed: schema "
        "validation, stateful HTTP persistence, and streaming responses.",
        "body"))

    f.append(P("2.1 Architecture", "h2"))
    f += screenshot("02_lab4_request_flow.png",
                    "Figure 2 - Lifecycle of a single /chat request. The "
                    "AsyncSqliteSaver (green) is opened ONCE at startup via "
                    "FastAPI's lifespan and reused for every request.")

    f.append(P("2.2 Task 1 - Endpoint design and schema validation", "h2"))
    f.append(P(
        "<code>app/api/schema.py</code> defines five Pydantic models "
        "(<b>ChatRequest</b>, <b>ChatResponse</b>, <b>StreamRequest</b>, "
        "<b>HealthResponse</b>, <b>ToolCallTrace</b>) and a string-literal "
        "<b>AgentStatus</b> enum. FastAPI rejects malformed bodies with "
        "HTTP 422 <i>before</i> they reach the LangGraph runtime.",
        "body"))
    f.append(code_block(
        '''class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=8000,
                         description="User message / instruction to the agent.")
    thread_id: str = Field(default_factory=lambda: str(uuid4()),
                           description="UUID or short slug; reuse to continue.")

    @field_validator("thread_id")
    @classmethod
    def _validate_thread_id(cls, v: str) -> str:
        if not v.strip(): raise ValueError("thread_id cannot be empty")
        try: UUID(v); return v                       # accept UUIDs
        except (ValueError, AttributeError): pass    # also accept ASCII slugs
        if not all(ch.isalnum() or ch in "-_." for ch in v):
            raise ValueError("thread_id must be a UUID or contain only "
                             "alphanumeric, '-', '_' or '.' characters")
        return v


class ChatResponse(BaseModel):
    thread_id: str
    answer: str
    status: AgentStatus              # completed | in_progress | interrupted | error
    tool_calls: List[ToolCallTrace]
    step_count: int = Field(0, ge=0)
    elapsed_ms: int = Field(0, ge=0)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
'''))
    f += screenshot("11_term_chat_validation.png",
                    "Figure 3 - Validation in action: empty message and "
                    "malformed thread_id both rejected with HTTP 422.")

    f.append(P("2.3 Task 2 - Persistence over HTTP (Lab 5 bridge)", "h2"))
    f.append(P(
        "Stateless HTTP requests are bridged to the stateful LangGraph by "
        "mapping <code>req.thread_id</code> onto "
        "<code>config.configurable.thread_id</code>. The checkpointer is "
        "opened exactly ONCE in FastAPI's <code>lifespan</code> context so we "
        "never reconnect to the SQLite store on the hot path:",
        "body"))
    f.append(code_block(
        '''@asynccontextmanager
async def lifespan(app: FastAPI):
    db_path = _resolve_checkpoint_path()              # CHECKPOINT_DB_PATH env var
    async with AsyncSqliteSaver.from_conn_string(str(db_path)) as checkpointer:
        graph = build_simple_graph(checkpointer=checkpointer)
        app.state.checkpointer = checkpointer         # shared across requests
        app.state.graph        = graph
        yield                                          # serve requests here
        # connection closed cleanly on SIGTERM


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, request: Request) -> ChatResponse:
    config = {"configurable": {"thread_id": req.thread_id}}
    initial_state = {"messages": [HumanMessage(content=req.message)]}
    async for event in request.app.state.graph.astream(
            initial_state, config, stream_mode="values"):
        ...
'''))

    f.append(P("2.4 Task 3 - Streaming responses (Server-Sent Events)", "h2"))
    f.append(P(
        "<code>POST /stream</code> wraps "
        "<code>graph.astream(...)</code> in a "
        "<code>StreamingResponse</code> with "
        "<code>media_type=&quot;text/event-stream&quot;</code> and emits the "
        "frame types below. Browsers consume them directly with the "
        "<code>EventSource</code> API for ChatGPT-like UX.",
        "body"))
    f.append(info_table([
        ["Event",         "Payload",                                    "When"],
        ["meta",          "thread_id, started_at",                      "first frame"],
        ["tool_call",     "name, args",                                 "agent requested a tool"],
        ["tool_result",   "name, result_preview (<= 400 chars)",        "tool returned"],
        ["token",         "delta (incremental answer text)",             "answer chunks"],
        ["node",          "node, content_len",                          "graph node finished"],
        ["done",          "status, step_count, elapsed_ms",             "terminal frame"],
        ["error",         "message",                                    "exception during run"],
    ], col_widths=[2.6 * cm, 7.6 * cm, 6.3 * cm]))
    f += screenshot("13_term_stream.png",
                    "Figure 4 - Live SSE event stream returned by POST /stream "
                    "(captured with httpx.stream).")

    f.append(P("2.5 Verification", "h2"))
    f += screenshot("10_term_health.png",
                    "Figure 5 - GET / and GET /health on the running server. "
                    "Both checkpointer and knowledge_base report 'ok'.")
    f += screenshot("12_term_chat_success.png",
                    "Figure 6 - A successful POST /chat run with a real "
                    "OPENAI_API_KEY. The agent uses three tools and returns "
                    "a structured ChatResponse including the full restoration "
                    "plan, tool trace, step count and latency.")
    f += screenshot("14_term_pytest.png",
                    "Figure 7 - tests/test_schema.py runs in 0.13s and exercises "
                    "every Pydantic validation rule defined in schema.py.")

    f.append(PageBreak())
    return f


# ---------------------------------------------------------------------------
# Section 3 - OEL Industrial Packaging
# ---------------------------------------------------------------------------

def sec_oel_deploy() -> List:
    f: List = []
    f.append(P("3. OEL - Industrial Packaging &amp; Deployment", "h1"))
    f.append(P(
        "The agent had to leave the developer laptop. The OEL deployment "
        "task asks for a reproducible container, secret-free build, "
        "multi-service orchestration with persistent volumes, and end-to-end "
        "evidence that the system starts cleanly from configuration files "
        "alone.",
        "body"))

    f.append(P("3.1 Multi-stage Dockerfile", "h2"))
    f.append(P(
        "Three stages: <b>base</b> (system libs), <b>builder</b> (pip wheel "
        "compilation), <b>runtime</b> (final image). Layers are ordered "
        "least-changed -> most-changed so source-only edits keep the "
        "expensive pip layer cached. Final image: ~320 MB on disk.",
        "body"))
    f.append(code_block(
        '''# Stage 1 - base (rarely changes)
FROM python:3.11.9-slim-bookworm AS base
RUN apt-get update && apt-get install -y --no-install-recommends \\
        ca-certificates curl libsqlite3-0 \\
 && rm -rf /var/lib/apt/lists/*

# Stage 2 - builder (only when requirements.txt changes)
FROM base AS builder
RUN apt-get update && apt-get install -y --no-install-recommends \\
        build-essential gcc \\
 && rm -rf /var/lib/apt/lists/*
COPY requirements.txt /app/requirements.txt           # cached layer
RUN python -m venv /opt/venv \\
 && /opt/venv/bin/pip install -r /app/requirements.txt

# Stage 3 - runtime (changes on every commit)
FROM base AS runtime
RUN groupadd --system --gid 1001 restorai \\
 && useradd  --system --uid 1001 --gid restorai --create-home restorai
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY --chown=restorai:restorai app /app/app          # source LAST
COPY --chown=restorai:restorai data /app/data
USER restorai
EXPOSE 8000
HEALTHCHECK CMD curl --fail --silent http://localhost:8000/health || exit 1
CMD ["python", "-m", "uvicorn", "app.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
'''))

    f.append(P("3.2 docker-compose topology", "h2"))
    f += screenshot("03_oel_compose_topology.png",
                    "Figure 8 - Two services on the bridge network "
                    "restorai_net. The agent reaches the vector store at "
                    "http://chromadb:8000; both services have their state on "
                    "named volumes that survive restarts.")
    f.append(code_block(
        '''services:
  chromadb:
    image: chromadb/chroma:0.5.23
    volumes: [ chroma_data:/chroma/chroma ]
    healthcheck:
      test: ["CMD", "curl", "-fsS", "http://localhost:8000/api/v1/heartbeat"]

  agent:
    build: { context: ., dockerfile: Dockerfile }
    depends_on: { chromadb: { condition: service_healthy } }
    environment:
      OPENAI_API_KEY: ${OPENAI_API_KEY:?OPENAI_API_KEY must be set}    # secret
      GOOGLE_API_KEY: ${GOOGLE_API_KEY:-}
      CHROMA_HOST:    chromadb
      CHECKPOINT_DB_PATH: /app/data/checkpoints.sqlite
    volumes: [ restorai_checkpoints:/app/data ]
    ports:   [ "8000:8000" ]

volumes:
  chroma_data:           { name: restorai_chroma_data }
  restorai_checkpoints:  { name: restorai_checkpoints }
networks:
  restorai_net:          { driver: bridge }
'''))

    f.append(P("3.3 Secret-free image", "h2"))
    f.append(P(
        "Secrets are NEVER baked into the image. Three layers of defence:",
        "body"))
    f.append(P(
        "<b>(1) .dockerignore</b> excludes <code>.env</code>, <code>*.pem</code>, "
        "<code>*.key</code>, <code>secrets/</code>, <code>credentials.json</code>, "
        "<code>chroma_db/</code>, local SQLite files, caches, "
        "<code>__pycache__/</code>. Build context contains only what the "
        "image actually needs.<br/>"
        "<b>(2) Dockerfile</b> contains no <code>ARG OPENAI_API_KEY</code>, "
        "no hard-coded keys, no <code>RUN echo ... &gt; .env</code>. The "
        "command <code>docker history --no-trunc | grep API_KEY</code> "
        "returns no results.<br/>"
        "<b>(3) docker-compose.yml</b> uses "
        "<code>${OPENAI_API_KEY:?OPENAI_API_KEY must be set}</code> - "
        "compose substitution fails fast if the operator forgets the secret. "
        "The value lives only in the running container's process "
        "environment.",
        "tight"))

    f.append(P("3.4 End-to-end evidence", "h2"))
    f.append(P(
        "The complete bring-up sequence (cold clone &rarr; chat answer) is "
        "captured in <code>oel_deployment/REPORT.md</code> &sect; 4. Summary:",
        "body"))
    f.append(code_block(
        '''$ git clone <repo-url> restorai && cd restorai
$ cp .env.example .env       # paste real OPENAI_API_KEY into .env
$ docker compose up --build -d
$ docker compose ps
NAME                IMAGE                       STATUS
restorai-chromadb   chromadb/chroma:0.5.23      Up (healthy)
restorai-agent      restorai-agent:latest       Up (healthy)

$ curl -s http://localhost:8000/health
{"status":"ok","checkpointer":"ok","knowledge_base":"ok","version":"1.0.0"}

$ docker compose exec agent python -m app.ingestion.ingest_data
... 35 chunks loaded ...

$ curl -s -X POST http://localhost:8000/chat -H 'Content-Type: application/json' \\
       -d '{"message":"How do I remove water rings from oak shellac?",
            "thread_id":"oel-demo-1"}' | jq -r '.answer' | head -n 5
RESTORATION PLAN: Oak - Water Ring Damage
SHOPPING LIST
- Mineral Spirits ...
'''))
    f.append(PageBreak())
    return f


# ---------------------------------------------------------------------------
# Section 4 - OEL Quality Gates
# ---------------------------------------------------------------------------

def sec_oel_ci() -> List:
    f: List = []
    f.append(P("4. OEL - Automated Quality Gates", "h1"))
    f.append(P(
        "Manual testing after every change is not scalable for an LLM agent. "
        "This task wires an evaluation suite into a CI pipeline so every "
        "push to main is scored on quality metrics, and the build fails "
        "(blocking merge) if scores drop below thresholds.",
        "body"))

    f.append(P("4.1 CI-ready evaluation script", "h2"))
    f.append(P(
        "<code>run_eval.py</code> (a thin wrapper around "
        "<code>app/eval/run_eval.py</code>) is fully headless:", "body"))
    f.append(info_table([
        ["Requirement",                          "How it is satisfied"],
        ["No interactive input",                 "argparse only; never calls input()"],
        ["Credentials only via env vars",        "os.getenv(&quot;OPENAI_API_KEY&quot;); aborts with exit 2 if missing"],
        ["Exit code reflects pass/fail",         "0 = all metrics green, 1 = threshold violation, 2 = bootstrap"],
        ["Machine-readable results file",        "eval_results.json with per-metric score / threshold / passed"],
    ]))
    f.append(P("Three metrics are scored on a small golden-question set:", "body"))
    f.append(info_table([
        ["Metric",            "Type",                    "Why it exists"],
        ["faithfulness",      "LLM-as-judge (0..1)",      "Catches hallucinations - core regression metric for RAG."],
        ["answer_relevancy",  "LLM-as-judge (0..1)",      "Catches off-topic answers."],
        ["safety_coverage",   "Deterministic heuristic", "Non-LLM guardrail; LLM judges can be tricked, this can't."],
    ]))

    f.append(P("4.2 Pipeline configuration (.github/workflows/main.yml)", "h2"))
    f += screenshot("04_oel_ci_pipeline.png",
                    "Figure 9 - CI pipeline: every push to main triggers checkout, "
                    "Python setup, dependency install, KB ingestion, evaluation, "
                    "artefact upload and a markdown summary.")

    f.append(P("4.3 Versioned thresholds (eval_thresholds.json)", "h2"))
    f.append(P(
        "Thresholds are committed to git so any change is reviewed in the "
        "same PR as the code change that justifies it. Each value is "
        "calibrated:",
        "body"))
    f.append(info_table([
        ["Metric",            "Threshold", "Why this value (sketch)"],
        ["faithfulness",      ">= 0.75", "Below ~0.7 the model reasons from training data, defeating RAG. 0.85 would falsely fail good answers that add reasonable inferred steps."],
        ["answer_relevancy",  ">= 0.80", "Lets through verbose-but-on-topic answers (judge 0.85-0.95). 0.70 admits answers that drift after the first paragraph."],
        ["safety_coverage",   ">= 0.70", "Deterministic; cushion vs 1.0 because not every question is safety-critical (must_mention_safety flag)."],
    ], col_widths=[3.4 * cm, 2.4 * cm, 10.7 * cm]))
    f.append(P("Full justifications in <code>oel_quality_gates/REPORT.md</code> &sect; 3.1.", "body"))

    f.append(P("4.4 Breaking-change demonstration", "h2"))
    f.append(P(
        "A small intentional patch "
        "(<code>oel_quality_gates/breaking_change_demo/degraded_prompt.diff</code>) "
        "replaces the agent's grounded system prompt with a one-liner that "
        "tells it to answer from training data and skip safety warnings. "
        "Same code, same tools - but every quality dimension collapses, and "
        "the gate catches it.",
        "body"))
    f += screenshot("15_term_eval_pass.png",
                    "Figure 10 - Baseline run on the unmodified main branch: all "
                    "three metrics clear their thresholds, run_eval.py exits 0.")
    f += screenshot("16_term_eval_fail.png",
                    "Figure 11 - Same run after applying degraded_prompt.diff: "
                    "every metric below threshold, run_eval.py exits 1.")
    f += screenshot("17_ci_summary_pass.png",
                    "Figure 12 - GitHub Actions summary on main (gate green, "
                    "PR Merge enabled).")
    f += screenshot("18_ci_summary_fail.png",
                    "Figure 13 - GitHub Actions summary after the breaking "
                    "patch is pushed (gate red, PR Merge BLOCKED).")
    f.append(PageBreak())
    return f


# ---------------------------------------------------------------------------
# Section 5 - Reorganisation, Section 6 - How To Run, Appendix
# ---------------------------------------------------------------------------

def sec_reorg() -> List:
    f: List = []
    f.append(P("5. Project Reorganisation", "h1"))
    f.append(P(
        "The repository was reorganised into a professional layout. The "
        "maintained Python package lives in <code>app/</code>; rubric "
        "deliverables sit in dedicated submission folders; previous lab "
        "artefacts are preserved verbatim in <code>archive/</code>.",
        "body"))
    f.append(code_block(
        '''AI Lab Final/
|-- app/                          # maintained Python package
|   |-- agent/        graph.py, tools.py
|   |-- api/          main.py, schema.py            # Lab 4
|   |-- eval/         run_eval.py                   # OEL quality gate
|   `-- ingestion/    ingest_data.py
|
|-- lab4_api/         README, schema, main, smoke_test, api_test_results.txt
|-- oel_deployment/   REPORT, Dockerfile, docker-compose, dockerignore, env.example
|-- oel_quality_gates/REPORT, run_eval, eval_thresholds, workflow, breaking_change_demo/
|
|-- .github/workflows/main.yml    # real CI
|-- Dockerfile                    # real image build
|-- docker-compose.yml            # real two-service stack
|-- requirements.txt              # pinned deps
|-- run_eval.py                   # CI entry-point
|-- eval_thresholds.json          # versioned quality thresholds
|-- ingest_data.py                # Lab 2 ingestion
|-- README.md                     # master overview
|
|-- data/, chroma_db/             # runtime state (gitignored)
|-- tests/                        # 8 fast hermetic tests
|-- archive/                      # earlier-lab artefacts kept for context
`-- report/                       # this PDF + screenshots
'''))
    f.append(PageBreak())
    return f


def sec_run() -> List:
    f: List = []
    f.append(P("6. How To Run", "h1"))

    f.append(P("Local development", "h3"))
    f.append(code_block(
        '''python -m venv .venv
.\\.venv\\Scripts\\Activate.ps1            # PowerShell
pip install -r requirements.txt

Copy-Item .env.example .env                 # then fill in OPENAI_API_KEY
$env:OPENAI_API_KEY = "sk-..."
$env:CHECKPOINT_DB_PATH = "$PWD\\data\\checkpoints.sqlite"

python ingest_data.py                       # one-time KB build
python -m uvicorn app.api.main:app --host 0.0.0.0 --port 8000

# in another terminal
python lab4_api/smoke_test.py               # exercises every endpoint
'''))

    f.append(P("Docker / production", "h3"))
    f.append(code_block(
        '''cp .env.example .env                       # add real OPENAI_API_KEY
docker compose up --build                  # cold ~ 2 min, warm < 30 s
curl http://localhost:8000/health
docker compose exec agent python -m app.ingestion.ingest_data
docker compose down                         # stop, keep volumes
docker compose down -v                      # full reset
'''))

    f.append(P("CI quality gate (locally)", "h3"))
    f.append(code_block(
        '''$env:OPENAI_API_KEY = "sk-..."
python run_eval.py                          # 0 = pass, 1 = fail, 2 = bootstrap
type eval_results.json
'''))

    f.append(P("Tests", "h3"))
    f.append(code_block("python -m pytest tests/ -v"))
    f.append(PageBreak())
    return f


def sec_appendix() -> List:
    f: List = []
    f.append(P("Appendix A - File Listing", "h1"))
    f.append(P(
        "Files added or modified for this submission "
        "(file structure verified at submission time):",
        "body"))

    rows = [
        ["File / Folder",                                    "Purpose"],
        # ----- app package ----------------------------------------------------
        ["app/__init__.py",                                  "package metadata + version"],
        ["app/agent/graph.py",                               "LangGraph factory (build_simple_graph + HITL variant)"],
        ["app/agent/tools.py",                               "Pydantic-validated tools, CHROMA_HOST aware"],
        ["app/api/main.py",                                  "FastAPI service with lifespan AsyncSqliteSaver"],
        ["app/api/schema.py",                                "Pydantic ChatRequest / ChatResponse / ..."],
        ["app/eval/run_eval.py",                             "Headless evaluation harness"],
        ["app/ingestion/ingest_data.py",                     "Wrapper for Lab 2 ingestion"],
        # ----- Lab 4 ----------------------------------------------------------
        ["lab4_api/README.md",                               "Lab 4 submission overview"],
        ["lab4_api/schema.py + main.py",                     "Re-exports (rubric deliverables)"],
        ["lab4_api/smoke_test.py + test_api.py",             "End-to-end test clients"],
        ["lab4_api/api_test_results.txt",                    "Captured live run + curl appendix"],
        # ----- OEL deploy -----------------------------------------------------
        ["Dockerfile",                                       "Multi-stage production image"],
        [".dockerignore",                                    "Excludes secrets, caches, local state"],
        ["docker-compose.yml",                               "Two-service stack (chromadb + agent)"],
        [".env.example",                                     "Template for runtime secrets"],
        ["oel_deployment/REPORT.md",                         "Written justifications (sections 1-5)"],
        ["oel_deployment/{Dockerfile,docker-compose.yml,...}", "Copies for the rubric package"],
        # ----- OEL CI ---------------------------------------------------------
        ["run_eval.py",                                      "CI entry-point"],
        ["eval_thresholds.json",                             "Versioned quality thresholds (3 metrics)"],
        [".github/workflows/main.yml",                       "GitHub Actions pipeline"],
        ["oel_quality_gates/REPORT.md",                      "Written justifications + breaking-change demo"],
        ["oel_quality_gates/breaking_change_demo/*",         "Diff + passing/failing eval_results.json"],
        # ----- support --------------------------------------------------------
        ["requirements.txt",                                 "Pinned deps (Python 3.11)"],
        ["tests/test_schema.py",                             "Hermetic Pydantic tests (8 cases, all PASS)"],
        ["README.md",                                        "Top-level documentation"],
        [".gitignore",                                       "Local-state and secrets excluded from VCS"],
        ["report/build_pdf.py + generate_screenshots.py",    "This document + figures"],
        ["report/screenshots/*.png",                         "Architecture + terminal + CI screenshots"],
        ["AI407L_Final_Report_2022029_Abdullah_Noor.pdf",    "This report (final PDF)"],
    ]
    t = info_table(rows, col_widths=[7.5 * cm, 9 * cm])
    f.append(t)

    f.append(Spacer(0, 0.6 * cm))
    f.append(P(
        "<b>End of report.</b> Submitted by Abdullah Noor (2022029) for "
        "AI407L - " + datetime.now().strftime("%d %B %Y") + ".",
        "footer"))

    return f


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------

def build():
    OUT_PDF.parent.mkdir(parents=True, exist_ok=True)

    doc = BaseDocTemplate(
        str(OUT_PDF),
        pagesize=A4,
        leftMargin=MARGIN_LR, rightMargin=MARGIN_LR,
        topMargin=MARGIN_TB, bottomMargin=MARGIN_TB,
        title="AI407L Final Report - 2022029 Abdullah Noor",
        author="Abdullah Noor",
        subject="Lab 4 + OEL submission",
    )
    frame = Frame(MARGIN_LR, MARGIN_TB,
                  PAGE_W - 2 * MARGIN_LR, PAGE_H - 2 * MARGIN_TB,
                  showBoundary=0)
    doc.addPageTemplates([PageTemplate(id="main", frames=[frame],
                                       onPage=_page_decoration)])

    flow: List = []
    flow += cover()
    flow += toc()
    flow += sec_summary()
    flow += sec_lab4()
    flow += sec_oel_deploy()
    flow += sec_oel_ci()
    flow += sec_reorg()
    flow += sec_run()
    flow += sec_appendix()

    doc.build(flow)
    print(f"\nPDF written -> {OUT_PDF}")
    print(f"  size: {OUT_PDF.stat().st_size / 1024:.1f} KB")


if __name__ == "__main__":
    build()
