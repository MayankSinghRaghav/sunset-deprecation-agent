# CLAUDE.md — working rules for this repo

Sunset assembles the evidentiary case for deprecating a software feature and
refuses to make the decision itself. Read `README.md` and the build plan before
changing anything structural.

## The one rule that matters

**Do not read `eval/truth/` while writing or tuning agent, metric, or reconciler
code.** The ground-truth sheet is the answer key. If you look at it and then
adjust a threshold until the score improves, the evaluation is measuring your
memory, not the system. This is the single failure mode the whole project is
built to prevent.

The database enforces this for the *running* agent (`sunset_app` is REVOKE'd
from schema `truth`). This rule is the human-facing half of the same guard.

If you must change a threshold, justify it with a written business rationale in
the module docstring — never with "it scored higher" — and log the change in
`eval/CHANGELOG.md`.

## Architectural invariants — do not violate without updating the tests that pin them

- `src/sunset/**` must never import `datagen` or `eval`. (`tests/test_isolation.py`)
- The pre-filter emits `KEEP` or `needs_audit` only — **never `KILL`**. The cheap
  path must not be able to reach a catastrophic verdict.
- The pre-filter counts `actor_type='human'` usage only. Counting bot/QA events
  makes trap-6 features look busy and they never get audited.
- The reconciler is pure Python. No LLM decides a verdict, a cap, or whether two
  auditors contradict. Risk tolerance is a business decision, not a model output.
- `KILL` must be structurally unreachable when a contract is obligated /
  possibly-obligated or revenue is concentrated. This is a property test, not a
  hope. (`tests/test_precedence.py`)
- Every factual claim in a memo carries an `evidence_ref`. The citation validator
  resolves each one against a real row. An unresolvable citation fails the run
  loudly — it never reaches the UI.
- `dissent` is never empty. If no counter-argument exists, say so explicitly.
- Reflection is capped at exactly one pass.

## Commands

`make doctor` before anything. `make db-up && make seed` to get a working
database. `make test` runs the suite. See `make help`.

## Provider modes (`SUNSET_LLM_MODE`)

- `offline` — deterministic stub, default, no key. Runs everything but
  `eval/score.py` refuses to print an accuracy headline.
- `replay` — committed cassettes; a miss is a hard error.
- `live` — real Gemini; needs `GEMINI_API_KEY`.
