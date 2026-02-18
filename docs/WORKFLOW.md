# Workflow

## Goals
- Spec-driven execution
- Minimal-token supervision
- Quality-gated acceptance
- Durable status files
- Event-driven wakeup + unattended operations

## Core files
- `agent/TASK.md`: scope, milestones, acceptance
- `agent/POLICY.md`: hard rules
- `agent/STATUS.json`: state machine
- `agent/DECISIONS.md`: human approvals
- `agent/RESULT.md`: final delivery summary
- `agent/BLUEPRINT.json`: deterministic steps (model does not decide flow)
- `agent/HOT.md` / `agent/WARM.md`: minimal context buffers
- `docs/QUALITY_GATES.md`: gate policy, thresholds, and stop rules

## State transitions
- `idle` → `running`: when Codex starts
- `running` → `blocked`: if Codex fails or needs approval
- `running` → `done`: when tests pass and Result is complete
  - practical definition: `QA_CMD` pass (or `TEST_CMD` fallback for legacy repos)
- `running` → `idle`: when Codex finishes without errors but not yet done

## Minimal-token discipline
- Logs are truncated to the last 150 lines and written to `agent/test_tail.log`.
- The agent should write summaries to `agent/RESULT.md` instead of chatting full logs.
- Prompt must only include HOT/WARM + error tail; cold memory stays as references.

## Suggested cadence
- First run: `--run-once --start --full-auto`
- Overnight: `--interval 1800 --full-auto`
- Event task arrival: `trigger_supervisor.py` + launchd kickstart

## Self-healing
- QA failures can retry automatically (`--qa-retries`, `--qa-retry-sleep`) before marking failed.
- Timeouts/no-progress are tracked in `STATUS.last_error_sig` and routed to blocked with clear actions.

## Optional release automation
- Enable `supervisor.autopr` to create branch/commit/PR automatically after `STATUS=done` and gates pass.
- `mode=dev` allows `auto_merge`; `staging/prod` should keep manual approval.
