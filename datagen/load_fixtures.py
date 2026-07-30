"""`make seed` — load committed fixtures into the database. Keyless, no network."""

from __future__ import annotations

import json
import os

import psycopg

from datagen.embed import embed_all, load_fixture
from datagen.fixtures_io import load_fixtures
from sunset.config import settings
from sunset.providers.embeddings import HashingEmbeddingProvider

FIX_EXPORT = "db/fixtures/100_embeddings_gemini.jsonl.zst"


def _dsn() -> str:
    # psycopg wants a libpq DSN, not the SQLAlchemy URL.
    return settings.database_url.replace("postgresql+psycopg://", "postgresql://")


def main() -> None:
    with psycopg.connect(_dsn()) as conn:
        counts = load_fixtures(conn)
        # embeddings: prefer committed Gemini vectors when present and we are in a
        # matching mode; otherwise fall back to the keyless hashing embedder so
        # retrieval always works.
        loaded = 0
        if os.path.exists(FIX_EXPORT) and settings.embedding_model != "hashing-v1":
            loaded = load_fixture(conn)
        if loaded:
            counts["embeddings"] = f"{loaded} (committed {settings.embedding_model})"
        else:
            emb = embed_all(conn, HashingEmbeddingProvider())
            counts["embeddings"] = f"{sum(emb.values())} (hashing, keyless)"
    print("Loaded:", json.dumps(counts, indent=2))


if __name__ == "__main__":
    main()
