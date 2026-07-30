"""The reconciler: pure Python, zero LLM, table-driven precedence.

This is where risk tolerance lives, and risk tolerance is a business decision, not
a model output (spec §5.4). The LLM gathers and interprets evidence; this layer
converts evidence into a verdict under hard-coded precedence. It does NOT average.

The single most important property is a theorem, not a hope: KILL is unreachable
whenever a contract is obligated/possibly-obligated or revenue is concentrated.
tests/test_precedence.py proves it by exhaustive enumeration.

Verdict ranking by aggressiveness toward removal (KILL is most aggressive). A
"cap at MIGRATE" forbids KILL but allows anything less aggressive.
"""

from __future__ import annotations

from sunset.schemas import (
    AuditorOutput,
    Disagreement,
    ReconcilerResult,
    SecondaryAction,
    Verdict,
)

# how aggressive toward removal — used only to apply caps
_AGGRESSION = {Verdict.KILL: 3, Verdict.MIGRATE: 2, Verdict.FIX: 1, Verdict.KEEP: 1,
               Verdict.ESCALATE: 0}


def _sig(outputs: dict[str, AuditorOutput], auditor: str, key: str, default=None):
    o = outputs.get(auditor)
    return o.signals.get(key, default) if o else default


def reconcile(
    outputs: dict[str, AuditorOutput],
    *,
    after_reflection: bool = False,
) -> ReconcilerResult:
    """Map four auditor outputs to a single verdict under precedence. Deterministic."""
    applied: list[str] = []
    disagreements: list[Disagreement] = []

    contract_status = _sig(outputs, "contract", "status", "clear")
    revenue_concentrated = _sig(outputs, "usage", "revenue_concentrated", False)
    phantom = _sig(outputs, "usage", "phantom_usage", False)
    seasonal = _sig(outputs, "usage", "seasonality_detected", False)
    trend = _sig(outputs, "usage", "human_trend", "dead")
    defect = _sig(outputs, "support", "defect_signal", False)
    latent = _sig(outputs, "support", "latent_demand", False)
    sales_critical = _sig(outputs, "revenue", "sales_critical", False)
    inbound_from_keep = bool(_sig(outputs, "usage", "inbound_from_keep", []))
    active_accounts = _sig(outputs, "usage", "active_human_accounts", 0)

    # --- Rule 1: contract obligated -> ESCALATE. Non-negotiable, wins outright. --
    if contract_status == "obligated":
        applied.append("R1 contract obligated -> ESCALATE")
        return ReconcilerResult(
            verdict=Verdict.ESCALATE, confidence="high", applied_rules=applied,
            disagreements=_detect_disagreements(outputs, after_reflection),
        )

    # --- Base verdict from the usage picture ---------------------------------
    base, secondary, base_rule = _base_verdict(
        trend=trend, seasonal=seasonal, phantom=phantom, defect=defect,
        latent=latent, sales_critical=sales_critical, active_human_accounts=active_accounts,
    )
    applied.append(base_rule)

    # --- Caps (each forbids KILL, i.e. caps aggressiveness at MIGRATE) --------
    cap: Verdict | None = None
    if contract_status == "possibly_obligated":
        cap = Verdict.MIGRATE
        applied.append("R2 contract possibly-obligated -> cap MIGRATE")
    if revenue_concentrated:
        cap = Verdict.MIGRATE
        applied.append("R3 revenue concentrated -> cap MIGRATE")
    if inbound_from_keep:
        cap = Verdict.MIGRATE
        applied.append("R5 inbound dependency from a KEEP feature -> cap MIGRATE")

    verdict = base
    secondary_action = secondary
    if cap is not None and _AGGRESSION[verdict] > _AGGRESSION[cap]:
        verdict = cap
        secondary_action = None  # a capped feature isn't a reclassify
        applied.append(f"applied cap -> {cap.value}")

    # --- Rule 6: genuine post-reflection contradiction -> ESCALATE -----------
    disagreements = _detect_disagreements(outputs, after_reflection)
    if after_reflection and disagreements:
        applied.append("R6 auditors contradict after reflection -> ESCALATE")
        return ReconcilerResult(
            verdict=Verdict.ESCALATE, confidence="low", applied_rules=applied,
            disagreements=disagreements,
        )

    confidence = "high" if verdict in (Verdict.KEEP, Verdict.ESCALATE) and not disagreements \
        else "medium"
    return ReconcilerResult(
        verdict=verdict, secondary_action=secondary_action, confidence=confidence,
        cap=cap, applied_rules=applied, disagreements=disagreements,
        needs_reflection=bool(disagreements) and not after_reflection,
    )


def _base_verdict(*, trend, seasonal, phantom, defect, latent, sales_critical,
                  active_human_accounts=0):
    """The verdict implied by the demand picture, before contract/revenue caps."""
    # Rule 4: a defect on a collapsed feature is a repair, not a deprecation.
    if defect and trend in ("declining", "collapsed", "dead"):
        return Verdict.FIX, None, "R4 defect + declining usage -> FIX"
    # Seasonal features are alive, just dormant out of season.
    if seasonal:
        return Verdict.KEEP, None, "seasonal usage -> KEEP"
    # Phantom: bots inflate the totals; the real feature is dead.
    if phantom:
        return Verdict.KILL, None, "phantom usage -> KILL"
    # Sales-critical but product-quiet (not hard-collapsed): keep as collateral.
    if sales_critical and trend in ("flat", "declining"):
        return (Verdict.KEEP, SecondaryAction.RECLASSIFY_SALES_COLLATERAL,
                "sales-critical + product-quiet -> KEEP + reclassify")
    if trend == "growing":
        return Verdict.KEEP, None, "growing usage -> KEEP"
    if trend == "flat" and active_human_accounts >= 6:
        return Verdict.KEEP, None, "broad, steady usage -> KEEP"
    if trend == "flat" and latent:
        return Verdict.KEEP, None, "steady usage with active demand -> KEEP"
    # everything else — narrow flat usage, decline, dead/collapsed — is a removal
    # candidate at base. The caps (contract, revenue, dependency) then decide
    # whether it can actually be killed or must be migrated/escalated instead.
    return Verdict.KILL, None, "low / narrow / declining usage -> KILL (base)"


# ---------------------------------------------------------------------------
# Contradiction matrix. NOT every disagreement is a contradiction — usage
# declining + support defect is rule 4, not a conflict. Only genuinely opposed
# conclusions count.
# ---------------------------------------------------------------------------


def _detect_disagreements(outputs: dict[str, AuditorOutput], after_reflection: bool
                          ) -> list[Disagreement]:
    d: list[Disagreement] = []
    revenue_concentrated = _sig(outputs, "usage", "revenue_concentrated", False)
    sales_critical = _sig(outputs, "revenue", "sales_critical", False)
    trend = _sig(outputs, "usage", "human_trend", "dead")
    contract_status = _sig(outputs, "contract", "status", "clear")
    defect = _sig(outputs, "support", "defect_signal", False)

    # revenue says the feature closes deals, usage says it's hard-dead: a real
    # tension a human may want to see. But if a defect explains the collapse, the
    # collapse is a repair story (rule 4), not a revenue conflict — don't escalate.
    if sales_critical and trend in ("dead", "collapsed") and not revenue_concentrated \
            and not defect:
        d.append(Disagreement(
            between=("usage", "revenue"),
            description="Revenue reads this as sales-critical while usage reads it as dead.",
        ))
    # contract possibly-obligated but usage says clearly-dead and no replacement
    # confirmed: a migration-vs-escalate judgment call.
    if contract_status == "possibly_obligated" and trend in ("dead",):
        d.append(Disagreement(
            between=("contract", "usage"),
            description="A possible obligation touches a feature usage calls dead.",
        ))
    return d
