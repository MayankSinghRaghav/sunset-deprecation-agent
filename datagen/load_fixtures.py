"""`make seed` — load committed fixtures into the database. Keyless, no network."""

from __future__ import annotations

import json

import psycopg

from datagen.fixtures_io import load_fixtures
from sunset.config import settings


def _dsn() -> str:
    # psycopg wants a libpq DSN, not the SQLAlchemy URL.
    return settings.database_url.replace("postgresql+psycopg://", "postgresql://")


def main() -> None:
    with psycopg.connect(_dsn()) as conn:
        counts = load_fixtures(conn)
    print("Loaded:", json.dumps(counts, indent=2))


if __name__ == "__main__":
    main()
