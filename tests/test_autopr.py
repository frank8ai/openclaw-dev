from __future__ import annotations

from tests.load_script import load_script_module

autopr = load_script_module("scripts/autopr.py", "autopr")


def test_should_skip_runtime_status_file() -> None:
    assert autopr._should_skip("agent/STATUS.json", ("agent/",), set()) is True


def test_should_skip_prefixed_path() -> None:
    assert autopr._should_skip("memory/supervisor.log", ("memory/",), set()) is True


def test_should_include_normal_code_path() -> None:
    assert autopr._should_skip("scripts/supervisor_loop.py", ("agent/",), {"openclaw.json"}) is False
