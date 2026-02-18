# OpenClaw Dev（中文）

OpenClaw + Codex CLI 的自动化开发工作流，目标是让交付流程可复用、低 token 成本，并由质量门禁把关。

## 仓库包含内容
- `SKILL.md`: OpenClaw skill 入口定义。
- `scripts/init_openclaw_dev.py`: 在目标仓库初始化 `agent/` 模板。
- `scripts/supervisor_loop.py`: 循环驱动 Codex 执行/续跑，并更新 `agent/STATUS.json`。
- `scripts/run_supervisor_daemon.sh`: 用于本机无人值守常驻执行 supervisor 的封装脚本。
- `scripts/trigger_supervisor.py`: 事件触发执行（可附带新任务并 kickstart launchd）。
- `scripts/memory_namespace.py`: tenant/agent/project 记忆命名空间解析与初始化工具。
- `scripts/autopr.py`: 可选的自动分支/提交/PR/自动合并脚本。
- `scripts/sync_to_skill.py`: 在主机侧同步文件到本地 skill 副本目录。
- 可选第二大脑上下文注入（Daily Index + Session Slice），用于长任务降 token。
- `references/agent_templates.md`: `agent/` 模板参考。

## 快速开始
1. 初始化目标仓库：
```bash
python3 /path/to/openclaw-dev/scripts/init_openclaw_dev.py \
  --repo /path/to/your-repo \
  --task "目标描述"
```

2. 首次启动（新会话）：
```bash
python3 /path/to/openclaw-dev/scripts/supervisor_loop.py \
  --repo /path/to/your-repo \
  --run-once --start --full-auto
```

3. 周期巡检运行：
```bash
python3 /path/to/openclaw-dev/scripts/supervisor_loop.py \
  --repo /path/to/your-repo \
  --interval 1800 --full-auto \
  --codex-timeout 300 --max-attempts 12
```

如需本机无人值守常驻运行（macOS `launchd`），见 `docs/USAGE_CN.md` 的 `3.4` 节。

CI（持续集成）= 每次 push / PR 自动执行 lint、typecheck、tests、eval、security、review。

## 跨目录同步（推荐配置）
如果任务需要写到仓库外目录（例如 `../skills/openclaw-dev`），在 `openclaw.json` 中配置：
```json
{
  "supervisor": {
    "add_dirs": ["../skills/openclaw-dev"]
  }
}
```

也可运行时传入：
```bash
python3 /path/to/openclaw-dev/scripts/supervisor_loop.py \
  --repo /path/to/your-repo \
  --run-once --add-dir ../skills/openclaw-dev
```

你也可以直接执行主机同步脚本：
```bash
python3 /path/to/openclaw-dev/scripts/sync_to_skill.py \
  --repo /path/to/your-repo \
  --target ../skills/openclaw-dev
```

说明：当蓝图步骤目标同时包含 `sync` 与 `skill` 时，supervisor 会走 host sync 路径，并跳过 Codex 无进展兜底逻辑，避免无关改写 `agent/PLAN.md` / `agent/HOT.md`。

你也可以立即事件触发一次执行（不等 interval）：
```bash
python3 /path/to/openclaw-dev/scripts/trigger_supervisor.py \
  --repo /path/to/your-repo \
  --reason "new-task" \
  --task "实现功能 X"
```

可选：通过 `openclaw.json` 开启自动 PR：
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
需要本机已安装并登录 `gh` CLI。

可选：开启第二大脑精简上下文注入：
```json
{
  "supervisor": {
    "second_brain": {
      "enabled": true,
      "root": "..",
      "memory_template": "brain/tenants/{tenant_id}/global/MEMORY.md",
      "daily_index_template": "brain/tenants/{tenant_id}/agents/{agent_id}/projects/{project_id}/daily/{date}/_DAILY_INDEX.md",
      "session_glob_template": "brain/tenants/{tenant_id}/agents/{agent_id}/projects/{project_id}/sessions/session_*.md",
      "max_chars": 1800
    },
    "memory_namespace": {
      "enabled": true,
      "strict_isolation": true,
      "allow_cross_project": false
    }
  }
}
```
该模式只注入紧凑关键信息，降低长会话 token 消耗。

可选：初始化命名空间目录骨架：
```bash
python3 /path/to/openclaw-dev/scripts/memory_namespace.py \
  --root .. \
  --tenant-id default \
  --agent-id assistant-main \
  --project-id my-repo \
  init
```
`resolve` 子命令仅解析并输出路径，不写入文件。

## 质量门禁
一键执行全部门禁：
```bash
make qa
```
按门禁单独执行：
```bash
make lint
make typecheck
make test
make eval
make security
make review
```
策略与阈值见：`docs/QUALITY_GATES.md`

## 文档导航
- 中文
- `docs/USAGE_CN.md`
- `docs/WORKFLOW_CN.md`
- `docs/MEMORY_NAMESPACE_SOP.md`
- `docs/TROUBLESHOOTING_CN.md`
- English
- `README.md`
- `docs/USAGE.md`
- `docs/WORKFLOW.md`
- `docs/TROUBLESHOOTING.md`
- `docs/QUALITY_GATES.md`

## 说明
- 活跃运行产生的 `agent/*` 文件（`HOT`、`WARM`、`PLAN`、`RESULT`、`STATUS`）属于运行态数据，默认不建议纳入常规提交。
