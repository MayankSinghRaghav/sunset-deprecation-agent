"""Populate embeddings for the evidence tables.

Default (keyless): the hashing embedder, so retrieval works offline with no key.
`make seed` calls embed_all with it after loading fixtures.

With a key: `make embed` uses the Gemini embedder and also writes the vectors to a
committed fixture (db/fixtures/100_embeddings_gemini.jsonl.zst) so every later
clone — CI, another machine, a reviewer with no key — gets real semantic
retrieval without a network call. That committed export is the single highest-
leverage mitigation for huggingface.co being blocked.
"""

from __future__ import annotations

import io
import json

import psycopg
import zstandard as zstd

from sunset.config import settings
from sunset.evidence.retrieval import TEXT_COLUMN

FIX_EXPORT = "db/fixtures/100_embeddings_gemini.jsonl.zst"


def _dsn() -> str:
    return settings.database_url.replace("postgresql+psycopg://", "postgresql://")


def _vec_literal(v) -> str:
    return "[" + ",".join(f"{x:.6f}" for x in v) + "]"


def embed_all(conn, embedder) -> dict[str, int]:
    counts: dict[str, int] = {}
    use_vector = settings.vector_backend == "pgvector"
    for table, col in TEXT_COLUMN.items():
        with conn.cursor() as cur:
            cur.execute(f"SELECT id, {col} FROM {table} ORDER BY id")
            rows = cur.fetchall()
        ids = [r[0] for r in rows]
        vecs = embedder.embed([r[1] for r in rows])
        with conn.cursor() as cur:
            for rid, vec in zip(ids, vecs, strict=True):
                if use_vector:
                    cur.execute(
                        f"UPDATE {table} SET embedding = %s::vector, embedding_model = %s "
                        f"WHERE id = %s",
                        (_vec_literal(vec), embedder.model_id, rid),
                    )
                else:
                    cur.execute(
                        f"UPDATE {table} SET embedding = %s, embedding_model = %s "
                        f"WHERE id = %s",
                        (list(vec), embedder.model_id, rid),
                    )
        counts[table] = len(ids)
    conn.commit()
    return counts


def export_fixture(conn, model_id: str) -> None:
    """Write committed vectors so a keyless clone gets real semantic retrieval."""
    lines: list[str] = []
    for table, _col in TEXT_COLUMN.items():
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT id, embedding FROM {table} "
                f"WHERE embedding_model = %s ORDER BY id",
                (model_id,),
            )
            for rid, emb in cur.fetchall():
                vec = emb if isinstance(emb, list) else [
                    float(x) for x in str(emb).strip("[]").split(",") if x
                ]
                lines.append(json.dumps({"t": table, "id": rid, "v": vec}))
    raw = ("\n".join(lines) + "\n").encode()
    comp = zstd.ZstdCompressor(level=19).compress(raw)
    with open(FIX_EXPORT, "wb") as f:
        f.write(comp)


def load_fixture(conn) -> int:
    """Load committed Gemini vectors (if the fixture exists) into the DB."""
    import os

    if not os.path.exists(FIX_EXPORT):
        return 0
    raw = zstd.ZstdDecompressor().decompress(open(FIX_EXPORT, "rb").read()).decode()
    use_vector = settings.vector_backend == "pgvector"
    n = 0
    with conn.cursor() as cur:
        for line in io.StringIO(raw):
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            val = _vec_literal(rec["v"]) if use_vector else rec["v"]
            cast = "%s::vector" if use_vector else "%s"
            cur.execute(
                f"UPDATE {rec['t']} SET embedding = {cast}, "
                f"embedding_model = %s WHERE id = %s",
                (val, settings.embedding_model, rec["id"]),
            )
            n += 1
    conn.commit()
    return n


def main() -> None:
    from sunset.providers.embeddings import GeminiEmbeddingProvider

    embedder = GeminiEmbeddingProvider()
    with psycopg.connect(_dsn()) as conn:
        counts = embed_all(conn, embedder)
        export_fixture(conn, embedder.model_id)
    print("Embedded (Gemini):", counts, "-> exported", FIX_EXPORT)


if __name__ == "__main__":
    main()
