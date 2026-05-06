"""
CI-Ready Evaluation Runner (OEL: Automated Quality Gates).

Invoked by ``.github/workflows/main.yml`` and submission rubric. Delegates to
the maintained harness in ``app/eval/run_eval.py`` so the CI command line and
the package layout stay decoupled.

Behaviour required by the rubric:
    * No interactive input.
    * All credentials read from environment variables (OPENAI_API_KEY ...).
    * Writes a machine-readable results file (eval_results.json by default).
    * Exits 0 when every metric passes its threshold, exits 1 otherwise.

Usage:
    python run_eval.py
    python run_eval.py --thresholds eval_thresholds.json --output eval_results.json
"""

from __future__ import annotations

import sys

from app.eval.run_eval import main


if __name__ == "__main__":
    sys.exit(main())
