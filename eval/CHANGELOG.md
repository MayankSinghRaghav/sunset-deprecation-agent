# Eval changelog

Every change to a threshold, the baseline, or the golden set is logged here with
its rationale. A threshold moved *after* seeing per-feature scores must say so
explicitly — that is the difference between engineering and overfitting.

## 2026-07-29 — Golden set authored and locked

- `eval/truth/ground_truth.csv` written by hand, before any evidence generation.
- 40 features. Verdicts: KILL 11, KEEP 13, MIGRATE 9, FIX 4, ESCALATE 3.
- Trap classes: 7 obvious kills, 5 obvious keeps, 4 in each of the 7 traps.
- sha256: `0d951835cf27429e00793c3eb90a744a93d13e4c1dcc544c74e564f52992bd77`
- This sheet is frozen. Changing it invalidates every number the case study
  quotes, so it does not change without a new entry here explaining why.
