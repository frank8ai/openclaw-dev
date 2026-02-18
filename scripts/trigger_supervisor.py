#!/usr/bin/env python3
"""Trigger an event-driven supervisor run with optional task update."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

TRIGGER_FILE = "TRIGGER.json"


def upsert_goal(text: str, goal: str) -> str:
    lines = text.splitlines()
    value = goal.strip()
    updated = False
    for idx, line in enumerate(lines):
        if line.startswith("目标："):
            lines[idx] = f"目标：{value}"
            updated = True
            break
        if line.lower().startswith("goal:"):
            lines[idx] = f"Goal: {value}"
            updated = True
            break
    if not updated:
        if lines and lines[0].startswith("#"):
            lines.insert(1, f"目标：{value}")
        else:
            lines.insert(0, f"目标：{value}")
    return "\n".join(lines).rstrip() + "\n"


def read_status(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def write_status(path: Path, status: dict) -> None:
    status["last_update"] = datetime.now().isoformat(timespec="seconds")
    path.write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def maybe_kickstart(label: str) -> tuple[int, str]:
    cmd = [
        "launchctl",
        "kickstart",
        "-k",
        f"gui/{os.getuid()}/{label}",
    ]
    try:
        proc = subprocess.run(cmd, check=False, capture_output=True, text=True)
    except FileNotFoundError:
        return 127, "launchctl not found"
    message = (proc.stdout or "").strip() or (proc.stderr or "").strip() or "kickstart issued"
    return proc.returncode, message


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True, help="Repo root path.")
    parser.add_argument("--reason", default="manual", help="Trigger reason.")
    parser.add_argument("--task", default="", help="Optional new task goal.")
    parser.add_argument("--reset-step", action="store_true", default=True, help="Reset to step 1.")
    parser.add_argument("--no-reset-step", action="store_false", dest="reset_step")
    parser.add_argument("--kickstart-label", default="com.openclaw.dev-supervisor", help="launchd label.")
    parser.add_argument("--no-kickstart", action="store_true", help="Only write trigger file.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo = Path(args.repo).expanduser().resolve()
    agent_dir = repo / "agent"
    if not agent_dir.exists():
        print("trigger: missing agent/ directory", file=sys.stderr)
        return 2

    task_path = agent_dir / "TASK.md"
    if isinstance(args.task, str) and args.task.strip():
        original = task_path.read_text(encoding="utf-8") if task_path.exists() else "# Task\n"
        task_path.write_text(upsert_goal(original, args.task.strip()), encoding="utf-8")

    status_path = agent_dir / "STATUS.json"
    status = read_status(status_path)
    if status:
        status["state"] = "idle"
        status["needs_human"] = False
        status["human_question"] = ""
        status["last_error_sig"] = "triggered"
        status["last_action"] = "triggered_run"
        if args.reset_step:
            status["current_step"] = 1
            status["checkpoint_id"] = ""
        write_status(status_path, status)

    payload = {
        "requested_at": datetime.now().isoformat(timespec="seconds"),
        "reason": args.reason,
        "task": args.task,
        "reset_step": bool(args.reset_step),
    }
    trigger_path = agent_dir / TRIGGER_FILE
    trigger_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if args.no_kickstart:
        print(f"trigger: queued at {trigger_path}")
        return 0

    rc, message = maybe_kickstart(args.kickstart_label)
    if rc != 0:
        print(f"trigger: queued but kickstart failed ({rc}): {message}", file=sys.stderr)
        return 1

    print(f"trigger: queued and kickstarted ({message})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
