"""Usage-shape generators, one per trap profile.

Each feature's daily usage time series is produced here from its trap class. The
shapes are the whole point: a naive reader of raw event counts should reach the
WRONG verdict on the trap features, and the right verdict only becomes available
once you look at the dimension the trap hides (actor type, ARR band, timing,
periodicity). We emit a row only for (feature, account, day, actor) with nonzero
usage; a missing row means zero that day, and the metrics treat it that way.

Determinism: each feature gets its own numpy Generator seeded from the global
seed and the feature index, so features are independent and byte-reproducible.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

import numpy as np

from datagen.world import BREAK_DATE, WINDOW_END, WINDOW_START


@dataclass
class Account:
    id: str
    band: str  # whale | mid_market | smb
    arr: int


@dataclass
class UsageRow:
    feature_id: str
    account_id: str
    day: date
    actor_type: str  # human | bot | internal_qa
    active_users: int
    events: int


SEASON_MONTHS = {
    "f29": {12, 1},        # year-end close
    "f30": {2, 3, 4},      # tax season
    "f31": {11},           # open enrollment
    "f32": {9, 10},        # pre-peak
}


def _all_days() -> list[date]:
    days = []
    d = WINDOW_START
    while d <= WINDOW_END:
        days.append(d)
        d += timedelta(days=1)
    return days


def _pick(rng: np.random.Generator, accounts: list[Account], n: int) -> list[Account]:
    """Deterministically pick n accounts (by id order) without replacement."""
    ordered = sorted(accounts, key=lambda a: a.id)
    n = min(n, len(ordered))
    idx = rng.choice(len(ordered), size=n, replace=False)
    return [ordered[i] for i in sorted(idx)]


def _whales(accounts: list[Account]) -> list[Account]:
    return [a for a in accounts if a.band == "whale"]


def _band(accounts: list[Account], band: str) -> list[Account]:
    return [a for a in accounts if a.band == band]


def _emit(
    feature_id: str,
    account: Account,
    days: list[date],
    intensity: np.ndarray,
    actor_type: str,
    rng: np.random.Generator,
    users_per_100_events: float = 25.0,
) -> list[UsageRow]:
    """Turn a per-day intensity (expected events) into rows, skipping zero days."""
    rows: list[UsageRow] = []
    for d, lam in zip(days, intensity, strict=True):
        if lam <= 0:
            continue
        ev = int(rng.poisson(lam))
        if ev <= 0:
            continue
        users = max(1, int(round(ev * users_per_100_events / 100.0)))
        rows.append(UsageRow(feature_id, account.id, d, actor_type, users, ev))
    return rows


# ---------------------------------------------------------------------------
# Profiles. Each returns a list[UsageRow] for the whole feature.
# ---------------------------------------------------------------------------


def _steady(days, base, slope=0.0, noise=0.15, rng=None):
    """Baseline events/day with optional linear trend and multiplicative noise."""
    n = len(days)
    trend = base * (1.0 + slope * np.arange(n) / n)
    jitter = 1.0 + rng.normal(0, noise, n)
    # weekday dip on weekends
    weekend = np.array([0.55 if d.weekday() >= 5 else 1.0 for d in days])
    return np.clip(trend * jitter * weekend, 0, None)


def profile_none_keep(fid, accounts, rng):
    days = _all_days()
    rows = []
    users = _pick(rng, accounts, 12)
    for a in users:
        base = {"whale": 60, "mid_market": 30, "smb": 12}[a.band] * rng.uniform(0.7, 1.4)
        inten = _steady(days, base, slope=rng.uniform(-0.1, 0.4), rng=rng)
        rows += _emit(fid, a, days, inten, "human", rng)
        # a small, realistic background of bot traffic (~5%), never enough to
        # matter — this is what keeps trap-6's threshold honest.
        rows += _emit(fid, a, days, inten * 0.05, "bot", rng)
    return rows


def profile_none_kill(fid, accounts, rng):
    days = _all_days()
    rows = []
    users = _pick(rng, _band(accounts, "smb"), 2)
    for a in users:
        # decays from a low base to ~zero within the first few months
        n = len(days)
        decay = np.exp(-np.arange(n) / 90.0)
        inten = 3.0 * decay * (1.0 + rng.normal(0, 0.2, n))
        rows += _emit(fid, a, days, np.clip(inten, 0, None), "human", rng)
    return rows


def profile_contract_bound(fid, accounts, rng):
    # Genuinely LOW, slowly declining usage in a couple of enterprise accounts.
    # A naive usage read says "kill" — and that is the whole danger of the trap:
    # the feature is quiet in the product but load-bearing in a signed contract.
    # The obligation (attached in contracts) is the only thing standing between
    # the naive baseline and a contract breach.
    days = _all_days()
    rows = []
    users = _pick(rng, _band(accounts, "whale") + _band(accounts, "mid_market"), 2)
    n = len(days)
    for a in users:
        # steep decline to genuinely dormant: recent usage sits well below the
        # bottom quartile, so a usage-only baseline reads it as a safe KILL —
        # and, because keyword grep cannot read the capability-language clause,
        # nothing stops the breach. That KILL is the trap.
        decline = np.exp(-np.arange(n) / 170.0)
        inten = _steady(days, 0.8 * rng.uniform(0.7, 1.1), rng=rng) * decline
        rows += _emit(fid, a, days, np.clip(inten, 0, None), "human", rng)
    return rows


def profile_hidden_dependency(fid, accounts, rng):
    # near-zero DIRECT usage: it is backing infrastructure. The dependency edge
    # from a keep feature is the entire signal.
    days = _all_days()
    rows = []
    users = _pick(rng, accounts, 1)
    for a in users:
        inten = _steady(days, 1.2, rng=rng) * 0.4
        rows += _emit(fid, a, days, inten, "human", rng)
    return rows


def profile_segment_concentrated(fid, accounts, rng):
    # a tiny number of accounts, but they are whales. Raw user count says kill;
    # ARR concentration says migrate.
    days = _all_days()
    rows = []
    users = _whales(accounts)[: rng.integers(2, 4)]
    for a in users:
        inten = _steady(days, 14 * rng.uniform(0.8, 1.2), rng=rng)
        rows += _emit(fid, a, days, inten, "human", rng)
    return rows


def profile_broken_not_unwanted(fid, accounts, rng):
    # healthy until the break date, then collapses. The drop + the defect tickets
    # (attached in tickets.py) mark this as FIX, not lost interest.
    days = _all_days()
    rows = []
    users = _pick(rng, accounts, 10)
    break_i = days.index(BREAK_DATE)
    for a in users:
        base = {"whale": 45, "mid_market": 24, "smb": 10}[a.band] * rng.uniform(0.8, 1.2)
        inten = _steady(days, base, rng=rng)
        # after the break: collapse to ~1.5% (a few stubborn retries). Recent
        # usage reads as near-dead, so a usage-only baseline KILLs it — missing
        # that the ticket stream shows people still trying and failing (FIX).
        collapse = np.ones(len(days))
        collapse[break_i:] = 0.015
        rows += _emit(fid, a, days, inten * collapse, "human", rng)
    return rows


def profile_seasonal(fid, accounts, rng):
    days = _all_days()
    months = SEASON_MONTHS[fid]
    rows = []
    users = _pick(rng, accounts, 8)
    for a in users:
        base = {"whale": 50, "mid_market": 28, "smb": 12}[a.band] * rng.uniform(0.8, 1.2)
        season = np.array([base if d.month in months else 0.0 for d in days])
        # genuinely dormant ten months a year: zero off-season. A recent-usage
        # read taken out of season reads it as dead — that is the trap. Two full
        # annual cycles (24-month window) make the periodicity honestly
        # detectable rather than a single bump.
        inten = season * (1.0 + rng.normal(0, 0.12, len(days)))
        rows += _emit(fid, a, days, np.clip(inten, 0, None), "human", rng)
    return rows


def profile_phantom_usage(fid, accounts, rng):
    # human usage is dead; bots and internal QA inflate the totals. A reader who
    # sums across actor types sees a healthy feature — the false KEEP this trap
    # exists to catch.
    days = _all_days()
    rows = []
    # a whisper of real human usage
    for a in _pick(rng, _band(accounts, "smb"), 1):
        inten = _steady(days, 0.6, rng=rng)
        rows += _emit(fid, a, days, inten, "human", rng)
    # heavy bot + QA traffic
    bot_accts = _pick(rng, accounts, 2)
    for a in bot_accts:
        rows += _emit(fid, a, days, _steady(days, 40, rng=rng), "bot", rng)
        rows += _emit(fid, a, days, _steady(days, 18, rng=rng), "internal_qa", rng)
    return rows


def profile_sales_critical(fid, accounts, rng):
    # never used post-signup. Human usage is a flat near-zero. The won-deal notes
    # (attached in deal_notes) are the only reason to keep it.
    days = _all_days()
    rows = []
    for a in _pick(rng, accounts, 2):
        inten = _steady(days, 0.8, rng=rng) * 0.5
        rows += _emit(fid, a, days, inten, "human", rng)
    return rows


PROFILES = {
    "none_keep": profile_none_keep,
    "none_kill": profile_none_kill,
    "contract_bound": profile_contract_bound,
    "hidden_dependency": profile_hidden_dependency,
    "segment_concentrated": profile_segment_concentrated,
    "broken_not_unwanted": profile_broken_not_unwanted,
    "seasonal": profile_seasonal,
    "phantom_usage": profile_phantom_usage,
    "sales_critical": profile_sales_critical,
}


def generate_usage(
    fid: str, trap_class: str, accounts: list[Account], rng: np.random.Generator
) -> list[UsageRow]:
    return PROFILES[trap_class](fid, accounts, rng)
