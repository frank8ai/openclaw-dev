# Usage

## 1) Initialize templates in a target repo
```bash
python3 /path/to/openclaw-dev/scripts/init_openclaw_dev.py \
  --repo /path/to/your-repo \
  --task "Goal summary"
```

This creates:
- `agent/COMMANDS.env`
- `agent/POLICY.md`
- `agent/TASK.md`
- `agent/STATUS.json`
- `agent/DECISIONS.md`
- `agent/RESULT.md`
- `agent/PLAN.md`
- `agent/BLUEPRINT.json`
- `agent/CONTEXT.json`
- `agent/HOT.md` / `agent/WARM.md` / `agent/COLD.ref.json`
- `agent/HANDOFF.json`
- `agent/APPROVALS.json`

## 2) Start the Codex loop (first run)
```bash
python3 /path/to/openclaw-dev/scripts/supervisor_loop.py \
  --repo /path/to/your-repo \
  --run-once --start --full-auto
```

## 3) Periodic supervisor loop
```bash
python3 /path/to/openclaw-dev/scripts/supervisor_loop.py \
  --repo /path/to/your-repo \
  --interval 1800 --full-auto \
  --codex-timeout 300 --max-attempts 12 \
  --qa-retries 1 --qa-retry-sleep 5
```

## 3.1) Allow cross-repo writes when needed
When a task needs syncing files to another directory (for example `../skills/openclaw-dev`), add writable dirs:

`openclaw.json`
```json
{
  "supervisor": {
    "add_dirs": ["../skills/openclaw-dev"]
  }
}
```

Or pass explicitly:
```bash
python3 /path/to/openclaw-dev/scripts/supervisor_loop.py \
  --repo /path/to/your-repo \
  --run-once --add-dir ../skills/openclaw-dev
```

## 3.2) Manual host sync (optional)
```bash
python3 /path/to/openclaw-dev/scripts/sync_to_skill.py \
  --repo /path/to/your-repo \
  --target ../skills/openclaw-dev
```
This runs outside Codex sandbox and is safe for local one-shot sync.

## 3.3) Sync step behavior
If a blueprint step objective contains both `sync` and `skill`, `supervisor_loop.py` will run host sync directly and skip Codex fallback logic for that step. This prevents unrelated rewrites of `agent/PLAN.md` and `agent/HOT.md` during sync-only runs.

## 3.4) Persistent local deployment with launchd (macOS)
Use the wrapper script for unattended restart-safe operation:
```bash
chmod +x /path/to/openclaw-dev/scripts/run_supervisor_daemon.sh
OPENCLAW_TARGET_REPO=/path/to/your-repo \
  /path/to/openclaw-dev/scripts/run_supervisor_daemon.sh
```

Create `~/Library/LaunchAgents/ai.openclaw.dev.supervisor.plist`:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
  <dict>
    <key>Label</key><string>ai.openclaw.dev.supervisor</string>
    <key>ProgramArguments</key>
    <array>
      <string>/bin/zsh</string>
      <string>-lc</string>
      <string>/path/to/openclaw-dev/scripts/run_supervisor_daemon.sh</string>
    </array>
    <key>EnvironmentVariables</key>
    <dict>
      <key>OPENCLAW_TARGET_REPO</key><string>/path/to/your-repo</string>
      <key>OPENCLAW_SUPERVISOR_INTERVAL</key><string>1800</string>
      <key>OPENCLAW_CODEX_TIMEOUT</key><string>300</string>
      <key>OPENCLAW_MAX_ATTEMPTS</key><string>12</string>
      <key>OPENCLAW_QA_RETRIES</key><string>1</string>
      <key>OPENCLAW_QA_RETRY_SLEEP</key><string>5</string>
    </dict>
    <key>RunAtLoad</key><true/>
    <key>KeepAlive</key><true/>
    <key>WorkingDirectory</key><string>/path/to/openclaw-dev</string>
    <key>StandardOutPath</key><string>/tmp/openclaw-dev-supervisor.out.log</string>
    <key>StandardErrorPath</key><string>/tmp/openclaw-dev-supervisor.err.log</string>
  </dict>
</plist>
```

Load/unload:
```bash
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/ai.openclaw.dev.supervisor.plist
launchctl kickstart -k gui/$(id -u)/ai.openclaw.dev.supervisor
launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/ai.openclaw.dev.supervisor.plist
```

## 3.5) Event-driven run trigger
When a new task arrives, trigger an immediate run instead of waiting for interval:
```bash
python3 /path/to/openclaw-dev/scripts/trigger_supervisor.py \
  --repo /path/to/your-repo \
  --reason "new-task" \
  --task "Implement feature X" \
  --handoff-from commander \
  --handoff-to engineer \
  --tenant-id default \
  --agent-id assistant-main \
  --project-id your-repo
```
By default it also runs `launchctl kickstart` on `com.openclaw.dev-supervisor`.
To avoid duplicate triggers, the command deduplicates identical payloads in a short window
(`--dedup-seconds`, default `90`).

## 3.6) Optional Auto-PR pipeline
Enable in `openclaw.json`:
```json
{
  "supervisor": {
    "autopr": {
      "enabled": true,
      "required": false,
      "mode": "dev",
      "base": "master",
      "branch_prefix": "autodev",
      "auto_merge": true,
      "commit_message": "chore: automated supervisor delivery",
      "title": "chore: automated supervisor delivery",
      "body_file": "agent/RESULT.md"
    }
  }
}
```
Requires `gh` CLI authentication.

## 3.7) Optional second-brain compact context
Enable in `openclaw.json`:
```json
{
  "supervisor": {
    "second_brain": {
      "enabled": true,
      "root": "..",
      "memory_template": "brain/tenants/{tenant_id}/global/MEMORY.md",
      "daily_index_template": "brain/tenants/{tenant_id}/agents/{agent_id}/projects/{project_id}/daily/{date}/_DAILY_INDEX.md",
      "session_glob_template": "brain/tenants/{tenant_id}/agents/{agent_id}/projects/{project_id}/sessions/session_*.md",
      "include_memory_md": true,
      "max_chars": 1800,
      "max_sessions": 1,
      "max_lines_per_file": 40
    },
    "memory_namespace": {
      "enabled": true,
      "tenant_id": "default",
      "default_agent_id": "main",
      "default_project_id": "your-repo",
      "strict_isolation": true,
      "allow_cross_project": false
    }
  }
}
```
When enabled, supervisor injects compact key lines from daily/session memory into Codex prompts.

## 3.8) Bootstrap memory namespace directories
Create tenant/agent/project memory skeleton:
```bash
python3 /path/to/openclaw-dev/scripts/memory_namespace.py \
  --root .. \
  --tenant-id default \
  --agent-id assistant-main \
  --project-id your-repo \
  init
```
Inspect only (no writes):
```bash
python3 /path/to/openclaw-dev/scripts/memory_namespace.py \
  --root .. \
  --tenant-id default \
  --agent-id assistant-main \
  --project-id your-repo \
  resolve
```

## 3.9) Standardized handoff contract
Generate a handoff template:
```bash
python3 /path/to/openclaw-dev/scripts/handoff_protocol.py template \
  --from-agent commander --to-agent engineer --objective "Implement feature X"
```
Validate handoff file:
```bash
python3 /path/to/openclaw-dev/scripts/handoff_protocol.py validate --file /path/to/HANDOFF.json
```
Trigger with explicit handoff:
```bash
python3 /path/to/openclaw-dev/scripts/trigger_supervisor.py \
  --repo /path/to/your-repo --handoff-file /path/to/HANDOFF.json
```

## 3.10) Observability report and alerts
Report current window metrics:
```bash
python3 /path/to/openclaw-dev/scripts/observability_report.py --repo /path/to/your-repo --json
```
The supervisor writes route/failure/token metrics into `memory/supervisor_nightly.log`.
When thresholds are exceeded, `agent/ALERTS.md` is generated.

## 3.11) Security approvals and audit
Approve outbound Auto-PR:
```bash
python3 /path/to/openclaw-dev/scripts/security_gate.py \
  --file /path/to/your-repo/agent/APPROVALS.json \
  approve --action autopr
```
When `supervisor.security.require_autopr_approval=true`, Auto-PR is blocked until approval exists.
Recommended config:
```json
{
  "supervisor": {
    "security": {
      "enabled": true,
      "require_autopr_approval": true,
      "approval_file": "agent/APPROVALS.json",
      "audit_log": "logs/security_audit.jsonl"
    },
    "observability": {
      "enabled": true,
      "window": 20,
      "failure_rate_alert": 0.35,
      "route_miss_rate_alert": 0.05,
      "prompt_token_budget": 2400
    }
  }
}
```

## 4) Handle decisions
When `agent/STATUS.json.state = blocked`, check `agent/DECISIONS.md` and answer the questions, then resume:
```bash
python3 /path/to/openclaw-dev/scripts/supervisor_loop.py \
  --repo /path/to/your-repo \
  --run-once --full-auto
```

## 5) Run quality gates locally
```bash
make qa
```
Or run a single gate:
```bash
make lint
make typecheck
make test
make eval
make security
make review
```

## 6) Commit hygiene (recommended)
The following files are run artifacts and usually should not be part of functional commits:
- `agent/HOT.md`
- `agent/WARM.md`
- `agent/PLAN.md`
- `agent/RESULT.md`
- `agent/STATUS.json`

Use targeted staging:
```bash
git add <meaningful-files-only>
```
