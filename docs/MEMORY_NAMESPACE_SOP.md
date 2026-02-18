# Memory Namespace SOP

## Goal
Prevent memory mixing across tenants, sub-agents, and projects while keeping second-brain context token-efficient.

## Required metadata
All runs must resolve these fields:
- `tenant_id`: organization or user space (default `default`)
- `agent_id`: channel/sub-agent identity (for example `assistant-main`, `researcher`, `coder`)
- `project_id`: workload/project key (for example `openclaw-dev-repo`)

Storage source of truth:
- Runtime: `agent/STATUS.json`
- Trigger payload: `agent/TRIGGER.json`
- Config defaults: `openclaw.json` -> `supervisor.memory_namespace`

## Directory templates (default)
- Global memory: `brain/tenants/{tenant_id}/global/MEMORY.md`
- Daily index: `brain/tenants/{tenant_id}/agents/{agent_id}/projects/{project_id}/daily/{date}/_DAILY_INDEX.md`
- Session slices: `brain/tenants/{tenant_id}/agents/{agent_id}/projects/{project_id}/sessions/session_*.md`
- Research cards: `brain/tenants/{tenant_id}/agents/{agent_id}/projects/{project_id}/cards/{date}/`
- Research packs: `brain/tenants/{tenant_id}/agents/{agent_id}/projects/{project_id}/packs/{date}/`

## Routing rules
1. Trigger writes namespace IDs into payload/status (`trigger_supervisor.py`).
2. Supervisor normalizes namespace IDs before each run (`supervisor_loop.py`).
3. Second-brain context reads only resolved namespace paths when strict isolation is enabled.
4. Cross-project recall is disabled by default (`allow_cross_project=false`).

## Compression and retention tiers
- `#P0`: identity/security/policy, keep in tenant global memory.
- `#P1`: project decisions/milestones, keep in project daily index and cards.
- `#P2`: transient debugging notes, keep in session slices only.
- `#GOLD`: promoted facts, mirror to daily index and long-term card.

## Operational commands
Initialize namespace skeleton:
```bash
python3 scripts/memory_namespace.py \
  --root .. \
  --tenant-id default \
  --agent-id assistant-main \
  --project-id openclaw-dev-repo \
  init
```

Inspect effective paths:
```bash
python3 scripts/memory_namespace.py \
  --root .. \
  --tenant-id default \
  --agent-id assistant-main \
  --project-id openclaw-dev-repo \
  resolve
```

Trigger isolated run:
```bash
python3 scripts/trigger_supervisor.py \
  --repo . \
  --reason "new-task" \
  --task "Implement feature X" \
  --tenant-id default \
  --agent-id assistant-main \
  --project-id openclaw-dev-repo
```

## Acceptance checklist
- Namespace keys always present in `agent/STATUS.json`.
- Context block includes `[NAMESPACE] tenant_id/agent_id/project_id`.
- Tests pass for namespace isolation and trigger dedup fingerprint.
- No cross-project lines appear in prompt context unless explicitly imported.
