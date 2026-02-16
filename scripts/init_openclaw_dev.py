#!/usr/bin/env python3
"""
Initialize openclaw-dev agent/ templates in a repo.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from datetime import datetime


COMMANDS_ENV = """export NEXUS_PYTHON_PATH="$HOME/.openclaw/workspace/skills/deepsea-nexus/.venv-3.13/bin/python"

TEST_CMD='
if [ -f pnpm-lock.yaml ]; then pnpm -s test;
elif [ -f package-lock.json ]; then npm test;
elif [ -f yarn.lock ]; then yarn test;
elif [ -f pyproject.toml ] || [ -f requirements.txt ]; then pytest -q;
else echo "no tests"; fi
'

LINT_CMD='if [ -f package.json ]; then (pnpm -s lint || npm run lint || yarn lint); fi'
TYPECHECK_CMD='if [ -f tsconfig.json ]; then (pnpm -s typecheck || npm run typecheck || yarn typecheck); fi'
BUILD_CMD='if [ -f package.json ]; then (pnpm -s build || npm run build || yarn build); fi'
"""


POLICY_MD = """目标：在保证测试通过的前提下，最小改动、最低 token、可恢复。

硬规则：
- 每轮修改后必须运行 TEST_CMD。
- 禁止新增依赖；若必须新增，写入 DECISIONS.md 并 blocked。
- 不做大重构；每次只完成一个里程碑。
- 终端输出只保留错误段 + 最后 150 行。
- 最终必须写 RESULT.md（files、diff--stat、验证、风险）。
"""


STATUS_JSON = {
    "state": "idle",
    "last_update": "",
    "current_milestone": 0,
    "last_cmd": "",
    "last_test_ok": False,
    "needs_human": False,
    "human_question": "",
}


DECISIONS_MD = """# Decisions Needed
- [ ] 是否允许新增依赖 X？原因：...
- [ ] API 方案 A vs B 选择？
"""


RESULT_MD = """# Result
- 完成情况：
- 改动文件：
- diff --stat：
- 验证：
- 风险点：
"""


PLAN_MD = """# Plan
1.
2.
3.
"""


def task_md(task: str) -> str:
    return f"""# Task
目标：{task or ''}

里程碑：
1.
2.
3.

验收标准：
- TEST_CMD 通过

允许/禁止范围：
- 允许改：
- 禁止改：
"""


def write_file(path: Path, content: str, force: bool) -> None:
    if path.exists() and not force:
        return
    path.write_text(content, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True, help="Path to repo root")
    parser.add_argument("--task", default="", help="Short task summary")
    parser.add_argument("--force", action="store_true", help="Overwrite existing files")
    args = parser.parse_args()

    repo = Path(args.repo).expanduser().resolve()
    agent_dir = repo / "agent"
    agent_dir.mkdir(parents=True, exist_ok=True)

    write_file(agent_dir / "COMMANDS.env", COMMANDS_ENV, args.force)
    write_file(agent_dir / "POLICY.md", POLICY_MD, args.force)
    write_file(agent_dir / "DECISIONS.md", DECISIONS_MD, args.force)
    write_file(agent_dir / "RESULT.md", RESULT_MD, args.force)
    write_file(agent_dir / "PLAN.md", PLAN_MD, args.force)
    write_file(agent_dir / "TASK.md", task_md(args.task), args.force)

    status_path = agent_dir / "STATUS.json"
    if not status_path.exists() or args.force:
        status = dict(STATUS_JSON)
        status["last_update"] = datetime.now().isoformat(timespec="seconds")
        status_path.write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"Initialized agent/ templates in {agent_dir}")


if __name__ == "__main__":
    main()
