"""PostgresSaver setup.

The checkpointer is why LangGraph earns its place (spec §9.1): without the
human-review gate, plain async Python would do. It persists into the `checkpoints`
schema in the same cluster — no Redis, no new infrastructure — and it survives a
process restart, which matters because a feature can sit at AWAITING_REVIEW across
an API restart.
"""

from __future__ import annotations

from contextlib import contextmanager

from sunset.config import settings


def _saver_dsn() -> str:
    dsn = settings.database_url.replace("postgresql+psycopg://", "postgresql://")
    # keep the checkpoint tables in their own schema
    sep = "&" if "?" in dsn else "?"
    return f"{dsn}{sep}options=-csearch_path%3Dcheckpoints,public"


@contextmanager
def checkpointer():
    from langgraph.checkpoint.postgres import PostgresSaver

    with PostgresSaver.from_conn_string(_saver_dsn()) as cp:
        cp.setup()  # idempotent: creates the checkpoint tables if absent
        yield cp
