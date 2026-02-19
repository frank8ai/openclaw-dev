# Plan
1. 对齐约束：读取 `agent/TASK.md`、`agent/POLICY.md`、`agent/COMMANDS.env`，明确最小可交付范围与质量门禁。
2. 基线检查：定位模板与监督脚本相关文件，确认当前缺口并锁定最小改动清单。
3. 实施改动：按清单修复/补全模板与监督流程，保持无新增依赖与小步变更。
4. 质量验证：执行 `QA_CMD`（失败则执行 `TEST_CMD`），仅保存错误与末尾摘要到日志文件。
5. 收尾交付：更新 `agent/RESULT.md`、`agent/HOT.md`、`agent/WARM.md`、`agent/STATUS.json` 并标记完成。
