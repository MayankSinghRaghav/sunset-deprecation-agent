"""Embedding providers.

The environment blocks huggingface.co, so `bge-small-en-v1.5` (spec §9.1) cannot
be downloaded here. Two providers cover the gap:

- HashingEmbeddingProvider — deterministic feature hashing. Zero deps, no network,
  no key. It is explicitly NOT semantic: it will underperform on the capability-
  language retrieval (trap 1) and deal-note retrieval (trap 7). That floor is
  recorded honestly rather than hidden. It is the default so the whole system
  runs keyless.
- GeminiEmbeddingProvider — the real semantic embedder, used in live mode and to
  produce the committed vector fixtures.

SentenceTransformerProvider is written and lazily imported as the documented path
for environments where huggingface.co is reachable; it is untested here.
"""

from __future__ import annotations

import hashlib
import math
import re

from sunset.config import settings

_TOKEN = re.compile(r"[a-z0-9]+")


class HashingEmbeddingProvider:
    model_id = "hashing-v1"
    dim = 768

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._one(t) for t in texts]

    def _one(self, text: str) -> list[float]:
        vec = [0.0] * self.dim
        words = _TOKEN.findall(text.lower())
        # word unigrams + word bigrams + char 3-grams, signed hashing
        grams: list[str] = list(words)
        grams += [f"{a}_{b}" for a, b in zip(words, words[1:], strict=False)]
        joined = " ".join(words)
        grams += [joined[i : i + 3] for i in range(max(0, len(joined) - 2))]
        for g in grams:
            h = int(hashlib.md5(g.encode()).hexdigest(), 16)
            idx = h % self.dim
            sign = 1.0 if (h >> 20) & 1 else -1.0
            vec[idx] += sign
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]


class GeminiEmbeddingProvider:
    def __init__(self):
        self.model_id = settings.embedding_model
        self.dim = settings.embedding_dim
        if not settings.gemini_api_key:
            from sunset.errors import ProviderConfigError

            raise ProviderConfigError("GEMINI_API_KEY required for Gemini embeddings")
        from google import genai

        self._client = genai.Client(api_key=settings.gemini_api_key)

    def embed(self, texts: list[str]) -> list[list[float]]:
        out: list[list[float]] = []
        # Gemini's embed endpoint takes batches; keep them modest.
        for i in range(0, len(texts), 100):
            batch = texts[i : i + 100]
            resp = self._client.models.embed_content(
                model=self.model_id,
                contents=batch,
                config={"output_dimensionality": self.dim},
            )
            out.extend(e.values for e in resp.embeddings)
        return out


class SentenceTransformerProvider:
    """Documented path for environments where huggingface.co is reachable.

    Deliberately lazy: importing sentence_transformers (and downloading the model)
    only happens if this provider is actually constructed, which never occurs in
    this environment.
    """

    def __init__(self, model_name: str = "BAAI/bge-small-en-v1.5"):
        from sentence_transformers import SentenceTransformer

        self._model = SentenceTransformer(model_name)
        self.model_id = model_name
        self.dim = self._model.get_sentence_embedding_dimension()

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [v.tolist() for v in self._model.encode(texts, normalize_embeddings=True)]
