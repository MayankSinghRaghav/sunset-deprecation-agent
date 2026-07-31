"""Assemble the frontend-shaped memo and catalogue rows from real audit data.

The composer persists a structured Memo (summary, claims, at_risk_accounts,
migration_plan, dissent) in `feature_audits.memo_json`. The frontend renders a
richer layout than the pipeline emits, so a few narrative fields (headline,
recommendation heading, the decision-trace timeline) are *derived from the real
verdict and signals* here — nothing is invented, it is composed from facts the
pipeline actually produced.
"""

from __future__ import annotations

from fastapi import HTTPException

from sunset.api.deps import dict_rows

_WHO = {
    "usage": "Usage", "contract": "Contract",
    "support": "Support", "revenue": "Revenue",
}
_AMBER_VERDICTS = {"ESCALATE", "MIGRATE"}

_HEADLINE = {
    "KILL": "Remove {name} — no obligation, negligible usage.",
    "MIGRATE": "Remove {name} — after migrating the at-risk accounts.",
    "KEEP": "Keep {name}.",
    "FIX": "Fix {name} — a defect signature, not a deprecation.",
    "ESCALATE": "Escalate {name} to Legal — a contract obligation was found.",
}


def _money(n: float | int | None) -> str:
    if not n:
        return "$0"
    n = float(n)
    if n >= 1_000_000:
        return f"${n / 1_000_000:.2f}M"
    if n >= 1_000:
        return f"${round(n / 1000)}K"
    return f"${int(n)}"


def _reviewed(created_at) -> str:
    if created_at is None:
        return "recently"
    from datetime import UTC, datetime
    now = datetime.now(UTC)
    delta = now - created_at
    days = delta.days
    if days <= 0:
        hrs = int(delta.total_seconds() // 3600)
        return "just now" if hrs <= 0 else f"{hrs}h ago"
    if days == 1:
        return "1d ago"
    return f"{days}d ago"


def _latest_run(cur) -> str | None:
    cur.execute("SELECT id FROM audit_runs WHERE status='completed' "
                "ORDER BY started_at DESC LIMIT 1")
    row = cur.fetchone()
    return row[0] if row else None


def _account_arr(cur) -> dict[str, int]:
    cur.execute("SELECT id, arr_usd FROM accounts")
    return {r[0]: r[1] for r in cur.fetchall()}


def catalogue(conn) -> list[dict]:
    """FeatureRow[] for the catalogue: every audited feature in the latest run."""
    with conn.cursor() as cur:
        run_id = _latest_run(cur)
        if not run_id:
            return []
        cur.execute(
            "SELECT fa.feature_id, f.name, f.area, fa.verdict, fa.secondary_action, "
            "fa.confidence, f.annual_maintenance_usd, fa.memo_json, fa.created_at "
            "FROM feature_audits fa JOIN features f ON f.id=fa.feature_id "
            "WHERE fa.run_id=%s ORDER BY fa.feature_id", (run_id,))
        rows = dict_rows(cur)

    out: list[dict] = []
    for r in rows:
        mj = r.get("memo_json") or {}
        at_risk = mj.get("at_risk_accounts") or []
        risk = f"{len(at_risk)} account{'s' if len(at_risk) != 1 else ''}" if at_risk else None
        out.append({
            "id": r["feature_id"],
            "name": r["name"],
            "area": r["area"],
            "verdict": r["verdict"] or "KEEP",
            "reclassify": r["secondary_action"] == "RECLASSIFY_SALES_COLLATERAL",
            "confidence": r["confidence"] or "medium",
            "annual_cost": r["annual_maintenance_usd"] or 0,
            "risk_accounts": risk,
            "reviewed": _reviewed(r["created_at"]),
        })
    return out


def memo_view(conn, feature_id: str) -> dict:
    """The structured memo the frontend renders, assembled from real audit data."""
    with conn.cursor() as cur:
        run_id = _latest_run(cur)
        if not run_id:
            raise HTTPException(404, "no completed run yet")
        cur.execute(
            "SELECT fa.id AS audit_id, fa.feature_id, fa.verdict, fa.secondary_action, "
            "fa.confidence, fa.dissent, fa.memo_json, fa.applied_rules, "
            "f.name, f.area, f.annual_maintenance_usd, f.replacement_feature_id "
            "FROM feature_audits fa JOIN features f ON f.id=fa.feature_id "
            "WHERE fa.run_id=%s AND fa.feature_id=%s", (run_id, feature_id))
        rows = dict_rows(cur)
        if not rows:
            raise HTTPException(404, "no audit for that feature in the latest run")
        a = rows[0]
        mj = a["memo_json"] or {}
        arr = _account_arr(cur)

        # citations: resolve each claim's first evidence ref to (source, quote)
        cur.execute("SELECT id, source_table, claim_text, quoted_span "
                    "FROM evidence_refs WHERE feature_audit_id=%s", (a["audit_id"],))
        refs = {r["id"]: r for r in dict_rows(cur)}

    verdict = a["verdict"] or "KEEP"

    # --- claims (real: composer output, one line per auditor) --------------
    claims: list[dict] = []
    for c in mj.get("claims", []):
        text = c.get("text", "")
        who = "Usage"
        if text.startswith("[") and "]" in text:
            tag = text[1:text.index("]")].strip().lower()
            who = _WHO.get(tag, "Usage")
            text = text[text.index("]") + 1:].strip()
        ref_ids = c.get("evidence_ref_ids") or []
        if ref_ids and ref_ids[0] in refs:
            rr = refs[ref_ids[0]]
            citation = {
                "id": rr["id"],
                "source": rr["source_table"],
                "quote": rr["quoted_span"] or rr["claim_text"] or "cited evidence",
            }
        else:
            citation = {"id": "—", "source": "reconciler",
                        "quote": "reconciler judgment — no single row cited for this line"}
        claims.append({
            "who": who,
            "amber": who in ("Contract", "Revenue") and verdict in _AMBER_VERDICTS,
            "text": text,
            "citation": citation,
        })

    # --- at-risk accounts (real: composer at_risk_accounts + account ARR) ---
    at_risk: list[dict] = []
    total_exposure = 0
    for ar in mj.get("at_risk_accounts", []):
        aid = ar.get("account_id")
        arr_usd = arr.get(aid, 0)
        total_exposure += arr_usd
        band = ar.get("arr_band", "")
        why = f"{band} · {ar.get('reason', '')}".strip(" ·") if band else ar.get("reason", "")
        at_risk.append({"name": ar.get("name", aid), "why": why, "arr": f"{_money(arr_usd)} ARR"})

    # --- migration (real: composer migration_plan, split into steps) --------
    migration = None
    plan = mj.get("migration_plan")
    if plan:
        steps = [s.strip() for s in plan.replace("\n", " ").split(". ") if s.strip()]
        migration = [s if s.endswith(".") else s + "." for s in steps]

    # --- applied rule (real: reconciler trace) ------------------------------
    rules = a["applied_rules"] or []
    applied_rule = next((r for r in rules if r.strip().upper().startswith("R")), None) \
        or (rules[-1] if rules else "base rule")

    # --- decision-trace timeline (real: the reconciler's applied rules) -----
    timeline = [{
        "when": f"Step {i + 1}",
        "what": rule,
        "warn": any(k in rule.upper() for k in ("CAP", "ESCALATE", "MIGRATE", "KILL")),
    } for i, rule in enumerate(rules)]

    # --- derived narrative (from the real verdict + signals) ----------------
    name = a["name"]
    reclassify = a["secondary_action"] == "RECLASSIFY_SALES_COLLATERAL"
    headline = _HEADLINE.get(verdict, "Review {name}.").format(name=name)
    if verdict == "KEEP" and reclassify:
        headline = f"Keep {name}, but reclassify it as sales collateral."
    summary = mj.get("summary") or a["dissent"] or ""

    return {
        "id": feature_id,
        "audit_id": a["audit_id"],
        "name": name,
        "area": a["area"],
        "verdict": verdict,
        "reclassify": reclassify,
        "confidence": a["confidence"] or "medium",
        "headline": headline,
        "annual_cost": a["annual_maintenance_usd"] or 0,
        "revenue_exposure": f"{_money(total_exposure)} ARR" if total_exposure else None,
        "claims": claims,
        "timeline": timeline,
        "recommendation": {
            "eyebrow": "Recommendation",
            "heading": headline,
            "body": summary,
        },
        "at_risk": at_risk,
        "migration": migration,
        "dissent": a["dissent"] or mj.get("dissent") or "",
        "applied_rule": applied_rule,
    }
