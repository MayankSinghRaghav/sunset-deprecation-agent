#!/usr/bin/env bash
# Environment preflight. Prints a green/red table and exits non-zero if any
# hard requirement is missing.
set -uo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

PGPORT="${SUNSET_PGPORT:-54329}"
PGHOST=127.0.0.1
fail=0

ok()   { printf '  \033[1;32m✓\033[0m %s\n' "$*"; }
bad()  { printf '  \033[1;31m✗\033[0m %s\n' "$*"; fail=1; }
note() { printf '  \033[1;33m•\033[0m %s\n' "$*"; }

echo "Sunset doctor"
echo "-------------"

# Load .env if present (for SUNSET_LLM_MODE / SUNSET_VECTOR_BACKEND).
[ -f .env ] && set -a && . ./.env && set +a

# Toolchain
command -v uv >/dev/null 2>&1 && ok "uv $(uv --version | awk '{print $2}')" || bad "uv not found"
[ -d .venv ] && ok "virtualenv present" || note ".venv missing — run: make install"

# Postgres cluster
if pg_isready -h "$PGHOST" -p "$PGPORT" -q 2>/dev/null; then
  ok "Postgres reachable on $PGHOST:$PGPORT"
else
  bad "Postgres not reachable on $PGHOST:$PGPORT — run: make db-up"
fi

# Schema + isolation, via the app role
APP_URL="postgresql://sunset_app:sunset_app@$PGHOST:$PGPORT/sunset"
tables=$(psql "$APP_URL" -tAc \
  "SELECT count(*) FROM pg_tables WHERE schemaname='public'" 2>/dev/null)
if [ "${tables:-0}" -ge 14 ]; then
  ok "schema applied ($tables public tables)"
else
  bad "schema missing (found ${tables:-0} tables) — run: make db-up"
fi

if psql "$APP_URL" -c "SELECT 1 FROM truth.ground_truth LIMIT 1" >/dev/null 2>&1; then
  bad "ISOLATION BREACH: sunset_app can read schema truth"
else
  ok "ground-truth isolation holds (sunset_app denied on schema truth)"
fi

# Vector backend
backend="${SUNSET_VECTOR_BACKEND:-pgvector}"
if [ "$backend" = "pgvector" ]; then
  if psql "$APP_URL" -tAc "SELECT '[1,0]'::vector <=> '[0,1]'::vector" >/dev/null 2>&1; then
    ok "pgvector cosine round-trip"
  else
    bad "SUNSET_VECTOR_BACKEND=pgvector but vector ops fail"
  fi
else
  note "vector backend = numpy (brute-force cosine; supported degradation)"
fi

# Provider mode
mode="${SUNSET_LLM_MODE:-offline}"
case "$mode" in
  offline) note "LLM mode = offline (deterministic stub; no accuracy headline)";;
  replay)  note "LLM mode = replay (cassettes)";;
  live)    [ -n "${GEMINI_API_KEY:-}" ] && ok "LLM mode = live (key present)" \
             || bad "LLM mode = live but GEMINI_API_KEY is empty";;
  *)       bad "unknown SUNSET_LLM_MODE=$mode";;
esac

echo "-------------"
if [ "$fail" -eq 0 ]; then
  printf '\033[1;32mAll green.\033[0m\n'
else
  printf '\033[1;31mSome checks failed.\033[0m See above.\n'
fi
exit $fail
