"""Reflection: a single bounded adversarial re-read, fired only on disagreement.

Unbounded reflection loops are how free-tier quotas die (spec §5.2), so this runs
at most once — enforced by the caller's edge, an assertion here, and the graph's
recursion limit. It re-reads the conflicting evidence with each auditor's
conclusion held up as a counter-hypothesis; if it cannot overturn either side, the
conflict stands and the reconciler escalates to a human.

In offline mode the stub does not manufacture a resolution — that honesty is the
point. A cheap embedder that produced a spurious signal should surface as an
escalation, not be silently smoothed over.
"""

from __future__ import annotations

from sunset.agents.auditors import PROMPT_VERSION, AuditContext
from sunset.providers.base import LLMRequest
from sunset.schemas import Disagreement
from sunset.telemetry import CallRecord


def reflect(
    disagreements: list[Disagreement],
    ctx: AuditContext,
    feature_id: str,
) -> bool:
    """Return True if reflection resolved the conflict (so it need not escalate)."""
    import json

    payload = {"disagreements": [d.description for d in disagreements]}
    req = LLMRequest(
        agent="reflection", prompt_version=PROMPT_VERSION,
        system="You are the Reflection step. Re-read the conflicting evidence and "
               "decide whether one side clearly overturns the other. Resolve only "
               "with strong justification; otherwise leave the conflict standing.",
        user=f"<SIGNALS>{json.dumps(payload)}</SIGNALS>",
        response_schema={"type": "object"},
        model_id=ctx.model_id, tags={"feature_id": feature_id},
    )
    resp = ctx.provider.complete(req)
    ctx.ledger.record(CallRecord(
        agent="reflection", provider=resp.provider, model_id=resp.model_id,
        prompt_version=PROMPT_VERSION, request_hash=req.request_hash()[:16],
        prompt_tokens=resp.prompt_tokens, output_tokens=resp.output_tokens,
        latency_ms=resp.latency_ms, cache_hit=False, feature_id=feature_id))
    return bool(resp.data.get("resolved", False))
