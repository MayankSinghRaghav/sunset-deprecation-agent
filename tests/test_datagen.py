"""Phase-3 gate as tests: no leaks, signal is detectable, fixtures are reproducible."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import psycopg
import pytest
from datagen.fixtures_io import FIX
from datagen.generate import build_all
from datagen.lint import check_leaks, check_signals

from sunset.config import settings
from tests.conftest import requires_db

REPO = Path(__file__).resolve().parents[1]


def _dsn() -> str:
    return settings.database_url.replace("postgresql+psycopg://", "postgresql://")


def test_no_verdict_or_trap_leaks_in_fixtures():
    problems = check_leaks()
    assert not problems, "evidence must not leak labels:\n" + "\n".join(problems)


def test_build_all_is_deterministic():
    a = build_all()
    b = build_all()
    assert {k: len(v) for k, v in a.items()} == {k: len(v) for k, v in b.items()}
    # spot-check the usage series is identical
    assert a["usage"][:50] == b["usage"][:50]
    assert a["usage"][-50:] == b["usage"][-50:]


def test_committed_fixtures_match_manifest():
    manifest = json.loads((FIX / "MANIFEST.json").read_text())
    for name, sha in manifest["files"].items():
        actual = hashlib.sha256((FIX / name).read_bytes()).hexdigest()
        assert actual == sha, f"{name} differs from MANIFEST (regenerate fixtures)"


@requires_db
@pytest.mark.gate
def test_signal_is_detectable_in_raw_evidence():
    with psycopg.connect(_dsn()) as conn:
        fails = check_signals(conn)
    assert not fails, "trap signals not detectable in raw evidence:\n" + "\n".join(fails)
