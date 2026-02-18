from __future__ import annotations

from tests.load_script import load_script_module

handoff = load_script_module("scripts/handoff_protocol.py", "handoff_protocol")


def test_build_template_is_valid() -> None:
    payload = handoff.build_handoff_template("planner", "coder", "Ship feature A")
    ok, errors = handoff.validate_handoff(payload)
    assert ok is True
    assert errors == []


def test_validate_handoff_rejects_missing_required_field() -> None:
    payload = handoff.build_handoff_template("planner", "coder", "Ship feature A")
    payload.pop("rollback_plan")
    ok, errors = handoff.validate_handoff(payload)
    assert ok is False
    assert any("rollback_plan" in err for err in errors)


def test_route_isolation_predicate() -> None:
    expected = handoff.route_key("discord", "engineer", "user-1")
    observed = handoff.route_key("discord", "engineer", "user-1")
    assert handoff.is_route_isolated(expected, observed) is True


def test_handoff_convergence_detects_ping_pong() -> None:
    history = [
        {"from_agent": "planner", "to_agent": "coder", "status": "in_progress"},
        {"from_agent": "coder", "to_agent": "planner", "status": "in_progress"},
        {"from_agent": "planner", "to_agent": "coder", "status": "in_progress"},
        {"from_agent": "coder", "to_agent": "planner", "status": "in_progress"},
    ]
    ok, reason = handoff.evaluate_handoff_convergence(history, max_hops=8, ping_pong_limit=1)
    assert ok is False
    assert "ping-pong" in reason
