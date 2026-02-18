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
  --codex-timeout 300 --max-attempts 12
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
