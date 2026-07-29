"""Freeze the deterministic baseline. These numbers are quoted in the case study;
if a change moves them, that is a deliberate act that must be logged in
eval/CHANGELOG.md, not an accident.
"""

from __future__ import annotations

import pytest
from eval.baseline import baseline_predictions
from eval.holdout import DEV, HOLDOUT
from eval.score import score

from tests.conftest import requires_db


@requires_db
@pytest.mark.gate
def test_baseline_frozen_numbers():
    preds = baseline_predictions()
    sc = score(preds, "baseline")
    # frozen: seed-1337 fixtures, rules in eval/baseline.py
    assert sc.correct == 13, f"baseline moved to {sc.correct}/40 — update CHANGELOG"
    assert sc.n == 40
    assert 0.25 <= sc.accuracy < 0.75, "baseline outside the sane band"


@requires_db
@pytest.mark.gate
def test_baseline_commits_a_contract_breach():
    """The whole point of §3.1: the naive baseline KILLs contract-bound features.
    The agent must later drive this to zero."""
    preds = baseline_predictions()
    sc = score(preds, "baseline")
    assert len(sc.catastrophic_kills) >= 2, (
        "baseline should breach at least two contracts; "
        f"got {sc.catastrophic_kills}"
    )


@requires_db
@pytest.mark.gate
def test_baseline_fails_the_hard_traps():
    """Traps that need semantic/structured/graph reading are unreachable for a
    naive baseline. If any of these is above zero, either the data leaked or the
    baseline is doing something it should not."""
    preds = baseline_predictions()
    sc = score(preds, "baseline")
    for trap in ["hidden_dependency", "segment_concentrated",
                 "phantom_usage", "sales_critical"]:
        correct, total = sc.per_trap[trap]
        assert correct == 0, f"baseline unexpectedly scored {correct}/{total} on {trap}"


@requires_db
def test_holdout_is_never_scored_during_dev():
    """Sanity: dev and holdout partition the 40, and holdout is 12."""
    assert len(HOLDOUT) == 12
    assert DEV.isdisjoint(HOLDOUT)
    assert len(DEV | HOLDOUT) == 40
