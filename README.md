# OpenClaw Dev

Autonomous OpenClaw + Codex CLI development workflow that enforces spec-driven execution, minimal-token supervision, and test-gated acceptance.

## What this repo provides
- `SKILL.md`: the skill entry point for OpenClaw.
- `scripts/init_openclaw_dev.py`: initializes `agent/` templates in any target repo.
- `scripts/supervisor_loop.py`: resumes Codex work, runs tests, and updates `agent/STATUS.json`.
- `references/agent_templates.md`: canonical templates for `agent/` files.

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

## Version
- `VERSION` file and Git tag `v1.0.0`.

## Notes
- This workflow is intentionally minimal-token: long logs stay on disk, not in chat.
- When the agent needs human approval (new deps, API changes), it writes to `agent/DECISIONS.md` and sets `STATUS.state=blocked`.

## Documentation
- `docs/USAGE.md`
- `docs/WORKFLOW.md`
- `docs/TROUBLESHOOTING.md`
