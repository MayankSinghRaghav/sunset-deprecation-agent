"""Deterministic pre-filter. No LLM. Cuts agent spend by resolving obvious keeps.

Two hard rules the whole safety story leans on:

1. It may emit only "obvious_keep" or "needs_audit" — NEVER a KILL. The cheap path
   must not be able to reach a catastrophic verdict; anything that could be killed
   goes to the full auditor pipeline where contract and revenue checks run.

2. It reads HUMAN usage only. If it counted bot/QA traffic it would wave every
   trap-6 phantom feature through as an obvious keep, they would never be audited,
   and the trap would score 100% for exactly the wrong reason. tests/test_prefilter
   pins this.
"""

from __future__ import annotations

from typing import Literal

from sunset.evidence.metrics import MetricBundle

PrefilterVerdict = Literal["obvious_keep", "needs_audit"]

# A feature is an "obvious keep" only if it is broadly and healthily used by real
# people RIGHT NOW. The bar is deliberately conservative: anything with a hidden
# dimension — phantom inflation, seasonality, revenue concentration, a decline —
# is a question for the auditors, even when its final verdict will turn out to be
# KEEP. Waving a seasonal feature through here would keep it for the wrong reason
# and rob the usage auditor of the chance to actually detect the periodicity.
MIN_KEEP_ACCOUNTS = 6
MIN_RECENT_HUMAN_EVENTS = 1000


def prefilter(b: MetricBundle) -> PrefilterVerdict:
    if b.phantom_usage or b.seasonality_detected or b.revenue_concentrated:
        return "needs_audit"
    if (
        b.human_trend in ("growing", "flat")
        and b.active_human_accounts >= MIN_KEEP_ACCOUNTS
        and b.human_events_recent >= MIN_RECENT_HUMAN_EVENTS
    ):
        return "obvious_keep"
    return "needs_audit"
