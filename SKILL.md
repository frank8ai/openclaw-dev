---
name: openclaw-dev
description: Autonomous OpenClaw + Codex CLI development workflow that enforces spec-driven execution, minimal-token supervision, and test-gated acceptance. Use when you need to set up agent/ templates, run codex exec/resume loops, and manage STATUS/DECISIONS/RESULT files for autonomous project delivery.
---

# OpenClaw Dev Supervisor

## Overview
Create a repeatable, low-token, spec-driven workflow where OpenClaw supervises Codex CLI to finish a project with test-gated acceptance and durable status files.

## Workflow (best-practice, low token)

### 1) Initialize agent/ workspace
Run the scaffold script in the target repo to create the standard agent files:
```bash
python3 scripts/init_openclaw_dev.py --repo /path/to/repo --task "Goal summary"
```
This creates:
- `agent/COMMANDS.env` (auto-detect test/lint/build commands)
- `agent/POLICY.md` (hard rules: test gating, minimal output)
- `agent/TASK.md` (current task spec)
- `agent/STATUS.json` (state machine)
- `agent/DECISIONS.md` (human approvals)
- `agent/RESULT.md` (final delivery summary)
- `agent/PLAN.md` (short execution plan)
- `agent/BLUEPRINT.json` (deterministic steps)
- `agent/CONTEXT.json` (budgets and thresholds)
- `agent/HOT.md` / `agent/WARM.md` / `agent/COLD.ref.json`

### 2) Write a tight task spec
Edit `agent/TASK.md` with:
- Goal
- 1–3 milestones
- Acceptance criteria (tests/commands)
- In/Out of scope

### 3) Start Codex exec (full auto)
```bash
codex exec --full-auto "
Follow agent/POLICY.md and agent/TASK.md.
Read agent/COMMANDS.env for TEST_CMD/LINT_CMD/BUILD_CMD.
Write agent/PLAN.md, update agent/STATUS.json, and finish with agent/RESULT.md.
Any human decision goes to agent/DECISIONS.md and STATUS=blocked.
"
```

### 4) Supervisor loop (resume + test)
Use the supervisor script to resume work and run tests with minimal output:
```bash
python3 scripts/supervisor_loop.py --repo /path/to/repo --run-once
```
Or run periodically:
```bash
python3 scripts/supervisor_loop.py --repo /path/to/repo --interval 1800
```
First run with a fresh exec (no prior Codex session):
```bash
python3 scripts/supervisor_loop.py --repo /path/to/repo --run-once --start --full-auto
```

### 5) Handle blocked decisions
If `agent/STATUS.json` is `blocked`, answer the item in `agent/DECISIONS.md`, then resume.

### 6) Accept and finalize
Completion requires:
- `agent/RESULT.md` filled
- `TEST_CMD` passes
- `STATUS.json.state = done`

## Conventions (must-follow)
- No large logs in chat; write to files and only tail 150 lines.
- All changes checkpointed with `diff --stat` in RESULT.
- No new deps without DECISIONS approval.
- Use `agent/STATUS.json` as the single source of truth.
- Keep HOT/WARM small; cold context is reference only.

## Scripts
- `scripts/init_openclaw_dev.py` — create agent/ files + templates.
- `scripts/supervisor_loop.py` — resume Codex, run tests, update status.

## References
See `references/agent_templates.md` for the exact file templates and fields.
