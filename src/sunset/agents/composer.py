"""The Memo Composer. Renders the verdict as a structured, cited case — and the
strongest surviving argument against itself.

The memo is structured, not free prose: {summary, claims[], at_risk_accounts,
migration_plan, dissent}. Structure is what makes citation validation possible —
every claim carries evidence-ref ids that resolve to real rows. `dissent` is
required and never empty: a deprecation tool that only argues its own side is how
you get a confident, wrong, expensive removal (spec §8.2). If no counter-argument
survives, the composer says so explicitly rather than omitting it.

Migration plans are proposed only when a replacement feature exists in the
catalogue; otherwise the memo states that a path is required and stops (the
decision locked with the user).
"""

from __future__ import annotations

import json

from sunset.agents.auditors import PROMPT_VERSION, AuditContext
from sunset.evidence.refs import new_ref_id
from sunset.providers.base import LLMRequest
from sunset.schemas import (
    AccountRef,
    AuditorOutput,
    Claim,
    EvidenceRef,
    Memo,
    ReconcilerResult,
    Verdict,
)
from sunset.telemetry import CallRecord

_VERB = {
    Verdict.KILL: "Remove this feature.",
    Verdict.MIGRATE: "Remove this feature after migrating the named accounts.",
    Verdict.KEEP: "Keep this feature.",
    Verdict.FIX: "Repair this feature before re-evaluating.",
    Verdict.ESCALATE: "Escalate: a human must decide with legal input.",
}


def compose(
    feature_id: str,
    feature: dict,
    result: ReconcilerResult,
    outputs: dict[str, AuditorOutput],
    ctx: AuditContext,
) -> tuple[Memo, list[EvidenceRef]]:
    # 1. assemble cited claims from the auditors
    claims: list[Claim] = []
    all_refs: list[EvidenceRef] = []
    for auditor in ("usage", "contract", "support", "revenue"):
        o = outputs.get(auditor)
        if o is None:
            continue
        ref_ids: list[str] = []
        for ref in o.citations:
            ref.ref_id = new_ref_id()
            all_refs.append(ref)
            ref_ids.append(ref.ref_id)
        claims.append(Claim(text=f"[{auditor}] {o.finding}", evidence_ref_ids=ref_ids))

    # 2. at-risk accounts (contract obligations + concentration)
    at_risk = _at_risk_accounts(outputs, ctx)

    # 3. migration plan — only when a replacement exists in the catalogue
    migration_plan = _migration_plan(feature, result, at_risk, ctx)

    # 4. dissent — never empty
    dissent = _dissent(result.verdict, outputs)

    # 5. LLM prose for the summary line (offline templates it)
    summary_hint = f"{_VERB[result.verdict]} " + _one_line_reason(result, outputs)
    signals_block = json.dumps({
        "verdict": result.verdict.value,
        "summary_hint": summary_hint,
        "dissent_hint": dissent,
    })
    req = LLMRequest(
        agent="composer", prompt_version=PROMPT_VERSION,
        system="You are the Memo Composer. Write a single-sentence executive summary "
               "in the imperative, and restate the strongest counter-argument. Verbs, "
               "not nouns.",
        user=f"<SIGNALS>{signals_block}</SIGNALS>",
        response_schema={"type": "object"}, model_id=ctx.model_id,
        tags={"feature_id": feature_id},
    )
    resp = ctx.provider.complete(req)
    ctx.ledger.record(CallRecord(
        agent="composer", provider=resp.provider, model_id=resp.model_id,
        prompt_version=PROMPT_VERSION, request_hash=req.request_hash()[:16],
        prompt_tokens=resp.prompt_tokens, output_tokens=resp.output_tokens,
        latency_ms=resp.latency_ms, cache_hit=False, feature_id=feature_id))
    summary = resp.data.get("summary", summary_hint)
    dissent = resp.data.get("dissent", dissent)

    memo = Memo(
        verdict=result.verdict, secondary_action=result.secondary_action,
        confidence=result.confidence, summary=summary, claims=claims,
        at_risk_accounts=at_risk, migration_plan=migration_plan, dissent=dissent,
    )
    return memo, all_refs


def _at_risk_accounts(outputs, ctx) -> list[AccountRef]:
    account_ids: dict[str, str] = {}
    contract = outputs.get("contract")
    if contract:
        for aid in contract.signals.get("obligated_accounts", []) or []:
            if aid:
                account_ids[aid] = "named in a contractual obligation"
    usage = outputs.get("usage")
    if usage and usage.signals.get("revenue_concentrated"):
        # whale accounts using the feature carry the revenue exposure
        for aid in _whale_users(ctx, usage):
            account_ids.setdefault(aid, "high-ARR account with concentrated usage")
    refs: list[AccountRef] = []
    for aid, reason in account_ids.items():
        info = _account_info(ctx, aid)
        if info:
            refs.append(AccountRef(account_id=aid, name=info[0], arr_band=info[1], reason=reason))
    return refs


def _whale_users(ctx, usage) -> list[str]:
    fid = None
    # usage citation source_id is the feature_id for the usage_daily data ref
    for c in usage.citations:
        if c.source_table == "usage_daily":
            fid = c.source_id
    if not fid:
        return []
    with ctx.conn.cursor() as cur:
        cur.execute(
            "SELECT DISTINCT u.account_id FROM usage_daily u JOIN accounts a ON a.id=u.account_id "
            "WHERE u.feature_id=%s AND u.actor_type='human' AND a.arr_band='whale'",
            (fid,),
        )
        return [r[0] for r in cur.fetchall()]


def _account_info(ctx, aid):
    with ctx.conn.cursor() as cur:
        cur.execute("SELECT name, arr_band FROM accounts WHERE id=%s", (aid,))
        return cur.fetchone()


def _migration_plan(feature, result, at_risk, ctx) -> str | None:
    if result.verdict != Verdict.MIGRATE:
        return None
    replacement = feature.get("replacement_feature_id")
    names = ", ".join(a.name for a in at_risk) or "the affected accounts"
    if replacement and replacement in ctx.features_by_id:
        rep_name = ctx.features_by_id[replacement]["name"]
        return (
            f"Move {names} to {rep_name}, then remove this feature. Confirm the "
            f"replacement covers each obligation before cutover."
        )
    return (
        "A migration path is required before removal: no replacement feature exists "
        f"in the catalogue, and {names} would lose capability. Define the path first."
    )


def _dissent(verdict: Verdict, outputs: dict[str, AuditorOutput]) -> str:
    """The strongest surviving argument AGAINST the verdict. Never empty."""
    u = outputs.get("usage")
    c = outputs.get("contract")
    s = outputs.get("support")
    r = outputs.get("revenue")
    if verdict == Verdict.KILL:
        if r and r.signals.get("won_deal_mentions", 0) > 0:
            return (f"Revenue found {r.signals['won_deal_mentions']} won-deal mention(s); "
                    "if those citations are genuine, removal loses sales narrative.")
        if s and s.signals.get("latent_demand"):
            return "Support shows unmet requests — some users still want this."
        return ("No counter-argument survives: usage is dead, no contract attaches, no "
                "deals cite it, nothing depends on it.")
    if verdict == Verdict.KEEP:
        if u and u.signals.get("active_human_accounts", 99) < 6:
            return "Usage is thin; if the sales/seasonal signal weakens, revisit removal."
        return "Maintenance cost is ongoing; confirm the usage justifies it next quarter."
    if verdict == Verdict.MIGRATE:
        return ("If the replacement fully covers the obligation today, this could be a "
                "clean removal rather than a migration — verify before committing effort.")
    if verdict == Verdict.FIX:
        return ("If the defect is cheap to leave broken and demand keeps falling, this "
                "may still become a removal candidate next quarter.")
    if verdict == Verdict.ESCALATE:
        if c and c.signals.get("status") == "obligated":
            return ("The obligation may be satisfiable another way; legal may find the "
                    "removal acceptable after all.")
        return "The auditors' conflict may resolve on closer reading; escalation may be avoidable."
    return "No counter-argument recorded."


def _one_line_reason(result: ReconcilerResult, outputs) -> str:
    if result.applied_rules:
        return "Basis: " + result.applied_rules[-1] + "."
    return ""
