"""The pre-filter is the cheap path; these tests pin the two properties the safety
story depends on."""

from __future__ import annotations

import csv
from pathlib import Path

import psycopg
import pytest

from sunset.agents.prefilter import prefilter
from sunset.config import settings
from sunset.evidence.metrics import compute_all_metrics
from tests.conftest import requires_db

REPO = Path(__file__).resolve().parents[1]


def _truth():
    with (REPO / "eval" / "truth" / "ground_truth.csv").open() as f:
        return {r["feature_id"]: (r["correct_verdict"], r["trap_class"])
                for r in csv.DictReader(f)}


def _dsn():
    return settings.database_url.replace("postgresql+psycopg://", "postgresql://")


@pytest.fixture(scope="module")
def verdicts():
    with psycopg.connect(_dsn()) as conn:
        m = compute_all_metrics(conn)
    return {fid: prefilter(b) for fid, b in m.items()}


@requires_db
def test_prefilter_only_ever_keeps(verdicts):
    """Structural: the cheap path can only KEEP or defer — never KILL."""
    assert set(verdicts.values()) <= {"obvious_keep", "needs_audit"}


@requires_db
@pytest.mark.gate
def test_zero_false_obvious_keep(verdicts):
    """Every obvious_keep must actually be a KEEP in ground truth. A false keep
    here is a feature that never gets audited — the one thing the pre-filter must
    not do."""
    truth = _truth()
    for fid, pv in verdicts.items():
        if pv == "obvious_keep":
            assert truth[fid][0] == "KEEP", (
                f"{fid} waved through as obvious_keep but truth is {truth[fid]}"
            )


@requires_db
@pytest.mark.gate
def test_phantom_never_obvious_keep(verdicts):
    """Trap 6: if a phantom feature were waved through it would never be audited
    and the trap would score 100% for the wrong reason."""
    truth = _truth()
    for fid, (_v, trap) in truth.items():
        if trap == "phantom_usage":
            assert verdicts[fid] == "needs_audit"


@requires_db
def test_prefilter_resolution_is_reported(verdicts):
    """Not a hard bar — the eval set is deliberately trap-dense, so few features
    are unambiguously healthy. We just assert the pre-filter does *something* and
    never everything."""
    n_keep = sum(1 for v in verdicts.values() if v == "obvious_keep")
    assert 1 <= n_keep < len(verdicts)
