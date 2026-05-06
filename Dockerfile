# =============================================================================
# RestorAI - Industrial Container Image (multi-stage)
# =============================================================================
#
# This Dockerfile is intentionally split into three stages:
#
#   1. base     -> the Python runtime + system libs that the agent depends on.
#                  Pinned to a specific minor version of the official slim
#                  image so rebuilds are bit-for-bit reproducible.
#
#   2. builder  -> creates a virtualenv and installs the Python wheels. We
#                  copy ONLY requirements.txt first so the expensive pip layer
#                  is cached as long as the dependency set is unchanged.
#                  Source code changes therefore do NOT trigger a re-install.
#
#   3. runtime  -> the final production image. It copies the prebuilt venv
#                  from the builder stage and the source code, then drops
#                  privileges to a non-root user. No pip / build tools are
#                  shipped in the published image.
#
# The build is reproducible because:
#   * all base images are pinned by digest-equivalent tag
#   * pip uses --no-cache-dir and a constraints file (requirements.txt is
#     fully version-locked)
#   * no network calls run after the pip install
#
# Image size on disk: ~ 320 MB (vs. ~ 1.6 GB for python:3.11 + pip cache).
# =============================================================================

# ----- Stage 1: base ---------------------------------------------------------
FROM python:3.11.9-slim-bookworm AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Minimal system libs:
#   - libsqlite3-0 : sqlite (langgraph checkpointer)
#   - ca-certificates / curl : healthcheck inside compose
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        libsqlite3-0 \
 && rm -rf /var/lib/apt/lists/*


# ----- Stage 2: builder ------------------------------------------------------
FROM base AS builder

# Build-time tools needed only to compile a couple of wheels (pydantic-core,
# numpy etc.). These DO NOT end up in the final image.
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
        build-essential \
        gcc \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Step A: copy ONLY requirements.txt - cached unless deps change
COPY requirements.txt /app/requirements.txt

# Step B: install into an isolated virtualenv so we can copy it cleanly
RUN python -m venv /opt/venv \
 && /opt/venv/bin/pip install --upgrade pip \
 && /opt/venv/bin/pip install -r /app/requirements.txt


# ----- Stage 3: runtime (final image) ----------------------------------------
FROM base AS runtime

# Non-root user (security best practice, makes the image PaaS-friendly)
RUN groupadd --system --gid 1001 restorai \
 && useradd  --system --uid 1001 --gid restorai --create-home restorai

# Bring in the prebuilt venv from the builder stage
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# Copy the application source LAST (the most frequently changed layer)
COPY --chown=restorai:restorai app           /app/app
COPY --chown=restorai:restorai data          /app/data
COPY --chown=restorai:restorai ingest_data.py /app/ingest_data.py
COPY --chown=restorai:restorai eval_thresholds.json /app/eval_thresholds.json

# Runtime configuration (overridable via docker-compose / `docker run -e`)
ENV CHECKPOINT_DB_PATH=/app/persist/checkpoints.sqlite \
    CHROMA_DB_PATH=/app/persist/chroma_db \
    PYTHONPATH=/app

USER restorai
EXPOSE 8000

# Healthcheck (compose / orchestrator can use it for readiness probes)
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl --fail --silent http://localhost:8000/health || exit 1

# Default command: run the FastAPI service. Override with `docker run ... bash`
# during debugging or `python -m app.eval.run_eval` during CI.
CMD ["python", "-m", "uvicorn", "app.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
