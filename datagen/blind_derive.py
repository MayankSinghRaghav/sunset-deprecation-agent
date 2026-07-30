"""Print ONLY raw evidence for a feature — no verdict, no trap class — so a human
can derive the verdict independently (spec §4.1 step 5, the gate before Week 2).

Usage: uv run python -m datagen.blind_derive f13 f23 f30 ...
"""

from __future__ import annotations

import sys

import psycopg

from datagen.world import BREAK_DATE
from sunset.config import settings


def _dsn() -> str:
    return settings.database_url.replace("postgresql+psycopg://", "postgresql://")


def evidence(conn, fid: str) -> dict:
    cur = conn.cursor()
    cur.execute("SELECT name, description, area FROM features WHERE id=%s", (fid,))
    name, desc, area = cur.fetchone()

    cur.execute(
        "SELECT actor_type, sum(events), count(distinct account_id) "
        "FROM usage_daily WHERE feature_id=%s GROUP BY actor_type", (fid,))
    actor = {r[0]: (r[1], r[2]) for r in cur.fetchall()}

    cur.execute(
        "SELECT a.arr_band, sum(u.events) FROM usage_daily u "
        "JOIN accounts a ON a.id=u.account_id "
        "WHERE u.feature_id=%s AND u.actor_type='human' GROUP BY a.arr_band", (fid,))
    band = {r[0]: r[1] for r in cur.fetchall()}

    cur.execute(
        "SELECT sum(events) FILTER (WHERE day < %s), sum(events) FILTER (WHERE day >= %s) "
        "FROM usage_daily WHERE feature_id=%s AND actor_type='human'",
        (BREAK_DATE, BREAK_DATE, fid))
    pre, post = cur.fetchone()

    cur.execute(
        "SELECT EXTRACT(MONTH FROM day)::int m, sum(events) FROM usage_daily "
        "WHERE feature_id=%s AND actor_type='human' GROUP BY m ORDER BY 2 DESC LIMIT 3",
        (fid,))
    top_months = cur.fetchall()

    cur.execute(
        "SELECT count(*), count(*) FILTER (WHERE body ILIKE '%%error%%' OR body ILIKE "
        "'%%fail%%' OR body ILIKE '%%stopped%%'), "
        "count(*) FILTER (WHERE subject ILIKE '%%request%%' OR subject ILIKE '%%please%%' "
        "OR subject ILIKE '%%would love%%') "
        "FROM support_tickets WHERE feature_id_guess=%s", (fid,))
    tk_total, tk_defect, tk_request = cur.fetchone()

    # contract clauses whose text overlaps the feature's capability words (crude,
    # deliberately not the real semantic retrieval — just enough to see if any
    # obligation plausibly touches this capability)
    words = [w for w in desc.lower().replace(",", " ").replace(".", " ").split()
             if len(w) > 5][:6]
    cur.execute("SELECT id, section, text FROM contract_clauses")
    clauses = []
    for cid, section, text in cur.fetchall():
        tl = text.lower()
        hits = sum(1 for w in words if w in tl)
        if hits >= 2:
            clauses.append((cid, section, hits, text[:120]))

    cur.execute(
        "SELECT outcome, count(*) FROM deal_notes "
        "WHERE body ILIKE %s GROUP BY outcome",
        (f"%{name.lower()}%",))
    deals = {r[0]: r[1] for r in cur.fetchall()}

    cur.execute(
        "SELECT from_feature_id, kind FROM feature_dependencies WHERE to_feature_id=%s",
        (fid,))
    inbound = cur.fetchall()

    return dict(
        name=name, area=area, desc=desc, actor=actor, band=band,
        pre=pre or 0, post=post or 0, top_months=top_months,
        tickets=(tk_total, tk_defect, tk_request), clauses=clauses,
        deals=deals, inbound=inbound,
    )


def main():
    fids = sys.argv[1:] or ["f13"]
    with psycopg.connect(_dsn()) as conn:
        for fid in fids:
            e = evidence(conn, fid)
            print(f"\n===== {fid}: {e['name']} ({e['area']}) =====")
            print(f"  desc: {e['desc']}")
            h = e["actor"].get("human", (0, 0))
            b = e["actor"].get("bot", (0, 0))
            q = e["actor"].get("internal_qa", (0, 0))
            tot = h[0] + b[0] + q[0]
            bot_share = (b[0] + q[0]) / tot if tot else 0
            print(f"  usage events: human={h[0]} (accts {h[1]}), bot={b[0]}, qa={q[0]}, "
                  f"bot_share={bot_share:.0%}")
            print(f"  human events by ARR band: {e['band']}")
            print(f"  human events pre/post {BREAK_DATE}: {e['pre']} -> {e['post']} "
                  f"(ratio {e['post']/max(1,e['pre']):.2f})")
            print(f"  top human-usage months: {e['top_months']}")
            print(f"  tickets total/defect/request: {e['tickets']}")
            print(f"  contract clauses matching capability: "
                  f"{[(c[0],c[1],c[3]) for c in e['clauses']] or 'none'}")
            print(f"  deal-note mentions: {e['deals'] or 'none'}")
            print(f"  inbound dependencies (from -> this): {e['inbound'] or 'none'}")


if __name__ == "__main__":
    main()
