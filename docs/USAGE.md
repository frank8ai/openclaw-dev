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
  --interval 1800 --full-auto
```

## 4) Handle decisions
When `agent/STATUS.json.state = blocked`, check `agent/DECISIONS.md` and answer the questions, then resume:
```bash
python3 /path/to/openclaw-dev/scripts/supervisor_loop.py \
  --repo /path/to/your-repo \
  --run-once --full-auto
```
