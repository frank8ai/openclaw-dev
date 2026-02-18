# Changelog

## 2.3.0
- Add optional second-brain compact context injection from `MEMORY.md` + daily index + latest session slice.
- Add trigger dedup window in `scripts/trigger_supervisor.py` to avoid repeated identical runs.
- Keep quality unchanged with existing QA gates, retries, and optional auto-PR pipeline.
- Update init defaults/docs to include `supervisor.second_brain` settings and token-optimized workflow guidance.

## 2.2.0
- Add event-driven supervisor trigger via `scripts/trigger_supervisor.py` (`agent/TRIGGER.json` + optional launchd kickstart).
- Add QA self-healing retries (`--qa-retries`, `--qa-retry-sleep`) and config defaults in `openclaw.json`.
- Add optional auto-PR pipeline via `scripts/autopr.py` and `supervisor.autopr` config.
- Update supervisor workflow/docs for unattended automation, release mode guidance, and CI definition clarity.

## 2.1.1
- Add `scripts/run_supervisor_daemon.sh` for unattended long-running supervisor execution.
- Document macOS `launchd` deployment and restart workflow in `docs/USAGE.md` and `docs/USAGE_CN.md`.
- Clarify commit hygiene: avoid committing volatile runtime `agent/*` artifacts from active runs.
- Refresh README/README_CN navigation and version notes.

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
