from __future__ import annotations

import json
from pathlib import Path

from tests.load_script import load_script_module

trigger_supervisor = load_script_module("scripts/trigger_supervisor.py", "trigger_supervisor")


def test_upsert_goal_replaces_chinese_goal_line() -> None:
    content = "# Task\n目标：old goal\n里程碑：\n1.\n"
    updated = trigger_supervisor.upsert_goal(content, "new goal")
    assert "目标：new goal" in updated
    assert "目标：old goal" not in updated


def test_upsert_goal_inserts_when_missing() -> None:
    content = "# Task\n里程碑：\n1.\n"
    updated = trigger_supervisor.upsert_goal(content, "inserted goal")
    assert "目标：inserted goal" in updated


def test_trigger_fingerprint_is_stable() -> None:
    left = trigger_supervisor.trigger_fingerprint("manual", "Task A", True)
    right = trigger_supervisor.trigger_fingerprint("manual", "Task A", True)
    assert left == right


def test_should_skip_duplicate_true(tmp_path: Path) -> None:
    trigger_path = tmp_path / "TRIGGER.json"
    fp = trigger_supervisor.trigger_fingerprint("manual", "Task A", True)
    payload = {
        "fingerprint": fp,
        "requested_at_epoch": int(trigger_supervisor.datetime.now().timestamp()),
    }
    trigger_path.write_text(json.dumps(payload), encoding="utf-8")
    assert trigger_supervisor.should_skip_duplicate(trigger_path, fp, 120) is True
