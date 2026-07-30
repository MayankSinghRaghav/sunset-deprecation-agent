"""Gemini provider. Structured output at temperature 0.

Untested in this environment (no key), but written to the google-genai structured-
output contract: response_mime_type=application/json + a response_schema. In live
mode the factory can wrap this in a recorder so a single keyed run produces the
cassettes that CI then replays.
"""

from __future__ import annotations

import json
import time

from sunset.config import settings
from sunset.errors import ProviderConfigError
from sunset.providers.base import LLMRequest, LLMResponse


class GeminiProvider:
    name = "gemini"

    def __init__(self):
        if not settings.gemini_api_key:
            raise ProviderConfigError("GEMINI_API_KEY required for live mode")
        from google import genai

        self._genai = genai
        self._client = genai.Client(api_key=settings.gemini_api_key)

    def complete(self, req: LLMRequest) -> LLMResponse:
        t0 = time.perf_counter()
        resp = self._client.models.generate_content(
            model=req.model_id,
            contents=f"{req.system}\n\n{req.user}",
            config={
                "temperature": req.temperature,
                "max_output_tokens": req.max_tokens,
                "response_mime_type": "application/json",
                "response_schema": req.response_schema,
            },
        )
        latency = int((time.perf_counter() - t0) * 1000)
        data = json.loads(resp.text)
        usage = getattr(resp, "usage_metadata", None)
        return LLMResponse(
            data=data,
            provider="gemini",
            model_id=req.model_id,
            prompt_tokens=getattr(usage, "prompt_token_count", 0) or 0,
            output_tokens=getattr(usage, "candidates_token_count", 0) or 0,
            latency_ms=latency,
        )
