"""The deterministic rules baseline. Frozen once measured; never tuned to a score.

Built BEFORE any agent code so its number means something (spec §3.2). It uses
exactly the three levers the spec names — usage percentile thresholds, keyword
grep against contract text, ticket-count thresholds — and nothing else. In
particular it does NOT filter bot traffic and does NOT join usage to ARR bands,
because those are precisely the structured reads that separate a naive rules
engine from the agent. The baseline's failures are therefore diagnostic:
whatever it misses is what semantic/structured reasoning has to earn.

Rules, in order:
  1. contract grep: a >=5-char token of the feature name appears as a whole word
     in any clause  -> ESCALATE
  2. recently quiet (recent usage in the bottom quartile) -> KILL
  3. otherwise -> KEEP

"Recent usage" is the signal a naive analyst actually reaches for — "has anyone
used this lately?" — which is exactly why it misreads a seasonal feature out of
season, a feature broken last quarter, a product-dead-but-sales-critical one,
and (fatally) a low-usage but contract-obligated one, which it happily KILLs.

The baseline can only ever say KILL, KEEP, or ESCALATE. It has no concept of FIX
or MIGRATE — a count-based rule cannot tell a defect from indifference, or see
that a low-usage feature is load-bearing in a contract or a dependency graph.
Those four traps therefore fail by construction, which is precisely the gap that
semantic and structured reasoning has to earn back.

The thresholds are percentiles of the data (self-calibrating), not numbers chosen
by looking at the score.
"""

from __future__ import annotations

import re
from datetime import timedelta

import numpy as np
import psycopg

from eval.score import Prediction
from sunset.config import settings

RECENT_WINDOW_DAYS = 120


def _dsn() -> str:
    return settings.database_url.replace("postgresql+psycopg://", "postgresql://")


def _gather(conn) -> dict[str, dict]:
    cur = conn.cursor()
    cur.execute("SELECT id, name FROM features")
    feats = {fid: {"name": name} for fid, name in cur.fetchall()}

    cur.execute("SELECT max(day) FROM usage_daily")
    max_day = cur.fetchone()[0]
    recent_cut = max_day - timedelta(days=RECENT_WINDOW_DAYS)

    cur.execute("SELECT feature_id, sum(events) FROM usage_daily GROUP BY feature_id")
    alltime = dict(cur.fetchall())
    cur.execute(
        "SELECT feature_id, sum(events) FROM usage_daily WHERE day >= %s GROUP BY feature_id",
        (recent_cut,),
    )
    recent = dict(cur.fetchall())
    cur.execute(
        "SELECT feature_id_guess, count(*) FROM support_tickets "
        "WHERE feature_id_guess IS NOT NULL GROUP BY feature_id_guess"
    )
    tickets = dict(cur.fetchall())

    cur.execute("SELECT lower(text) FROM contract_clauses")
    clause_texts = [r[0] for r in cur.fetchall()]

    for fid, d in feats.items():
        d["alltime"] = alltime.get(fid, 0) or 0
        d["recent"] = recent.get(fid, 0) or 0
        d["tickets"] = tickets.get(fid, 0) or 0
        d["contract_hit"] = _contract_hit(d["name"], clause_texts)
    return feats


def _contract_hit(name: str, clause_texts: list[str]) -> bool:
    tokens = [t.lower() for t in re.findall(r"[A-Za-z]+", name) if len(t) >= 5]
    for tok in tokens:
        pat = re.compile(rf"\b{re.escape(tok)}\b")
        if any(pat.search(txt) for txt in clause_texts):
            return True
    return False


def baseline_predictions() -> dict[str, Prediction]:
    with psycopg.connect(_dsn()) as conn:
        feats = _gather(conn)

    recent_vals = np.array([d["recent"] for d in feats.values()])
    kill_recent = np.percentile(recent_vals, 25)

    preds: dict[str, Prediction] = {}
    for fid, d in feats.items():
        if d["contract_hit"]:
            v = "ESCALATE"
        elif d["recent"] <= kill_recent:
            v = "KILL"
        else:
            v = "KEEP"
        preds[fid] = Prediction(feature_id=fid, verdict=v, used_offline=False)
    return preds


def main() -> None:
    from eval.score import format_scorecard, score

    preds = baseline_predictions()
    print(format_scorecard(score(preds, "Deterministic baseline (all 40)")))


if __name__ == "__main__":
    main()
