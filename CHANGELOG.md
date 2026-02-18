# Changelog

## 2.5.0
- Add standardized handoff protocol (`scripts/handoff_protocol.py`) and integrate handoff context into trigger + supervisor prompt.
- Add observability metrics (`route_hit`, `failure`, `prompt_tokens`, `token_cost`) and rolling alert output (`agent/ALERTS.md`).
- Add security gate (`scripts/security_gate.py`) with approval file + audit log, and enforce Auto-PR approval when configured.
- Add CI multi-agent regression checks (`tests/eval/test_multi_agent_regression.py`) for route isolation and convergence behavior.
- Update docs and init defaults for `agent/HANDOFF.json`, `agent/APPROVALS.json`, `supervisor.observability`, and `supervisor.security`.

## 2.4.0
- Add strict tenant/agent/project memory namespace support in supervisor context loading.
- Add namespace metadata propagation through trigger payload and runtime status (`tenant_id`, `agent_id`, `project_id`).
- Add `scripts/memory_namespace.py` with `init`/`resolve` commands for namespace directory bootstrap.
- Add namespace isolation tests for supervisor context and trigger fingerprint dedup.
- Add `docs/MEMORY_NAMESPACE_SOP.md` and update usage/workflow docs for multi-subagent memory isolation.

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
