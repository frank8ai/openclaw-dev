#!/usr/bin/env python3
"""
Initialize openclaw-dev agent/ templates in a repo.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

COMMANDS_ENV = """CHECKPOINT_MODE='patch'

SETUP_CMD='bash scripts/qa/bootstrap.sh setup'
LINT_CMD='bash scripts/qa/bootstrap.sh lint'
TYPECHECK_CMD='bash scripts/qa/bootstrap.sh typecheck'
TEST_CMD='bash scripts/qa/bootstrap.sh tests'
EVAL_CMD='bash scripts/qa/bootstrap.sh eval'
SECURITY_CMD='bash scripts/qa/bootstrap.sh security'
REVIEW_CMD='bash scripts/qa/bootstrap.sh review'
QA_CMD='bash scripts/qa/bootstrap.sh all'
BUILD_CMD='echo "build step not required for this repository"'
"""


POLICY_MD = """目标：在保证质量门禁通过的前提下，最小改动、最低 token、可恢复。

硬规则：
- 每轮修改后必须运行 QA_CMD（至少 LINT/TYPECHECK/TEST/EVAL/SECURITY/REVIEW）。
- 禁止新增依赖；若必须新增，写入 DECISIONS.md 并 blocked。
- 不做大重构；每次只完成一个里程碑。
- 终端输出只保留错误段 + 最后 150 行。
- 每次运行必须更新 HOT.md（当前任务/错误/路径），里程碑完成更新 WARM.md。
- 最终必须写 RESULT.md（files、diff--stat、验证、风险）。

上下文纪律：
- Prompt 只允许包含 HOT/WARM/ERROR_TAIL（禁止长日志/大段代码回填）。
- 冷记忆只保留引用（COLD.ref.json）。
"""


STATUS_JSON = {
    "state": "idle",
    "last_update": "",
    "current_step": 0,
    "current_milestone": 0,
    "checkpoint_id": "",
    "last_cmd": "",
    "last_test_ok": False,
    "last_error_sig": "",
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


BLUEPRINT_JSON = """{
  "version": "1.0",
  "steps": [
    {
      "id": 1,
      "name": "spec",
      "objective": "Read TASK.md and write a short PLAN.md",
      "checkpoint": true
    },
    {
      "id": 2,
      "name": "implement",
      "objective": "Implement changes per PLAN.md with minimal diffs",
      "checkpoint": true
    },
    {
      "id": 3,
      "name": "verify",
      "objective": "Run TEST_CMD and fix failures",
      "checkpoint": false
    },
    {
      "id": 4,
      "name": "finalize",
      "objective": "Write RESULT.md and set STATUS.state=done",
      "checkpoint": false
    }
  ]
}
"""


CONTEXT_JSON = """{
  "hot_budget": 1000,
  "warm_budget": 1500,
  "cold_top_k": 4,
  "total_budget": 3500,
  "compression_triggers": [0.6, 0.75, 0.85]
}
"""


HOT_MD = """# HOT
- Current step:
- Current error:
- Relevant files/paths:
- Constraints:
"""


WARM_MD = """# WARM
- Stage summary:
- Decisions:
- Next steps:
"""


COLD_REF_JSON = """{
  "refs": []
}
"""


def ensure_openclaw_config(repo: Path, force: bool) -> None:
    config_path = repo / "openclaw.json"
    config: dict = {}

    if config_path.exists():
        try:
            loaded = json.loads(config_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            loaded = {}
        if isinstance(loaded, dict):
            config = loaded

    supervisor = config.get("supervisor")
    if not isinstance(supervisor, dict):
        supervisor = {}
        config["supervisor"] = supervisor

    if force or not isinstance(supervisor.get("default_scope"), str) or not supervisor["default_scope"].strip():
        supervisor["default_scope"] = "."

    add_dirs = supervisor.get("add_dirs")
    if not isinstance(add_dirs, list):
        add_dirs = []

    # Common case: "<name>-repo" syncs back to sibling "skills/<name>".
    if repo.name.endswith("-repo"):
        mirror_name = repo.name[:-5]
        mirror_rel = f"../skills/{mirror_name}"
        mirror_abs = (repo / mirror_rel).resolve()
        if mirror_abs.exists() and mirror_abs.is_dir() and mirror_rel not in add_dirs:
            add_dirs.append(mirror_rel)

    supervisor["add_dirs"] = add_dirs

    config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


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
    write_file(agent_dir / "BLUEPRINT.json", BLUEPRINT_JSON, args.force)
    write_file(agent_dir / "CONTEXT.json", CONTEXT_JSON, args.force)
    write_file(agent_dir / "HOT.md", HOT_MD, args.force)
    write_file(agent_dir / "WARM.md", WARM_MD, args.force)
    write_file(agent_dir / "COLD.ref.json", COLD_REF_JSON, args.force)

    status_path = agent_dir / "STATUS.json"
    if not status_path.exists() or args.force:
        status = dict(STATUS_JSON)
        status["last_update"] = datetime.now().isoformat(timespec="seconds")
        status_path.write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    ensure_openclaw_config(repo, args.force)

    checkpoints = agent_dir / "checkpoints"
    checkpoints.mkdir(parents=True, exist_ok=True)

    print(f"Initialized agent/ templates in {agent_dir}")


if __name__ == "__main__":
    main()
