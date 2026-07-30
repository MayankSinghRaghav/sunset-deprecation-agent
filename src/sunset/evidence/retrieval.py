"""Semantic retrieval over the embedded evidence tables.

Two interchangeable backends behind one protocol, selected by
SUNSET_VECTOR_BACKEND:

- PgVectorIndex — pgvector's `<=>` cosine operator with an HNSW index.
- NumpyIndex — load the (~1,500) vectors for a table and brute-force cosine in
  Python. At this scale it is sub-millisecond, so the project keeps working even
  if the pgvector apt install failed.

Every query filters `embedding_model = <current>` so a hashing vector can never be
cosine-compared against a Gemini one.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from sunset.config import settings

# text column per embeddable table
TEXT_COLUMN = {
    "support_tickets": "body",
    "contract_clauses": "text",
    "deal_notes": "body",
}


@dataclass
class Hit:
    source_id: str
    text: str
    score: float  # cosine similarity in [-1, 1]


class VectorIndex(Protocol):
    def search(
        self, query_vec: list[float], table: str, top_k: int,
        where: str | None = None, params: tuple = (),
    ) -> list[Hit]: ...


def _vec_literal(v: list[float]) -> str:
    return "[" + ",".join(f"{x:.6f}" for x in v) + "]"


class PgVectorIndex:
    def __init__(self, conn, model_id: str):
        self.conn = conn
        self.model_id = model_id

    def search(self, query_vec, table, top_k, where=None, params=()):
        text_col = TEXT_COLUMN[table]
        extra = f" AND ({where})" if where else ""
        sql = (
            f"SELECT id, {text_col}, 1 - (embedding <=> %s::vector) AS score "
            f"FROM {table} "
            f"WHERE embedding IS NOT NULL AND embedding_model = %s{extra} "
            f"ORDER BY embedding <=> %s::vector LIMIT %s"
        )
        lit = _vec_literal(query_vec)
        args = (lit, self.model_id, *params, lit, top_k)
        with self.conn.cursor() as cur:
            cur.execute(sql, args)
            return [Hit(r[0], r[1], float(r[2])) for r in cur.fetchall()]


class NumpyIndex:
    def __init__(self, conn, model_id: str):
        import numpy as np

        self.np = np
        self.conn = conn
        self.model_id = model_id
        self._cache: dict[str, tuple] = {}

    def _load(self, table: str, where: str | None, params: tuple):
        key = f"{table}|{where}|{params}"
        if key in self._cache:
            return self._cache[key]
        text_col = TEXT_COLUMN[table]
        extra = f" AND ({where})" if where else ""
        sql = (
            f"SELECT id, {text_col}, embedding FROM {table} "
            f"WHERE embedding IS NOT NULL AND embedding_model = %s{extra}"
        )
        with self.conn.cursor() as cur:
            cur.execute(sql, (self.model_id, *params))
            rows = cur.fetchall()
        ids = [r[0] for r in rows]
        texts = [r[1] for r in rows]
        mat = self.np.array([_parse_vec(r[2]) for r in rows], dtype="float32") if rows \
            else self.np.zeros((0, settings.embedding_dim), dtype="float32")
        self._cache[key] = (ids, texts, mat)
        return ids, texts, mat

    def search(self, query_vec, table, top_k, where=None, params=()):
        ids, texts, mat = self._load(table, where, params)
        if len(ids) == 0:
            return []
        q = self.np.array(query_vec, dtype="float32")
        qn = q / (self.np.linalg.norm(q) or 1.0)
        mn = mat / (self.np.linalg.norm(mat, axis=1, keepdims=True) + 1e-9)
        scores = mn @ qn
        order = self.np.argsort(-scores)[:top_k]
        return [Hit(ids[i], texts[i], float(scores[i])) for i in order]


def _parse_vec(v):
    # pgvector returns a str like "[0.1,0.2,...]"; real[] returns a list.
    if isinstance(v, str):
        return [float(x) for x in v.strip("[]").split(",") if x]
    return list(v)


def get_index(conn, model_id: str) -> VectorIndex:
    if settings.vector_backend == "numpy":
        return NumpyIndex(conn, model_id)
    return PgVectorIndex(conn, model_id)
