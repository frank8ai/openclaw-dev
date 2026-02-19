#!/usr/bin/env python3
"""Top-1% readiness score for OpenClaw dev supervisor projects."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

DEFAULT_THRESHOLDS: Dict[str, float] = {
    "min_samples": 30.0,
    "max_failure_rate": 0.03,
    "max_timeout_no_progress_rate": 0.02,
    "max_route_miss_rate": 0.01,
    "max_avg_prompt_tokens": 1800.0,
    "min_success_rate": 0.80,
}
DEFAULT_WINDOW = 60
DEFAULT_MIN_SCORE = 90
HARD_FAILURE_MARKERS = (
    "tests_failed",
    "run_tests_failed",
    "codex_failed",
    "sync_failed",
    "autopr_failed",
    "max_attempts",
    "codex_timeout",
    "codex_no_progress",
)
TIMEOUT_NO_PROGRESS_MARKERS = ("codex_timeout", "codex_no_progress", "max_attempts")


def _status_tokens(status_raw: object) -> List[str]:
    if isinstance(status_raw, list):
        tokens: List[str] = []
        for item in status_raw:
            if isinstance(item, str):
                cleaned = item.strip()
                if cleaned:
                    tokens.append(cleaned)
        return tokens
    if not isinstance(status_raw, str):
        return []
    return [item.strip() for item in status_raw.split(",") if item.strip()]


def _load_repo_payload(repo: Path) -> Dict[str, Any]:
    path = repo / "openclaw.json"
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(payload, dict):
        return {}
    return payload


def _resolve_supervisor(payload: Dict[str, Any]) -> Dict[str, Any]:
    supervisor = payload.get("supervisor", {})
    if isinstance(supervisor, dict):
        return supervisor
    return {}


def resolve_thresholds_and_window(
    repo: Path, window_override: int | None = None
) -> Tuple[Dict[str, float], int, Dict[str, Any]]:
    payload = _load_repo_payload(repo)
    supervisor = _resolve_supervisor(payload)
    observability = supervisor.get("observability", {})
    if not isinstance(observability, dict):
        observability = {}
    top1 = supervisor.get("top1", {})
    if not isinstance(top1, dict):
        top1 = {}

    thresholds: Dict[str, float] = dict(DEFAULT_THRESHOLDS)
    prompt_budget = observability.get("prompt_token_budget")
    if isinstance(prompt_budget, (int, float)) and prompt_budget > 0:
        thresholds["max_avg_prompt_tokens"] = float(prompt_budget)

    for key in list(thresholds.keys()):
        value = top1.get(key)
        if isinstance(value, (int, float)):
            thresholds[key] = float(value)

    obs_window = observability.get("window")
    top1_window = top1.get("window")
    window = DEFAULT_WINDOW
    if isinstance(obs_window, int) and obs_window > 0:
        window = max(window, obs_window)
    if isinstance(top1_window, int) and top1_window > 0:
        window = top1_window
    if window_override is not None:
        window = max(1, int(window_override))
    return thresholds, window, supervisor


def load_records(repo: Path, window: int) -> List[Dict[str, Any]]:
    path = repo / "memory" / "supervisor_nightly.log"
    if not path.exists():
        return []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    records: List[Dict[str, Any]] = []
    for line in lines[-max(1, window) :]:
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


def compute_metrics(records: List[Dict[str, Any]]) -> Dict[str, float]:
    total = len(records)
    failures = 0
    timeout_no_progress = 0
    successes = 0
    route_total = 0
    route_hits = 0
    prompt_tokens: List[int] = []
    token_cost_usd: List[float] = []

    for record in records:
        token_list = _status_tokens(record.get("status", ""))
        tokens = set(token_list)
        is_failure = any(marker in tokens for marker in HARD_FAILURE_MARKERS)
        if is_failure:
            failures += 1
        if any(marker in tokens for marker in TIMEOUT_NO_PROGRESS_MARKERS):
            timeout_no_progress += 1

        if ("tests_ok" in tokens or "run_tests_ok" in tokens) and not is_failure:
            successes += 1

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

    failure_rate = (failures / total) if total else 0.0
    timeout_no_progress_rate = (timeout_no_progress / total) if total else 0.0
    success_rate = (successes / total) if total else 0.0
    route_miss_rate = 0.0
    if route_total > 0:
        route_miss_rate = 1.0 - (route_hits / route_total)
    avg_prompt_tokens = (sum(prompt_tokens) / len(prompt_tokens)) if prompt_tokens else 0.0
    avg_token_cost_usd = (sum(token_cost_usd) / len(token_cost_usd)) if token_cost_usd else 0.0
    return {
        "samples": float(total),
        "failure_rate": failure_rate,
        "timeout_no_progress_rate": timeout_no_progress_rate,
        "success_rate": success_rate,
        "route_miss_rate": route_miss_rate,
        "avg_prompt_tokens": avg_prompt_tokens,
        "avg_token_cost_usd": avg_token_cost_usd,
    }


def _check_leq(check_id: str, actual: float, target: float, weight: int, detail: str) -> Dict[str, Any]:
    return {
        "id": check_id,
        "ok": actual <= target,
        "actual": actual,
        "target": target,
        "op": "<=",
        "weight": weight,
        "detail": detail,
    }


def _check_geq(check_id: str, actual: float, target: float, weight: int, detail: str) -> Dict[str, Any]:
    return {
        "id": check_id,
        "ok": actual >= target,
        "actual": actual,
        "target": target,
        "op": ">=",
        "weight": weight,
        "detail": detail,
    }


def _feature_flag(supervisor: Dict[str, Any], section: str, key: str) -> bool:
    candidate = supervisor.get(section, {})
    if not isinstance(candidate, dict):
        return False
    return bool(candidate.get(key, False))


def build_checks(
    metrics: Dict[str, float], thresholds: Dict[str, float], supervisor: Dict[str, Any]
) -> List[Dict[str, Any]]:
    checks: List[Dict[str, Any]] = [
        _check_geq(
            "samples",
            metrics["samples"],
            thresholds["min_samples"],
            10,
            "Need enough production-like runs to trust the signal.",
        ),
        _check_leq(
            "failure_rate",
            metrics["failure_rate"],
            thresholds["max_failure_rate"],
            20,
            "Keep hard failures rare in steady-state operation.",
        ),
        _check_leq(
            "timeout_no_progress_rate",
            metrics["timeout_no_progress_rate"],
            thresholds["max_timeout_no_progress_rate"],
            10,
            "Timeouts with no progress should be exceptional.",
        ),
        _check_leq(
            "route_miss_rate",
            metrics["route_miss_rate"],
            thresholds["max_route_miss_rate"],
            10,
            "Agent routing should be deterministic.",
        ),
        _check_leq(
            "avg_prompt_tokens",
            metrics["avg_prompt_tokens"],
            thresholds["max_avg_prompt_tokens"],
            5,
            "Prompt budget discipline is required for sustained throughput.",
        ),
        _check_geq(
            "success_rate",
            metrics["success_rate"],
            thresholds["min_success_rate"],
            10,
            "Most runs should complete with tests passing.",
        ),
    ]

    feature_checks = [
        ("second_brain_enabled", _feature_flag(supervisor, "second_brain", "enabled"), 8),
        ("memory_namespace_enabled", _feature_flag(supervisor, "memory_namespace", "enabled"), 8),
        (
            "memory_strict_isolation",
            bool(supervisor.get("memory_namespace", {}).get("strict_isolation", False))
            if isinstance(supervisor.get("memory_namespace", {}), dict)
            else False,
            6,
        ),
        ("observability_enabled", _feature_flag(supervisor, "observability", "enabled"), 4),
        ("security_enabled", _feature_flag(supervisor, "security", "enabled"), 5),
        (
            "security_autopr_approval",
            bool(supervisor.get("security", {}).get("require_autopr_approval", False))
            if isinstance(supervisor.get("security", {}), dict)
            else False,
            4,
        ),
    ]
    for check_id, enabled, weight in feature_checks:
        checks.append(
            {
                "id": check_id,
                "ok": enabled,
                "actual": bool(enabled),
                "target": True,
                "op": "==",
                "weight": weight,
                "detail": "Top-1 operations require this control plane capability.",
            }
        )
    return checks


def score_checks(checks: List[Dict[str, Any]]) -> int:
    total_weight = sum(int(item.get("weight", 0)) for item in checks)
    if total_weight <= 0:
        return 0
    passed_weight = sum(int(item.get("weight", 0)) for item in checks if bool(item.get("ok", False)))
    return int(round((passed_weight / total_weight) * 100))


def build_recommendations(checks: List[Dict[str, Any]]) -> List[str]:
    messages = {
        "samples": "Increase real runs; keep a rolling window of at least 30 recent samples.",
        "failure_rate": "Reduce hard failures by improving prompt specificity and retry strategy.",
        "timeout_no_progress_rate": "Raise codex timeout or tighten task scope to avoid empty timeouts.",
        "route_miss_rate": "Review agent bindings and router rules; enforce deterministic routing tests.",
        "avg_prompt_tokens": "Trim injected context and summarize memory to reduce prompt size.",
        "success_rate": "Improve first-pass completion by tightening PLAN/TASK quality and QA automation.",
        "second_brain_enabled": "Enable second_brain context injection for long-horizon continuity.",
        "memory_namespace_enabled": "Enable memory_namespace for project-level memory isolation.",
        "memory_strict_isolation": "Set memory_namespace.strict_isolation=true.",
        "observability_enabled": "Enable supervisor.observability and keep nightly logs available.",
        "security_enabled": "Enable supervisor.security and keep audit logging active.",
        "security_autopr_approval": "Require approval for Auto-PR via security gate.",
    }
    recs: List[str] = []
    for item in checks:
        if bool(item.get("ok", False)):
            continue
        check_id = str(item.get("id", ""))
        rec = messages.get(check_id, f"Fix failed check: {check_id}.")
        if rec not in recs:
            recs.append(rec)
    return recs


def evaluate_top1(
    records: List[Dict[str, Any]],
    thresholds: Dict[str, float],
    supervisor: Dict[str, Any],
    min_score: int = DEFAULT_MIN_SCORE,
) -> Dict[str, Any]:
    metrics = compute_metrics(records)
    checks = build_checks(metrics, thresholds, supervisor)
    score = score_checks(checks)
    failed_checks = [item["id"] for item in checks if not bool(item.get("ok", False))]
    top1_ready = (score >= min_score) and (len(failed_checks) == 0)
    return {
        "top1_ready": top1_ready,
        "score": score,
        "min_score": min_score,
        "metrics": metrics,
        "thresholds": thresholds,
        "checks": checks,
        "failed_checks": failed_checks,
        "recommendations": build_recommendations(checks),
    }


def _fmt_percent(value: float) -> str:
    return f"{value:.2%}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default=".", help="Repo root path.")
    parser.add_argument("--window", type=int, default=None, help="Override rolling window.")
    parser.add_argument("--min-score", type=int, default=DEFAULT_MIN_SCORE, help="Minimum score for readiness pass.")
    parser.add_argument("--json", action="store_true", help="Print JSON output.")
    parser.add_argument("--fail-on-gap", action="store_true", help="Exit non-zero when not top1_ready.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo = Path(args.repo).expanduser().resolve()
    thresholds, window, supervisor = resolve_thresholds_and_window(repo, args.window)
    records = load_records(repo, window)
    report = evaluate_top1(records, thresholds, supervisor, min_score=max(1, int(args.min_score)))
    report["window"] = window
    report["sample_count"] = len(records)

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"top1_ready={'yes' if report['top1_ready'] else 'no'}")
        print(f"score={report['score']}/{report['min_score']}")
        metrics = report["metrics"]
        print(f"samples={int(metrics['samples'])} (window={window})")
        print(f"failure_rate={_fmt_percent(float(metrics['failure_rate']))}")
        print(f"timeout_no_progress_rate={_fmt_percent(float(metrics['timeout_no_progress_rate']))}")
        print(f"route_miss_rate={_fmt_percent(float(metrics['route_miss_rate']))}")
        print(f"success_rate={_fmt_percent(float(metrics['success_rate']))}")
        print(f"avg_prompt_tokens={metrics['avg_prompt_tokens']:.0f}")
        if report["failed_checks"]:
            print("failed_checks:")
            for check_id in report["failed_checks"]:
                print(f"- {check_id}")
            if report["recommendations"]:
                print("recommendations:")
                for item in report["recommendations"]:
                    print(f"- {item}")
        else:
            print("failed_checks: none")

    if args.fail_on_gap and not bool(report["top1_ready"]):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
