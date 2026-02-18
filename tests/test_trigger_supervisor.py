from __future__ import annotations

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
