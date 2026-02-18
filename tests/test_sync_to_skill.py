from __future__ import annotations

from tests.load_script import load_script_module

sync_to_skill = load_script_module("scripts/sync_to_skill.py", "sync_to_skill")


def test_should_skip_excluded_prefix() -> None:
    assert sync_to_skill._should_skip("agent/RESULT.md", ("agent/",), set()) is True


def test_should_skip_excluded_file_name() -> None:
    assert sync_to_skill._should_skip("openclaw.json", tuple(), {"openclaw.json"}) is True


def test_should_not_skip_normal_file() -> None:
    assert sync_to_skill._should_skip("scripts/supervisor_loop.py", ("agent/",), {"openclaw.json"}) is False
