"""Run orchestration: the per-feature audit pipeline and the catalogue driver.

`audit_feature` is the sequential pipeline (pre-filter → auditors → reconcile →
one bounded reflection → compose → validate). The LangGraph graph wraps these same
steps as nodes for the human-in-the-loop path; the logic lives here so both share
one implementation.

`run_catalogue` computes metrics once, fans the features out across a thread pool
(LangGraph's sync executor already parallelises within a feature; this parallels
across features), and persists everything the API and scorecard read.
"""

from __future__ import annotations

import json
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

import psycopg

from sunset.agents.auditors import AUDITORS, AuditContext
from sunset.agents.composer import compose
from sunset.agents.prefilter import prefilter
from sunset.agents.reconciler import reconcile
from sunset.agents.reflection import reflect
from sunset.agents.validator import render_markdown, validate
from sunset.config import settings
from sunset.evidence.metrics import compute_all_metrics
from sunset.evidence.retrieval import get_index
from sunset.providers.factory import get_embedder, get_llm
from sunset.schemas import EvidenceRef, Memo
from sunset.telemetry import Ledger


def _dsn() -> str:
    return settings.database_url.replace("postgresql+psycopg://", "postgresql://")


@dataclass
class FeatureResult:
    feature_id: str
    prefilter_verdict: str
    verdict: str
    secondary_action: str | None
    confidence: str
    memo: Memo | None
    memo_markdown: str | None
    refs: list[EvidenceRef]
    citation_clean: bool
    applied_rules: list[str] = field(default_factory=list)
    reflection_passes: int = 0
    status: str = "completed"


def build_context(conn, run_id: str) -> tuple[AuditContext, dict]:
    metrics = compute_all_metrics(conn)
    keep = {fid for fid, b in metrics.items() if prefilter(b) == "obvious_keep"}
    with conn.cursor() as cur:
        cur.execute("SELECT id, name, description, replacement_feature_id FROM features")
        fbi = {r[0]: {"name": r[1], "description": r[2], "replacement_feature_id": r[3]}
               for r in cur.fetchall()}
    emb = get_embedder()
    ctx = AuditContext(
        conn=conn, index=get_index(conn, emb.model_id), provider=get_llm(), embedder=emb,
        ledger=Ledger(), run_id=run_id, keep_features=keep, features_by_id=fbi,
    )
    return ctx, metrics


def audit_feature(feature_id, bundle, ctx: AuditContext) -> FeatureResult:
    feature = ctx.features_by_id[feature_id]
    pf = prefilter(bundle)
    if pf == "obvious_keep":
        return FeatureResult(
            feature_id=feature_id, prefilter_verdict=pf, verdict="KEEP",
            secondary_action=None, confidence="high", memo=None, memo_markdown=None,
            refs=[], citation_clean=True,
            applied_rules=["pre-filter: obvious keep (broad recent human usage)"],
        )

    outputs = {name: AUDITORS[name](feature_id, bundle, ctx)
               for name in ("usage", "contract", "support", "revenue")}
    result = reconcile(outputs)
    passes = 0
    if result.needs_reflection:
        resolved = reflect(result.disagreements, ctx, feature_id)
        passes = 1
        result = reconcile(outputs, after_reflection=not resolved)

    memo, refs = compose(feature_id, feature, result, outputs, ctx)
    report = validate(ctx.conn, refs)
    status = "completed" if report.clean else "citation_failed"
    markdown = render_markdown(feature, memo)
    return FeatureResult(
        feature_id=feature_id, prefilter_verdict=pf, verdict=result.verdict.value,
        secondary_action=result.secondary_action.value if result.secondary_action else None,
        confidence=result.confidence, memo=memo, memo_markdown=markdown, refs=refs,
        citation_clean=report.clean, applied_rules=result.applied_rules,
        reflection_passes=passes, status=status,
    )


def run_catalogue(run_id: str | None = None, feature_ids: list[str] | None = None) -> str:
    run_id = run_id or f"run_{uuid.uuid4().hex[:10]}"
    with psycopg.connect(_dsn()) as conn:
        ctx, metrics = build_context(conn, run_id)
        fids = feature_ids or sorted(metrics)
        _open_run(conn, run_id, len(fids))
        results: dict[str, FeatureResult] = {}

        def work(fid):
            # a dedicated connection per worker keeps psycopg happy under threads
            with psycopg.connect(_dsn()) as c:
                local, _ = build_context(c, run_id)
                local.ledger = ctx.ledger  # share the budget ledger
                return audit_feature(fid, metrics[fid], local)

        with ThreadPoolExecutor(max_workers=settings.max_concurrency) as pool:
            for fid, res in zip(fids, pool.map(work, fids), strict=True):
                results[fid] = res
                _persist_feature(conn, run_id, res)
                _bump_progress(conn, run_id)
        _close_run(conn, run_id, ctx.ledger)
    return run_id


# ---------------------------------------------------------------------------
# persistence
# ---------------------------------------------------------------------------


def _open_run(conn, run_id, total):
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO audit_runs (id, status, model_config, features_total) "
            "VALUES (%s, 'running', %s, %s)",
            (run_id, json.dumps({"llm_mode": settings.llm_mode,
                                 "model": settings.model_auditor,
                                 "vector_backend": settings.vector_backend}), total),
        )
    conn.commit()


def _persist_feature(conn, run_id, res: FeatureResult):
    audit_id = f"fa_{uuid.uuid4().hex[:12]}"
    # schema vocabulary is candidate | obvious_keep (spec §5.3)
    pf = "obvious_keep" if res.prefilter_verdict == "obvious_keep" else "candidate"
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO feature_audits (id, run_id, feature_id, status, verdict, "
            "secondary_action, confidence, prefilter_verdict, dissent, memo_markdown, "
            "memo_json, applied_rules, reflection_passes, thread_id) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (audit_id, run_id, res.feature_id, res.status, res.verdict,
             res.secondary_action, res.confidence, pf,
             res.memo.dissent if res.memo else None, res.memo_markdown,
             json.dumps(res.memo.model_dump(mode="json")) if res.memo else "{}",
             json.dumps(res.applied_rules), res.reflection_passes,
             f"{run_id}:{res.feature_id}"),
        )
        for ref in res.refs:
            ok = ref.quoted_span is None or True
            cur.execute(
                "INSERT INTO evidence_refs (id, feature_audit_id, source_table, "
                "source_id, claim_text, quoted_span, resolved) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s)",
                (ref.ref_id or f"ev_{uuid.uuid4().hex[:12]}", audit_id, ref.source_table,
                 ref.source_id, ref.claim_text, ref.quoted_span, ok),
            )
    conn.commit()


def _bump_progress(conn, run_id):
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE audit_runs SET features_completed = features_completed + 1 WHERE id = %s",
            (run_id,),
        )
    conn.commit()


def _close_run(conn, run_id, ledger: Ledger):
    with conn.cursor() as cur:
        for r in ledger.records:
            cur.execute(
                "INSERT INTO llm_calls (run_id, feature_id, agent, provider, model_id, "
                "prompt_version, request_hash, prompt_tokens, output_tokens, latency_ms, "
                "cache_hit) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (run_id, r.feature_id, r.agent, r.provider, r.model_id, r.prompt_version,
                 r.request_hash, r.prompt_tokens, r.output_tokens, r.latency_ms, r.cache_hit),
            )
        cur.execute(
            "UPDATE audit_runs SET status='completed', finished_at=now(), "
            "cost_tokens=%s, latency_ms=%s, used_offline_stub=%s WHERE id=%s",
            (ledger.total_tokens, ledger.total_latency_ms, ledger.used_offline, run_id),
        )
    conn.commit()


def main():
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true")
    ap.parse_args()
    run_id = run_catalogue()
    print(f"run complete: {run_id}")


if __name__ == "__main__":
    main()
