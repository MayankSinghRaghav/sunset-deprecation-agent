"""The API surface is a contract. The spec's twelve core endpoints (§7) plus two
frontend view endpoints — /catalogue and /features/{id}/memo-view — that shape
the same real audit data into what the UI renders. The set is still pinned: a
stray endpoint beyond this set fails the test. Plus smoke tests against the
seeded DB."""

from __future__ import annotations

import psycopg
import pytest
from fastapi.testclient import TestClient

from sunset.api.app import app
from sunset.config import settings
from tests.conftest import requires_db

client = TestClient(app)

EXPECTED_ROUTES = {
    ("GET", "/"),
    ("POST", "/runs"),
    ("GET", "/runs"),
    ("GET", "/runs/{run_id}"),
    ("GET", "/runs/{run_id}/audits"),
    ("GET", "/audits/{audit_id}"),
    ("GET", "/audits/{audit_id}/memo"),
    ("POST", "/audits/{audit_id}/override"),
    ("GET", "/audits/{audit_id}/evidence/{ref_id}"),
    ("GET", "/features"),
    ("GET", "/accounts/{account_id}/exposure"),
    ("GET", "/eval/scorecard"),
    # frontend view endpoints (real audit data, UI-shaped)
    ("GET", "/catalogue"),
    ("GET", "/features/{feature_id}/memo-view"),
}


def _dsn():
    return settings.database_url.replace("postgresql+psycopg://", "postgresql://")


def test_endpoint_set_is_pinned():
    spec = app.openapi()
    routes = {(m.upper(), path) for path, methods in spec["paths"].items() for m in methods}
    assert routes == EXPECTED_ROUTES, (
        f"unexpected: {routes - EXPECTED_ROUTES}, missing: {EXPECTED_ROUTES - routes}")


def test_root_states_positioning():
    r = client.get("/")
    assert r.status_code == 200
    assert "human signs the death warrant" in r.json()["positioning"]


@requires_db
def test_features_returns_catalogue():
    r = client.get("/features")
    assert r.status_code == 200
    assert len(r.json()) == 40


@requires_db
def test_scorecard_has_baseline_and_offline_guard():
    r = client.get("/eval/scorecard")
    assert r.status_code == 200
    body = r.json()
    assert "baseline" in body
    assert body["baseline"]["accuracy"] is not None  # baseline is a real number
    if "agent" in body:
        # an offline agent run must NOT expose an accuracy number
        assert body["agent"]["accuracy"] is None
        assert body["agent"]["used_offline_stub"] is True


@requires_db
def test_account_exposure_inverts_the_product():
    r = client.get("/accounts/a01/exposure")
    assert r.status_code == 200
    assert r.json()["account"]["id"] == "a01"
    assert "would_lose" in r.json()


@requires_db
def test_memo_endpoint_for_a_persisted_audit():
    with psycopg.connect(_dsn()) as conn, conn.cursor() as cur:
        cur.execute("SELECT id FROM feature_audits WHERE memo_markdown IS NOT NULL LIMIT 1")
        row = cur.fetchone()
    if not row:
        pytest.skip("no persisted audit with a memo yet")
    r = client.get(f"/audits/{row[0]}/memo")
    assert r.status_code == 200
    assert "Dissent" in (r.json()["memo_markdown"] or "")
