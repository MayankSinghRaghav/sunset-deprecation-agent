"""End-to-end: the offline pipeline over the whole catalogue must beat the baseline
on the traps, keep catastrophic errors at zero, and validate every citation.

This is the Week-4 gate. The accuracy HEADLINE is suppressed for an offline run,
but the per-trap structure, the catastrophic count, and citation validity are all
real and asserted here."""

from __future__ import annotations

import psycopg
import pytest

from sunset.config import settings
from sunset.runner import audit_feature, build_context
from tests.conftest import requires_db


def _dsn():
    return settings.database_url.replace("postgresql+psycopg://", "postgresql://")


@pytest.fixture(scope="module")
def results():
    with psycopg.connect(_dsn()) as conn:
        ctx, metrics = build_context(conn, "test_run")
        return {fid: audit_feature(fid, metrics[fid], ctx) for fid in sorted(metrics)}


def _truth():
    import csv
    from pathlib import Path
    p = Path(__file__).resolve().parents[1] / "eval" / "truth" / "ground_truth.csv"
    with p.open() as f:
        return {r["feature_id"]: (r["correct_verdict"], r["trap_class"])
                for r in csv.DictReader(f)}


@requires_db
@pytest.mark.gate
def test_no_catastrophic_kills(results):
    """The absolute bar (spec §3.1): zero KILLs on contract-bound or
    revenue-concentrated features."""
    truth = _truth()
    breaches = [
        fid for fid, r in results.items()
        if r.verdict == "KILL" and truth[fid][1] in ("contract_bound", "segment_concentrated")
    ]
    assert not breaches, f"catastrophic KILLs: {breaches}"


@requires_db
@pytest.mark.gate
def test_all_citations_resolve(results):
    """Citation validity must be 100% — a hallucinated citation never ships."""
    dirty = [fid for fid, r in results.items() if not r.citation_clean]
    assert not dirty, f"features with unresolved citations: {dirty}"


@requires_db
@pytest.mark.gate
def test_agent_beats_baseline_on_the_hard_traps(results):
    """Traps the baseline scores 0/4 on must be substantially recovered."""
    truth = _truth()
    for trap in ["contract_bound", "hidden_dependency", "segment_concentrated",
                 "broken_not_unwanted", "phantom_usage"]:
        fids = [f for f, (_v, t) in truth.items() if t == trap]
        correct = sum(1 for f in fids if results[f].verdict == truth[f][0])
        assert correct >= 3, f"{trap}: only {correct}/4 (baseline gets 0)"


@requires_db
def test_reflection_never_exceeds_one_pass(results):
    for r in results.values():
        assert r.reflection_passes <= 1


@requires_db
def test_dissent_is_never_empty(results):
    for r in results.values():
        if r.memo is not None:
            assert r.memo.dissent.strip(), f"{r.feature_id} has empty dissent"
