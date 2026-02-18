# 工作流说明

## 目标
- 按规格执行（spec-driven）
- 低 token 监督
- 质量门禁验收
- 状态文件可追踪
- 事件触发 + 无人值守

## 核心文件
- `agent/TASK.md`: 目标范围、里程碑、验收条件
- `agent/POLICY.md`: 硬规则
- `agent/STATUS.json`: 状态机
- `agent/DECISIONS.md`: 人工审批与决策
- `agent/RESULT.md`: 最终交付摘要
- `agent/BLUEPRINT.json`: 确定性步骤
- `agent/HOT.md` / `agent/WARM.md`: 精简上下文缓存
- `docs/QUALITY_GATES.md`: 质量门禁策略、阈值和停止条件

## 状态流转
- `idle` -> `running`: 开始执行
- `running` -> `blocked`: 执行失败或等待人工决策
- `running` -> `done`: 质量门禁通过且结果写完整
- `running` -> `idle`: 一轮完成但未最终收敛

## 低 token 纪律
- 日志默认只保留末尾 150 行写入 `agent/test_tail.log`
- 结果写入 `agent/RESULT.md`，避免在会话里贴大段日志
- 提示词优先使用 HOT/WARM 与错误摘要，冷数据按需引用

## 建议节奏
- 首次运行：`--run-once --start --full-auto`
- 持续巡检：`--interval 1800 --full-auto`
- 新任务到达：`trigger_supervisor.py` + launchd kickstart

## 自愈策略
- 质量门禁失败可自动重试（`--qa-retries`、`--qa-retry-sleep`）后再判定失败。
- 超时/无进展会写入 `STATUS.last_error_sig`，并给出明确 blocked 处理动作。

## 上下文策略（低 token）
- 默认使用 HOT/WARM + 错误尾部摘要。
- 可选开启 `supervisor.second_brain`，注入 `MEMORY.md`、Daily Index、最新 Session Slice 的压缩关键信息。
- 触发器默认带去重窗口，避免同任务短时间重复空转。

## 可选发布自动化
- 开启 `supervisor.autopr` 后，`STATUS=done` 且门禁通过时可自动建分支/提交/PR。
- `mode=dev` 可启用 `auto_merge`，`staging/prod` 建议保持人工审批。
