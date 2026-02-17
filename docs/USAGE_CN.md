# 使用说明

## 1) 在目标仓库初始化模板
```bash
python3 /path/to/openclaw-dev/scripts/init_openclaw_dev.py \
  --repo /path/to/your-repo \
  --task "目标描述"
```

会创建：
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

## 2) 首次启动 Codex 循环
```bash
python3 /path/to/openclaw-dev/scripts/supervisor_loop.py \
  --repo /path/to/your-repo \
  --run-once --start --full-auto
```

## 3) 周期运行 supervisor
```bash
python3 /path/to/openclaw-dev/scripts/supervisor_loop.py \
  --repo /path/to/your-repo \
  --interval 1800 --full-auto \
  --codex-timeout 300 --max-attempts 12
```

## 3.1) 需要跨仓库写入时
如果任务要同步到其它目录（例如 `../skills/openclaw-dev`），请添加可写目录。

`openclaw.json`:
```json
{
  "supervisor": {
    "add_dirs": ["../skills/openclaw-dev"]
  }
}
```

或运行时指定：
```bash
python3 /path/to/openclaw-dev/scripts/supervisor_loop.py \
  --repo /path/to/your-repo \
  --run-once --add-dir ../skills/openclaw-dev
```

## 3.2) 手动主机同步（可选）
```bash
python3 /path/to/openclaw-dev/scripts/sync_to_skill.py \
  --repo /path/to/your-repo \
  --target ../skills/openclaw-dev
```

该命令在主机侧运行，不依赖 Codex 沙箱跨目录写权限。

## 3.3) 同步步骤行为
当蓝图 step 的 objective 同时包含 `sync` 和 `skill` 时，`supervisor_loop.py` 会直接执行 host sync，并跳过该步的 Codex fallback 逻辑，从而避免无关改写 `agent/PLAN.md` 与 `agent/HOT.md`。

## 4) 处理人工决策
当 `agent/STATUS.json.state = blocked` 时，查看 `agent/DECISIONS.md` 并回答后再继续：
```bash
python3 /path/to/openclaw-dev/scripts/supervisor_loop.py \
  --repo /path/to/your-repo \
  --run-once --full-auto
```
