---
name: openclaw-dev
description: Autonomous OpenClaw + Codex CLI development workflow that enforces spec-driven execution, minimal-token supervision, and quality-gated acceptance. Use when you need to set up agent/ templates, run codex exec/resume loops, and manage STATUS/DECISIONS/RESULT files for autonomous project delivery.
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
python3 scripts/supervisor_loop.py --repo /path/to/repo --interval 1800 --codex-timeout 300 --max-attempts 12 --qa-retries 1 --qa-retry-sleep 5
```
First run with a fresh exec (no prior Codex session):
```bash
python3 scripts/supervisor_loop.py --repo /path/to/repo --run-once --start --full-auto
```

If the task needs writes outside the repo (for example syncing to sibling `../skills/...`), declare writable dirs in `openclaw.json`:
```json
{
  "supervisor": {
    "add_dirs": ["../skills/openclaw-dev"]
  }
}
```
You can also pass them at runtime:
```bash
python3 scripts/supervisor_loop.py --repo /path/to/repo --run-once --add-dir ../skills/openclaw-dev
```
When a step objective includes `sync` + `skill`, supervisor will run host-side `scripts/sync_to_skill.py` directly (not via Codex shell), so sync no longer depends on Codex sandbox writes.
For these sync steps, supervisor also bypasses the Codex no-progress fallback path, avoiding accidental rewrites of `agent/PLAN.md`/`agent/HOT.md`.

### 4.1) Event-driven immediate trigger
```bash
python3 scripts/trigger_supervisor.py --repo /path/to/repo --reason "new-task" --task "Goal summary" --handoff-from commander --handoff-to engineer --tenant-id default --agent-id assistant-main --project-id your-repo --dedup-seconds 90
```
This writes `agent/TRIGGER.json`, optionally updates `agent/TASK.md`, and kickstarts launchd.

Validate explicit handoff file before trigger:
```bash
python3 scripts/handoff_protocol.py validate --file /path/to/HANDOFF.json
```

### 4.2) Optional auto-PR after done
Configure in `openclaw.json`:
```json
{
  "supervisor": {
    "autopr": {
      "enabled": true,
      "mode": "dev",
      "base": "master",
      "branch_prefix": "autodev",
      "auto_merge": true
    }
  }
}
```
Requires `gh` CLI auth.

### 4.3) Optional second-brain compact context
```json
{
  "supervisor": {
    "second_brain": {
      "enabled": true,
      "root": "..",
      "memory_template": "brain/tenants/{tenant_id}/global/MEMORY.md",
      "daily_index_template": "brain/tenants/{tenant_id}/agents/{agent_id}/projects/{project_id}/daily/{date}/_DAILY_INDEX.md",
      "session_glob_template": "brain/tenants/{tenant_id}/agents/{agent_id}/projects/{project_id}/sessions/session_*.md",
      "max_chars": 1800
    },
    "memory_namespace": {
      "enabled": true,
      "strict_isolation": true,
      "allow_cross_project": false
    }
  }
}
```
When enabled, Codex receives compact key lines from Daily/Session memory with bounded chars.

### 4.4) Namespace bootstrap (recommended)
```bash
python3 scripts/memory_namespace.py --root .. --tenant-id default --agent-id assistant-main --project-id your-repo init
```
Use `resolve` subcommand to inspect paths without writes.

### 4.5) Observability report
```bash
python3 scripts/observability_report.py --repo /path/to/repo --json
```
Supervisor writes route/failure/token metrics to `memory/supervisor_nightly.log` and emits `agent/ALERTS.md` on threshold breaches.

### 4.6) Security approvals
```bash
python3 scripts/security_gate.py --file /path/to/repo/agent/APPROVALS.json approve --action autopr
```
If `supervisor.security.require_autopr_approval=true`, Auto-PR requires this approval.

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
- Gate completion is `QA_CMD` pass (or `TEST_CMD` fallback for legacy repos).
- Use `agent/STATUS.json` as the single source of truth.
- Keep HOT/WARM small; cold context is reference only.

## Scripts
- `scripts/init_openclaw_dev.py` — create agent/ files + templates.
- `scripts/supervisor_loop.py` — resume Codex, run tests, update status.
- `scripts/trigger_supervisor.py` — event-trigger run and optionally reset current step.
- `scripts/handoff_protocol.py` — generate/validate/summarize standardized handoff JSON.
- `scripts/observability_report.py` — summarize observability metrics and alerts.
- `scripts/security_gate.py` — approvals and audit helper for outbound actions.
- `scripts/memory_namespace.py` — namespace resolver/bootstrap for isolated memory directories.
- `scripts/autopr.py` — automated branch/commit/PR/auto-merge helper.

## References
See `references/agent_templates.md` for the exact file templates and fields.
