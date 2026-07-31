# Sunset backend — FastAPI + the LangGraph pipeline.
# Multi-stage: install deps with uv, then a slim runtime with a psql client for
# the schema/seed steps in docker/entrypoint.sh.
FROM python:3.11-slim AS base

# psql + pg_isready (schema apply, readiness, guards) and certs for outbound TLS.
RUN apt-get update \
    && apt-get install -y --no-install-recommends postgresql-client ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# uv, pinned by digestless tag; copied from the official image.
COPY --from=ghcr.io/astral-sh/uv:0.8.17 /uv /uvx /bin/

WORKDIR /app
ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src:/app

# Dependency layer (cached until the lockfile changes).
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Application.
COPY . .
RUN uv sync --frozen --no-dev
ENV PATH="/app/.venv/bin:$PATH"

# Hosted-demo defaults: the offline pipeline needs no API key. Override
# SUNSET_LLM_MODE=live + GEMINI_API_KEY for a real model run.
ENV SUNSET_LLM_MODE=offline \
    SUNSET_EMBEDDING_MODEL=hashing-v1 \
    SUNSET_VECTOR_BACKEND=pgvector \
    SUNSET_CORS_ORIGINS=* \
    PORT=8000

RUN chmod +x docker/entrypoint.sh
EXPOSE 8000
CMD ["docker/entrypoint.sh"]
