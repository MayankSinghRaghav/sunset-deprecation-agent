"""Metrics carry the traps. If a trap's signal stops firing here, the auditor that
depends on it is blind. These run against the seeded DB."""

from __future__ import annotations

import csv
from pathlib import Path

import psycopg
import pytest

from sunset.config import settings
from sunset.evidence.metrics import compute_all_metrics
from tests.conftest import requires_db

REPO = Path(__file__).resolve().parents[1]


def _truth():
    with (REPO / "eval" / "truth" / "ground_truth.csv").open() as f:
        return {r["feature_id"]: r["trap_class"] for r in csv.DictReader(f)}


def _dsn():
    return settings.database_url.replace("postgresql+psycopg://", "postgresql://")


@pytest.fixture(scope="module")
def metrics():
    with psycopg.connect(_dsn()) as conn:
        return compute_all_metrics(conn)


def _fids(trap):
    return [f for f, t in _truth().items() if t == trap]


@requires_db
@pytest.mark.gate
def test_phantom_fires_only_for_phantom(metrics):
    for fid in _fids("phantom_usage"):
        assert metrics[fid].phantom_usage, f"{fid} should read as phantom"
    for fid in _fids("none_keep") + _fids("none_kill"):
        assert not metrics[fid].phantom_usage, f"{fid} wrongly flagged phantom"


@requires_db
@pytest.mark.gate
def test_seasonality_fires_only_for_seasonal(metrics):
    for fid in _fids("seasonal"):
        assert metrics[fid].seasonality_detected, f"{fid} should read as seasonal"
    for fid in _fids("none_keep") + _fids("none_kill"):
        assert not metrics[fid].seasonality_detected


@requires_db
@pytest.mark.gate
def test_concentration_fires_only_for_concentrated(metrics):
    for fid in _fids("segment_concentrated"):
        assert metrics[fid].revenue_concentrated, f"{fid} should read as concentrated"
    for fid in _fids("none_keep"):
        assert not metrics[fid].revenue_concentrated


@requires_db
@pytest.mark.gate
def test_defect_after_drop_fires_only_for_broken(metrics):
    for fid in _fids("broken_not_unwanted"):
        assert metrics[fid].defect_after_drop, f"{fid} should show a defect after a drop"
    for fid in _fids("none_kill"):
        assert not metrics[fid].defect_after_drop


@requires_db
@pytest.mark.gate
def test_hidden_dependency_has_inbound_keep_edge(metrics):
    for fid in _fids("hidden_dependency"):
        assert metrics[fid].inbound_from_keep, f"{fid} should have an inbound KEEP edge"
    # and no would-be-KILL feature may (rule 5 would wrongly cap it)
    for fid in _fids("none_kill") + _fids("phantom_usage"):
        assert not metrics[fid].inbound_from_keep, f"{fid} has a mis-capping edge"
