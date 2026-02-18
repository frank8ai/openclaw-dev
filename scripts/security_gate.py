#!/usr/bin/env python3
"""Security approval and audit helpers for outbound/high-risk actions."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

DEFAULT_APPROVALS = {
    "autopr": False,
    "publish_external": False,
    "service_restart": False,
}


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def read_approvals(path: Path) -> dict:
    if not path.exists():
        return dict(DEFAULT_APPROVALS)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return dict(DEFAULT_APPROVALS)
    if not isinstance(payload, dict):
        return dict(DEFAULT_APPROVALS)
    merged = dict(DEFAULT_APPROVALS)
    for key, value in payload.items():
        if isinstance(value, bool):
            merged[key] = value
    return merged


def write_approvals(path: Path, approvals: dict) -> None:
    normalized: dict[str, bool] = {}
    for key, value in approvals.items():
        if isinstance(key, str) and key.strip():
            normalized[key.strip()] = bool(value)
    payload = dict(DEFAULT_APPROVALS)
    payload.update(normalized)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def set_approval(path: Path, action: str, allow: bool) -> dict:
    approvals = read_approvals(path)
    approvals[action.strip()] = bool(allow)
    write_approvals(path, approvals)
    return approvals


def is_action_approved(path: Path, action: str) -> bool:
    approvals = read_approvals(path)
    return bool(approvals.get(action.strip(), False))


def append_audit_log(
    log_path: Path,
    *,
    event: str,
    outcome: str,
    detail: str,
    metadata: dict | None = None,
) -> None:
    record: dict[str, object] = {
        "timestamp": _now_iso(),
        "event": event,
        "outcome": outcome,
        "detail": detail,
    }
    if isinstance(metadata, dict) and metadata:
        record["metadata"] = metadata
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", default="agent/APPROVALS.json", help="Approval json path.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    status = subparsers.add_parser("status", help="Print current approvals.")
    status.add_argument("--json", action="store_true")

    approve = subparsers.add_parser("approve", help="Approve one action.")
    approve.add_argument("--action", required=True)

    revoke = subparsers.add_parser("revoke", help="Revoke one action.")
    revoke.add_argument("--action", required=True)

    return parser.parse_args()


def main() -> int:
    args = parse_args()
    path = Path(args.file).expanduser().resolve()

    if args.command == "approve":
        payload = set_approval(path, str(args.action), True)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    if args.command == "revoke":
        payload = set_approval(path, str(args.action), False)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    payload = read_approvals(path)
    if bool(getattr(args, "json", False)):
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    for key in sorted(payload.keys()):
        print(f"{key}={'allow' if payload[key] else 'deny'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
