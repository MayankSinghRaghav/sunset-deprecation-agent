"""The blind holdout split.

12 of 40 features are scored ONLY at phase gates, never during iteration. This is
the countermeasure to the realistic circularity failure — a developer (or a coding
agent) nudging thresholds until the dev-set score climbs. If the change also lifts
the untouched holdout, it generalised; if only the dev set moved, it overfit.

The split is a transparent, hand-picked constant (like the truth sheet itself)
rather than a hash, so it is auditable and guaranteed to span every trap class.
"""

from __future__ import annotations

# Chosen to cover all nine classes: none_kill x2, none_keep x2, and one or two
# from each of the seven traps.
HOLDOUT: frozenset[str] = frozenset({
    "f06", "f07",   # obvious kills
    "f11", "f12",   # obvious keeps
    "f15",          # contract_bound
    "f20",          # hidden_dependency
    "f24",          # segment_concentrated
    "f28",          # broken_not_unwanted
    "f32",          # seasonal
    "f36",          # phantom_usage
    "f39", "f40",   # sales_critical
})

ALL_FEATURES: frozenset[str] = frozenset(f"f{i:02d}" for i in range(1, 41))
DEV: frozenset[str] = ALL_FEATURES - HOLDOUT

assert len(HOLDOUT) == 12
assert len(DEV) == 28
