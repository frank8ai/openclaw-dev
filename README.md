# OpenClaw Dev

Autonomous OpenClaw + Codex CLI development workflow that enforces spec-driven execution, minimal-token supervision, and quality-gated acceptance.

## What this repo provides
- `SKILL.md`: the skill entry point for OpenClaw.
- `scripts/init_openclaw_dev.py`: initializes `agent/` templates in any target repo.
- `scripts/supervisor_loop.py`: resumes Codex work, runs tests, and updates `agent/STATUS.json`.
- `scripts/run_supervisor_daemon.sh`: wrapper for unattended long-running supervisor execution.
- `scripts/trigger_supervisor.py`: event-driven trigger (optional task update + launchd kickstart).
- `scripts/autopr.py`: optional branch/commit/PR/auto-merge automation.
- `scripts/sync_to_skill.py`: host-side sync from repo to local skill copy.
- `references/agent_templates.md`: canonical templates for `agent/` files.
- Deterministic `agent/BLUEPRINT.json` and minimal-context `agent/HOT.md`/`agent/WARM.md`.

## Quickstart
1) Initialize `agent/` templates in your target repo
```bash
python3 /path/to/openclaw-dev/scripts/init_openclaw_dev.py \
  --repo /path/to/your-repo \
  --task "Goal summary"
```

2) Start Codex (first run)
```bash
python3 /path/to/openclaw-dev/scripts/supervisor_loop.py \
  --repo /path/to/your-repo \
  --run-once --start --full-auto
```

3) Keep it running (periodic)
```bash
python3 /path/to/openclaw-dev/scripts/supervisor_loop.py \
  --repo /path/to/your-repo \
  --interval 1800 --full-auto
```

For unattended local deployment (macOS `launchd`), see `docs/USAGE.md` section `3.4`.

CI = Continuous Integration: every push/PR runs lint/typecheck/tests/eval/security/review automatically.

4) If your task must write outside repo (e.g. sync to sibling skill dir), declare writable dirs:
```json
{
  "supervisor": {
    "add_dirs": ["../skills/openclaw-dev"]
  }
}
```
or pass at runtime:
```bash
python3 /path/to/openclaw-dev/scripts/supervisor_loop.py \
  --repo /path/to/your-repo \
  --run-once --add-dir ../skills/openclaw-dev
```

5) Optional host sync command (no Codex sandbox dependency):
```bash
python3 /path/to/openclaw-dev/scripts/sync_to_skill.py \
  --repo /path/to/your-repo \
  --target ../skills/openclaw-dev
```
The supervisor will auto-use this script for sync steps when objective contains `sync` + `skill`.
In sync steps, supervisor skips Codex no-progress fallback, so it will not rewrite `agent/PLAN.md`/`agent/HOT.md` unexpectedly.

6) Event-trigger a run immediately (no need to wait for interval):
```bash
python3 /path/to/openclaw-dev/scripts/trigger_supervisor.py \
  --repo /path/to/your-repo \
  --reason "new-task" \
  --task "Implement feature X"
```

7) Optional full automation after gate pass (Auto-PR):
`openclaw.json`
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
Requires `gh` CLI and authenticated GitHub session.

## Iter-2 utilities
- `scripts/para_recall.py`: lightweight memory recall over `memory/`.
  - Example: `python3 scripts/para_recall.py --query "focus areas" --trace logs/retrieval_trace.jsonl`
  - `--trace` writes JSONL retrieval entries; default is `logs/retrieval_trace.jsonl`.
- `scripts/session_end_extractor.py`: append a compact session-end summary from a log tail.
  - Example: `python3 scripts/session_end_extractor.py --input agent/test_tail.log --out agent/session_ends.md`
  - Output appends to `agent/session_ends.md`.
- Pycache note: if `py_compile`/`__pycache__` churn appears, set `PYTHONPYCACHEPREFIX=/tmp/pycache`.

## Quality gates (best-practice baseline)
- Install and run all gates:
```bash
make qa
```
- Individual gates:
```bash
make lint
make typecheck
make test
make eval
make security
make review
```
- Gate policy and thresholds: `docs/QUALITY_GATES.md`

## Version
- `VERSION` file and Git tag `v2.2.0`.

## Notes
- This workflow is intentionally minimal-token: long logs stay on disk, not in chat.
- When the agent needs human approval (new deps, API changes), it writes to `agent/DECISIONS.md` and sets `STATUS.state=blocked`.
- Runtime `agent/*` files from active runs (`HOT`, `WARM`, `PLAN`, `RESULT`, `STATUS`) are volatile; stage commits selectively.

## Documentation
- English
- `docs/USAGE.md`
- `docs/WORKFLOW.md`
- `docs/TROUBLESHOOTING.md`
- `docs/QUALITY_GATES.md`
- Chinese
- `README_CN.md`
- `docs/USAGE_CN.md`
- `docs/WORKFLOW_CN.md`
- `docs/TROUBLESHOOTING_CN.md`
