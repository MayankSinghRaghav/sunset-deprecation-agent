"""The tests that carry the product's central integrity claim: the agent cannot
read the answer key, and the agent package cannot import its way around that.

Three independent layers:
  1. DB role denial   — sunset_app is REVOKE'd from schema truth.
  2. Import isolation  — src/sunset/** never imports datagen or eval.
  3. (fixture leak)    — no app-visible fixture carries a verdict/trap label.
                         Enforced in datagen/lint.py and its own test.
"""

from __future__ import annotations

import ast
import pathlib

import pytest
from sqlalchemy import text

from tests.conftest import requires_db

REPO = pathlib.Path(__file__).resolve().parents[1]
SUNSET_PKG = REPO / "src" / "sunset"


# ---------------------------------------------------------------------------
# Layer 1: the running agent physically cannot read ground truth.
# ---------------------------------------------------------------------------


@requires_db
def test_app_role_denied_on_truth_schema(app_engine):
    """sunset_app must be denied on schema truth, whether or not a table exists."""
    from sqlalchemy.exc import ProgrammingError

    with pytest.raises(ProgrammingError) as ei:
        with app_engine.connect() as c:
            c.execute(text("SELECT 1 FROM truth.ground_truth LIMIT 1"))
    msg = str(ei.value).lower()
    assert "permission denied" in msg, f"expected permission denial, got: {msg}"


@requires_db
def test_app_role_cannot_create_in_truth_schema(app_engine):
    from sqlalchemy.exc import ProgrammingError

    with pytest.raises(ProgrammingError) as ei:
        with app_engine.begin() as c:
            c.execute(text("CREATE TABLE truth.sneaky (x int)"))
    assert "permission denied" in str(ei.value).lower()


# ---------------------------------------------------------------------------
# Layer 2: the agent package cannot import the generator or the scorer.
# ---------------------------------------------------------------------------

FORBIDDEN_TOP_LEVEL = {"datagen", "eval"}

# The agent's DECISION path must never import the generator or the scorer. The API
# presentation layer (src/sunset/api) is exempt for exactly one reason: the
# /eval/scorecard endpoint is the eval surface itself and aggregates baseline-vs-
# agent numbers. The hard guarantee is unaffected — the agent connects as
# sunset_app, which is REVOKE'd from schema truth at the database level.
EXEMPT_DIRS = {SUNSET_PKG / "api"}


def _iter_py_files(root: pathlib.Path):
    for p in root.rglob("*.py"):
        if any(exempt in p.parents for exempt in EXEMPT_DIRS):
            continue
        yield p


def test_sunset_agent_core_never_imports_datagen_or_eval():
    offenders: list[str] = []
    for path in _iter_py_files(SUNSET_PKG):
        tree = ast.parse(path.read_text(), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    top = alias.name.split(".")[0]
                    if top in FORBIDDEN_TOP_LEVEL:
                        offenders.append(f"{path.relative_to(REPO)}: import {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                top = (node.module or "").split(".")[0]
                if top in FORBIDDEN_TOP_LEVEL:
                    offenders.append(
                        f"{path.relative_to(REPO)}: from {node.module} import ..."
                    )
    assert not offenders, "src/sunset must not import datagen/eval:\n" + "\n".join(offenders)


def test_sunset_never_references_truth_path():
    """The agent must not even know where the truth sheet lives."""
    offenders: list[str] = []
    for path in _iter_py_files(SUNSET_PKG):
        src = path.read_text()
        if "SUNSET_TRUTH_PATH" in src or "ground_truth" in src:
            offenders.append(str(path.relative_to(REPO)))
    assert not offenders, "src/sunset references ground truth: " + ", ".join(offenders)
