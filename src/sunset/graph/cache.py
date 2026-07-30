"""The (feature_id, evidence_hash) auditor cache — spec §9.3's token lever.

Kept in its own table, NOT in the LangGraph checkpointer: checkpoints are
thread-scoped, so they cannot serve reuse across runs, which is the whole point.
Including prompt_version in the key means editing a downstream prompt (say the
composer's) costs zero auditor tokens on the next full run.
"""

from __future__ import annotations

import hashlib


def cache_key(feature_id: str, evidence_hash: str, auditor: str,
              prompt_version: str, model_id: str) -> str:
    raw = f"{feature_id}|{evidence_hash}|{auditor}|{prompt_version}|{model_id}"
    return hashlib.sha256(raw.encode()).hexdigest()


def cache_get(conn, key: str) -> dict | None:
    with conn.cursor() as cur:
        cur.execute("SELECT output_json FROM auditor_cache WHERE cache_key = %s", (key,))
        row = cur.fetchone()
    return row[0] if row else None


def cache_put(conn, key: str, *, feature_id: str, evidence_hash: str, auditor: str,
              prompt_version: str, model_id: str, output_json: dict,
              prompt_tokens: int, output_tokens: int) -> None:
    import json

    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO auditor_cache (cache_key, feature_id, evidence_hash, auditor, "
            "prompt_version, model_id, output_json, prompt_tokens, output_tokens) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (cache_key) DO NOTHING",
            (key, feature_id, evidence_hash, auditor, prompt_version, model_id,
             json.dumps(output_json), prompt_tokens, output_tokens),
        )
    conn.commit()


def cache_invalidate(conn, feature_id: str, auditor: str) -> int:
    """Drop one auditor's cache for a feature — used by a 'fact' override so a
    resume re-runs exactly that auditor, not all four."""
    with conn.cursor() as cur:
        cur.execute(
            "DELETE FROM auditor_cache WHERE feature_id = %s AND auditor = %s",
            (feature_id, auditor),
        )
        n = cur.rowcount
    conn.commit()
    return n
