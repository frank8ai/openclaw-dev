#!/usr/bin/env python3
"""
OpenClaw Dev Supervisor Loop
Resume Codex, run tests, update agent/STATUS.json.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import time
from datetime import datetime
from pathlib import Path


def load_status(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def save_status(path: Path, status: dict) -> None:
    status["last_update"] = datetime.now().isoformat(timespec="seconds")
    path.write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run_cmd(cmd: list[str], cwd: Path) -> int:
    return subprocess.run(cmd, cwd=str(cwd), check=False).returncode


def run_tests(agent_dir: Path) -> int:
    cmd = [
        "bash",
        "-lc",
        'source agent/COMMANDS.env && eval "$TEST_CMD" 2>&1 | tail -n 150 > agent/test_tail.log',
    ]
    return run_cmd(cmd, agent_dir.parent)


def build_prompt() -> str:
    return (
        "Follow agent/POLICY.md and agent/TASK.md. "
        "Read agent/COMMANDS.env for TEST_CMD/LINT_CMD/TYPECHECK_CMD/BUILD_CMD. "
        "Write agent/PLAN.md, update agent/STATUS.json, and finish with agent/RESULT.md. "
        "Any human decision goes to agent/DECISIONS.md and set STATUS.state=blocked."
    )


def run_codex_start(agent_dir: Path, full_auto: bool) -> int:
    prompt = build_prompt()
    cmd = ["codex", "exec"]
    if full_auto:
        cmd.append("--full-auto")
    cmd.append(prompt)
    return run_cmd(cmd, agent_dir.parent)


def run_codex_resume(agent_dir: Path) -> int:
    cmd = ["codex", "exec", "resume", "--last"]
    return run_cmd(cmd, agent_dir.parent)


def loop(repo: Path, interval: int, run_once: bool, full_auto: bool, force_start: bool) -> None:
    agent_dir = repo / "agent"
    status_path = agent_dir / "STATUS.json"
    if not agent_dir.exists():
        raise SystemExit("agent/ directory not found. Run init_openclaw_dev.py first.")

    while True:
        status = load_status(status_path)
        state = status.get("state", "idle")

        if state in ("done", "blocked"):
            print(f"Status={state}. Exiting.")
            return

        start_needed = force_start or not status.get("last_cmd")

        status["state"] = "running"
        status["last_cmd"] = "codex exec --full-auto" if start_needed and full_auto else "codex exec resume --last"
        save_status(status_path, status)

        codex_rc = run_codex_start(agent_dir, full_auto=full_auto) if start_needed else run_codex_resume(agent_dir)

        status = load_status(status_path)
        if codex_rc != 0:
            status["state"] = "blocked"
            status["needs_human"] = True
            status["human_question"] = "codex exec failed; inspect logs and agent/RESULT.md"
            save_status(status_path, status)
            return

        test_rc = run_tests(agent_dir)
        status["last_test_ok"] = (test_rc == 0)
        if status.get("state") not in ("blocked", "done"):
            status["state"] = "idle"
        save_status(status_path, status)

        if run_once:
            return
        time.sleep(interval)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True, help="Repo root")
    parser.add_argument("--interval", type=int, default=1800)
    parser.add_argument("--run-once", action="store_true")
    parser.add_argument("--full-auto", action="store_true")
    parser.add_argument("--start", action="store_true", help="Force a fresh codex exec")
    args = parser.parse_args()

    loop(Path(args.repo).expanduser().resolve(), args.interval, args.run_once, args.full_auto, args.start)


if __name__ == "__main__":
    main()
