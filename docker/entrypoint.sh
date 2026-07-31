#!/usr/bin/env bash
# Backend container entrypoint. Idempotently brings the database up to a served
# state, then runs the API. Safe to run on every container start: each step is
# guarded so a restart re-uses the existing schema, fixtures, and audit run.
#
#   1. wait for Postgres
#   2. CREATE EXTENSION vector; apply roles / schema / indexes
#   3. seed the committed fixtures if the DB is empty
#   4. run the offline pipeline once so the API has real audit data to serve
#   5. exec uvicorn
#
# The offline pipeline needs no API key; set SUNSET_LLM_MODE=live + GEMINI_API_KEY
# to populate a real model run instead (see DEPLOY.md).
set -euo pipefail

: "${DATABASE_URL:?DATABASE_URL is required (Railway injects it when a Postgres service is attached)}"

# psql/pg_isready want a plain postgresql:// scheme, not the +psycopg driver form.
PSQL_DSN="${DATABASE_URL/postgresql+psycopg:/postgresql:}"
PSQL_DSN="${PSQL_DSN/postgres:\/\//postgresql://}"
PORT="${PORT:-8000}"

echo "==> waiting for Postgres"
for i in $(seq 1 60); do
  if pg_isready -d "$PSQL_DSN" >/dev/null 2>&1; then break; fi
  echo "   ... not ready yet ($i)"; sleep 2
done
pg_isready -d "$PSQL_DSN" >/dev/null 2>&1 || { echo "Postgres never became ready"; exit 1; }

# Detect pgvector. The schema stores embeddings as vector(768) when the
# extension is available and real[] otherwise, so the runtime vector backend
# must match: pgvector (HNSW cosine) if present, numpy (brute force over ~1,500
# vectors) if not. Either works — the numpy path needs no extension at all.
if psql "$PSQL_DSN" -q -c "CREATE EXTENSION IF NOT EXISTS vector;" >/dev/null 2>&1; then
  VB="pgvector"
else
  echo "==> pgvector not available on this database — using the numpy backend"
  VB="numpy"
fi
export SUNSET_VECTOR_BACKEND="$VB"

echo "==> roles + schema + indexes (vector_backend=$VB)"
psql "$PSQL_DSN" -v ON_ERROR_STOP=1 -q -f db/roles.sql
psql "$PSQL_DSN" -v ON_ERROR_STOP=1 -v vector_backend="$VB" -q -f db/schema.sql
psql "$PSQL_DSN" -v ON_ERROR_STOP=1 -v vector_backend="$VB" -q -f db/indexes.sql

FEATURES="$(psql "$PSQL_DSN" -tAc "SELECT count(*) FROM features;" 2>/dev/null || echo 0)"
if [ "${FEATURES:-0}" -lt 1 ]; then
  echo "==> seeding committed fixtures"
  python -m datagen.load_fixtures
else
  echo "==> fixtures already present ($FEATURES features) — skipping seed"
fi

COMPLETED="$(psql "$PSQL_DSN" -tAc "SELECT count(*) FROM audit_runs WHERE status='completed';" 2>/dev/null || echo 0)"
if [ "${COMPLETED:-0}" -lt 1 ]; then
  echo "==> running the pipeline once (mode=${SUNSET_LLM_MODE:-offline})"
  python -m sunset.runner --all
else
  echo "==> a completed audit run already exists — skipping pipeline"
fi

echo "==> starting API on :$PORT"
exec uvicorn sunset.api.app:app --host 0.0.0.0 --port "$PORT"
