from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str((ROOT / "scripts").resolve()))


def _load_module(relative_path: str, module_name: str):
    script_path = ROOT / relative_path
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {relative_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


handoff = _load_module("scripts/handoff_protocol.py", "handoff_protocol_eval")
trigger = _load_module("scripts/trigger_supervisor.py", "trigger_supervisor_eval")


def test_eval_route_isolation_key_mismatch_detected() -> None:
    expected = handoff.route_key("discord", "researcher", "user-a")
    observed = handoff.route_key("discord", "researcher", "user-b")
    assert handoff.is_route_isolated(expected, observed) is False


def test_eval_convergence_done_within_hops() -> None:
    history = [
        {"from_agent": "commander", "to_agent": "researcher", "status": "in_progress"},
        {"from_agent": "researcher", "to_agent": "coder", "status": "in_progress"},
        {"from_agent": "coder", "to_agent": "commander", "status": "done"},
    ]
    ok, reason = handoff.evaluate_handoff_convergence(history, max_hops=6, ping_pong_limit=2)
    assert ok is True
    assert "done" in reason


def test_eval_trigger_fingerprint_changes_with_handoff_id() -> None:
    first = trigger.trigger_fingerprint("new-task", "A", True, "default", "main", "proj", "h-1")
    second = trigger.trigger_fingerprint("new-task", "A", True, "default", "main", "proj", "h-2")
    assert first != second
