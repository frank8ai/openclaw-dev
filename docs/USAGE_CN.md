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
- `agent/HANDOFF.json`
- `agent/APPROVALS.json`

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
  --codex-timeout 300 --max-attempts 12 \
  --qa-retries 1 --qa-retry-sleep 5
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

## 3.4) 使用 launchd 常驻运行（macOS）
先使用封装脚本验证无人值守运行：
```bash
chmod +x /path/to/openclaw-dev/scripts/run_supervisor_daemon.sh
OPENCLAW_TARGET_REPO=/path/to/your-repo \
  /path/to/openclaw-dev/scripts/run_supervisor_daemon.sh
```

创建 `~/Library/LaunchAgents/ai.openclaw.dev.supervisor.plist`：
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

加载/重载/停止：
```bash
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/ai.openclaw.dev.supervisor.plist
launchctl kickstart -k gui/$(id -u)/ai.openclaw.dev.supervisor
launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/ai.openclaw.dev.supervisor.plist
```

## 3.5) 事件触发立即执行
当有新任务时，可立即触发，不必等待 interval：
```bash
python3 /path/to/openclaw-dev/scripts/trigger_supervisor.py \
  --repo /path/to/your-repo \
  --reason "new-task" \
  --task "实现功能 X" \
  --handoff-from commander \
  --handoff-to engineer \
  --tenant-id default \
  --agent-id assistant-main \
  --project-id your-repo
```
默认会尝试对 `com.openclaw.dev-supervisor` 执行 `launchctl kickstart`。
为避免重复触发，命令默认启用去重窗口（`--dedup-seconds`，默认 `90` 秒）。

## 3.6) 可选自动 PR 流水线
在 `openclaw.json` 启用：
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
需要本机已登录 `gh` CLI。

## 3.7) 可选第二大脑精简上下文
在 `openclaw.json` 启用：
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
开启后，supervisor 会把 Daily/Session 的关键信息以压缩格式注入 prompt，降低长会话 token 开销。

## 3.8) 初始化命名空间目录
创建 tenant/agent/project 记忆目录骨架：
```bash
python3 /path/to/openclaw-dev/scripts/memory_namespace.py \
  --root .. \
  --tenant-id default \
  --agent-id assistant-main \
  --project-id your-repo \
  init
```
仅解析路径（不写文件）：
```bash
python3 /path/to/openclaw-dev/scripts/memory_namespace.py \
  --root .. \
  --tenant-id default \
  --agent-id assistant-main \
  --project-id your-repo \
  resolve
```

## 3.9) 标准化交接协议
生成交接模板：
```bash
python3 /path/to/openclaw-dev/scripts/handoff_protocol.py template \
  --from-agent commander --to-agent engineer --objective "实现功能 X"
```
校验交接文件：
```bash
python3 /path/to/openclaw-dev/scripts/handoff_protocol.py validate --file /path/to/HANDOFF.json
```
使用交接文件触发：
```bash
python3 /path/to/openclaw-dev/scripts/trigger_supervisor.py \
  --repo /path/to/your-repo --handoff-file /path/to/HANDOFF.json
```

## 3.10) 可观测性报告与告警
查看当前窗口指标：
```bash
python3 /path/to/openclaw-dev/scripts/observability_report.py --repo /path/to/your-repo --json
```
supervisor 会把路由命中/失败率/token 指标写入 `memory/supervisor_nightly.log`。
超过阈值会自动生成 `agent/ALERTS.md`。

## 3.11) 安全审批与审计
为 Auto-PR 授权：
```bash
python3 /path/to/openclaw-dev/scripts/security_gate.py \
  --file /path/to/your-repo/agent/APPROVALS.json \
  approve --action autopr
```
当 `supervisor.security.require_autopr_approval=true` 时，未审批将被门禁拦截。
推荐配置：
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

## 4) 处理人工决策
当 `agent/STATUS.json.state = blocked` 时，查看 `agent/DECISIONS.md` 并回答后再继续：
```bash
python3 /path/to/openclaw-dev/scripts/supervisor_loop.py \
  --repo /path/to/your-repo \
  --run-once --full-auto
```

## 5) 本地执行质量门禁
```bash
make qa
```
或按门禁单独执行：
```bash
make lint
make typecheck
make test
make eval
make security
make review
```

## 6) 提交清洁建议
以下文件属于运行态产物，通常不应进入功能提交：
- `agent/HOT.md`
- `agent/WARM.md`
- `agent/PLAN.md`
- `agent/RESULT.md`
- `agent/STATUS.json`

建议只精确暂存有价值文件：
```bash
git add <有价值文件路径>
```
