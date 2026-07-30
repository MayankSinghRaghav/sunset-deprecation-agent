"""The four parallel auditors and their shared run harness.

Each auditor computes its quantitative signals in Python (via metrics.py) and does
its retrieval in Python, then calls the provider ONLY to interpret — to read the
retrieved text and label the signals. In offline mode that interpretation is a
rule table; in live mode it is Gemini. Either way the auditor is responsible for
minting the evidence refs, because a claim without a citation is not allowed.

Ownership (spec §5.2): Usage owns traps 3/5/6, Contract owns trap 1 (with veto
power), Support owns trap 4, Revenue owns trap 7. The Reconciler owns trap 2 via
the dependency signal Usage carries.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field

from sunset.config import settings
from sunset.evidence.metrics import MetricBundle
from sunset.evidence.refs import clip_span
from sunset.graph.cache import cache_get, cache_key, cache_put
from sunset.providers.base import LLMProvider, LLMRequest
from sunset.schemas import AuditorOutput, EvidenceRef
from sunset.telemetry import CallRecord, Ledger

PROMPT_VERSION = "v1"

# Retrieval-similarity cutoffs, calibrated to the keyless HASHING embedder so the
# offline pipeline produces sensible output. They are floor calibrations, not eval
# tuning (offline accuracy is suppressed). With Gemini the separation widens, so
# these stay valid. See eval/CHANGELOG.md.
#   - clause 0.40: contract features cluster at 0.45-0.64; noise sits below 0.40.
#   - deal   0.45: trap-7 notes fire at >0.45; generic won-deal noise sits under it.
#     (The hashing floor still misses f39 — "On-Prem" vs "on-premises" share no
#     tokens — which is precisely the paraphrase gap semantic embeddings close.)
DEAL_SIM_THRESHOLD = 0.45
CLAUSE_SIM_THRESHOLD = 0.4


@dataclass
class AuditContext:
    conn: object
    index: object  # VectorIndex
    provider: LLMProvider
    embedder: object
    ledger: Ledger
    run_id: str
    keep_features: set[str]
    features_by_id: dict  # fid -> dict(name, description, replacement_feature_id)
    model_id: str = field(default_factory=lambda: settings.model_auditor)


def evidence_hash(b: MetricBundle) -> str:
    """Hash the INPUTS an auditor sees, never its outputs. Re-running with the same
    evidence hits the cache; regenerated data busts it."""
    payload = {
        "trend": b.human_trend, "recent": b.human_events_recent,
        "bot": round(b.bot_share, 3), "phantom": b.phantom_usage,
        "seasonal": b.seasonality_detected, "conc": b.revenue_concentrated,
        "users": b.active_human_accounts, "revshare": round(b.revenue_share, 3),
        "defect": b.defect_after_drop, "dtk": b.defect_tickets, "rtk": b.request_tickets,
        "indeps": sorted(b.inbound_from_keep), "collapse": round(b.collapse_ratio, 3),
        "ds": settings.dataset_version,
        # thresholds live in the hash so changing them busts the cache rather than
        # silently serving a stale interpretation.
        "thr": (CLAUSE_SIM_THRESHOLD, DEAL_SIM_THRESHOLD),
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:16]


_SCHEMA = {"type": "object"}  # gemini structured-output schema; offline ignores it


def _run(name: str, feature_id: str, ehash: str, system: str, signals: dict,
         ctx: AuditContext) -> tuple[dict, bool]:
    """Cache-checked provider call. Returns (response_data, cache_hit)."""
    key = cache_key(feature_id, ehash, name, PROMPT_VERSION, ctx.model_id)
    cached = cache_get(ctx.conn, key)
    if cached is not None:
        ctx.ledger.record(CallRecord(
            agent=name, provider="cache", model_id=ctx.model_id,
            prompt_version=PROMPT_VERSION, request_hash=key[:16],
            prompt_tokens=0, output_tokens=0, latency_ms=0, cache_hit=True,
            feature_id=feature_id))
        return cached, True

    user = (
        f"Interpret the following signals for feature {feature_id} and return the "
        f"structured verdict.\n<SIGNALS>{json.dumps(signals)}</SIGNALS>"
    )
    req = LLMRequest(agent=name, prompt_version=PROMPT_VERSION, system=system,
                     user=user, response_schema=_SCHEMA, model_id=ctx.model_id,
                     tags={"feature_id": feature_id, "run_id": ctx.run_id})
    resp = ctx.provider.complete(req)
    ctx.ledger.record(CallRecord(
        agent=name, provider=resp.provider, model_id=resp.model_id,
        prompt_version=PROMPT_VERSION, request_hash=req.request_hash()[:16],
        prompt_tokens=resp.prompt_tokens, output_tokens=resp.output_tokens,
        latency_ms=resp.latency_ms, cache_hit=False, feature_id=feature_id))
    cache_put(ctx.conn, key, feature_id=feature_id, evidence_hash=ehash, auditor=name,
              prompt_version=PROMPT_VERSION, model_id=ctx.model_id, output_json=resp.data,
              prompt_tokens=resp.prompt_tokens, output_tokens=resp.output_tokens)
    return resp.data, False


def _to_output(data: dict) -> AuditorOutput:
    cites = [
        EvidenceRef(
            ref_id="", source_table=c["source_table"], source_id=c["source_id"],
            claim_text=c["claim_text"], quoted_span=c.get("quoted_span"),
        )
        for c in data.get("_citations", [])
    ]
    return AuditorOutput(
        auditor=data["auditor"], finding=data["finding"], rationale=data["rationale"],
        confidence=data["confidence"], signals=data["signals"], citations=cites,
    )


# ---------------------------------------------------------------------------
# Usage
# ---------------------------------------------------------------------------

_USAGE_SYS = (
    "You are the Usage Auditor. You are given precomputed telemetry signals. Do not "
    "recompute them. Interpret whether usage is healthy, declining, collapsed, "
    "seasonal, phantom (bot-inflated), or revenue-concentrated, and state it plainly."
)


def audit_usage(feature_id: str, b: MetricBundle, ctx: AuditContext) -> AuditorOutput:
    signals = {
        "human_trend": b.human_trend,
        "seasonality_detected": b.seasonality_detected,
        "seasonal_period_months": b.seasonal_period_months,
        "bot_share": round(b.bot_share, 3),
        "phantom_usage": b.phantom_usage,
        "revenue_concentrated": b.revenue_concentrated,
        "revenue_share": round(b.revenue_share, 3),
        "whale_usage": b.whale_usage,
        "active_human_accounts": b.active_human_accounts,
        "inbound_from_keep": sorted(b.inbound_from_keep),
    }
    data, _ = _run("usage", feature_id, evidence_hash(b), _USAGE_SYS, signals, ctx)
    out = _to_output(data)
    # a data ref to the feature's usage backs the quantitative claim
    out.citations.append(EvidenceRef(
        ref_id="", source_table="usage_daily", source_id=feature_id,
        claim_text=out.finding, quoted_span=None,
    ))
    return out


# ---------------------------------------------------------------------------
# Contract (veto power)
# ---------------------------------------------------------------------------

_CONTRACT_SYS = (
    "You are the Contract Risk Auditor. You are given clauses retrieved by semantic "
    "similarity to a feature's capability. Decide whether an obligation attaches: "
    "'obligated' if a clause requires this capability and no other live feature "
    "provides it; 'possibly_obligated' if a clause touches it but a replacement may "
    "cover it; 'clear' otherwise. A signed obligation is a legal question, not a "
    "product one — you hold veto power."
)


def _clause_account(conn, clause_id: str) -> str | None:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT c.account_id FROM contract_clauses cl "
            "JOIN contracts c ON c.id = cl.contract_id WHERE cl.id = %s",
            (clause_id,),
        )
        row = cur.fetchone()
    return row[0] if row else None


def audit_contract(feature_id: str, b: MetricBundle, ctx: AuditContext) -> AuditorOutput:
    feat = ctx.features_by_id[feature_id]
    qv = ctx.embedder.embed([feat["description"]])[0]
    hits = ctx.index.search(qv, "contract_clauses", top_k=3)
    top_clauses = [
        {
            "id": h.source_id, "score": round(h.score, 3),
            "account_id": _clause_account(ctx.conn, h.source_id),
            "quote": clip_span(h.text),
        }
        for h in hits
    ]
    replacement = feat.get("replacement_feature_id")
    has_live_replacement = bool(replacement and replacement in ctx.keep_features)
    signals = {"top_clauses": top_clauses, "has_live_replacement": has_live_replacement,
               "clause_threshold": CLAUSE_SIM_THRESHOLD}
    data, _ = _run("contract", feature_id, evidence_hash(b), _CONTRACT_SYS, signals, ctx)
    return _to_output(data)


# ---------------------------------------------------------------------------
# Support
# ---------------------------------------------------------------------------

_SUPPORT_SYS = (
    "You are the Support Signal Auditor. Distinguish a defect (repeated failed "
    "attempts after a usage drop) from latent demand (requests, 'please add') from "
    "indifference (silence). Collapsed usage plus a defect is a repair, not a "
    "deprecation."
)


def audit_support(feature_id: str, b: MetricBundle, ctx: AuditContext) -> AuditorOutput:
    want_defect = b.defect_after_drop
    like = (
        "body ILIKE '%%error%%' OR body ILIKE '%%fail%%' OR body ILIKE '%%stopped%%'"
        if want_defect else
        "subject ILIKE '%%request%%' OR subject ILIKE '%%please%%' OR subject ILIKE '%%support%%'"
    )
    with ctx.conn.cursor() as cur:
        cur.execute(
            f"SELECT id, body FROM support_tickets WHERE feature_id_guess = %s AND ({like}) "
            f"ORDER BY created_at DESC LIMIT 3",
            (feature_id,),
        )
        rows = cur.fetchall()
    citations = [
        {"source_table": "support_tickets", "source_id": tid,
         "claim_text": "defect report" if want_defect else "feature request",
         "quoted_span": clip_span(body)}
        for tid, body in rows
    ]
    signals = {
        "defect_after_drop": b.defect_after_drop,
        "defect_tickets": b.defect_tickets,
        "request_tickets": b.request_tickets,
        "ticket_count": b.ticket_count,
        "collapse_ratio": round(b.collapse_ratio, 3),
        "ticket_citations": citations,
    }
    data, _ = _run("support", feature_id, evidence_hash(b), _SUPPORT_SYS, signals, ctx)
    return _to_output(data)


# ---------------------------------------------------------------------------
# Revenue
# ---------------------------------------------------------------------------

_REVENUE_SYS = (
    "You are the Revenue Signal Auditor. Read won-deal notes retrieved by similarity "
    "to a feature. Decide whether the feature is cited as a reason deals closed — "
    "sales-critical even when it is quiet in the product."
)


def audit_revenue(feature_id: str, b: MetricBundle, ctx: AuditContext) -> AuditorOutput:
    feat = ctx.features_by_id[feature_id]
    qv = ctx.embedder.embed([feat["description"]])[0]
    hits = ctx.index.search(qv, "deal_notes", top_k=8, where="outcome = 'won'")
    mentions = [h for h in hits if h.score >= DEAL_SIM_THRESHOLD]
    citations = [
        {"source_table": "deal_notes", "source_id": h.source_id,
         "claim_text": "cited in a won deal", "quoted_span": clip_span(h.text)}
        for h in mentions[:3]
    ]
    displacement = any(
        w in h.text.lower() for h in mentions for w in ("beat", "over ", "competitor", "against")
    )
    signals = {
        "won_deal_count": len(mentions),
        "competitive_displacement": displacement,
        "deal_citations": citations,
    }
    data, _ = _run("revenue", feature_id, evidence_hash(b), _REVENUE_SYS, signals, ctx)
    return _to_output(data)


AUDITORS = {
    "usage": audit_usage,
    "contract": audit_contract,
    "support": audit_support,
    "revenue": audit_revenue,
}
