"""Provider protocols and the one value everything hangs off: the request hash.

Every LLM call in this system is structured output at temperature 0. That makes a
call a pure function of its inputs, so we can canonicalize those inputs into a
sha256 and use it as the cassette filename, the dedup key, and the telemetry key.
Replay mode is just a dict lookup on this hash; a miss is a hard error, never a
silent fall-through to a live call.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class LLMRequest:
    agent: str  # usage | contract | support | revenue | reflection | composer
    prompt_version: str
    system: str
    user: str
    response_schema: dict  # JSON Schema; every call is structured output
    model_id: str
    temperature: float = 0.0
    max_tokens: int = 768
    # observability only — excluded from the hash
    tags: dict = field(default_factory=dict)

    def request_hash(self) -> str:
        payload = {
            "prompt_version": self.prompt_version,
            "system": self.system,
            "user": self.user,
            "response_schema": self.response_schema,
            "model_id": self.model_id,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
        canon = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canon.encode()).hexdigest()


@dataclass
class LLMResponse:
    data: dict  # parsed structured output, conforming to response_schema
    provider: str  # gemini | replay | offline
    model_id: str
    prompt_tokens: int
    output_tokens: int
    latency_ms: int
    cache_hit: bool = False


@runtime_checkable
class LLMProvider(Protocol):
    name: str

    def complete(self, req: LLMRequest) -> LLMResponse: ...


@runtime_checkable
class EmbeddingProvider(Protocol):
    model_id: str
    dim: int

    def embed(self, texts: list[str]) -> list[list[float]]: ...
