from __future__ import annotations

from tests.load_script import load_script_module

top1 = load_script_module("scripts/top1_readiness.py", "top1_readiness")


def _all_features_enabled() -> dict:
    return {
        "second_brain": {"enabled": True},
        "memory_namespace": {"enabled": True, "strict_isolation": True},
        "observability": {"enabled": True},
        "security": {"enabled": True, "require_autopr_approval": True},
    }


def test_compute_metrics_treats_timeout_progress_as_non_failure() -> None:
    records = [
        {"status": "codex_timeout_progress,run_tests_ok", "route_hit": True, "prompt_tokens": 300},
        {"status": "codex_ok,tests_ok", "route_hit": True, "prompt_tokens": 200},
    ]
    metrics = top1.compute_metrics(records)
    assert metrics["samples"] == 2
    assert metrics["failure_rate"] == 0.0
    assert metrics["timeout_no_progress_rate"] == 0.0
    assert metrics["success_rate"] == 1.0


def test_evaluate_top1_ready_for_clean_signal() -> None:
    thresholds = dict(top1.DEFAULT_THRESHOLDS)
    thresholds["min_samples"] = 3.0
    records = [
        {"status": "codex_ok,tests_ok", "route_hit": True, "prompt_tokens": 400},
        {"status": "codex_ok,tests_ok", "route_hit": True, "prompt_tokens": 450},
        {"status": "codex_timeout_progress,run_tests_ok", "route_hit": True, "prompt_tokens": 500},
    ]
    report = top1.evaluate_top1(records, thresholds, _all_features_enabled(), min_score=90)
    assert report["top1_ready"] is True
    assert report["score"] == 100
    assert report["failed_checks"] == []


def test_evaluate_top1_not_ready_when_controls_missing_and_failures_present() -> None:
    thresholds = dict(top1.DEFAULT_THRESHOLDS)
    thresholds["min_samples"] = 2.0
    records = [
        {"status": "codex_failed", "route_hit": False, "prompt_tokens": 2600},
        {"status": "codex_ok,tests_failed", "route_hit": False, "prompt_tokens": 2800},
    ]
    report = top1.evaluate_top1(records, thresholds, {}, min_score=90)
    assert report["top1_ready"] is False
    assert "failure_rate" in report["failed_checks"]
    assert "memory_namespace_enabled" in report["failed_checks"]
    assert "security_enabled" in report["failed_checks"]
