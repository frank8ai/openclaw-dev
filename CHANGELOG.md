# Changelog

## 2.1.0
- Add enforced quality gates (`lint`, `typecheck`, `tests`, `eval`, `security`, `review`) with `make qa`.
- Add CI workflow to run all gates on `push` and `pull_request`.
- Add three-tier quality SOP (`docs/QUALITY_GATES.md`) and PR review checklist template.
- Add Python test suite and eval suite for key scripts.
- Update supervisor and templates to prefer `QA_CMD` with `TEST_CMD` fallback.

## 2.0.0
- Deterministic blueprint steps (BLUEPRINT.json) with step tracking.
- Minimal-context buffers (HOT/WARM) and cold references.
- Patch-based checkpoints written to agent/checkpoints.
- Supervisor loop updated to advance steps and record checkpoints.

## 1.0.0
- Initial release: OpenClaw Dev skill, agent templates, supervisor loop, and docs.
