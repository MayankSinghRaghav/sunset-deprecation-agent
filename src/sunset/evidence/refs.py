"""Evidence references: mint them, resolve them, verify the quoted span.

This is the table that separates Sunset from a summarisation demo (spec §6). Two
kinds of ref:

- TEXT refs (contract_clauses, support_tickets, deal_notes) carry a quoted span
  that MUST be a normalised substring of the source row's text. That is what makes
  a citation checkable rather than decorative.
- DATA refs (usage_daily, features, feature_dependencies, accounts) point at a row
  whose existence is the evidence — a computed statistic has no quotable span, so
  we verify the row resolves and leave the span null.

A ref that cannot be resolved fails the run loudly; a hallucinated citation must
never reach the UI.
"""

from __future__ import annotations

import re
import uuid

from sunset.schemas import EvidenceRef

TEXT_TABLES = {
    "contract_clauses": ("text", "id"),
    "support_tickets": ("body", "id"),
    "deal_notes": ("body", "id"),
}
DATA_TABLES = {
    "features": "id",
    "accounts": "id",
    "usage_daily": None,  # composite key, encoded in source_id as f:a:day:actor
    "feature_dependencies": None,
}


def new_ref_id() -> str:
    return f"ev_{uuid.uuid4().hex[:12]}"


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip().lower()


def resolve(conn, ref: EvidenceRef) -> tuple[bool, str | None]:
    """Return (resolved, error). Verifies existence and, for text refs, the span."""
    table = ref.source_table
    if table in TEXT_TABLES:
        text_col, id_col = TEXT_TABLES[table]
        with conn.cursor() as cur:
            cur.execute(f"SELECT {text_col} FROM {table} WHERE {id_col} = %s", (ref.source_id,))
            row = cur.fetchone()
        if not row:
            return False, f"{table} id {ref.source_id} not found"
        if ref.quoted_span:
            if _norm(ref.quoted_span) not in _norm(row[0]):
                return False, "quoted span is not a substring of the source text"
        return True, None

    if table == "usage_daily":
        return _resolve_usage(conn, ref.source_id)
    if table == "feature_dependencies":
        return _resolve_dep(conn, ref.source_id)
    if table in DATA_TABLES:
        with conn.cursor() as cur:
            cur.execute(f"SELECT 1 FROM {table} WHERE id = %s", (ref.source_id,))
            if not cur.fetchone():
                return False, f"{table} id {ref.source_id} not found"
        return True, None
    return False, f"unknown source_table {table}"


def _resolve_usage(conn, source_id: str) -> tuple[bool, str | None]:
    # source_id encodes feature_id (aggregate claim) — verify the feature has usage.
    fid = source_id.split(":")[0]
    with conn.cursor() as cur:
        cur.execute("SELECT 1 FROM usage_daily WHERE feature_id = %s LIMIT 1", (fid,))
        return (bool(cur.fetchone()), None) if cur.rowcount != 0 else (False, "no usage rows")


def _resolve_dep(conn, source_id: str) -> tuple[bool, str | None]:
    try:
        frm, to = source_id.split("->")
    except ValueError:
        return False, "malformed dependency ref"
    with conn.cursor() as cur:
        cur.execute(
            "SELECT 1 FROM feature_dependencies WHERE from_feature_id=%s AND to_feature_id=%s",
            (frm, to),
        )
        return (bool(cur.fetchone()), None)


def clip_span(text: str, max_len: int = 140) -> str:
    """A verbatim leading slice of a source text, safe to use as a quoted span."""
    return text[:max_len]
