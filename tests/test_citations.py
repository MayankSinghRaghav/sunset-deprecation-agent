"""Citation validation is the wall between the agent and a hallucinated fact. These
tests prove real refs resolve and fabricated ones are rejected."""

from __future__ import annotations

import psycopg
import pytest

from sunset.config import settings
from sunset.evidence.refs import resolve
from sunset.schemas import EvidenceRef
from tests.conftest import requires_db


def _dsn():
    return settings.database_url.replace("postgresql+psycopg://", "postgresql://")


@pytest.fixture(scope="module")
def conn():
    c = psycopg.connect(_dsn())
    yield c
    c.close()


@requires_db
def test_valid_text_span_resolves(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT id, text FROM contract_clauses LIMIT 1")
        cid, text = cur.fetchone()
    ref = EvidenceRef(ref_id="e1", source_table="contract_clauses", source_id=cid,
                      claim_text="x", quoted_span=text[:40])
    ok, err = resolve(conn, ref)
    assert ok, err


@requires_db
def test_fabricated_span_is_rejected(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM contract_clauses LIMIT 1")
        cid = cur.fetchone()[0]
    ref = EvidenceRef(ref_id="e2", source_table="contract_clauses", source_id=cid,
                      claim_text="x", quoted_span="this text is definitely not in the clause")
    ok, err = resolve(conn, ref)
    assert not ok and "substring" in err


@requires_db
def test_missing_source_row_is_rejected(conn):
    ref = EvidenceRef(ref_id="e3", source_table="deal_notes", source_id="nope",
                      claim_text="x", quoted_span=None)
    ok, err = resolve(conn, ref)
    assert not ok


@requires_db
def test_usage_data_ref_resolves(conn):
    ref = EvidenceRef(ref_id="e4", source_table="usage_daily", source_id="f08",
                      claim_text="usage", quoted_span=None)
    ok, _ = resolve(conn, ref)
    assert ok
