"""Shared fixtures and DB availability gating."""

from __future__ import annotations

import os

import pytest
from sqlalchemy import create_engine, text

APP_URL = os.environ.get(
    "SUNSET_DATABASE_URL",
    "postgresql+psycopg://sunset_app:sunset_app@127.0.0.1:54329/sunset",
)


def _db_available() -> bool:
    try:
        eng = create_engine(APP_URL, connect_args={"connect_timeout": 2})
        with eng.connect() as c:
            c.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


DB_AVAILABLE = _db_available()

requires_db = pytest.mark.skipif(
    not DB_AVAILABLE,
    reason="no Postgres cluster reachable — run `make db-up`",
)


@pytest.fixture(scope="session")
def app_engine():
    return create_engine(APP_URL, future=True)
