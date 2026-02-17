目标：在保证测试通过的前提下，最小改动、最低 token、可恢复。

硬规则：
- 每轮修改后必须运行 TEST_CMD。
- 禁止新增依赖；若必须新增，写入 DECISIONS.md 并 blocked。
- 不做大重构；每次只完成一个里程碑。
- 终端输出只保留错误段 + 最后 150 行。
- 每次运行必须更新 HOT.md（当前任务/错误/路径），里程碑完成更新 WARM.md。
- 最终必须写 RESULT.md（files、diff--stat、验证、风险）。

上下文纪律：
- Prompt 只允许包含 HOT/WARM/ERROR_TAIL（禁止长日志/大段代码回填）。
- 冷记忆只保留引用（COLD.ref.json）。
