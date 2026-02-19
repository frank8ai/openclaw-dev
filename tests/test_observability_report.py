from __future__ import annotations

import json
from pathlib import Path

from tests.load_script import load_script_module

obs = load_script_module("scripts/observability_report.py", "observability_report")


def test_compute_metrics_aggregates_failure_and_route() -> None:
    records = [
        {"status": "codex_ok,tests_ok", "route_hit": True, "prompt_tokens": 1000, "token_cost_usd": 0.01},
        {"status": "codex_ok,tests_failed", "route_hit": False, "prompt_tokens": 2000, "token_cost_usd": 0.02},
    ]
    metrics = obs.compute_metrics(records)
    assert metrics["samples"] == 2
    assert metrics["failure_rate"] == 0.5
    assert metrics["route_miss_rate"] == 0.5
    assert metrics["avg_prompt_tokens"] == 1500


def test_load_records_respects_window(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    memory_dir = repo / "memory"
    memory_dir.mkdir(parents=True, exist_ok=True)
    log = memory_dir / "supervisor_nightly.log"
    payloads = [{"status": "a"}, {"status": "b"}, {"status": "c"}]
    log.write_text("\n".join(json.dumps(item) for item in payloads) + "\n", encoding="utf-8")
    recent = obs._load_records(repo, window=2)
    assert len(recent) == 2
    assert recent[0]["status"] == "b"
    assert recent[1]["status"] == "c"


def test_compute_alerts_triggers_on_threshold() -> None:
    metrics = {
        "samples": 10,
        "failure_rate": 0.4,
        "route_miss_rate": 0.1,
        "avg_prompt_tokens": 3000,
        "avg_token_cost_usd": 0.02,
    }
    config = {
        "failure_rate_alert": 0.35,
        "route_miss_rate_alert": 0.05,
        "prompt_token_budget": 2400,
        "token_cost_alert_usd": 0.01,
    }
    alerts = obs.compute_alerts(metrics, config)
    assert len(alerts) == 4


def test_compute_metrics_timeout_progress_is_not_failure() -> None:
    records = [
        {"status": "codex_timeout_progress,run_tests_ok", "route_hit": True, "prompt_tokens": 200},
        {"status": "codex_ok,tests_ok", "route_hit": True, "prompt_tokens": 250},
    ]
    metrics = obs.compute_metrics(records)
    assert metrics["samples"] == 2
    assert metrics["failure_rate"] == 0.0


def test_compute_metrics_supports_list_status_tokens() -> None:
    records = [
        {"status": ["codex_ok", "tests_ok"], "route_hit": True},
        {"status": ["codex_failed"], "route_hit": False},
    ]
    metrics = obs.compute_metrics(records)
    assert metrics["samples"] == 2
    assert metrics["failure_rate"] == 0.5
    assert metrics["route_miss_rate"] == 0.5
