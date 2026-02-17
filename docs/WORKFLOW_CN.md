# 工作流说明

## 目标
- 按规格执行（spec-driven）
- 低 token 监督
- 测试门禁验收
- 状态文件可追踪

## 核心文件
- `agent/TASK.md`: 目标范围、里程碑、验收条件
- `agent/POLICY.md`: 硬规则
- `agent/STATUS.json`: 状态机
- `agent/DECISIONS.md`: 人工审批与决策
- `agent/RESULT.md`: 最终交付摘要
- `agent/BLUEPRINT.json`: 确定性步骤
- `agent/HOT.md` / `agent/WARM.md`: 精简上下文缓存

## 状态流转
- `idle` -> `running`: 开始执行
- `running` -> `blocked`: 执行失败或等待人工决策
- `running` -> `done`: 测试通过且结果写完整
- `running` -> `idle`: 一轮完成但未最终收敛

## 低 token 纪律
- 日志默认只保留末尾 150 行写入 `agent/test_tail.log`
- 结果写入 `agent/RESULT.md`，避免在会话里贴大段日志
- 提示词优先使用 HOT/WARM 与错误摘要，冷数据按需引用

## 建议节奏
- 首次运行：`--run-once --start --full-auto`
- 持续巡检：`--interval 1800 --full-auto`
