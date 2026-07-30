"""The offline provider: a deterministic rule-table stand-in for the LLM.

It works *because of* the architecture. The auditors compute the quantitative
signals in Python and do the retrieval; the model's only job is to interpret
those signals and read the retrieved text. So a rule table over the same signals
produces schema-valid, defensible output with no key and no network — enough to
exercise the entire graph, the reconciler, the citation validator, and the HITL
loop end to end.

It is NOT a model. Every response is tagged provider="offline", the run is marked
`used_offline`, and eval/score.py refuses to print an accuracy headline for it.

The auditors hand this provider a `<SIGNALS>{json}</SIGNALS>` block in the user
prompt; the real Gemini provider gets the same prompt as prose and returns the
same schema. The two cannot drift because they answer the same request shape.
"""

from __future__ import annotations

import json
import re
import time

from sunset.providers.base import LLMRequest, LLMResponse

_SIGNALS_RE = re.compile(r"<SIGNALS>(.*?)</SIGNALS>", re.DOTALL)


def parse_signals(user: str) -> dict:
    m = _SIGNALS_RE.search(user)
    return json.loads(m.group(1)) if m else {}


def _tokens(text: str) -> int:
    return max(1, len(text) // 4)


class OfflineProvider:
    name = "offline"

    def complete(self, req: LLMRequest) -> LLMResponse:
        t0 = time.perf_counter()
        s = parse_signals(req.user)
        data = _DISPATCH.get(req.agent, _passthrough)(s)
        latency = int((time.perf_counter() - t0) * 1000)
        return LLMResponse(
            data=data,
            provider="offline",
            model_id="offline-rules-v1",
            prompt_tokens=_tokens(req.system) + _tokens(req.user),
            output_tokens=_tokens(json.dumps(data)),
            latency_ms=max(1, latency),
        )


# ---------------------------------------------------------------------------
# Per-agent interpreters. Each maps the computed signals to the auditor's schema.
# ---------------------------------------------------------------------------


def _usage(s: dict) -> dict:
    trend = s.get("human_trend", "dead")
    seasonal = s.get("seasonality_detected", False)
    phantom = s.get("phantom_usage", False)
    conc = s.get("revenue_concentrated", False)
    if phantom:
        finding = "Headline usage is inflated by bots and internal QA; real human usage is negligible."
    elif seasonal:
        finding = "Usage is dormant most of the year and spikes in a recurring season — periodic, not dead."
    elif conc:
        finding = "Very few accounts use this, but they are high-ARR — usage is concentrated, not broad."
    elif trend in ("collapsed", "dead"):
        finding = "Human usage has collapsed to near zero."
    elif trend == "declining":
        finding = "Human usage is declining."
    else:
        finding = "Human usage is healthy and broad."
    return {
        "auditor": "usage",
        "finding": finding,
        "rationale": (
            f"trend={trend}, bot_share={s.get('bot_share', 0):.2f}, "
            f"accounts={s.get('active_human_accounts', 0)}, "
            f"revenue_share={s.get('revenue_share', 0):.2f}"
        ),
        "confidence": "high" if trend != "declining" else "medium",
        "signals": {
            "human_trend": trend,
            "seasonality_detected": seasonal,
            "seasonal_period_months": s.get("seasonal_period_months"),
            "bot_share": round(s.get("bot_share", 0.0), 3),
            "phantom_usage": phantom,
            "top1pct_arr_share": round(s.get("revenue_share", 0.0), 3),
            "revenue_concentrated": conc,
            "whale_usage": s.get("whale_usage", False),
            "active_human_accounts": s.get("active_human_accounts", 0),
        },
    }


def _contract(s: dict) -> dict:
    clauses = s.get("top_clauses", [])
    best = max((c.get("score", 0.0) for c in clauses), default=0.0)
    matched = [c for c in clauses if c.get("score", 0.0) >= 0.5]
    has_replacement = s.get("has_live_replacement", False)
    if best >= 0.5 and not has_replacement:
        status = "obligated"
        finding = "A contractual obligation names this capability and no other feature provides it."
    elif best >= 0.5 and has_replacement:
        # The obligation may be satisfiable by the named replacement, but that
        # is a migration to confirm, not a free kill. Caps at MIGRATE downstream.
        status = "possibly_obligated"
        finding = "A contractual obligation touches this capability; a live replacement may cover it."
    else:
        status = "clear"
        finding = "No contractual obligation clearly attaches to this capability."
    return {
        "auditor": "contract",
        "finding": finding,
        "rationale": f"best_clause_similarity={best:.2f}, has_replacement={has_replacement}",
        "confidence": "high" if best >= 0.6 or best < 0.35 else "medium",
        "signals": {
            "status": status,
            "matched_clause_ids": [c["id"] for c in matched],
            "obligated_accounts": sorted({c.get("account_id") for c in matched if c.get("account_id")}),
        },
        "_citations": [
            {"source_table": "contract_clauses", "source_id": c["id"],
             "claim_text": finding, "quoted_span": c.get("quote")}
            for c in matched
        ],
    }


def _support(s: dict) -> dict:
    defect = s.get("defect_after_drop", False)
    requests = s.get("request_tickets", 0)
    defects = s.get("defect_tickets", 0)
    latent = requests >= 8 or (s.get("ticket_count", 0) >= 20 and not defect)
    if defect:
        sentiment = "frustrated"
        finding = "Repeated failure reports coincide with the usage drop — this reads as a defect, not indifference."
    elif latent:
        sentiment = "mixed"
        finding = "Active demand in the ticket stream: requests and asks, not defects."
    else:
        sentiment = "neutral"
        finding = "No strong support signal either way."
    return {
        "auditor": "support",
        "finding": finding,
        "rationale": f"defect_after_drop={defect}, defect_tickets={defects}, request_tickets={requests}",
        "confidence": "high" if defect or latent else "low",
        "signals": {
            "latent_demand": latent,
            "defect_signal": defect,
            "sentiment": sentiment,
            "ticket_count": s.get("ticket_count", 0),
        },
        "_citations": s.get("ticket_citations", []),
    }


def _revenue(s: dict) -> dict:
    won = s.get("won_deal_count", 0)
    displacement = s.get("competitive_displacement", False)
    critical = won >= 2
    finding = (
        f"Cited as a deciding factor in {won} won deal(s) — sales-critical even if product-quiet."
        if critical else "Not materially cited in won deals."
    )
    return {
        "auditor": "revenue",
        "finding": finding,
        "rationale": f"won_deal_mentions={won}, competitive_displacement={displacement}",
        "confidence": "high" if won >= 3 else ("medium" if won >= 1 else "low"),
        "signals": {
            "sales_critical": critical,
            "won_deal_mentions": won,
            "competitive_displacement": displacement,
        },
        "_citations": s.get("deal_citations", []),
    }


def _reflection(s: dict) -> dict:
    # bounded, single pass: the stub does not manufacture a resolution.
    return {
        "resolved": False,
        "note": "Adversarial re-read found no basis to overturn either auditor; conflict stands.",
    }


def _composer(s: dict) -> dict:
    verdict = s.get("verdict", "KEEP")
    summary = s.get("summary_hint", f"Recommendation: {verdict}.")
    dissent = s.get("dissent_hint") or "No material counter-argument survives the evidence."
    return {"summary": summary, "dissent": dissent}


def _passthrough(s: dict) -> dict:
    return dict(s)


_DISPATCH = {
    "usage": _usage,
    "contract": _contract,
    "support": _support,
    "revenue": _revenue,
    "reflection": _reflection,
    "composer": _composer,
}
