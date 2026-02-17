# Agent Templates (openclaw-dev)

## agent/COMMANDS.env
```bash
export NEXUS_PYTHON_PATH="$HOME/.openclaw/workspace/skills/deepsea-nexus/.venv-3.13/bin/python"

CHECKPOINT_MODE='patch'

TEST_CMD='
if [ -f pnpm-lock.yaml ]; then pnpm -s test;
elif [ -f package-lock.json ]; then npm test;
elif [ -f yarn.lock ]; then yarn test;
elif [ -f pyproject.toml ] || [ -f requirements.txt ]; then pytest -q;
elif ls scripts/*.py >/dev/null 2>&1; then python3 -m py_compile scripts/*.py;
else echo "no tests"; fi
'

LINT_CMD='if [ -f package.json ]; then (pnpm -s lint || npm run lint || yarn lint); fi'
TYPECHECK_CMD='if [ -f tsconfig.json ]; then (pnpm -s typecheck || npm run typecheck || yarn typecheck); fi'
BUILD_CMD='if [ -f package.json ]; then (pnpm -s build || npm run build || yarn build); fi'
```

## agent/POLICY.md
```markdown
目标：在保证测试通过的前提下，最小改动、最低 token、可恢复。

硬规则：
- 每轮修改后必须运行 TEST_CMD。
- 禁止新增依赖；若必须新增，写入 DECISIONS.md 并 blocked。
- 不做大重构；每次只完成一个里程碑。
- 终端输出只保留错误段 + 最后 150 行。
- 最终必须写 RESULT.md（files、diff--stat、验证、风险）。

上下文纪律：
- Prompt 只允许包含 HOT/WARM/ERROR_TAIL（禁止长日志/大段代码回填）。
- 冷记忆只保留引用（COLD.ref.json）。
```

## agent/STATUS.json
```json
{
  "state": "idle",
  "last_update": "",
  "current_step": 0,
  "current_milestone": 0,
  "checkpoint_id": "",
  "last_cmd": "",
  "last_test_ok": false,
  "last_error_sig": "",
  "needs_human": false,
  "human_question": ""
}
```

## agent/DECISIONS.md
```markdown
# Decisions Needed
- [ ] 是否允许新增依赖 X？原因：...
- [ ] API 方案 A vs B 选择？
```

## agent/RESULT.md
```markdown
# Result
- 完成情况：
- 改动文件：
- diff --stat：
- 验证：
- 风险点：
```

## agent/PLAN.md
```markdown
# Plan
1.
2.
3.
```

## agent/BLUEPRINT.json
```json
{
  "version": "1.0",
  "steps": [
    {"id": 1, "name": "spec", "objective": "Read TASK.md and write PLAN.md", "checkpoint": true},
    {"id": 2, "name": "implement", "objective": "Implement changes per PLAN.md", "checkpoint": true},
    {"id": 3, "name": "verify", "objective": "Run TEST_CMD and fix failures", "checkpoint": false},
    {"id": 4, "name": "finalize", "objective": "Write RESULT.md and set STATUS.state=done", "checkpoint": false}
  ]
}
```

## agent/CONTEXT.json
```json
{
  "hot_budget": 1000,
  "warm_budget": 1500,
  "cold_top_k": 4,
  "total_budget": 3500,
  "compression_triggers": [0.6, 0.75, 0.85]
}
```

## agent/HOT.md
```markdown
# HOT
- Current step:
- Current error:
- Relevant files/paths:
- Constraints:
```

## agent/WARM.md
```markdown
# WARM
- Stage summary:
- Decisions:
- Next steps:
```

## agent/COLD.ref.json
```json
{
  "refs": []
}
```

## agent/TASK.md
```markdown
# Task
目标：

里程碑：
1.
2.
3.

验收标准：
- TEST_CMD 通过

允许/禁止范围：
- 允许改：
- 禁止改：
```
