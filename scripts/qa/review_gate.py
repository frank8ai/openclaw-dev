#!/usr/bin/env python3
"""Validate review-policy artifacts required by quality gates."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

REQUIRED_FILES = [
    ROOT / "docs" / "QUALITY_GATES.md",
    ROOT / ".github" / "pull_request_template.md",
]

REQUIRED_CHECKLIST_ITEMS = [
    "- [ ] Lint and typecheck passed",
    "- [ ] Tests and eval suite passed",
    "- [ ] Security scan passed",
    "- [ ] Scope is minimal and documented",
]


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def _validate_status_json() -> list[str]:
    issues: list[str] = []
    status_path = ROOT / "agent" / "STATUS.json"
    if not status_path.exists():
        issues.append("Missing agent/STATUS.json")
        return issues
    try:
        payload = json.loads(_read(status_path))
    except json.JSONDecodeError:
        issues.append("agent/STATUS.json is not valid JSON")
        return issues
    if not isinstance(payload, dict):
        issues.append("agent/STATUS.json must be a JSON object")
    return issues


def _validate_files() -> list[str]:
    issues: list[str] = []
    for path in REQUIRED_FILES:
        if not path.exists():
            issues.append(f"Missing required file: {path.relative_to(ROOT)}")
    return issues


def _validate_pr_template() -> list[str]:
    issues: list[str] = []
    template = _read(ROOT / ".github" / "pull_request_template.md")
    if not template:
        return ["Pull request template is missing or empty"]
    for item in REQUIRED_CHECKLIST_ITEMS:
        if item not in template:
            issues.append(f"PR template missing checklist item: {item}")
    return issues


def main() -> int:
    issues: list[str] = []
    issues.extend(_validate_status_json())
    issues.extend(_validate_files())
    issues.extend(_validate_pr_template())

    if issues:
        for issue in issues:
            print(f"REVIEW_GATE_FAIL: {issue}", file=sys.stderr)
        return 1

    print("review_gate: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
