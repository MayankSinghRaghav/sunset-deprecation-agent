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

## 2026-07-29 — Dataset fidelity pass, then baseline frozen

Two evidence-shape adjustments were made **for trap fidelity, not to hit a score**
(the truth sheet — the answer key — was untouched):
- Contract-bound features made genuinely dormant in recent usage. Trap 1 is a
  *low-usage* feature that is nonetheless contract-obligated; if its usage were
  healthy there would be no trap. This is what lets the naive baseline commit the
  contract breach the whole product exists to prevent.
- Seasonal features made zero off-season (previously a small trickle). "Dormant
  ten months a year" is the trap; a trickle that keeps recent usage above the
  kill threshold defeats it. Zero off-season also sharpens the periodicity signal
  the agent must read.

## 2026-07-29 — Deterministic baseline FROZEN

Rules: contract keyword-grep → ESCALATE; recent-usage bottom-quartile → KILL; else
KEEP. It cannot express FIX or MIGRATE by design. Thresholds are data percentiles,
never chosen by looking at the score.

Frozen numbers on the golden set (seed 1337 fixtures):
- **Overall accuracy: 32.5% (13/40).**
- **Catastrophic KILLs: 2 of 12** — f14 (Data Residency) and f16 (Scheduled PDF),
  both contract-obligated, killed because usage looks dead and keyword grep cannot
  read capability language. This is the spec's central cautionary tale, made real.
- Escalation precision: 20% (1/5) — grep over-matches common words like "access".
- Per trap: none_kill 7/7, none_keep 4/5, seasonal 1/4 (f30 by luck),
  contract_bound 1/4 (f13 by grep luck); hidden_dependency, segment_concentrated,
  broken_not_unwanted, phantom_usage, sales_critical all **0/4**.

Everything the case study later claims is a delta against this. The gap is exactly
the traps that need semantic reading (1, 4, 7) or a structured join / graph read
the naive baseline omits (2, 3, 6). `eval/baseline.py` is frozen from here; any
change needs an entry above.
