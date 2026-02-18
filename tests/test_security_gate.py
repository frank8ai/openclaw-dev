from __future__ import annotations

import json
from pathlib import Path

from tests.load_script import load_script_module

security_gate = load_script_module("scripts/security_gate.py", "security_gate")


def test_set_and_check_approval(tmp_path: Path) -> None:
    path = tmp_path / "APPROVALS.json"
    security_gate.set_approval(path, "autopr", True)
    assert security_gate.is_action_approved(path, "autopr") is True
    security_gate.set_approval(path, "autopr", False)
    assert security_gate.is_action_approved(path, "autopr") is False


def test_append_audit_log_writes_jsonl(tmp_path: Path) -> None:
    log_path = tmp_path / "security_audit.jsonl"
    security_gate.append_audit_log(
        log_path,
        event="autopr",
        outcome="denied",
        detail="missing approval",
        metadata={"action": "autopr"},
    )
    lines = log_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    payload = json.loads(lines[0])
    assert payload["event"] == "autopr"
    assert payload["outcome"] == "denied"
