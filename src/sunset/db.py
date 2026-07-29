"""Engine and session management.

Sync SQLAlchemy on psycopg3. The app connects as `sunset_app`; the scoring
harness (eval/) is the only caller that may use the `sunset_eval` engine, and it
imports `eval_engine` explicitly so the boundary is visible in a grep.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from sunset.config import settings

_engine: Engine | None = None
_Session: sessionmaker[Session] | None = None


def get_engine() -> Engine:
    global _engine, _Session
    if _engine is None:
        _engine = create_engine(
            settings.database_url,
            pool_pre_ping=True,
            future=True,
        )
        _Session = sessionmaker(bind=_engine, expire_on_commit=False, future=True)
    return _engine


def get_sessionmaker() -> sessionmaker[Session]:
    get_engine()
    assert _Session is not None
    return _Session


@contextmanager
def session_scope() -> Iterator[Session]:
    """Transactional session. Commits on success, rolls back on error."""
    sm = get_sessionmaker()
    s = sm()
    try:
        yield s
        s.commit()
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()


def eval_engine() -> Engine:
    """Engine bound to the sunset_eval role. eval/ only. Never import from src/sunset."""
    return create_engine(settings.eval_database_url, pool_pre_ping=True, future=True)
