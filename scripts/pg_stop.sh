#!/usr/bin/env bash
set -euo pipefail
PGBIN="${PGBIN:-/usr/lib/postgresql/16/bin}"
PGDATA="${PGDATA:-/var/lib/sunset-pg}"

if sudo -u postgres "$PGBIN/pg_ctl" -D "$PGDATA" status >/dev/null 2>&1; then
  sudo -u postgres "$PGBIN/pg_ctl" -D "$PGDATA" -w -t 60 -m fast stop
  echo "Cluster stopped."
else
  echo "Cluster is not running."
fi
