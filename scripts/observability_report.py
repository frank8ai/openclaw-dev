#!/usr/bin/env python3
"""Summarize supervisor observability metrics and emit threshold alerts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

DEFAULT_CONFIG = {
    "window": 20,
    "failure_rate_alert": 0.35,
    "route_miss_rate_alert": 0.05,
    "prompt_token_budget": 2400,
    "token_cost_alert_usd": 0.0,
}
FAILURE_STATUS_MARKERS = (
    "tests_failed",
    "run_tests_failed",
    "codex_failed",
    "sync_failed",
    "autopr_failed",
    "max_attempts",
    "codex_timeout",
    "codex_no_progress",
)


def _load_config(repo: Path) -> dict:
    path = repo / "openclaw.json"
    merged = dict(DEFAULT_CONFIG)
    if not path.exists():
        return merged
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return merged
    if not isinstance(payload, dict):
        return merged
    supervisor = payload.get("supervisor", {})
    if not isinstance(supervisor, dict):
        return merged
    candidate = supervisor.get("observability", {})
    if not isinstance(candidate, dict):
        return merged
    merged.update(candidate)
    return merged


def _load_records(repo: Path, window: int) -> list[dict]:
    path = repo / "memory" / "supervisor_nightly.log"
    if not path.exists():
        return []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    records: list[dict] = []
    for line in lines[-max(1, window):]:
        stripped = line.strip()
        if not stripped:
            continue
        try:
            payload = json.loads(stripped)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            records.append(payload)
    return records


def compute_metrics(records: list[dict]) -> dict:
    total = len(records)
    failures = 0
    route_total = 0
    route_hits = 0
    prompt_tokens: list[int] = []
    token_cost_usd: list[float] = []
    for record in records:
        status = str(record.get("status", ""))
        if any(marker in status for marker in FAILURE_STATUS_MARKERS):
            failures += 1
        if "route_hit" in record:
            route_total += 1
            if bool(record.get("route_hit", False)):
                route_hits += 1
        prompt = record.get("prompt_tokens")
        if isinstance(prompt, int):
            prompt_tokens.append(max(0, prompt))
        cost = record.get("token_cost_usd")
        if isinstance(cost, (int, float)):
            token_cost_usd.append(max(0.0, float(cost)))

    failure_rate = failures / total if total else 0.0
    route_miss_rate = 0.0
    if route_total > 0:
        route_miss_rate = 1.0 - (route_hits / route_total)
    avg_prompt_tokens = (sum(prompt_tokens) / len(prompt_tokens)) if prompt_tokens else 0.0
    avg_token_cost_usd = (sum(token_cost_usd) / len(token_cost_usd)) if token_cost_usd else 0.0
    return {
        "samples": total,
        "failure_rate": failure_rate,
        "route_miss_rate": route_miss_rate,
        "avg_prompt_tokens": avg_prompt_tokens,
        "avg_token_cost_usd": avg_token_cost_usd,
    }


def compute_alerts(metrics: dict, config: dict) -> list[str]:
    alerts: list[str] = []
    if float(metrics.get("failure_rate", 0.0)) > float(config.get("failure_rate_alert", 0.35)):
        alerts.append("failure_rate exceeded threshold")
    if float(metrics.get("route_miss_rate", 0.0)) > float(config.get("route_miss_rate_alert", 0.05)):
        alerts.append("route_miss_rate exceeded threshold")
    if float(metrics.get("avg_prompt_tokens", 0.0)) > float(config.get("prompt_token_budget", 2400)):
        alerts.append("avg_prompt_tokens exceeded budget")
    token_cost_alert = float(config.get("token_cost_alert_usd", 0.0))
    if token_cost_alert > 0.0 and float(metrics.get("avg_token_cost_usd", 0.0)) > token_cost_alert:
        alerts.append("avg_token_cost_usd exceeded budget")
    return alerts


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default=".", help="Repo root path.")
    parser.add_argument("--window", type=int, default=None, help="Override observability window.")
    parser.add_argument("--json", action="store_true", help="Print JSON output.")
    parser.add_argument("--fail-on-alert", action="store_true", help="Exit non-zero when alerts exist.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo = Path(args.repo).expanduser().resolve()
    config = _load_config(repo)
    window = int(config.get("window", 20))
    if args.window is not None:
        window = max(1, args.window)
    records = _load_records(repo, window)
    metrics = compute_metrics(records)
    alerts = compute_alerts(metrics, config)
    output = {"metrics": metrics, "alerts": alerts}

    if args.json:
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        print(f"samples={metrics['samples']}")
        print(f"failure_rate={metrics['failure_rate']:.2%}")
        print(f"route_miss_rate={metrics['route_miss_rate']:.2%}")
        print(f"avg_prompt_tokens={metrics['avg_prompt_tokens']:.0f}")
        print(f"avg_token_cost_usd={metrics['avg_token_cost_usd']:.6f}")
        if alerts:
            print("alerts:")
            for item in alerts:
                print(f"- {item}")
        else:
            print("alerts: none")

    if args.fail_on_alert and alerts:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
