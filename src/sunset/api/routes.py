"""The 12 endpoints (spec §7). No thirteenth — tests/test_api_contract pins the set.

Runs are long, so POST /runs uses a BackgroundTask with progress polling (no
Celery, no Redis — one user). The override endpoint routes through the LangGraph
checkpoint/resume machinery so a human decision demonstrably resumes the graph
rather than restarting it.
"""

from __future__ import annotations

import uuid

import psycopg
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel

from sunset.api.deps import dict_rows, dsn, get_conn
from sunset.evidence.refs import resolve
from sunset.schemas import EvidenceRef

router = APIRouter()


# ---- runs -----------------------------------------------------------------


@router.post("/runs")
def start_run(background: BackgroundTasks) -> dict:
    from sunset.runner import run_catalogue

    run_id = f"run_{uuid.uuid4().hex[:10]}"
    background.add_task(run_catalogue, run_id)
    return {"run_id": run_id, "status": "running"}


@router.get("/runs")
def list_runs(conn=Depends(get_conn)) -> list[dict]:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, status, features_completed, features_total, cost_tokens, "
            "used_offline_stub, started_at FROM audit_runs ORDER BY started_at DESC LIMIT 20")
        return dict_rows(cur)


@router.get("/runs/{run_id}")
def get_run(run_id: str, conn=Depends(get_conn)) -> dict:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, status, features_completed, features_total, cost_tokens, "
            "latency_ms, used_offline_stub, model_config, started_at, finished_at "
            "FROM audit_runs WHERE id=%s", (run_id,))
        rows = dict_rows(cur)
    if not rows:
        raise HTTPException(404, "run not found")
    return rows[0]


@router.get("/runs/{run_id}/audits")
def run_audits(run_id: str, verdict: str | None = Query(None),
               conn=Depends(get_conn)) -> list[dict]:
    q = ("SELECT fa.id, fa.feature_id, f.name, fa.verdict, fa.secondary_action, "
         "fa.confidence, fa.status, f.annual_maintenance_usd "
         "FROM feature_audits fa JOIN features f ON f.id=fa.feature_id WHERE fa.run_id=%s")
    args: list = [run_id]
    if verdict:
        q += " AND fa.verdict=%s"
        args.append(verdict)
    q += " ORDER BY fa.feature_id"
    with conn.cursor() as cur:
        cur.execute(q, tuple(args))
        return dict_rows(cur)


# ---- audits ---------------------------------------------------------------


@router.get("/audits/{audit_id}")
def get_audit(audit_id: str, conn=Depends(get_conn)) -> dict:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT fa.*, f.name AS feature_name FROM feature_audits fa "
            "JOIN features f ON f.id=fa.feature_id WHERE fa.id=%s", (audit_id,))
        rows = dict_rows(cur)
        if not rows:
            raise HTTPException(404, "audit not found")
        audit = rows[0]
        cur.execute(
            "SELECT id, source_table, source_id, claim_text, quoted_span, resolved "
            "FROM evidence_refs WHERE feature_audit_id=%s", (audit_id,))
        audit["evidence"] = dict_rows(cur)
        cur.execute("SELECT kind, original_verdict, new_verdict, reason, created_at "
                    "FROM human_overrides WHERE feature_audit_id=%s ORDER BY created_at",
                    (audit_id,))
        audit["overrides"] = dict_rows(cur)
    return audit


@router.get("/audits/{audit_id}/memo")
def get_memo(audit_id: str, conn=Depends(get_conn)) -> dict:
    with conn.cursor() as cur:
        cur.execute("SELECT feature_id, verdict, memo_markdown, dissent "
                    "FROM feature_audits WHERE id=%s", (audit_id,))
        rows = dict_rows(cur)
    if not rows:
        raise HTTPException(404, "audit not found")
    return rows[0]


class OverrideBody(BaseModel):
    new_verdict: str
    reason: str
    kind: str = "decision"  # decision | fact
    target_auditor: str | None = None


@router.post("/audits/{audit_id}/override")
def override(audit_id: str, body: OverrideBody, conn=Depends(get_conn)) -> dict:
    from sunset.graph.build import invoke_feature, resume_feature
    from sunset.graph.cache import cache_invalidate
    from sunset.graph.checkpoint import checkpointer
    from sunset.runner import build_context

    with conn.cursor() as cur:
        cur.execute("SELECT run_id, feature_id, verdict FROM feature_audits WHERE id=%s",
                    (audit_id,))
        row = cur.fetchone()
    if not row:
        raise HTTPException(404, "audit not found")
    run_id, feature_id, original = row

    if body.kind == "fact" and body.target_auditor:
        cache_invalidate(conn, feature_id, body.target_auditor)

    with checkpointer() as cp, psycopg.connect(dsn()) as c2:
        ctx, metrics = build_context(c2, run_id)
        bundle = metrics[feature_id]
        res = invoke_feature(cp, run_id, feature_id, ctx, bundle)
        if "__interrupt__" in res:
            res = resume_feature(cp, run_id, feature_id, ctx, bundle,
                                 {"new_verdict": body.new_verdict, "reason": body.reason})
        new_verdict = res.get("verdict", body.new_verdict)

    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO human_overrides (id, feature_audit_id, kind, original_verdict, "
            "new_verdict, target_auditor, reason) VALUES (%s,%s,%s,%s,%s,%s,%s)",
            (f"ov_{uuid.uuid4().hex[:10]}", audit_id, body.kind, original,
             body.new_verdict, body.target_auditor, body.reason))
        cur.execute("UPDATE feature_audits SET verdict=%s, status='completed' WHERE id=%s",
                    (new_verdict, audit_id))
    conn.commit()
    return {"audit_id": audit_id, "original_verdict": original,
            "new_verdict": new_verdict, "resumed_from_checkpoint": True}


@router.get("/audits/{audit_id}/evidence/{ref_id}")
def get_evidence(audit_id: str, ref_id: str, conn=Depends(get_conn)) -> dict:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT source_table, source_id, claim_text, quoted_span "
            "FROM evidence_refs WHERE id=%s AND feature_audit_id=%s", (ref_id, audit_id))
        rows = dict_rows(cur)
    if not rows:
        raise HTTPException(404, "evidence ref not found")
    r = rows[0]
    ref = EvidenceRef(ref_id=ref_id, source_table=r["source_table"],
                      source_id=r["source_id"], claim_text=r["claim_text"],
                      quoted_span=r["quoted_span"])
    ok, err = resolve(conn, ref)
    return {**r, "resolves": ok, "error": err}


# ---- catalogue / accounts / eval -----------------------------------------


@router.get("/features")
def features(conn=Depends(get_conn)) -> list[dict]:
    with conn.cursor() as cur:
        cur.execute("SELECT id, name, area, maintenance_cost_band, annual_maintenance_usd, "
                    "replacement_feature_id FROM features ORDER BY id")
        return dict_rows(cur)


@router.get("/accounts/{account_id}/exposure")
def account_exposure(account_id: str, conn=Depends(get_conn)) -> dict:
    """Invert the product: what would this account lose if we removed the features
    the latest run flagged for removal?"""
    with conn.cursor() as cur:
        cur.execute("SELECT id, name, arr_band, arr_usd FROM accounts WHERE id=%s",
                    (account_id,))
        acc = dict_rows(cur)
        if not acc:
            raise HTTPException(404, "account not found")
        cur.execute(
            "SELECT id FROM audit_runs WHERE status='completed' ORDER BY started_at DESC LIMIT 1")
        run = cur.fetchone()
        losses: list[dict] = []
        if run:
            cur.execute(
                "SELECT DISTINCT f.id, f.name, fa.verdict FROM feature_audits fa "
                "JOIN features f ON f.id=fa.feature_id "
                "JOIN usage_daily u ON u.feature_id=f.id "
                "WHERE fa.run_id=%s AND fa.verdict IN ('KILL','MIGRATE') "
                "AND u.account_id=%s AND u.actor_type='human' ORDER BY f.id",
                (run[0], account_id))
            losses = dict_rows(cur)
    return {"account": acc[0], "would_lose": losses}


@router.get("/eval/scorecard")
def scorecard() -> dict:
    from eval.baseline import baseline_predictions
    from eval.holdout import DEV, HOLDOUT
    from eval.score import agent_predictions, score

    def pack(sc):
        return {
            "label": sc.label, "n": sc.n, "correct": sc.correct,
            "accuracy": None if sc.used_offline else round(sc.accuracy, 3),
            "used_offline_stub": sc.used_offline,
            "catastrophic_kills": sc.catastrophic_kills,
            "catastrophic_rate": round(sc.catastrophic_rate, 3),
            "escalation_precision": round(sc.escalation_precision, 3),
            "per_trap": sc.per_trap,
        }

    base = baseline_predictions()
    out = {"baseline": pack(score(base, "baseline"))}
    agent = agent_predictions()
    if agent:
        out["agent"] = pack(score(agent, "agent"))
        out["agent_dev"] = pack(score(agent, "agent-dev", DEV))
        out["agent_holdout"] = pack(score(agent, "agent-holdout", HOLDOUT))
    return out
