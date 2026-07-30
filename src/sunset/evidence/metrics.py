"""Pure-Python evidence computation. No LLM, no randomness.

The spec is emphatic (§5.2): compute the numbers in Python and let the model only
interpret them — never ask a model to compute a seasonality index it can get
wrong. So every quantitative signal a trap depends on is derived here,
deterministically, and the auditors receive a `MetricBundle` they only have to
narrate.

Nothing here knows where the trap-4 break date is; a usage drop is detected from
the series itself. Nothing here reads ground truth. It computes all 40 features in
a handful of batch queries because at this scale that is both simpler and faster
than per-feature round-trips.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta

RECENT_DAYS = 120


@dataclass
class MetricBundle:
    feature_id: str
    # usage
    human_events_total: int = 0
    human_events_recent: int = 0
    human_trend: str = "dead"  # growing|flat|declining|collapsed|dead
    collapse_ratio: float = 1.0  # recent mean / prior peak mean (low => collapsed)
    active_human_accounts: int = 0
    bot_share: float = 0.0
    phantom_usage: bool = False
    # seasonality
    seasonality_detected: bool = False
    seasonal_period_months: int | None = None
    top3_month_share: float = 0.0
    active_months: int = 0
    # revenue concentration
    user_share: float = 0.0
    revenue_share: float = 0.0
    revenue_concentrated: bool = False
    whale_usage: bool = False
    using_account_ids: list[str] = field(default_factory=list)
    # support
    ticket_count: int = 0
    defect_tickets: int = 0
    request_tickets: int = 0
    recent_defect_tickets: int = 0
    defect_after_drop: bool = False
    # dependency
    inbound_edges: list[tuple[str, str]] = field(default_factory=list)  # (from, kind)
    inbound_from_keep: list[str] = field(default_factory=list)


def compute_all_metrics(conn) -> dict[str, MetricBundle]:
    cur = conn.cursor()
    cur.execute("SELECT id FROM features")
    fids = [r[0] for r in cur.fetchall()]
    bundles = {fid: MetricBundle(feature_id=fid) for fid in fids}

    cur.execute("SELECT id, arr_band, arr_usd FROM accounts")
    accounts = {r[0]: (r[1], r[2]) for r in cur.fetchall()}
    total_accounts = len(accounts)
    total_arr = sum(a[1] for a in accounts.values())

    cur.execute("SELECT max(day) FROM usage_daily")
    max_day: date = cur.fetchone()[0]
    recent_cut = max_day - timedelta(days=RECENT_DAYS)

    _usage_by_actor(cur, bundles)
    _usage_recent(cur, bundles, recent_cut)
    _usage_by_account(cur, bundles, accounts, total_accounts, total_arr)
    _usage_monthly(cur, bundles)
    _tickets(cur, bundles, max_day)
    _dependencies(cur, bundles)

    # keep-set heuristic for the dependency rule: broadly, healthily used features.
    # This is the same shape as the pre-filter's obvious_keep and is what precedence
    # rule 5 keys on ("inbound edge from a KEEP feature"). The agent never sees a
    # verdict here — only "is the upstream feature clearly alive".
    keep_set = {
        fid for fid, b in bundles.items()
        if b.human_trend in ("growing", "flat")
        and b.active_human_accounts >= 6
        and not b.phantom_usage
    }
    for b in bundles.values():
        b.inbound_from_keep = [src for (src, _k) in b.inbound_edges if src in keep_set]

    return bundles


# ---------------------------------------------------------------------------


def _usage_by_actor(cur, bundles):
    cur.execute(
        "SELECT feature_id, actor_type, sum(events) FROM usage_daily GROUP BY 1,2"
    )
    per: dict[str, dict[str, int]] = {}
    for fid, actor, ev in cur.fetchall():
        per.setdefault(fid, {})[actor] = ev
    for fid, b in bundles.items():
        a = per.get(fid, {})
        human, bot, qa = a.get("human", 0), a.get("bot", 0), a.get("internal_qa", 0)
        b.human_events_total = human
        tot = human + bot + qa
        b.bot_share = (bot + qa) / tot if tot else 0.0


def _usage_recent(cur, bundles, recent_cut):
    cur.execute(
        "SELECT feature_id, sum(events) FROM usage_daily "
        "WHERE actor_type='human' AND day >= %s GROUP BY 1",
        (recent_cut,),
    )
    for fid, ev in cur.fetchall():
        bundles[fid].human_events_recent = ev or 0


def _usage_by_account(cur, bundles, accounts, total_accounts, total_arr):
    cur.execute(
        "SELECT feature_id, account_id, sum(events) FROM usage_daily "
        "WHERE actor_type='human' GROUP BY 1,2 HAVING sum(events) > 0"
    )
    users: dict[str, list[str]] = {}
    for fid, aid, _ev in cur.fetchall():
        users.setdefault(fid, []).append(aid)
    for fid, b in bundles.items():
        using = users.get(fid, [])
        b.using_account_ids = sorted(using)
        b.active_human_accounts = len(using)
        b.whale_usage = any(accounts.get(a, ("", 0))[0] == "whale" for a in using)
        used_arr = sum(accounts.get(a, ("", 0))[1] for a in using)
        b.user_share = len(using) / total_accounts if total_accounts else 0.0
        b.revenue_share = used_arr / total_arr if total_arr else 0.0
        # few users, big revenue: the trap-3 shape. Deliberately excludes the
        # broadly-used keeps (many users) and the SMB-only dead features (low ARR).
        b.revenue_concentrated = (
            b.user_share < 0.15 and b.revenue_share > 0.25 and b.whale_usage
        )


def _usage_monthly(cur, bundles):
    cur.execute(
        "SELECT feature_id, date_trunc('month', day)::date m, sum(events) "
        "FROM usage_daily WHERE actor_type='human' GROUP BY 1,2 ORDER BY 1,2"
    )
    series: dict[str, list[tuple[date, int]]] = {}
    for fid, m, ev in cur.fetchall():
        series.setdefault(fid, []).append((m, ev))
    for fid, b in bundles.items():
        pts = series.get(fid, [])
        _derive_trend_and_seasonality(b, pts)


def _derive_trend_and_seasonality(b: MetricBundle, pts: list[tuple[date, int]]):
    if not pts:
        b.human_trend = "dead"
        return
    vals = [v for _m, v in pts]
    total = sum(vals)
    # calendar-month concentration (seasonality)
    by_cal: dict[int, int] = {}
    for m, v in pts:
        by_cal[m.month] = by_cal.get(m.month, 0) + v
    if total > 0:
        top3 = sum(sorted(by_cal.values(), reverse=True)[:3])
        b.top3_month_share = top3 / total
        peak = max(by_cal.values())
        b.active_months = sum(1 for v in by_cal.values() if v > 0.15 * peak)
    # dormant most of the year with sharp peaks => seasonal
    b.seasonality_detected = (
        b.top3_month_share > 0.55 and b.active_months <= 5 and total > 50
    )
    if b.seasonality_detected:
        b.seasonal_period_months = 12

    # trend / collapse from the monthly series (thirds)
    n = len(vals)
    third = max(1, n // 3)
    first_mean = sum(vals[:third]) / third
    last_mean = sum(vals[-third:]) / third
    peak_mean = max(
        sum(vals[i : i + third]) / third for i in range(0, max(1, n - third + 1))
    )
    b.collapse_ratio = last_mean / peak_mean if peak_mean else 0.0

    if total < 60:
        b.human_trend = "dead"
    elif b.seasonality_detected:
        # a dormant-out-of-season feature is not "declining"; call it flat so the
        # narrator reads periodicity, not death.
        b.human_trend = "flat"
    elif b.collapse_ratio < 0.10:
        b.human_trend = "collapsed"
    elif last_mean < 0.6 * first_mean:
        b.human_trend = "declining"
    elif last_mean > 1.4 * first_mean:
        b.human_trend = "growing"
    else:
        b.human_trend = "flat"

    # phantom: bots/QA dominate the totals while almost no humans touch it. This
    # is decoupled from the trend label on purpose — a steady whisper of one SMB
    # account still reads "flat", but if 99% of events are non-human and only a
    # handful of human accounts remain, the headline usage is a mirage. (Uses
    # active_human_accounts, set in _usage_by_account, which runs before this.)
    b.phantom_usage = b.bot_share > 0.6 and b.active_human_accounts <= 3


def _tickets(cur, bundles, max_day):
    recent_cut = max_day - timedelta(days=180)
    cur.execute(
        "SELECT feature_id_guess, "
        "count(*), "
        "count(*) FILTER (WHERE body ILIKE '%%error%%' OR body ILIKE '%%fail%%' "
        "   OR body ILIKE '%%stopped%%' OR body ILIKE '%%not working%%'), "
        "count(*) FILTER (WHERE subject ILIKE '%%request%%' OR subject ILIKE '%%please%%' "
        "   OR subject ILIKE '%%would love%%' OR subject ILIKE '%%support%%'), "
        "count(*) FILTER (WHERE (body ILIKE '%%error%%' OR body ILIKE '%%fail%%' "
        "   OR body ILIKE '%%stopped%%') AND created_at >= %s) "
        "FROM support_tickets WHERE feature_id_guess IS NOT NULL GROUP BY 1",
        (f"{recent_cut.isoformat()}T00:00:00+00:00",),
    )
    for fid, tot, defect, request, recent_def in cur.fetchall():
        b = bundles[fid]
        b.ticket_count = tot
        b.defect_tickets = defect
        b.request_tickets = request
        b.recent_defect_tickets = recent_def
    for b in bundles.values():
        # a defect signal is a cluster of recent failure reports coinciding with a
        # usage drop — not merely "some tickets exist".
        b.defect_after_drop = (
            b.recent_defect_tickets >= 8
            and b.collapse_ratio < 0.3
            and b.defect_tickets > b.request_tickets
        )


def _dependencies(cur, bundles):
    cur.execute("SELECT from_feature_id, to_feature_id, kind FROM feature_dependencies")
    for src, dst, kind in cur.fetchall():
        if dst in bundles:
            bundles[dst].inbound_edges.append((src, kind))
