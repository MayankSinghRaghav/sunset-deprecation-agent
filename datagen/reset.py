"""`make db-reset` helper — truncate all evidence + audit tables."""

from __future__ import annotations

import psycopg

from sunset.config import settings

TABLES = [
    "usage_daily", "support_tickets", "contract_clauses", "contracts",
    "deal_notes", "feature_dependencies", "evidence_refs", "human_overrides",
    "feature_audits", "audit_runs", "llm_calls", "auditor_cache", "features",
    "accounts",
]


def _dsn() -> str:
    return settings.database_url.replace("postgresql+psycopg://", "postgresql://")


def main() -> None:
    with psycopg.connect(_dsn()) as conn, conn.cursor() as cur:
        cur.execute("TRUNCATE " + ", ".join(TABLES) + " RESTART IDENTITY CASCADE;")
        conn.commit()
    print("All evidence and audit tables truncated.")


if __name__ == "__main__":
    main()
