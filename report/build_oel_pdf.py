"""
Build the OEL-only PDF report:
    AI407L_OEL_Report_2022029_Abdullah_Noor.pdf

This report intentionally excludes Lab 4 narrative and focuses only on:
  - Industrial Packaging & Deployment Strategy
  - Automated Quality Gates & CI/CD

Run:
    python report/build_oel_pdf.py
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import List

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    Image,
    PageBreak,
    PageTemplate,
    Paragraph,
    Preformatted,
    Spacer,
    Table,
    TableStyle,
)

REPO = Path(__file__).resolve().parent.parent
SHOTS = Path(__file__).resolve().parent / "screenshots"
OUT_PDF = REPO / "AI407L_OEL_Report_2022029_Abdullah_Noor.pdf"

PAGE_W, PAGE_H = A4
MARGIN_LR = 1.8 * cm
MARGIN_TB = 2.0 * cm

ACCENT = colors.HexColor("#3a6ea5")
ACCENT_DARK = colors.HexColor("#1f3f63")
SUBTLE = colors.HexColor("#5a6675")
RULE = colors.HexColor("#cdd5e0")
CODE_BG = colors.HexColor("#f4f6fa")
CODE_BORDER = colors.HexColor("#cdd5e0")
PASS_GREEN = colors.HexColor("#1f883d")
FAIL_RED = colors.HexColor("#cf222e")

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
}


def _page_decoration(canvas, doc):
    canvas.saveState()
    if doc.page > 1:
        canvas.setStrokeColor(RULE)
        canvas.setLineWidth(0.4)
        canvas.line(MARGIN_LR, PAGE_H - MARGIN_TB + 14, PAGE_W - MARGIN_LR, PAGE_H - MARGIN_TB + 14)
        canvas.setFont("Helvetica", 8.5)
        canvas.setFillColor(SUBTLE)
        canvas.drawString(MARGIN_LR, PAGE_H - MARGIN_TB + 18, "AI407L - OEL Report")
        canvas.drawRightString(PAGE_W - MARGIN_LR, PAGE_H - MARGIN_TB + 18, "Abdullah Noor / 2022029")

    canvas.setStrokeColor(RULE)
    canvas.setLineWidth(0.4)
    canvas.line(MARGIN_LR, MARGIN_TB - 16, PAGE_W - MARGIN_LR, MARGIN_TB - 16)
    canvas.setFont("Helvetica", 8.5)
    canvas.setFillColor(SUBTLE)
    canvas.drawString(MARGIN_LR, MARGIN_TB - 28, "RestorAI - OEL Submission")
    canvas.drawRightString(PAGE_W - MARGIN_LR, MARGIN_TB - 28, f"Page {doc.page}")
    canvas.restoreState()


def P(text: str, style: str = "body") -> Paragraph:
    return Paragraph(text, S[style])


def code_block(text: str) -> Preformatted:
    return Preformatted(text.strip("\n"), S["code"])


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
_CELL_PASS = ParagraphStyle("_cell_pass", parent=_CELL_BODY, fontName="Helvetica-Bold", textColor=PASS_GREEN, alignment=TA_CENTER)
_CELL_FAIL = ParagraphStyle("_cell_fail", parent=_CELL_BODY, fontName="Helvetica-Bold", textColor=FAIL_RED, alignment=TA_CENTER)


def _wrap_cell(value, header: bool = False):
    if isinstance(value, str):
        return Paragraph(value, _CELL_HEAD if header else _CELL_BODY)
    return value


def info_table(rows: List[List[str]], col_widths=None) -> Table:
    wrapped = []
    for r, row in enumerate(rows):
        wrapped.append([_wrap_cell(v, header=(r == 0)) for v in row])
    t = Table(wrapped, colWidths=col_widths, hAlign="LEFT")
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), ACCENT),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f6f8fc")]),
        ("BOX", (0, 0), (-1, -1), 0.5, RULE),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, RULE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return t


def ok_fail_table(rows: List[List[str]], col_widths=None) -> Table:
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


def screenshot(filename: str, caption: str, *, width: float = 16.5, max_height: float = 12.5) -> List:
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


def cover() -> List:
    flow: List = [Spacer(0, 3.5 * cm)]
    flow.append(P("AI407L - AI Lab", "subtitle"))
    flow.append(P("OEL Report", "title"))
    flow.append(P("Deployment Packaging  ·  Automated Quality Gates", "subtitle"))
    flow.append(Spacer(0, 0.7 * cm))

    bar = Table([[""]], colWidths=[16.5 * cm], rowHeights=[0.18 * cm])
    bar.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), ACCENT)]))
    bar.hAlign = "CENTER"
    flow.append(bar)
    flow.append(Spacer(0, 1.4 * cm))

    info = info_table([
        ["Field", "Value"],
        ["Student Name", "Abdullah Noor"],
        ["Roll Number", "2022029"],
        ["Course", "AI407L - AI Lab"],
        ["Submission", "OEL (Industrial Packaging + Quality Gates)"],
        ["Date", datetime.now().strftime("%d %B %Y")],
        ["Repository", "AI Lab Final/  (local)"],
    ], col_widths=[5.2 * cm, 11.3 * cm])
    info.hAlign = "CENTER"
    flow.append(info)

    flow.append(Spacer(0, 1.2 * cm))
    flow.append(P(
        "<b>Objective.</b> Package the RestorAI agent so it runs the same way on any machine "
        "with a single command, inject secrets at runtime (never at build time), orchestrate "
        "multiple services with persistence across restarts, and enforce an automated "
        "quality gate in CI that blocks degraded agents from reaching production.",
        "body",
    ))
    flow.append(PageBreak())
    return flow


def toc() -> List:
    flow: List = [P("Table of Contents", "h1")]
    rows = [
        ["1.", "Executive summary (OEL outcomes)"],
        ["2.", "Industrial Packaging & Deployment Strategy"],
        ["", "    2.1 Reproducible container image"],
        ["", "    2.2 Secret-free image & runtime injection"],
        ["", "    2.3 Multi-service orchestration & persistence"],
        ["", "    2.4 End-to-end proof (build logs + curl)"],
        ["3.", "Automated Quality Gates & CI/CD"],
        ["", "    3.1 CI-ready evaluation script (exit codes + JSON results)"],
        ["", "    3.2 Pipeline configuration (GitHub Actions)"],
        ["", "    3.3 Versioned thresholds (>= 2 metrics)"],
        ["", "    3.4 Breaking-change demonstration (red -> green)"],
        ["4.", "How to run (docker + CI)"],
        ["A.", "Appendix - Submission artefacts list"],
    ]
    t = Table(rows, colWidths=[1.5 * cm, 14 * cm])
    t.setStyle(TableStyle([
        ("FONT", (0, 0), (-1, -1), "Helvetica", 11),
        ("FONT", (0, 0), (0, -1), "Helvetica-Bold", 11),
        ("TEXTCOLOR", (0, 0), (0, -1), ACCENT_DARK),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    flow.append(t)
    flow.append(PageBreak())
    return flow


def sec_summary() -> List:
    f: List = []
    f.append(P("1. Executive summary (OEL outcomes)", "h1"))
    f.append(P(
        "This report documents only the OEL deliverables: (1) industrial packaging and deployment "
        "using Docker + docker-compose, and (2) automated quality gates that enforce evaluation "
        "thresholds on every push to main. Screenshots show the stack starting from configuration "
        "files alone and the CI gate turning red/green during the breaking-change demonstration.",
        "body",
    ))

    f.append(P("OEL mandatory outcomes checklist", "h2"))
    f.append(ok_fail_table([
        ["Outcome", "Where satisfied", "Status"],
        ["Reproducible container image", "Dockerfile (multi-stage) + requirements.txt pinned", "OK"],
        ["Secret-free image", ".dockerignore + runtime env injection (.env.example + compose)", "OK"],
        ["Multi-service orchestration", "docker-compose.yml (agent + chromadb) + volumes", "OK"],
        ["Persistence across restarts", "named volumes: restorai_chroma_data + restorai_checkpoints", "OK"],
        ["End-to-end proof", "Figure 4 + oel_deployment/REPORT.md", "OK"],
        ["CI-ready evaluation script", "run_eval.py + app/eval/run_eval.py", "OK"],
        ["Pipeline on push to main", ".github/workflows/main.yml", "OK"],
        ["Versioned thresholds (>=2 metrics)", "eval_thresholds.json (3 metrics)", "OK"],
        ["Breaking-change demonstration", "Figures 9-12 + oel_quality_gates/breaking_change_demo/", "OK"],
    ], col_widths=[7.0 * cm, 7.0 * cm, 2.2 * cm]))

    f.append(P("OEL architecture", "h2"))
    f += screenshot(
        "03_oel_compose_topology.png",
        "Figure 1 - OEL deployment topology: two services (agent API + ChromaDB) on the same network; "
        "state persists on named volumes; secrets are injected at runtime via environment variables.",
    )
    f.append(PageBreak())
    return f


def sec_deploy() -> List:
    f: List = []
    f.append(P("2. Industrial Packaging & Deployment Strategy", "h1"))

    f.append(P("2.1 Reproducible container image", "h2"))
    f.append(P(
        "A multi-stage Dockerfile produces a reproducible runtime image. Dependency installation is "
        "cached by copying requirements.txt before application code, so small code edits do not "
        "invalidate the pip layer.",
        "body",
    ))
    f.append(code_block(
        """FROM python:3.11.9-slim-bookworm AS base
...
FROM base AS builder
COPY requirements.txt /app/requirements.txt
RUN python -m venv /opt/venv && /opt/venv/bin/pip install -r /app/requirements.txt
FROM base AS runtime
COPY --from=builder /opt/venv /opt/venv
COPY app /app/app
CMD ["python","-m","uvicorn","app.api.main:app","--host","0.0.0.0","--port","8000"]
"""
    ))

    f.append(P("2.2 Secret-free image & runtime injection", "h2"))
    f.append(P(
        "Secrets are excluded from both git and Docker build context. They are injected only at runtime "
        "via docker-compose environment variables. The image contains no API keys at build time.",
        "body",
    ))
    f.append(info_table([
        ["Mechanism", "Evidence"],
        [".dockerignore excludes secrets", ".env, .env.*, *.pem, *.key, secrets/, credentials.json"],
        ["No ARG API keys in Dockerfile", "No OPENAI_API_KEY / GOOGLE_API_KEY baked into layers"],
        ["Runtime secret injection", "docker-compose.yml: OPENAI_API_KEY: ${OPENAI_API_KEY:?must be set}"],
    ], col_widths=[5.5 * cm, 10.7 * cm]))

    f.append(P("2.3 Multi-service orchestration & persistence", "h2"))
    f.append(P(
        "The system runs as two services: the agent API and a backing vector store (ChromaDB). "
        "Both services are started/stopped together by docker-compose. Persistent data survives "
        "container restarts because it lives on named volumes.",
        "body",
    ))
    f.append(info_table([
        ["Service", "Role", "Persistence"],
        ["agent", "FastAPI + LangGraph", "restorai_checkpoints -> /app/data (checkpoints.sqlite, orders)"],
        ["chromadb", "Vector DB backend", "restorai_chroma_data -> /chroma/chroma"],
    ], col_widths=[3.0 * cm, 6.2 * cm, 7.0 * cm]))

    f.append(P("2.4 End-to-end proof (build logs + curl)", "h2"))
    f += screenshot(
        "19_term_oel_end_to_end.png",
        "Figure 2 - End-to-end proof: docker compose up --build, curl /health, ingestion, and a chat request.",
        width=16.5, max_height=9.8,
    )
    f.append(PageBreak())
    return f


def sec_quality() -> List:
    f: List = []
    f.append(P("3. Automated Quality Gates & CI/CD", "h1"))

    f.append(P("3.1 CI-ready evaluation script (exit codes + JSON results)", "h2"))
    f.append(P(
        "The evaluation suite runs headlessly, reads credentials from environment variables, "
        "writes a machine-readable results JSON, and exits 0/1 so CI can mark the build pass/fail.",
        "body",
    ))
    f.append(info_table([
        ["Requirement", "How it is satisfied"],
        ["Headless execution", "run_eval.py uses argparse; no interactive input"],
        ["Secrets via env vars", "OPENAI_API_KEY read from env; missing -> exit 2"],
        ["Machine-readable output", "eval_results.json includes metric score/threshold/pass"],
        ["CI exit codes", "0 = pass, 1 = fail"],
    ], col_widths=[5.8 * cm, 10.4 * cm]))

    f.append(P("3.2 Pipeline configuration (GitHub Actions)", "h2"))
    f += screenshot(
        "04_oel_ci_pipeline.png",
        "Figure 3 - CI pipeline triggered on every push to main: checkout, install deps, ingest KB, "
        "run evaluation, upload artefact, block merge on failure.",
        width=16.5, max_height=7.6,
    )

    f.append(P("3.3 Versioned thresholds (>= 2 metrics)", "h2"))
    f.append(P(
        "Thresholds are committed in eval_thresholds.json and enforced like unit tests. "
        "At least two metrics are used; this project uses three: faithfulness, answer_relevancy, safety_coverage.",
        "body",
    ))
    f.append(info_table([
        ["Metric", "Threshold", "Why it matters"],
        ["faithfulness", ">= 0.75", "Blocks hallucinations / ungrounded answers in a RAG agent"],
        ["answer_relevancy", ">= 0.80", "Blocks off-topic answers"],
        ["safety_coverage", ">= 0.70", "Deterministic guardrail for safety-critical responses"],
    ], col_widths=[4.0 * cm, 2.6 * cm, 9.6 * cm]))

    f.append(P("3.4 Breaking-change demonstration (red -> green)", "h2"))
    f.append(P(
        "A deliberate patch disables grounding and safety reminders. The CI gate detects the regression "
        "and fails the build (merge blocked). Reverting the patch restores a passing state.",
        "body",
    ))
    f += screenshot("15_term_eval_pass.png", "Figure 4 - Baseline evaluation PASS (run_eval.py exits 0).", width=16.5, max_height=6.9)
    f += screenshot("16_term_eval_fail.png", "Figure 5 - After intentional degradation: FAIL (run_eval.py exits 1).", width=16.5, max_height=6.9)
    f += screenshot("17_ci_summary_pass.png", "Figure 6 - GitHub Actions summary: PASSING (merge enabled).", width=16.5, max_height=6.4)
    f += screenshot("18_ci_summary_fail.png", "Figure 7 - GitHub Actions summary: FAILING (merge blocked).", width=16.5, max_height=6.4)

    f.append(PageBreak())
    return f


def sec_run() -> List:
    f: List = []
    f.append(P("4. How to run (docker + CI)", "h1"))

    f.append(P("Docker bring-up (single command)", "h3"))
    f.append(code_block(
        """cp .env.example .env
# paste OPENAI_API_KEY into .env
docker compose up --build
curl http://localhost:8000/health
docker compose exec agent python -m app.ingestion.ingest_data
"""
    ))

    f.append(P("Quality gate (locally)", "h3"))
    f.append(code_block(
        """export OPENAI_API_KEY=sk-...
python run_eval.py
cat eval_results.json
"""
    ))
    f.append(PageBreak())
    return f


def sec_appendix() -> List:
    f: List = []
    f.append(P("Appendix - Submission artefacts list", "h1"))
    f.append(P("Key OEL artefacts included in the repository:", "body"))
    f.append(info_table([
        ["Artefact", "Location"],
        ["Dockerfile", "Dockerfile (copies in oel_deployment/)"],
        ["Compose file", "docker-compose.yml (copy in oel_deployment/)"],
        ["Secret injection template", ".env.example (copy in oel_deployment/)"],
        ["Deployment report", "oel_deployment/REPORT.md"],
        ["CI evaluation runner", "run_eval.py + app/eval/run_eval.py (copy in oel_quality_gates/)"],
        ["Threshold config", "eval_thresholds.json (copy in oel_quality_gates/)"],
        ["CI pipeline config", ".github/workflows/main.yml (copy in oel_quality_gates/workflow_main.yml)"],
        ["Breaking-change demo", "oel_quality_gates/breaking_change_demo/ (diff + passing/failing results)"],
        ["OEL report PDF", "AI407L_OEL_Report_2022029_Abdullah_Noor.pdf"],
    ], col_widths=[5.3 * cm, 10.9 * cm]))
    return f


def build():
    OUT_PDF.parent.mkdir(parents=True, exist_ok=True)

    doc = BaseDocTemplate(
        str(OUT_PDF),
        pagesize=A4,
        leftMargin=MARGIN_LR, rightMargin=MARGIN_LR,
        topMargin=MARGIN_TB, bottomMargin=MARGIN_TB,
        title="AI407L OEL Report - 2022029 Abdullah Noor",
        author="Abdullah Noor",
        subject="OEL submission",
    )
    frame = Frame(MARGIN_LR, MARGIN_TB, PAGE_W - 2 * MARGIN_LR, PAGE_H - 2 * MARGIN_TB, showBoundary=0)
    doc.addPageTemplates([PageTemplate(id="main", frames=[frame], onPage=_page_decoration)])

    flow: List = []
    flow += cover()
    flow += toc()
    flow += sec_summary()
    flow += sec_deploy()
    flow += sec_quality()
    flow += sec_run()
    flow += sec_appendix()

    doc.build(flow)
    print(f"PDF written -> {OUT_PDF}")
    print(f"  size: {OUT_PDF.stat().st_size / 1024:.1f} KB")


if __name__ == "__main__":
    build()

