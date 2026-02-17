# Workflow

## Goals
- Spec-driven execution
- Minimal-token supervision
- Test-gated acceptance
- Durable status files

## Core files
- `agent/TASK.md`: scope, milestones, acceptance
- `agent/POLICY.md`: hard rules
- `agent/STATUS.json`: state machine
- `agent/DECISIONS.md`: human approvals
- `agent/RESULT.md`: final delivery summary
- `agent/BLUEPRINT.json`: deterministic steps (model does not decide flow)
- `agent/HOT.md` / `agent/WARM.md`: minimal context buffers

## State transitions
- `idle` → `running`: when Codex starts
- `running` → `blocked`: if Codex fails or needs approval
- `running` → `done`: when tests pass and Result is complete
- `running` → `idle`: when Codex finishes without errors but not yet done

## Minimal-token discipline
- Logs are truncated to the last 150 lines and written to `agent/test_tail.log`.
- The agent should write summaries to `agent/RESULT.md` instead of chatting full logs.
- Prompt must only include HOT/WARM + error tail; cold memory stays as references.

## Suggested cadence
- First run: `--run-once --start --full-auto`
- Overnight: `--interval 1800 --full-auto`
