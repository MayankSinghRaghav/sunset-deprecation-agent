"""Replay provider: serve committed cassettes keyed by request hash.

A miss is a hard error (CassetteMiss), never a silent fall-through to a live call
— that is what makes replay safe to run in CI with no key. Cassettes are recorded
once from a live run and committed.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from sunset.errors import CassetteMiss
from sunset.providers.base import LLMRequest, LLMResponse

CASSETTE_DIR = Path(__file__).parent / "cassettes"


class ReplayProvider:
    name = "replay"

    def __init__(self, cassette_dir: Path = CASSETTE_DIR):
        self.dir = cassette_dir

    def complete(self, req: LLMRequest) -> LLMResponse:
        h = req.request_hash()
        path = self.dir / f"{h}.json"
        if not path.exists():
            raise CassetteMiss(
                f"no cassette for {req.agent} request {h[:12]} — record it with "
                f"SUNSET_LLM_MODE=live SUNSET_RECORD=1"
            )
        rec = json.loads(path.read_text())
        return LLMResponse(
            data=rec["data"],
            provider="replay",
            model_id=rec.get("model_id", req.model_id),
            prompt_tokens=rec.get("prompt_tokens", 0),
            output_tokens=rec.get("output_tokens", 0),
            latency_ms=1,
            cache_hit=False,
        )


def record_cassette(req: LLMRequest, resp: LLMResponse, cassette_dir: Path = CASSETTE_DIR) -> None:
    cassette_dir.mkdir(parents=True, exist_ok=True)
    path = cassette_dir / f"{req.request_hash()}.json"
    path.write_text(json.dumps({
        "agent": req.agent,
        "prompt_version": req.prompt_version,
        "model_id": resp.model_id,
        "prompt_tokens": resp.prompt_tokens,
        "output_tokens": resp.output_tokens,
        "recorded_at": time.time(),
        "data": resp.data,
    }, indent=2))
