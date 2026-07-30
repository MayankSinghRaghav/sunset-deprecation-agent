"""Load and validate the hand-written ground-truth sheet.

This is the ONE place datagen reads the verdicts. Everything downstream consumes
`TruthRow` objects and turns them into evidence. The sheet is never copied into
an app-visible table — datagen/lint.py enforces that.
"""

from __future__ import annotations

import csv
import os
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DEFAULT_TRUTH = REPO / "eval" / "truth" / "ground_truth.csv"

VALID_VERDICTS = {"KILL", "MIGRATE", "KEEP", "FIX", "ESCALATE"}
VALID_TRAPS = {
    "none_kill",
    "none_keep",
    "contract_bound",
    "hidden_dependency",
    "segment_concentrated",
    "broken_not_unwanted",
    "seasonal",
    "phantom_usage",
    "sales_critical",
}


@dataclass(frozen=True)
class TruthRow:
    feature_id: str
    feature_name: str
    area: str
    correct_verdict: str
    secondary_action: str  # "" for most
    trap_class: str
    has_distractor: bool
    justification: str


def truth_path() -> Path:
    return Path(os.environ.get("SUNSET_TRUTH_PATH", str(DEFAULT_TRUTH)))


def load_truth() -> list[TruthRow]:
    rows: list[TruthRow] = []
    with truth_path().open() as f:
        for r in csv.DictReader(f):
            row = TruthRow(
                feature_id=r["feature_id"].strip(),
                feature_name=r["feature_name"].strip(),
                area=r["area"].strip(),
                correct_verdict=r["correct_verdict"].strip(),
                secondary_action=r["secondary_action"].strip(),
                trap_class=r["trap_class"].strip(),
                has_distractor=r["has_distractor"].strip().lower() == "true",
                justification=r["justification"].strip(),
            )
            assert row.correct_verdict in VALID_VERDICTS, row
            assert row.trap_class in VALID_TRAPS, row
            rows.append(row)
    assert len(rows) == 40, f"expected 40 features, got {len(rows)}"
    ids = [r.feature_id for r in rows]
    assert len(set(ids)) == 40, "feature ids must be unique"
    return rows


def by_id(rows: list[TruthRow]) -> dict[str, TruthRow]:
    return {r.feature_id: r for r in rows}
