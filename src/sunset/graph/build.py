"""The feature-audit graph and its invoke/resume driver.

Flow:  audit -> human_gate -> finalize

The auditors' parallelism already lives in runner.ThreadPoolExecutor; LangGraph is
here for the one thing plain Python can't do cleanly — pause at a human gate,
persist, and resume later, possibly in another process. The gate interrupts ONLY
when the stakes warrant it (verdict in {ESCALATE, KILL} or low confidence);
blocking a human on all 40 features would make the tool unusable.

A 'fact' override does not need per-auditor nodes: it invalidates one auditor's
cache row and re-invokes, and the auditor cache makes the other three free — so
exactly one auditor re-runs.
"""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from sunset.graph.state import FeatureAuditState
from sunset.runner import audit_feature

GATING_VERDICTS = {"ESCALATE", "KILL"}


def _ctx_and_bundle(config):
    cfg = config["configurable"]
    return cfg["ctx"], cfg["bundle"]


def _audit_node(state: FeatureAuditState, config) -> dict:
    ctx, bundle = _ctx_and_bundle(config)
    res = audit_feature(state["feature_id"], bundle, ctx)
    needs_review = res.verdict in GATING_VERDICTS or res.confidence == "low"
    return {
        "prefilter_verdict": res.prefilter_verdict,
        "verdict": res.verdict,
        "secondary_action": res.secondary_action,
        "confidence": res.confidence,
        "applied_rules": res.applied_rules,
        "reflection_passes": res.reflection_passes,
        "memo_markdown": res.memo_markdown,
        "dissent": res.memo.dissent if res.memo else None,
        "citation_clean": res.citation_clean,
        "needs_review": needs_review,
        "status": "awaiting_review" if needs_review else "completed",
        "trace": [f"audit -> {res.verdict} (review={needs_review})"],
    }


def _human_gate(state: FeatureAuditState, config) -> dict:
    if not state.get("needs_review"):
        return {"trace": ["gate: auto-approved"]}
    # pause here; the payload is everything a reviewer needs without another call
    decision = interrupt({
        "feature_id": state["feature_id"],
        "verdict": state["verdict"],
        "confidence": state["confidence"],
        "memo_markdown": state["memo_markdown"],
        "dissent": state.get("dissent"),
        "applied_rules": state.get("applied_rules", []),
    })
    # resumed with an override payload
    override = decision or {}
    new_verdict = override.get("new_verdict")
    if new_verdict:
        return {
            "verdict": new_verdict,
            "human_override": override,
            "status": "completed",
            "trace": [f"gate: human override -> {new_verdict} ({override.get('reason','')})"],
        }
    return {"status": "completed", "human_override": override or {"decision": "approved"},
            "trace": ["gate: human approved as-is"]}


def _finalize(state: FeatureAuditState, config) -> dict:
    return {"status": "completed", "trace": ["finalize"]}


def build_graph(checkpointer):
    g = StateGraph(FeatureAuditState)
    g.add_node("audit", _audit_node)
    g.add_node("human_gate", _human_gate)
    g.add_node("finalize", _finalize)
    g.add_edge(START, "audit")
    g.add_edge("audit", "human_gate")
    g.add_edge("human_gate", "finalize")
    g.add_edge("finalize", END)
    return g.compile(checkpointer=checkpointer)


# ---------------------------------------------------------------------------
# Drivers used by the API
# ---------------------------------------------------------------------------


def _config(run_id, feature_id, ctx, bundle):
    return {"configurable": {
        "thread_id": f"{run_id}:{feature_id}", "ctx": ctx, "bundle": bundle,
    }}


def invoke_feature(checkpointer, run_id, feature_id, ctx, bundle) -> dict:
    graph = build_graph(checkpointer)
    return graph.invoke({"feature_id": feature_id, "run_id": run_id},
                        _config(run_id, feature_id, ctx, bundle))


def resume_feature(checkpointer, run_id, feature_id, ctx, bundle, override: dict) -> dict:
    graph = build_graph(checkpointer)
    return graph.invoke(Command(resume=override),
                        _config(run_id, feature_id, ctx, bundle))
