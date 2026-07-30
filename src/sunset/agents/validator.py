"""The Citation Validator. Deterministic. No LLM.

Every evidence ref in a memo is resolved against a real database row; text refs
must additionally have a quoted span that is a verbatim substring of the source.
A memo with any unresolvable citation does not ship — the whole product premise
dies if a hallucinated citation reaches the UI (spec §5.2). The graph gives the
composer exactly one chance to fix it, then fails the feature loudly.
"""

from __future__ import annotations

from sunset.evidence.refs import resolve
from sunset.schemas import CitationReport, EvidenceRef


def validate(conn, refs: list[EvidenceRef]) -> CitationReport:
    unresolved: list[str] = []
    resolved = 0
    for ref in refs:
        ok, err = resolve(conn, ref)
        ref.quoted_span  # noqa: B018 - keep the span on the ref for the UI
        if ok:
            resolved += 1
        else:
            unresolved.append(ref.ref_id or f"{ref.source_table}:{ref.source_id} ({err})")
    return CitationReport(total=len(refs), resolved=resolved, unresolved_ref_ids=unresolved)


def render_markdown(feature: dict, memo, at_risk_note: bool = True) -> str:
    """Render the memo as the document a PM takes to a forum. The dissent is a
    first-class section, never a footnote."""
    from sunset.schemas import Verdict

    lines = [
        f"# {feature['name']} — {memo.verdict.value}",
        "",
        f"**{memo.summary}**",
        "",
        f"_Confidence: {memo.confidence}_"
        + (f" · _Secondary action: {memo.secondary_action.value}_"
           if memo.secondary_action else ""),
        "",
        "## The case",
    ]
    for claim in memo.claims:
        cites = (
            f"  \n  ↳ evidence: {', '.join(claim.evidence_ref_ids)}"
            if claim.evidence_ref_ids else ""
        )
        lines.append(f"- {claim.text}{cites}")
    if memo.at_risk_accounts:
        lines += ["", "## Accounts at risk"]
        for a in memo.at_risk_accounts:
            lines.append(f"- **{a.name}** ({a.arr_band}) — {a.reason}")
    if memo.migration_plan:
        lines += ["", "## Migration", memo.migration_plan]
    lines += [
        "",
        "## Dissent — the strongest argument against this verdict",
        f"> {memo.dissent}",
    ]
    if memo.verdict == Verdict.ESCALATE:
        lines += ["", "_This memo does not decide. It assembles the case for a human to decide._"]
    return "\n".join(lines)
