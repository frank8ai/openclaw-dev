#!/usr/bin/env python3
"""Trigger an event-driven supervisor run with optional task update."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
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


def normalize_identifier(value: object, fallback: str) -> str:
    if not isinstance(value, str):
        return fallback
    cleaned = value.strip().lower()
    if not cleaned:
        return fallback
    return re.sub(r"[^a-z0-9._-]+", "-", cleaned)


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


def trigger_fingerprint(
    reason: str,
    task: str,
    reset_step: bool,
    tenant_id: str,
    agent_id: str,
    project_id: str,
) -> str:
    payload = (
        f"{reason.strip()}|{task.strip()}|{int(reset_step)}|"
        f"{tenant_id.strip()}|{agent_id.strip()}|{project_id.strip()}"
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def should_skip_duplicate(trigger_path: Path, fingerprint: str, dedup_seconds: int) -> bool:
    if dedup_seconds <= 0 or not trigger_path.exists():
        return False
    try:
        data = json.loads(trigger_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False
    if not isinstance(data, dict):
        return False
    previous = data.get("fingerprint")
    requested_at = data.get("requested_at_epoch")
    if not isinstance(previous, str) or previous != fingerprint:
        return False
    if not isinstance(requested_at, int):
        return False
    now_epoch = int(datetime.now().timestamp())
    return (now_epoch - requested_at) <= dedup_seconds


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True, help="Repo root path.")
    parser.add_argument("--reason", default="manual", help="Trigger reason.")
    parser.add_argument("--task", default="", help="Optional new task goal.")
    parser.add_argument("--reset-step", action="store_true", default=True, help="Reset to step 1.")
    parser.add_argument("--no-reset-step", action="store_false", dest="reset_step")
    parser.add_argument("--tenant-id", default="", help="Tenant namespace id (optional).")
    parser.add_argument("--agent-id", default="", help="Agent namespace id (optional).")
    parser.add_argument("--project-id", default="", help="Project namespace id (optional).")
    parser.add_argument("--kickstart-label", default="com.openclaw.dev-supervisor", help="launchd label.")
    parser.add_argument("--no-kickstart", action="store_true", help="Only write trigger file.")
    parser.add_argument(
        "--dedup-seconds",
        type=int,
        default=90,
        help="Skip duplicate trigger payloads within this window (seconds). Set 0 to disable.",
    )
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
    tenant_id = normalize_identifier(args.tenant_id, str(status.get("tenant_id", "default")))
    agent_id = normalize_identifier(args.agent_id, str(status.get("agent_id", "main")))
    project_id = normalize_identifier(args.project_id, str(status.get("project_id", repo.name)))

    if status:
        status["state"] = "idle"
        status["needs_human"] = False
        status["human_question"] = ""
        status["last_error_sig"] = "triggered"
        status["last_action"] = "triggered_run"
        status["tenant_id"] = tenant_id
        status["agent_id"] = agent_id
        status["project_id"] = project_id
        if args.reset_step:
            status["current_step"] = 1
            status["checkpoint_id"] = ""
        write_status(status_path, status)

    trigger_path = agent_dir / TRIGGER_FILE
    fingerprint = trigger_fingerprint(
        args.reason,
        args.task,
        bool(args.reset_step),
        tenant_id,
        agent_id,
        project_id,
    )
    if should_skip_duplicate(trigger_path, fingerprint, max(0, args.dedup_seconds)):
        print("trigger: skipped duplicate request in dedup window")
        return 0

    now = datetime.now()
    payload = {
        "requested_at": now.isoformat(timespec="seconds"),
        "requested_at_epoch": int(now.timestamp()),
        "reason": args.reason,
        "task": args.task,
        "reset_step": bool(args.reset_step),
        "tenant_id": tenant_id,
        "agent_id": agent_id,
        "project_id": project_id,
        "fingerprint": fingerprint,
    }
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
