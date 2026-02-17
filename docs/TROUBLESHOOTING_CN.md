# 故障排查

## 找不到 Codex 命令
请先安装 Codex CLI，或确认它已在 `PATH` 中。

## STATUS 一直是 blocked
查看 `agent/DECISIONS.md`，回答问题后重新执行 supervisor。

## 测试持续失败
查看 `agent/test_tail.log`，根据失败信息修复目标仓库代码。

## resume 后看起来没动作
先用一次 `--start` 强制新建 `codex exec` 会话。

## 同步到 ../skills/... 时权限被拒绝
原因：默认情况下，Codex 沙箱只允许写当前仓库目录。

处理方式：
- 在 `openclaw.json` 添加 `supervisor.add_dirs`（例如 `../skills/openclaw-dev`）
- 或运行 supervisor 时传入 `--add-dir ../skills/openclaw-dev`
- 或直接运行主机同步脚本：`python3 scripts/sync_to_skill.py --repo . --target ../skills/openclaw-dev`

## 同步步骤意外改写了 PLAN/HOT
原因：旧版 supervisor 可能把 sync-only 回合误导入 Codex fallback 逻辑。

处理方式：
- 升级到当前仓库最新版 `scripts/supervisor_loop.py`
- 确保该步骤 objective 同时包含 `sync` 与 `skill`，让 supervisor 走 host sync 路径
