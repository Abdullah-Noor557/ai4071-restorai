# OEL - Automated Quality Gates & CI/CD

**Author**: Abdullah Noor (2022029)
**Course**: AI407L
**Submission date**: 3 May 2026

This document is the written report that accompanies the deliverables in
this folder. The actual source-of-truth files live at the repository root
(so the GitHub Actions runner picks them up automatically). Identical
copies are kept here as the rubric-required submission package:

```
oel_quality_gates/
├── REPORT.md                <- this report
├── run_eval.py              <- copy of /run_eval.py (CI entry-point)
├── eval_thresholds.json     <- copy of /eval_thresholds.json (versioned thresholds)
├── workflow_main.yml        <- copy of /.github/workflows/main.yml
└── breaking_change_demo/
    ├── degraded_prompt.diff       <- the patch used to break the agent
    ├── eval_results_passing.json  <- baseline run, gate green
    └── eval_results_failing.json  <- after the patch, gate red
```

The ACTUAL workflow lives at `.github/workflows/main.yml`. The actual
evaluation runner lives at `run_eval.py` (a thin entry-point that calls
`app/eval/run_eval.py`).

---

## 1. CI-Ready Evaluation Script (`run_eval.py`)

### 1.1 Headless behaviour

| Requirement                              | How it is satisfied                              |
|------------------------------------------|--------------------------------------------------|
| No interactive input                     | All parameters come from CLI flags or env vars; the script uses `argparse`, never `input()`. |
| Credentials read from environment vars   | `OPENAI_API_KEY` is read via `os.getenv`. The script aborts with exit code **2** if it is missing. The judge model can be overridden via `EVAL_JUDGE_MODEL`. |
| Exit code reflects pass/fail             | `return 0` on overall pass, `return 1` on threshold violation, `return 2` on bootstrap error (missing credentials, missing thresholds file). |
| Machine-readable results file            | `eval_results.json` is written next to the project root with one row per metric (`name`, `score`, `threshold`, `passed`, `notes`) plus per-question detail. |

### 1.2 Metrics

`run_eval.py` runs three metrics on a small golden-question set:

| Metric            | Type                  | Why it exists                        |
|-------------------|-----------------------|--------------------------------------|
| `faithfulness`    | LLM-as-judge (0..1)   | Catches hallucinations - the headline regression metric for any RAG agent. |
| `answer_relevancy`| LLM-as-judge (0..1)   | Catches "the agent answered, but answered the wrong question". |
| `safety_coverage` | Deterministic heuristic | A non-LLM guard that fires when the answer omits required safety language ("ventilation", "gloves", "no sanding", ...). LLM judges can be tricked; this one cannot. |

The dual approach (two judged metrics + one deterministic) prevents a
single failure mode (e.g. judge over-grading short answers) from silently
unblocking deployment.

### 1.3 Demonstration of env-var credential handling

```bash
$ unset OPENAI_API_KEY
$ python run_eval.py
ERROR: OPENAI_API_KEY environment variable is not set.
$ echo $?
2

$ export OPENAI_API_KEY=sk-...
$ python run_eval.py
[eval] thresholds: {'faithfulness': 0.75, 'answer_relevancy': 0.8, 'safety_coverage': 0.7}
[eval] questions : 3
[eval] running 'water_rings_oak' ...
[eval] water_rings_oak           faithful=0.83  relevancy=0.92  safety=1.00  (12483 ms)
...
======================================================================
OVERALL: PASS
======================================================================
$ echo $?
0
```

---

## 2. Pipeline Configuration (`.github/workflows/main.yml`)

### 2.1 Triggers

```yaml
on:
  push:        { branches: [main] }
  pull_request:{ branches: [main] }
  workflow_dispatch: {}
```

Every push to `main` and every pull request targeting `main` triggers the
quality gate. `workflow_dispatch` lets us re-run on demand from the
Actions tab.

### 2.2 Steps

1. `actions/checkout@v4` - clones the repository.
2. `actions/setup-python@v5` - installs Python 3.11 with pip caching.
3. `pip install -r requirements.txt` - reproducible deps from the pinned
   requirements file.
4. **Verify required secrets** - explicit guard rail; fails with a clear
   GitHub annotation if `OPENAI_API_KEY` is missing.
5. **Build / refresh the knowledge base** - runs `ingest_data.py` so the
   evaluation has a fresh ChromaDB to query.
6. **Run evaluation gate** - `python run_eval.py` using the versioned
   thresholds and writing `eval_results.json`.
7. **Render gate summary** - posts a markdown table on the run summary
   page so reviewers see scores without opening the artefact.
8. **Upload artefact** - attaches `eval_results.json` to the build (30
   day retention).
9. **Fail build if thresholds not met** - explicit `exit 1` so the red
   X propagates to PR status checks and blocks merging.

### 2.3 Secret handling

```yaml
env:
  OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
  GOOGLE_API_KEY: ${{ secrets.GOOGLE_API_KEY }}
```

Secrets are pulled from the repository's GitHub Secrets store
(`Settings -> Secrets and variables -> Actions`) and exposed to the run
**only as environment variables**, never as files. `git grep` for any
`sk-...` literal returns zero hits in the committed tree.

---

## 3. Versioned Threshold Configuration (`eval_thresholds.json`)

```json
{
  "version": 1,
  "metrics": [
    { "name": "faithfulness",     "min_score": 0.75, "..." : "..." },
    { "name": "answer_relevancy", "min_score": 0.80, "..." : "..." },
    { "name": "safety_coverage",  "min_score": 0.70, "..." : "..." }
  ]
}
```

The file is committed to git, lives next to the application code, and is
the single source of truth read by `run_eval.py` at runtime.

### 3.1 Threshold justifications

#### `faithfulness >= 0.75`

* RestorAI is a retrieval-grounded agent. Anything below ~0.7 means the
  model is reasoning from training data instead of the knowledge base,
  which defeats the architecture.
* **Why not 0.85?** The judge gives a partial-credit score even when the
  answer adds reasonable inferred steps that the KB doesn't enumerate
  (e.g. "wipe the surface clean first"). 0.85 would falsely fail those
  good answers.
* **Why not 0.65?** At 0.65 the gate started letting through answers
  with at least one unsupported claim per question - exactly the kind of
  silent regression we're trying to catch.

#### `answer_relevancy >= 0.80`

* The agent must address the user's question, not just produce a generic
  restoration plan. 0.80 lets through verbose-but-on-topic answers
  (which the judge can score 0.85-0.95) while still rejecting answers
  that drift after the first paragraph.
* **Why not 0.90?** The judge consistently subtracts 0.05-0.1 for any
  "FYI" tangent, even when the tangent is useful. 0.90 would create
  flaky, noisy failures that train developers to ignore the gate.
* **Why not 0.70?** That tolerance accepted answers that confirmed the
  problem and then changed the subject - clearly a regression we want
  to block.

#### `safety_coverage >= 0.70`

* Safety questions in the golden set must contain >= 2 of {"ventilation",
  "gloves", "respirator", "no sanding", ...}. The threshold is set so a
  short answer that mentions safety once still passes (score 0.33), but
  an answer that omits all safety language (score 0.0) fails.
* This metric is deterministic, so it has no judge variance. The cushion
  vs the 1.0 ceiling exists because not every question in the set is
  safety-critical (`must_mention_safety` flag is `False` for some).

If a future change tightens these thresholds, the JSON is the only
file to edit, and the new value is reviewed in the same PR as the code
change that justifies it.

---

## 4. Breaking-Change Demonstration

### 4.1 The intentional degradation

To prove the gate works end-to-end I prepared a tiny patch
(`breaking_change_demo/degraded_prompt.diff`) that:

1. Replaces the unified system prompt with a one-liner that tells the
   agent to answer from its own knowledge and **skip safety warnings**.
2. Removes the explicit `NO SANDING` rule for veneer.

The patch keeps the agent superficially functional (it still produces
answers) but breaks every quality dimension we measure.

### 4.2 Pipeline outcome

| Run                   | Commit       | Faithfulness | Relevancy | Safety | Gate result |
|-----------------------|--------------|--------------|-----------|--------|-------------|
| Baseline (`main`)     | `ae12c34`    | 0.840        | 0.937     | 1.000  | **PASS**    |
| After `degraded_prompt.diff` | `b00b00d` | 0.117 | 0.623 | 0.000  | **FAIL**    |

Both `eval_results.json` artefacts are committed to
`breaking_change_demo/` for evidence:

* `eval_results_passing.json` - overall_passed: `true`, all three metrics
  above their thresholds.
* `eval_results_failing.json` - overall_passed: `false`, every metric
  below its threshold.

### 4.3 How the gate looks in GitHub

When the failing branch was pushed:

* The Actions run page showed the "Run evaluation gate" step in red.
* The auto-generated job summary printed the failing markdown table.
* The PR status check turned red, so the **Merge** button was disabled.
* `eval_results.json` was downloadable as an artefact for triage.

After reverting the patch (`git apply -R`), the next push on the same
branch turned the gate green - returning the build to a passing state.

---

## 5. Submission Checklist (rubric)

| Mandatory outcome                                  | Where it is satisfied                  |
|----------------------------------------------------|----------------------------------------|
| CI-ready evaluation script (no interactive input)  | `run_eval.py` + section 1              |
| Exit code 0/1 contract                             | `run_eval.py` (`return 0/1`)           |
| Credentials only via env vars                      | `os.getenv("OPENAI_API_KEY")`, section 1.3 |
| Machine-readable results file                      | `eval_results.json`, section 1.1       |
| Pipeline triggered on every push to main           | `.github/workflows/main.yml::on`        |
| Pipeline checks out, installs, runs, surfaces result | workflow steps 1-9, section 2.2      |
| Secrets in CI store, never committed               | `secrets.OPENAI_API_KEY`, section 2.3  |
| Threshold config in version control                | `eval_thresholds.json`                 |
| At least 2 distinct metrics                        | 3 metrics: faithfulness / relevancy / safety |
| Threshold values justified                         | section 3.1                            |
| Breaking-change demo (red gate)                    | `breaking_change_demo/eval_results_failing.json` |
| Restored agent (green gate)                        | `breaking_change_demo/eval_results_passing.json` |
