# The golden set — read this before you touch it

`ground_truth.csv` is the **hand-authored** verdict sheet for all 40 features. It
was written *first*, by a human, before any evidence was generated. The evidence
in `datagen/` exists to *encode* these verdicts; the verdicts do not come from
the evidence. That ordering is the entire defense against a circular evaluation
(spec §4.1).

## Do not tune against this file

If you are writing or adjusting agent code, metrics, or the reconciler, **do not
open this file to see whether your change scored better.** That turns the
evaluation into a measurement of your memory. See `../../CLAUDE.md`.

Twelve of these 40 rows are a **blind holdout** (`eval/holdout.py`) and are
scored only at phase gates, never during iteration.

## How isolation is enforced at runtime

This CSV is loaded into schema `truth`, owned by `sunset_eval`. The application
role `sunset_app` — which the agent and the API use — is `REVOKE`'d from that
schema. The agent physically cannot read it. `tests/test_isolation.py` proves it.
Committing the file for reviewers to inspect does not weaken that: the filesystem
is not in the running agent's read path.

## Columns

| column | meaning |
|---|---|
| `feature_id` | joins to `features.id` |
| `feature_name` | human readability only |
| `area` | product area |
| `correct_verdict` | one of KILL / MIGRATE / KEEP / FIX / ESCALATE |
| `secondary_action` | only for trap 7: `RECLASSIFY_SALES_COLLATERAL` |
| `trap_class` | which of the 7 traps (or `none_kill` / `none_keep`) |
| `has_distractor` | true if the evidence deliberately points the wrong way at first glance |
| `justification` | the human's one-sentence reasoning. **Never appears in any evidence table.** |

## Distribution (documented per the Phase 1 gate)

- **Verdicts:** KILL 11, KEEP 13, MIGRATE 9, FIX 4, ESCALATE 3. All five present.
- **Trap classes:** 7 obvious kills, 5 obvious keeps, and **4 features in each of
  the 7 traps** (28 trap features).
- **Distractors:** `f05` (a contract names a capability the feature relates to,
  but the obligation is satisfied elsewhere, so it is still a safe kill), `f11`
  and `f12` (heavy ticket volume that is engagement/demand, not defect or
  indifference). These exist so the system cannot win by pattern-matching
  "has tickets → fix" or "named in a contract → escalate".

## Trap 7 and the sixth verdict that isn't

Spec §2 says trap 7's correct answer is "keep, reclassify as sales collateral,
stop investing" — which the five-value vocabulary cannot express. Rather than add
a sixth verdict, the reclassification rides in `secondary_action`. Trap 7 scores
as `correct_verdict == KEEP AND secondary_action == RECLASSIFY_SALES_COLLATERAL`.
This is a deliberate, documented deviation from the literal spec.
