"""The reconciler is where catastrophic errors are made impossible — as a theorem,
not an observation about a model.

These tests enumerate auditor-output combinations and prove the precedence rules
hold for ALL of them. The headline property (spec §3.1): KILL is unreachable
whenever a contract is obligated/possibly-obligated or revenue is concentrated.
"""

from __future__ import annotations

import itertools

from sunset.agents.reconciler import reconcile
from sunset.schemas import AuditorOutput, Verdict


def _outputs(*, trend="flat", contract="clear", concentrated=False, phantom=False,
             seasonal=False, defect=False, latent=False, sales_critical=False,
             inbound=False, accounts=8):
    return {
        "usage": AuditorOutput(
            auditor="usage", finding="", rationale="", confidence="high",
            signals={
                "human_trend": trend, "revenue_concentrated": concentrated,
                "phantom_usage": phantom, "seasonality_detected": seasonal,
                "active_human_accounts": accounts,
                "inbound_from_keep": ["fX"] if inbound else [],
            }),
        "contract": AuditorOutput(
            auditor="contract", finding="", rationale="", confidence="high",
            signals={"status": contract, "matched_clause_ids": [], "obligated_accounts": []}),
        "support": AuditorOutput(
            auditor="support", finding="", rationale="", confidence="high",
            signals={"defect_signal": defect, "latent_demand": latent,
                     "sentiment": "neutral", "ticket_count": 0}),
        "revenue": AuditorOutput(
            auditor="revenue", finding="", rationale="", confidence="high",
            signals={"sales_critical": sales_critical, "won_deal_mentions": 0,
                     "competitive_displacement": False}),
    }


TRENDS = ["growing", "flat", "declining", "collapsed", "dead"]
CONTRACTS = ["clear", "possibly_obligated", "obligated"]
BOOLS = [False, True]


def _all_combos():
    for trend, contract, conc, phantom, defect, latent, sales, inbound in itertools.product(
        TRENDS, CONTRACTS, BOOLS, BOOLS, BOOLS, BOOLS, BOOLS, BOOLS
    ):
        for after in (False, True):
            yield reconcile(
                _outputs(trend=trend, contract=contract, concentrated=conc,
                         phantom=phantom, defect=defect, latent=latent,
                         sales_critical=sales, inbound=inbound),
                after_reflection=after,
            ), dict(trend=trend, contract=contract, conc=conc, phantom=phantom,
                    defect=defect, latent=latent, sales=sales, inbound=inbound, after=after)


def test_kill_unreachable_under_contract_or_concentration():
    """THE theorem. Over every combination, a contract obligation or revenue
    concentration makes KILL impossible."""
    for result, ctx in _all_combos():
        if ctx["contract"] in ("obligated", "possibly_obligated") or ctx["conc"]:
            assert result.verdict != Verdict.KILL, f"catastrophic KILL reachable: {ctx}"


def test_obligated_always_escalates():
    for result, ctx in _all_combos():
        if ctx["contract"] == "obligated":
            assert result.verdict == Verdict.ESCALATE, ctx


def test_possibly_obligated_caps_at_migrate():
    for result, ctx in _all_combos():
        if ctx["contract"] == "possibly_obligated":
            assert result.verdict in (
                Verdict.MIGRATE, Verdict.KEEP, Verdict.FIX, Verdict.ESCALATE), ctx


def test_defect_plus_decline_is_fix_not_kill():
    r = reconcile(_outputs(trend="collapsed", defect=True))
    assert r.verdict == Verdict.FIX


def test_inbound_keep_dependency_caps_at_migrate():
    r = reconcile(_outputs(trend="dead", inbound=True))
    assert r.verdict == Verdict.MIGRATE


def test_phantom_is_kill_when_no_protection():
    r = reconcile(_outputs(trend="flat", phantom=True, accounts=1))
    assert r.verdict == Verdict.KILL


def test_seasonal_is_keep():
    r = reconcile(_outputs(trend="flat", seasonal=True))
    assert r.verdict == Verdict.KEEP


def test_sales_critical_quiet_is_keep_reclassify():
    r = reconcile(_outputs(trend="flat", sales_critical=True, accounts=2))
    assert r.verdict == Verdict.KEEP
    assert r.secondary_action is not None


def test_reconciler_is_pure():
    """Same inputs, same outputs — no hidden state."""
    a = reconcile(_outputs(trend="dead", contract="obligated"))
    b = reconcile(_outputs(trend="dead", contract="obligated"))
    assert a.verdict == b.verdict and a.applied_rules == b.applied_rules
