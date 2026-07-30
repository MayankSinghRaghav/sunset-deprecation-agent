"""The scoring harness. The one place ground truth is read at evaluation time.

Reports the three ways the spec (§3.1) demands:
  1. overall accuracy
  2. per-trap-class accuracy  — the number that goes in the case study
  3. catastrophic error rate  — share of KILL verdicts that ground truth says are
     contract-bound or revenue-concentrated. The agent's must be zero.

Plus escalation precision, trap-7 correctness, and — critically — a guard: if any
prediction came from a run that used the offline stub, the accuracy HEADLINE is
suppressed and replaced with "OFFLINE STUB — not a model score", so a stub run can
never be screenshotted as a model result.
"""

from __future__ import annotations

import csv
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
TRUTH = REPO / "eval" / "truth" / "ground_truth.csv"

# ground truth says these traps are the ones you must never KILL
CATASTROPHIC_TRAPS = {"contract_bound", "segment_concentrated"}


@dataclass(frozen=True)
class TruthRow:
    feature_id: str
    verdict: str
    secondary_action: str
    trap_class: str


@dataclass
class Prediction:
    feature_id: str
    verdict: str
    secondary_action: str | None = None
    used_offline: bool = False


@dataclass
class Scorecard:
    label: str
    n: int
    correct: int
    per_trap: dict[str, tuple[int, int]]  # trap -> (correct, total)
    catastrophic_kills: list[str]
    kill_count: int
    escalate_predicted: list[str]
    escalate_correct: int
    used_offline: bool = False
    notes: list[str] = field(default_factory=list)

    @property
    def accuracy(self) -> float:
        return self.correct / self.n if self.n else 0.0

    @property
    def catastrophic_rate(self) -> float:
        return len(self.catastrophic_kills) / self.kill_count if self.kill_count else 0.0

    @property
    def escalation_precision(self) -> float:
        return (
            self.escalate_correct / len(self.escalate_predicted)
            if self.escalate_predicted else 1.0
        )


def load_truth() -> dict[str, TruthRow]:
    out: dict[str, TruthRow] = {}
    with TRUTH.open() as f:
        for r in csv.DictReader(f):
            out[r["feature_id"]] = TruthRow(
                r["feature_id"], r["correct_verdict"].strip(),
                r["secondary_action"].strip(), r["trap_class"].strip(),
            )
    return out


def _is_correct(pred: Prediction, t: TruthRow) -> bool:
    if pred.verdict != t.verdict:
        return False
    # trap 7 requires the reclassification too
    if t.trap_class == "sales_critical":
        return (pred.secondary_action or "") == t.secondary_action
    return True


def score(
    predictions: dict[str, Prediction],
    label: str,
    subset: frozenset[str] | None = None,
) -> Scorecard:
    truth = load_truth()
    fids = sorted(subset) if subset else sorted(truth)
    correct = 0
    per_trap: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    catastrophic: list[str] = []
    kill_count = 0
    esc_pred: list[str] = []
    esc_correct = 0
    used_offline = False

    for fid in fids:
        t = truth[fid]
        p = predictions.get(fid)
        if p is None:
            per_trap[t.trap_class][1] += 1
            continue
        used_offline = used_offline or p.used_offline
        ok = _is_correct(p, t)
        correct += int(ok)
        per_trap[t.trap_class][0] += int(ok)
        per_trap[t.trap_class][1] += 1
        if p.verdict == "KILL":
            kill_count += 1
            if t.trap_class in CATASTROPHIC_TRAPS:
                catastrophic.append(fid)
        if p.verdict == "ESCALATE":
            esc_pred.append(fid)
            esc_correct += int(t.verdict == "ESCALATE")

    return Scorecard(
        label=label, n=len(fids), correct=correct,
        per_trap={k: (v[0], v[1]) for k, v in per_trap.items()},
        catastrophic_kills=catastrophic, kill_count=kill_count,
        escalate_predicted=esc_pred, escalate_correct=esc_correct,
        used_offline=used_offline,
    )


TRAP_ORDER = [
    "none_kill", "none_keep", "contract_bound", "hidden_dependency",
    "segment_concentrated", "broken_not_unwanted", "seasonal",
    "phantom_usage", "sales_critical",
]


def format_scorecard(sc: Scorecard) -> str:
    lines = [f"── {sc.label} " + "─" * (40 - len(sc.label))]
    if sc.used_offline:
        lines.append("  OFFLINE STUB — not a model score (rerun with a real key)")
    else:
        lines.append(f"  overall accuracy      {sc.accuracy:5.1%}  ({sc.correct}/{sc.n})")
    lines.append(
        f"  catastrophic KILLs    {len(sc.catastrophic_kills):>2} of {sc.kill_count} "
        f"kills  ({sc.catastrophic_rate:.0%})"
        + (f"  {sc.catastrophic_kills}" if sc.catastrophic_kills else "  ✓ zero")
    )
    lines.append(
        f"  escalation precision  {sc.escalation_precision:5.1%}  "
        f"({sc.escalate_correct}/{len(sc.escalate_predicted)} predicted)"
    )
    lines.append("  per trap class:")
    for trap in TRAP_ORDER:
        if trap not in sc.per_trap:
            continue
        c, tot = sc.per_trap[trap]
        bar = "█" * c + "░" * (tot - c)
        lines.append(f"    {trap:22} {c}/{tot}  {bar}")
    return "\n".join(lines)


def agent_predictions(run_id: str | None = None) -> dict[str, Prediction]:
    """Read verdicts from a persisted agent run (latest if run_id is None)."""
    import psycopg

    from sunset.config import settings

    dsn = settings.database_url.replace("postgresql+psycopg://", "postgresql://")
    with psycopg.connect(dsn) as conn, conn.cursor() as cur:
        if run_id is None:
            cur.execute("SELECT id, used_offline_stub FROM audit_runs "
                        "WHERE status='completed' ORDER BY started_at DESC LIMIT 1")
            row = cur.fetchone()
            if not row:
                return {}
            run_id, used_offline = row
        else:
            cur.execute("SELECT used_offline_stub FROM audit_runs WHERE id=%s", (run_id,))
            used_offline = cur.fetchone()[0]
        cur.execute(
            "SELECT feature_id, verdict, secondary_action FROM feature_audits WHERE run_id=%s",
            (run_id,))
        return {
            fid: Prediction(feature_id=fid, verdict=v, secondary_action=sec,
                            used_offline=used_offline)
            for fid, v, sec in cur.fetchall()
        }


def main() -> None:
    from eval.baseline import baseline_predictions
    from eval.holdout import DEV, HOLDOUT

    base = baseline_predictions()
    print(format_scorecard(score(base, "Deterministic baseline (all 40)")))
    print()

    agent = agent_predictions()
    if agent:
        print(format_scorecard(score(agent, "Agent pipeline (all 40)")))
        print()
        print(format_scorecard(score(agent, "  agent — dev (28)", DEV)))
        print()
        print(format_scorecard(score(agent, "  agent — holdout (12)", HOLDOUT)))
    else:
        print("No agent run found. Run `make run` first.")


if __name__ == "__main__":
    main()
