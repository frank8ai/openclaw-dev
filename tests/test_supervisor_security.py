from __future__ import annotations

import json
from pathlib import Path

from tests.load_script import load_script_module

supervisor = load_script_module("scripts/supervisor_loop.py", "supervisor_loop_security")


def test_resolve_security_config_with_overrides(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir(parents=True, exist_ok=True)
    config = {
        "supervisor": {
            "security": {
                "enabled": True,
                "require_autopr_approval": False,
                "allowed_operation_classes": ["read_repo"],
                "blocked_command_patterns": ["sudo "],
            }
        }
    }
    (repo / "openclaw.json").write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    merged = supervisor.resolve_security_config(repo)
    assert merged["enabled"] is True
    assert merged["require_autopr_approval"] is False
    assert merged["allowed_operation_classes"] == ["read_repo"]
    assert merged["blocked_command_patterns"] == ["sudo"]


def test_build_security_context_contains_core_constraints() -> None:
    config = {
        "enabled": True,
        "allowed_operation_classes": ["read_repo", "edit_files"],
        "blocked_command_patterns": ["rm -rf /", "sudo "],
    }
    text = supervisor.build_security_context(config)
    assert "Allowed operation classes" in text
    assert "Blocked command patterns" in text
