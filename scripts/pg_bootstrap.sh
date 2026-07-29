#!/usr/bin/env bash
# Bring up a local Postgres 16 cluster with pgvector, without Docker.
#
# Why not docker-compose: this environment has the Docker CLI but no running
# daemon. Postgres 16 server binaries are installed, so we drive initdb/pg_ctl
# directly.
#
# Why every command is wrapped in `sudo -u postgres`: initdb and the postgres
# server refuse to run as uid 0. We run as root here, so the cluster is owned
# and run by the pre-existing `postgres` OS user.
#
# Idempotent. Safe to re-run.
set -euo pipefail

PGBIN="${PGBIN:-/usr/lib/postgresql/16/bin}"
PGDATA="${PGDATA:-/var/lib/sunset-pg}"
PGPORT="${SUNSET_PGPORT:-54329}"
PGSOCK="${PGSOCK:-/var/run/sunset-pg}"
PGLOG="${PGLOG:-/var/log/sunset-pg.log}"
DBNAME="${SUNSET_DBNAME:-sunset}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

say()  { printf '\033[1;36m==>\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[!] \033[0m%s\n' "$*" >&2; }
die()  { printf '\033[1;31m[x] \033[0m%s\n' "$*" >&2; exit 1; }

as_pg() { sudo -u postgres "$@"; }
psql_super() { as_pg "$PGBIN/psql" -v ON_ERROR_STOP=1 -h "$PGSOCK" -p "$PGPORT" "$@"; }

[ -x "$PGBIN/initdb" ] || die "Postgres 16 binaries not found at $PGBIN"
id postgres >/dev/null 2>&1 || die "OS user 'postgres' does not exist"

# ---------------------------------------------------------------------------
# 1. pgvector. If this fails we fall back to brute-force cosine in numpy rather
#    than aborting — at ~1,500 vectors the difference is unmeasurable.
# ---------------------------------------------------------------------------
VECTOR_BACKEND=pgvector
if dpkg -s postgresql-16-pgvector >/dev/null 2>&1; then
  say "pgvector already installed"
else
  say "Installing postgresql-16-pgvector"
  if ! (apt-get update -qq && apt-get install -y -qq postgresql-16-pgvector) >/dev/null 2>&1; then
    warn "pgvector install FAILED — falling back to SUNSET_VECTOR_BACKEND=numpy."
    warn "This is a supported degradation, not a broken build. Retrieval quality"
    warn "is identical at this scale; only the index strategy changes."
    VECTOR_BACKEND=numpy
  fi
fi

# ---------------------------------------------------------------------------
# 2. Cluster
# ---------------------------------------------------------------------------
mkdir -p "$PGSOCK" && chown postgres:postgres "$PGSOCK"
touch "$PGLOG" && chown postgres:postgres "$PGLOG"

if [ -f "$PGDATA/PG_VERSION" ]; then
  say "Cluster already initialised at $PGDATA"
else
  say "initdb -> $PGDATA"
  mkdir -p "$PGDATA" && chown postgres:postgres "$PGDATA" && chmod 700 "$PGDATA"
  as_pg "$PGBIN/initdb" -D "$PGDATA" -U postgres \
    --auth-local=trust --auth-host=trust --encoding=UTF8 --locale=C >/dev/null
fi

if as_pg "$PGBIN/pg_ctl" -D "$PGDATA" status >/dev/null 2>&1; then
  say "Cluster already running"
else
  say "Starting cluster on port $PGPORT"
  as_pg "$PGBIN/pg_ctl" -D "$PGDATA" -l "$PGLOG" -w -t 60 \
    -o "-p $PGPORT -k $PGSOCK -c listen_addresses=127.0.0.1" start \
    || { warn "pg_ctl start failed; last 40 lines of $PGLOG:"; tail -40 "$PGLOG" >&2; exit 1; }
fi

# ---------------------------------------------------------------------------
# 3. Database + extension
# ---------------------------------------------------------------------------
if psql_super -tAc "SELECT 1 FROM pg_database WHERE datname='$DBNAME'" postgres | grep -q 1; then
  say "Database '$DBNAME' exists"
else
  say "Creating database '$DBNAME'"
  as_pg "$PGBIN/createdb" -h "$PGSOCK" -p "$PGPORT" "$DBNAME"
fi

if [ "$VECTOR_BACKEND" = "pgvector" ]; then
  if psql_super -q -c "CREATE EXTENSION IF NOT EXISTS vector;" "$DBNAME" 2>/dev/null; then
    say "vector extension ready"
  else
    warn "CREATE EXTENSION vector failed — falling back to numpy backend"
    VECTOR_BACKEND=numpy
  fi
fi

# ---------------------------------------------------------------------------
# 4. Roles + schema. roles.sql is what actually enforces ground-truth isolation.
# ---------------------------------------------------------------------------
say "Applying roles.sql (ground-truth isolation)"
psql_super -q -f "$REPO_ROOT/db/roles.sql" "$DBNAME"

say "Applying schema.sql"
PGVECTOR_ON="$VECTOR_BACKEND" psql_super -q \
  -v vector_backend="$VECTOR_BACKEND" -f "$REPO_ROOT/db/schema.sql" "$DBNAME"

if [ -f "$REPO_ROOT/db/indexes.sql" ]; then
  say "Applying indexes.sql"
  psql_super -q -v vector_backend="$VECTOR_BACKEND" -f "$REPO_ROOT/db/indexes.sql" "$DBNAME"
fi

# ---------------------------------------------------------------------------
# 5. Health check — prove a vector round-trips before declaring success.
# ---------------------------------------------------------------------------
if [ "$VECTOR_BACKEND" = "pgvector" ]; then
  say "Health check: 768-d cosine round-trip"
  psql_super -q "$DBNAME" >/dev/null <<'SQL'
CREATE TEMP TABLE _vhealth (id int, v vector(768));
INSERT INTO _vhealth VALUES (1, (SELECT ('[' || string_agg('0.1', ',') || ']')::vector
                                 FROM generate_series(1, 768)));
SELECT id, v <=> v AS self_distance FROM _vhealth;
SQL
fi

# ---------------------------------------------------------------------------
# 6. Record the resolved backend so the app and tests agree with reality.
# ---------------------------------------------------------------------------
if [ ! -f "$REPO_ROOT/.env" ]; then
  say "Creating .env from .env.example"
  cp "$REPO_ROOT/.env.example" "$REPO_ROOT/.env"
fi
if grep -q '^SUNSET_VECTOR_BACKEND=' "$REPO_ROOT/.env"; then
  sed -i "s/^SUNSET_VECTOR_BACKEND=.*/SUNSET_VECTOR_BACKEND=$VECTOR_BACKEND/" "$REPO_ROOT/.env"
else
  echo "SUNSET_VECTOR_BACKEND=$VECTOR_BACKEND" >> "$REPO_ROOT/.env"
fi

say "Ready. backend=$VECTOR_BACKEND port=$PGPORT db=$DBNAME"
