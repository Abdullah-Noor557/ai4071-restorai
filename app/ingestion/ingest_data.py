"""
RestorAI Knowledge-Base Ingestion (Lab 2).

Thin wrapper that delegates to the original ingestion script at the repository
root while honouring the CHROMA_DB_PATH environment variable - so the same
ingestion can be run inside the Docker image (where chroma_db lives on a
mounted volume) or on a developer laptop.

Usage:
    python -m app.ingestion.ingest_data
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(repo_root))

    # Persisted *local* Chroma dir only (HTTP Chroma via CHROMA_HOST skips this).
    chroma_path = os.getenv("CHROMA_DB_PATH")
    if chroma_path and not os.getenv("CHROMA_HOST"):
        target = Path(chroma_path).resolve()
        target.mkdir(parents=True, exist_ok=True)
        # The legacy ingest_data.py uses ``./chroma_db`` relative to CWD.
        os.chdir(target.parent)

    import ingest_data as legacy  # noqa: WPS433  (legacy script at repo root)

    if hasattr(legacy, "main"):
        legacy.main()
    else:
        ingester = legacy.RestorationDataIngestion(
            data_directory=str(repo_root / "data" / "restoration_guides"),
        )
        ingester.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
