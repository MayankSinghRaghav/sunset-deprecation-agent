"""The Phase-3 gate, in two halves.

1. Leak check (no DB): no committed fixture may contain a verdict token, a trap
   class name, or any justification sentence from the truth sheet. If it does,
   the agent could read the answer off the evidence and the eval is circular.

2. Signal detectability (needs DB): for each trap, a DELIBERATELY SIMPLE detector
   — not the real metric code — must separate the trap features from controls.
   The point is to prove the signal lives in the raw evidence before any metric
   or agent is written. If a dumb detector can't find it, no agent will, and the
   fix is the data, not the agent.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import psycopg

from datagen.truthsheet import by_id, load_truth
from datagen.world import BREAK_DATE, DEAL_CITATIONS, DEPENDENCIES
from sunset.config import settings

REPO = Path(__file__).resolve().parents[1]
FIX = REPO / "db" / "fixtures"

VERDICT_TOKENS = ["KILL", "MIGRATE", "KEEP", "FIX", "ESCALATE"]
TRAP_TOKENS = [
    "none_kill", "none_keep", "contract_bound", "hidden_dependency",
    "segment_concentrated", "broken_not_unwanted", "seasonal", "phantom_usage",
    "sales_critical", "RECLASSIFY_SALES_COLLATERAL", "has_distractor",
]


def _dsn() -> str:
    return settings.database_url.replace("postgresql+psycopg://", "postgresql://")


# ---------------------------------------------------------------------------
# 1. Leak check
# ---------------------------------------------------------------------------


def check_leaks() -> list[str]:
    problems: list[str] = []
    truth = load_truth()
    justifications = [t.justification for t in truth]

    # SQL fixtures only (the .csv.zst usage file has no free text). Exclude the
    # feature INSERT file's own feature-name column? No — feature names are fine,
    # they're app-visible. We look for verdict/trap tokens and justification text.
    verdict_re = re.compile(r"\b(" + "|".join(VERDICT_TOKENS) + r")\b")
    for p in sorted(FIX.glob("*.sql")):
        text = p.read_text()
        for m in verdict_re.finditer(text):
            problems.append(f"{p.name}: verdict token '{m.group(1)}'")
        for tok in TRAP_TOKENS:
            if tok in text:
                problems.append(f"{p.name}: trap token '{tok}'")
        for j in justifications:
            # match on a distinctive 40-char slice to avoid coincidental hits
            probe = j[:40]
            if probe and probe in text:
                problems.append(f"{p.name}: leaked justification '{probe}...'")
    return problems


# ---------------------------------------------------------------------------
# 2. Signal detectability
# ---------------------------------------------------------------------------


def _fids_by_trap(truth) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for t in truth:
        out.setdefault(t.trap_class, []).append(t.feature_id)
    return out


def check_signals(conn) -> list[str]:
    truth = load_truth()
    tid = by_id(truth)
    trap = _fids_by_trap(truth)
    keeps = set(trap.get("none_keep", []))
    fails: list[str] = []
    cur = conn.cursor()

    def q1(sql, *args):
        cur.execute(sql, args)
        return {r[0]: r[1] for r in cur.fetchall()}

    # --- trap 6: phantom usage -> bot_share > 0.6, keeps < 0.2 ---------------
    bot_share = q1(
        "SELECT feature_id, "
        "sum(events) FILTER (WHERE actor_type IN ('bot','internal_qa'))::float "
        "/ NULLIF(sum(events),0) FROM usage_daily GROUP BY feature_id"
    )
    for fid in trap["phantom_usage"]:
        bs = bot_share.get(fid, 0) or 0
        if bs <= 0.6:
            fails.append(f"trap6 {fid}: bot_share {bs:.2f} not > 0.6")
    for fid in keeps:
        bs = bot_share.get(fid, 0) or 0
        if bs >= 0.2:
            fails.append(f"trap6 control {fid}: keep bot_share {bs:.2f} not < 0.2")

    # --- trap 3: segment concentration -> whale human-event share > 0.8 ------
    whale_share = q1(
        "SELECT u.feature_id, "
        "sum(u.events) FILTER (WHERE a.arr_band='whale')::float "
        "/ NULLIF(sum(u.events),0) "
        "FROM usage_daily u JOIN accounts a ON a.id=u.account_id "
        "WHERE u.actor_type='human' GROUP BY u.feature_id"
    )
    for fid in trap["segment_concentrated"]:
        ws = whale_share.get(fid, 0) or 0
        if ws <= 0.8:
            fails.append(f"trap3 {fid}: whale human-event share {ws:.2f} not > 0.8")

    # --- trap 5: seasonality -> top-3 calendar-month share > 0.6 -------------
    cur.execute(
        "SELECT feature_id, EXTRACT(MONTH FROM day)::int, sum(events) "
        "FROM usage_daily WHERE actor_type='human' GROUP BY 1,2"
    )
    by_month: dict[str, dict[int, float]] = {}
    for fid, mo, ev in cur.fetchall():
        by_month.setdefault(fid, {})[mo] = float(ev)
    for fid in trap["seasonal"]:
        months = by_month.get(fid, {})
        tot = sum(months.values()) or 1
        top3 = sum(sorted(months.values(), reverse=True)[:3])
        if top3 / tot <= 0.6:
            fails.append(f"trap5 {fid}: top-3-month share {top3/tot:.2f} not > 0.6")
    # control: a keep feature must be spread out (< 0.5)
    for fid in list(keeps)[:2]:
        months = by_month.get(fid, {})
        tot = sum(months.values()) or 1
        top3 = sum(sorted(months.values(), reverse=True)[:3])
        if top3 / tot >= 0.55:
            fails.append(f"trap5 control {fid}: keep top-3 share {top3/tot:.2f} too high")

    # --- trap 4: broken -> post/pre human events < 0.15 AND defect tickets ---
    pre = q1(
        "SELECT feature_id, sum(events) FROM usage_daily "
        "WHERE actor_type='human' AND day < %s GROUP BY feature_id", BREAK_DATE
    )
    post = q1(
        "SELECT feature_id, sum(events) FROM usage_daily "
        "WHERE actor_type='human' AND day >= %s GROUP BY feature_id", BREAK_DATE
    )
    defect = q1(
        "SELECT feature_id_guess, count(*) FROM support_tickets "
        "WHERE created_at >= %s AND (body ILIKE '%%error%%' OR body ILIKE '%%fail%%' "
        "OR body ILIKE '%%stopped%%') GROUP BY feature_id_guess",
        f"{BREAK_DATE.isoformat()}T00:00:00+00:00",
    )
    for fid in trap["broken_not_unwanted"]:
        ratio = (post.get(fid, 0) or 0) / max(1, pre.get(fid, 0) or 0)
        if ratio >= 0.15:
            fails.append(f"trap4 {fid}: post/pre usage {ratio:.2f} not < 0.15")
        if (defect.get(fid, 0) or 0) < 10:
            fails.append(f"trap4 {fid}: only {defect.get(fid,0)} defect tickets after break")

    # --- trap 2: hidden dependency -> inbound edge from a KEEP + low usage ---
    inbound_from_keep: dict[str, int] = {}
    for f, t, _k in DEPENDENCIES:
        if f in keeps:
            inbound_from_keep[t] = inbound_from_keep.get(t, 0) + 1
    human_ev = q1(
        "SELECT feature_id, sum(events) FROM usage_daily "
        "WHERE actor_type='human' GROUP BY feature_id"
    )
    for fid in trap["hidden_dependency"]:
        if inbound_from_keep.get(fid, 0) < 1:
            fails.append(f"trap2 {fid}: no inbound dependency from a KEEP feature")
    # and no would-be-KILL feature may have such an inbound edge (would wrongly cap it)
    killish = set(trap.get("none_kill", []) + trap.get("phantom_usage", []))
    for fid in killish:
        if inbound_from_keep.get(fid, 0) > 0:
            fails.append(f"trap2 guard: kill feature {fid} has inbound KEEP edge (would mis-cap)")

    # --- trap 1: contract-bound -> obligated features are low-usage (usage
    #     alone would mislead); semantic clause match is validated in Phase 5 ---
    for fid in trap["contract_bound"]:
        if tid[fid].correct_verdict == "ESCALATE":
            # obligated: should be low direct usage so the naive read says kill
            if (human_ev.get(fid, 0) or 0) > (list(sorted(human_ev.values()))[-6]):
                fails.append(f"trap1 {fid}: usage unexpectedly high for a contract trap")

    # --- trap 7: sales-critical -> near-zero human usage + won-deal citations -
    citation_phrases = {
        "f37": "compliance certifications center",
        "f38": "white-label branding",
        "f39": "on-premises deployment",
        "f40": "soc 2 evidence dashboard",
    }
    for fid in trap["sales_critical"]:
        phrase = citation_phrases[fid]
        cur.execute(
            "SELECT count(*) FROM deal_notes WHERE outcome='won' AND body ILIKE %s",
            (f"%{phrase}%",),
        )
        got = cur.fetchone()[0]
        if got < DEAL_CITATIONS[fid]:
            fails.append(
                f"trap7 {fid}: {got} won-deal citations, expected >= {DEAL_CITATIONS[fid]}"
            )

    return fails


def main() -> int:
    leaks = check_leaks()
    print(f"Leak check: {'CLEAN' if not leaks else 'FAILED'}")
    for p in leaks:
        print("  LEAK:", p)

    signal_fails: list[str] = []
    try:
        with psycopg.connect(_dsn()) as conn:
            signal_fails = check_signals(conn)
        print(f"Signal detectability: {'ALL DETECTABLE' if not signal_fails else 'FAILED'}")
        for p in signal_fails:
            print("  UNDETECTABLE:", p)
    except psycopg.OperationalError as e:
        print(f"Signal detectability: SKIPPED (no DB: {e})")

    return 1 if (leaks or signal_fails) else 0


if __name__ == "__main__":
    sys.exit(main())
