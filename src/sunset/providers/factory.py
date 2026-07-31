"""Select the LLM and embedding providers from settings. One switch, whole system."""

from __future__ import annotations

from functools import lru_cache

from sunset.config import settings
from sunset.providers.base import EmbeddingProvider, LLMProvider, LLMRequest, LLMResponse
from sunset.providers.embeddings import GeminiEmbeddingProvider, HashingEmbeddingProvider


class _RecordingProvider:
    """Wraps a live provider and writes a cassette for every call (SUNSET_RECORD=1)."""

    name = "gemini"

    def __init__(self, inner: LLMProvider):
        self.inner = inner

    def complete(self, req: LLMRequest) -> LLMResponse:
        from sunset.providers.replay import record_cassette

        resp = self.inner.complete(req)
        record_cassette(req, resp)
        return resp


@lru_cache
def get_llm() -> LLMProvider:
    mode = settings.llm_mode
    if mode == "offline":
        from sunset.providers.offline import OfflineProvider

        return OfflineProvider()
    if mode == "replay":
        from sunset.providers.replay import ReplayProvider

        return ReplayProvider()
    if mode == "live":
        import os

        from sunset.providers.gemini import GeminiProvider

        provider: LLMProvider = GeminiProvider()
        if os.environ.get("SUNSET_RECORD") == "1":
            provider = _RecordingProvider(provider)
        return provider
    raise ValueError(f"unknown SUNSET_LLM_MODE={mode}")


@lru_cache
def get_embedder() -> EmbeddingProvider:
    # The embedder is decoupled from llm_mode: it follows settings.embedding_model,
    # so a live Gemini run can still use keyless hashing retrieval (the hybrid
    # path) that matches a hashing-seeded corpus. Retrieval filters on
    # embedding_model, so this must agree with what's in the DB.
    if settings.embedding_model == "hashing-v1":
        return HashingEmbeddingProvider()
    if settings.llm_mode == "live" and settings.gemini_api_key:
        return GeminiEmbeddingProvider()
    return HashingEmbeddingProvider()
