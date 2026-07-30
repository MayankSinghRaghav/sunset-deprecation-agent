"""The human-in-the-loop gate: interrupt, survive a process restart, resume with an
override that changes the verdict — and a 'fact' override that re-runs exactly one
auditor via the cache. This is the Week-5 gate and the reason LangGraph is here."""

from __future__ import annotations

import psycopg
import pytest

from sunset.config import settings
from sunset.graph.build import invoke_feature, resume_feature
from sunset.graph.cache import cache_invalidate
from sunset.graph.checkpoint import checkpointer
from sunset.runner import build_context
from tests.conftest import requires_db


def _dsn():
    return settings.database_url.replace("postgresql+psycopg://", "postgresql://")


@requires_db
@pytest.mark.gate
def test_gate_interrupts_then_resume_overrides_across_restart():
    run_id = "resume_test"
    fid = "f13"  # contract-obligated -> ESCALATE -> gates

    # invocation: run to the gate
    with checkpointer() as cp, psycopg.connect(_dsn()) as conn:
        ctx, metrics = build_context(conn, run_id)
        res = invoke_feature(cp, run_id, fid, ctx, metrics[fid])
    assert res["status"] == "awaiting_review"
    assert "__interrupt__" in res

    # NEW checkpointer + NEW connection == a process restart
    with checkpointer() as cp, psycopg.connect(_dsn()) as conn:
        ctx, metrics = build_context(conn, run_id)
        res2 = resume_feature(cp, run_id, fid, ctx, metrics[fid],
                              {"new_verdict": "KEEP", "reason": "legal cleared it"})
    assert res2["status"] == "completed"
    assert res2["verdict"] == "KEEP"
    assert res2["human_override"]["reason"] == "legal cleared it"


@requires_db
def test_non_gating_feature_completes_without_interrupt():
    run_id = "nogate_test"
    fid = "f30"  # seasonal -> KEEP -> no gate
    with checkpointer() as cp, psycopg.connect(_dsn()) as conn:
        ctx, metrics = build_context(conn, run_id)
        res = invoke_feature(cp, run_id, fid, ctx, metrics[fid])
    assert res["status"] == "completed"
    assert "__interrupt__" not in res


@requires_db
@pytest.mark.gate
def test_fact_override_reruns_exactly_one_auditor():
    """Invalidate one auditor's cache; re-running must recompute only that auditor
    (the other three are cache hits)."""
    run_id = "factoverride_test"
    fid = "f13"
    with psycopg.connect(_dsn()) as conn:
        from sunset.runner import audit_feature

        ctx, metrics = build_context(conn, run_id)
        audit_feature(fid, metrics[fid], ctx)  # warm the cache (4 auditors)

        cache_invalidate(conn, fid, "contract")

        ctx2, _ = build_context(conn, run_id)
        audit_feature(fid, metrics[fid], ctx2)
        # count fresh (non-cache) auditor calls in the second pass
        fresh = [r for r in ctx2.ledger.records
                 if r.agent in ("usage", "contract", "support", "revenue")
                 and not r.cache_hit]
        assert len(fresh) == 1 and fresh[0].agent == "contract", \
            f"expected only contract to re-run, got {[r.agent for r in fresh]}"
