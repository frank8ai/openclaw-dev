# OpenClaw Dev

Autonomous OpenClaw + Codex CLI development workflow that enforces spec-driven execution, minimal-token supervision, and test-gated acceptance.

## What this repo provides
- `SKILL.md`: the skill entry point for OpenClaw.
- `scripts/init_openclaw_dev.py`: initializes `agent/` templates in any target repo.
- `scripts/supervisor_loop.py`: resumes Codex work, runs tests, and updates `agent/STATUS.json`.
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

## Iter-2 utilities
- `scripts/para_recall.py`: lightweight memory recall over `memory/`.
  - Example: `python3 scripts/para_recall.py --query "focus areas" --trace logs/retrieval_trace.jsonl`
  - `--trace` writes JSONL retrieval entries; default is `logs/retrieval_trace.jsonl`.
- `scripts/session_end_extractor.py`: append a compact session-end summary from a log tail.
  - Example: `python3 scripts/session_end_extractor.py --input agent/test_tail.log --out agent/session_ends.md`
  - Output appends to `agent/session_ends.md`.
- Pycache note: if `py_compile`/`__pycache__` churn appears, set `PYTHONPYCACHEPREFIX=/tmp/pycache`.

## Version
- `VERSION` file and Git tag `v2.0.0`.

## Notes
- This workflow is intentionally minimal-token: long logs stay on disk, not in chat.
- When the agent needs human approval (new deps, API changes), it writes to `agent/DECISIONS.md` and sets `STATUS.state=blocked`.

## Documentation
- `docs/USAGE.md`
- `docs/WORKFLOW.md`
- `docs/TROUBLESHOOTING.md`
