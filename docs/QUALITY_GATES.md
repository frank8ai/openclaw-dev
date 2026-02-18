# Quality Gates SOP (Three-Tier Standard)

## Goal
Create a deterministic release gate for `openclaw-dev` so delivery quality does not depend on manual judgment.

## Three-Tier Standard
1. **Tier-A (Correctness)**
- `lint` and `typecheck` must pass.
- `tests` must pass.
- Any failure blocks merge.

2. **Tier-B (Behavior Confidence)**
- `eval` suite must pass (targeted behavior checks, separate from unit tests).
- Coverage target for critical scripts: core paths validated by at least one test.
- Any failure blocks merge.

3. **Tier-C (Security + Review Discipline)**
- `security` scan must pass with configured baseline.
- `review` gate must pass (PR checklist and process artifacts present).
- Any failure blocks merge.

## Gate Matrix
| Gate | Command | Pass Criteria |
|---|---|---|
| Lint | `make lint` | `ruff check scripts tests` returns 0 |
| Typecheck | `make typecheck` | `mypy scripts` returns 0 |
| Tests | `make test` | `pytest tests` returns 0 |
| Eval | `make eval` | `pytest tests/eval` returns 0 |
| Security | `make security` | `bandit -ii` returns 0 with `bandit.yaml` policy |
| Review | `make review` | Review artifact checks return 0 |
| Full Gate | `make qa` | All gates pass in order |

## Stop and Rollback Rules
- If any gate fails: stop release and fix before merge.
- If security gate fails on high-confidence issue: pause rollout and triage before any deploy.
- If gate tooling itself breaks: repair CI scripts first; do not bypass by force merge.

## PR Review Rules
- PR must include problem statement, scope, and risk.
- PR checklist must explicitly confirm lint/typecheck/tests/eval/security.
- Reviewer blocks merge if checklist is incomplete or evidence is missing.

## CI Enforcement
- GitHub Actions runs all gates on `push` and `pull_request` to `master`.
- CI is mandatory; no manual override for failed gates.
