"""Shared API helpers: a psycopg connection per request, and small readers."""

from __future__ import annotations

from collections.abc import Iterator

import psycopg

from sunset.config import settings


def dsn() -> str:
    return settings.database_url.replace("postgresql+psycopg://", "postgresql://")


def get_conn() -> Iterator[psycopg.Connection]:
    conn = psycopg.connect(dsn())
    try:
        yield conn
    finally:
        conn.close()


def dict_rows(cur) -> list[dict]:
    cols = [c.name for c in cur.description]
    return [dict(zip(cols, row, strict=True)) for row in cur.fetchall()]
