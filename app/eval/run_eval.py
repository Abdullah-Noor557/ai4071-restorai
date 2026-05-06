"""
RestorAI - Headless Evaluation Harness (OEL: Automated Quality Gates)

Adapted from the Lab 7 manual evaluation suite. Designed to run in CI:

* Reads all credentials from environment variables (no interactive input).
* Loads thresholds from ``eval_thresholds.json`` (versioned in git).
* Runs the agent against a set of golden questions and scores the answers
  on three quality metrics:

      - faithfulness      (answer is grounded in retrieved context)
      - answer_relevancy  (answer addresses the user question)
      - safety_coverage   (answer mentions the required safety constraint)

* Writes a machine-readable ``eval_results.json`` with one row per metric,
  the threshold, the score, and a ``passed`` flag.
* Exits 0 when every metric clears its threshold, 1 otherwise.

Usage (CI):
    python -m app.eval.run_eval                     # default paths
    python -m app.eval.run_eval \
        --thresholds eval_thresholds.json \
        --output     eval_results.json

Author: Abdullah Noor - 2022029
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from langchain_core.messages import AIMessage, HumanMessage
from langchain_openai import ChatOpenAI

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.agent.graph import build_simple_graph  # noqa: E402
from app.agent.tools import KnowledgeBase  # noqa: E402


# ---------------------------------------------------------------------------
# Golden test set (small, fast, deterministic)
# ---------------------------------------------------------------------------

GOLDEN_QUESTIONS: List[Dict[str, Any]] = [
    {
        "id": "water_rings_oak",
        "question": (
            "I have water ring damage on an oak coffee table with a shellac finish. "
            "What technique should I use and what are the safety precautions?"
        ),
        "expected_keywords": ["shellac", "water ring", "ventilat"],
        "must_mention_safety": True,
    },
    {
        "id": "veneer_no_sanding",
        "question": (
            "I have a walnut veneer dresser with surface scratches. Can I sand it down "
            "and refinish it like solid wood?"
        ),
        "expected_keywords": ["veneer", "no sand", "thin"],
        "must_mention_safety": True,
    },
    {
        "id": "stripper_safety",
        "question": (
            "I want to use a chemical stripper on an old painted chair. "
            "What safety equipment and precautions do I need?"
        ),
        "expected_keywords": ["ventilat", "glove", "respir"],
        "must_mention_safety": True,
    },
]


# ---------------------------------------------------------------------------
# Result data classes
# ---------------------------------------------------------------------------

@dataclass
class MetricResult:
    name: str
    score: float
    threshold: float
    passed: bool
    notes: str = ""


@dataclass
class QuestionResult:
    id: str
    question: str
    answer: str
    contexts_used: int
    elapsed_ms: int
    metric_scores: Dict[str, float] = field(default_factory=dict)


@dataclass
class EvalReport:
    started_at: str
    finished_at: str
    git_sha: Optional[str]
    thresholds_file: str
    questions: List[QuestionResult]
    metrics: List[MetricResult]
    overall_passed: bool


# ---------------------------------------------------------------------------
# Metric implementations (LLM-as-judge)
# ---------------------------------------------------------------------------

JUDGE_MODEL = os.getenv("EVAL_JUDGE_MODEL", "gpt-4o-mini")


def _judge(prompt: str) -> float:
    """Ask an LLM judge for a 0-1 score and parse it robustly."""
    llm = ChatOpenAI(model=JUDGE_MODEL, temperature=0)
    response = llm.invoke([
        {"role": "system", "content":
            "You are a strict evaluator. Reply with ONLY a single floating-point "
            "number between 0.0 and 1.0 (no words, no punctuation)."},
        {"role": "user", "content": prompt},
    ])
    text = (response.content if isinstance(response, AIMessage) else str(response)).strip()
    try:
        score = float(text.split()[0])
    except Exception:
        score = 0.0
    return max(0.0, min(1.0, score))


def metric_faithfulness(question: str, answer: str, contexts: List[str]) -> float:
    """Is the answer grounded in the retrieved context?"""
    if not contexts:
        return 0.0
    joined_ctx = "\n---\n".join(contexts[:6])[:6000]
    prompt = (
        "Score how FAITHFUL the ANSWER is to the CONTEXT. "
        "1.0 = every claim in the answer is directly supported by the context. "
        "0.0 = the answer contradicts or invents information.\n\n"
        f"QUESTION:\n{question}\n\nCONTEXT:\n{joined_ctx}\n\nANSWER:\n{answer}\n\nScore:"
    )
    return _judge(prompt)


def metric_answer_relevancy(question: str, answer: str) -> float:
    """Does the answer actually address the user's question?"""
    prompt = (
        "Score how RELEVANT the ANSWER is to the QUESTION. "
        "1.0 = the answer directly addresses every part of the question. "
        "0.0 = the answer is off-topic.\n\n"
        f"QUESTION:\n{question}\n\nANSWER:\n{answer}\n\nScore:"
    )
    return _judge(prompt)


def metric_safety_coverage(answer: str, must_mention_safety: bool) -> float:
    """
    Cheap, deterministic heuristic: did the answer mention safety where it
    should? This complements the LLM-judged metrics with a non-LLM check
    that cannot be silently rewarded by a chatty model.
    """
    if not must_mention_safety:
        return 1.0
    haystack = answer.lower()
    needles = [
        "safety", "ventilat", "glove", "respir", "mask",
        "warning", "precaution", "no sanding", "do not sand",
    ]
    hits = sum(1 for n in needles if n in haystack)
    return min(1.0, hits / 3.0)  # 3 hits => full marks


# ---------------------------------------------------------------------------
# Evaluation runner
# ---------------------------------------------------------------------------

def run_question(graph, kb: KnowledgeBase, q: Dict[str, Any]) -> QuestionResult:
    started = time.perf_counter()

    # Pull contexts up-front so we can use them for the faithfulness metric,
    # independent of which tools the agent decided to call.
    kb_results = kb.search(q["question"], n_results=4)
    contexts = [r["content"] for r in kb_results.get("results", [])]

    config = {"configurable": {"thread_id": f"eval_{q['id']}_{int(time.time())}"}}
    initial = {"messages": [HumanMessage(content=q["question"])]}

    answer = ""
    for event in graph.stream(initial, config, stream_mode="values"):
        for m in event.get("messages", []):
            if isinstance(m, AIMessage) and m.content and not getattr(m, "tool_calls", None):
                answer = m.content

    elapsed_ms = int((time.perf_counter() - started) * 1000)
    return QuestionResult(
        id=q["id"],
        question=q["question"],
        answer=answer,
        contexts_used=len(contexts),
        elapsed_ms=elapsed_ms,
    ), contexts


def aggregate(scores: List[float]) -> float:
    return round(sum(scores) / len(scores), 3) if scores else 0.0


def run(thresholds_path: Path, output_path: Path) -> int:
    if not os.getenv("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY environment variable is not set.", file=sys.stderr)
        return 2

    if not thresholds_path.exists():
        print(f"ERROR: thresholds file not found: {thresholds_path}", file=sys.stderr)
        return 2

    thresholds_doc = json.loads(thresholds_path.read_text(encoding="utf-8"))
    threshold_map: Dict[str, float] = {
        m["name"]: float(m["min_score"]) for m in thresholds_doc["metrics"]
    }

    started_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    git_sha = os.getenv("GITHUB_SHA") or os.getenv("GIT_SHA")

    print(f"[eval] thresholds: {threshold_map}")
    print(f"[eval] questions : {len(GOLDEN_QUESTIONS)}")

    graph = build_simple_graph()
    kb = KnowledgeBase()

    per_question: List[QuestionResult] = []
    faithfulness_scores: List[float] = []
    relevancy_scores: List[float] = []
    safety_scores: List[float] = []

    for q in GOLDEN_QUESTIONS:
        print(f"[eval] running '{q['id']}' ...")
        try:
            result, contexts = run_question(graph, kb, q)
        except Exception as exc:
            print(f"[eval] FAILED to run question {q['id']}: {exc}", file=sys.stderr)
            result = QuestionResult(id=q["id"], question=q["question"], answer="",
                                     contexts_used=0, elapsed_ms=0)
            contexts = []

        f = metric_faithfulness(q["question"], result.answer or "", contexts)
        r = metric_answer_relevancy(q["question"], result.answer or "")
        s = metric_safety_coverage(result.answer or "", q["must_mention_safety"])

        result.metric_scores = {
            "faithfulness": round(f, 3),
            "answer_relevancy": round(r, 3),
            "safety_coverage": round(s, 3),
        }
        faithfulness_scores.append(f)
        relevancy_scores.append(r)
        safety_scores.append(s)
        per_question.append(result)

        print(
            f"[eval] {q['id']:<24}  faithful={f:.2f}  relevancy={r:.2f}  "
            f"safety={s:.2f}  ({result.elapsed_ms} ms)"
        )

    metrics: List[MetricResult] = []
    for name, scores in [
        ("faithfulness", faithfulness_scores),
        ("answer_relevancy", relevancy_scores),
        ("safety_coverage", safety_scores),
    ]:
        if name not in threshold_map:
            continue
        agg = aggregate(scores)
        passed = agg >= threshold_map[name]
        metrics.append(MetricResult(
            name=name, score=agg, threshold=threshold_map[name], passed=passed,
            notes=f"avg over {len(scores)} questions",
        ))

    overall_passed = all(m.passed for m in metrics)
    finished_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    report = EvalReport(
        started_at=started_at,
        finished_at=finished_at,
        git_sha=git_sha,
        thresholds_file=str(thresholds_path),
        questions=per_question,
        metrics=metrics,
        overall_passed=overall_passed,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(asdict(report), indent=2, default=str), encoding="utf-8"
    )

    print()
    print("=" * 70)
    print(f"OVERALL: {'PASS' if overall_passed else 'FAIL'}")
    print("=" * 70)
    for m in metrics:
        symbol = "PASS" if m.passed else "FAIL"
        print(f"  [{symbol}] {m.name:<18} score={m.score:.3f}  threshold={m.threshold:.3f}")
    print(f"\n[eval] report written to: {output_path}")
    return 0 if overall_passed else 1


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="RestorAI CI evaluation runner")
    parser.add_argument(
        "--thresholds", type=Path,
        default=REPO_ROOT / "eval_thresholds.json",
        help="Path to versioned threshold configuration file.",
    )
    parser.add_argument(
        "--output", type=Path,
        default=REPO_ROOT / "eval_results.json",
        help="Where to write the machine-readable results file.",
    )
    args = parser.parse_args()
    return run(args.thresholds, args.output)


if __name__ == "__main__":
    sys.exit(main())
