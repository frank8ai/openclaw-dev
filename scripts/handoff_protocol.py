#!/usr/bin/env python3
"""Standardized JSON handoff contract for multi-agent collaboration."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Sequence

HANDOFF_VERSION = "1.0"
ALLOWED_PRIORITIES = {"low", "medium", "high", "critical"}
ALLOWED_STATUS = {"planned", "in_progress", "done", "blocked"}
REQUIRED_FIELDS = (
    "version",
    "handoff_id",
    "from_agent",
    "to_agent",
    "objective",
    "inputs",
    "deliverables",
    "acceptance_criteria",
    "risks",
    "rollback_plan",
    "priority",
    "status",
    "created_at",
)


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def generate_handoff_id(prefix: str = "handoff") -> str:
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    return f"{prefix}-{ts}"


def _is_non_empty_text(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _validate_str_list(name: str, value: object, errors: list[str]) -> None:
    if not isinstance(value, list) or not value:
        errors.append(f"{name} must be a non-empty string list")
        return
    for item in value:
        if not _is_non_empty_text(item):
            errors.append(f"{name} must contain non-empty strings")
            return


def _validate_iso8601(value: object, field_name: str, errors: list[str]) -> None:
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{field_name} must be a non-empty string")
        return
    candidate = value.strip()
    normalized = candidate[:-1] + "+00:00" if candidate.endswith("Z") else candidate
    try:
        datetime.fromisoformat(normalized)
    except ValueError:
        errors.append(f"{field_name} must be ISO-8601 datetime")


def validate_handoff(payload: object) -> tuple[bool, list[str]]:
    errors: list[str] = []
    if not isinstance(payload, dict):
        return False, ["handoff payload must be a JSON object"]

    for field in REQUIRED_FIELDS:
        if field not in payload:
            errors.append(f"missing required field: {field}")

    if errors:
        return False, errors

    if payload.get("version") != HANDOFF_VERSION:
        errors.append(f"version must be '{HANDOFF_VERSION}'")
    if not _is_non_empty_text(payload.get("handoff_id")):
        errors.append("handoff_id must be a non-empty string")
    if not _is_non_empty_text(payload.get("from_agent")):
        errors.append("from_agent must be a non-empty string")
    if not _is_non_empty_text(payload.get("to_agent")):
        errors.append("to_agent must be a non-empty string")
    if _is_non_empty_text(payload.get("from_agent")) and payload.get("from_agent") == payload.get("to_agent"):
        errors.append("from_agent and to_agent must be different")
    if not _is_non_empty_text(payload.get("objective")):
        errors.append("objective must be a non-empty string")
    _validate_str_list("inputs", payload.get("inputs"), errors)
    _validate_str_list("deliverables", payload.get("deliverables"), errors)
    _validate_str_list("acceptance_criteria", payload.get("acceptance_criteria"), errors)
    _validate_str_list("risks", payload.get("risks"), errors)
    if not _is_non_empty_text(payload.get("rollback_plan")):
        errors.append("rollback_plan must be a non-empty string")
    priority = payload.get("priority")
    if not isinstance(priority, str) or priority not in ALLOWED_PRIORITIES:
        errors.append(f"priority must be one of: {sorted(ALLOWED_PRIORITIES)}")
    status = payload.get("status")
    if not isinstance(status, str) or status not in ALLOWED_STATUS:
        errors.append(f"status must be one of: {sorted(ALLOWED_STATUS)}")
    _validate_iso8601(payload.get("created_at"), "created_at", errors)

    due_at = payload.get("due_at")
    if due_at is not None:
        _validate_iso8601(due_at, "due_at", errors)

    tags = payload.get("tags")
    if tags is not None and (not isinstance(tags, list) or any(not _is_non_empty_text(tag) for tag in tags)):
        errors.append("tags must be a string list when provided")

    metadata = payload.get("metadata")
    if metadata is not None and not isinstance(metadata, dict):
        errors.append("metadata must be an object when provided")

    return not errors, errors


def build_handoff_template(from_agent: str, to_agent: str, objective: str) -> dict:
    return {
        "version": HANDOFF_VERSION,
        "handoff_id": generate_handoff_id(),
        "from_agent": from_agent.strip() or "requester",
        "to_agent": to_agent.strip() or "main",
        "objective": objective.strip() or "TBD objective",
        "inputs": ["task brief"],
        "deliverables": ["implementation summary", "verification result"],
        "acceptance_criteria": ["quality gates pass", "scope constraints respected"],
        "risks": ["dependency mismatch", "context drift"],
        "rollback_plan": "revert affected files to previous known-good commit",
        "priority": "medium",
        "status": "planned",
        "created_at": now_iso(),
        "tags": ["handoff", "standardized"],
        "metadata": {},
    }


def summarize_handoff(payload: dict, max_items: int = 3) -> str:
    ok, errors = validate_handoff(payload)
    if not ok:
        joined = "; ".join(errors[:5]) if errors else "unknown handoff format issue"
        return f"[HANDOFF_INVALID] {joined}"
    lines = [
        "[HANDOFF]",
        f"id={payload.get('handoff_id')} from={payload.get('from_agent')} to={payload.get('to_agent')}",
        f"priority={payload.get('priority')} status={payload.get('status')}",
        f"objective={payload.get('objective')}",
    ]
    for field in ("deliverables", "acceptance_criteria", "risks"):
        values = payload.get(field, [])
        if isinstance(values, list):
            compact = ", ".join(str(item) for item in values[:max_items])
            lines.append(f"{field}={compact}")
    return "\n".join(lines)


def route_key(channel: str, account_id: str, peer_id: str) -> str:
    return f"{channel.strip().lower()}::{account_id.strip().lower()}::{peer_id.strip().lower()}"


def is_route_isolated(expected_key: str, observed_key: str) -> bool:
    return expected_key.strip().lower() == observed_key.strip().lower()


def evaluate_handoff_convergence(
    history: Sequence[dict],
    max_hops: int = 8,
    ping_pong_limit: int = 2,
) -> tuple[bool, str]:
    if not history:
        return False, "empty handoff history"

    reversals = 0
    seen_done = False
    for index, item in enumerate(history):
        if not isinstance(item, dict):
            return False, f"invalid handoff at index={index}"
        status = item.get("status")
        if status == "done":
            seen_done = True

        if index == 0:
            continue
        prev = history[index - 1]
        if not isinstance(prev, dict):
            return False, f"invalid handoff at index={index - 1}"
        prev_from = str(prev.get("from_agent", "")).strip()
        prev_to = str(prev.get("to_agent", "")).strip()
        curr_from = str(item.get("from_agent", "")).strip()
        curr_to = str(item.get("to_agent", "")).strip()
        if prev_from == curr_to and prev_to == curr_from:
            reversals += 1
            if reversals > ping_pong_limit:
                return False, "ping-pong limit exceeded"
        else:
            reversals = 0

    if seen_done:
        return True, "handoff converged with done status"
    if len(history) > max_hops:
        return False, "max hops exceeded without done status"
    return True, "handoff still within hop budget"


def load_handoff_file(path: Path) -> tuple[dict | None, list[str]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        return None, [f"read failed: {exc}"]
    except json.JSONDecodeError as exc:
        return None, [f"invalid json: {exc}"]
    ok, errors = validate_handoff(payload)
    if not ok:
        return None, errors
    return payload, []


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    template = subparsers.add_parser("template", help="Print a handoff JSON template.")
    template.add_argument("--from-agent", default="requester")
    template.add_argument("--to-agent", default="main")
    template.add_argument("--objective", default="TBD objective")

    validate = subparsers.add_parser("validate", help="Validate a handoff JSON file.")
    validate.add_argument("--file", required=True, help="Path to handoff json file.")

    summarize = subparsers.add_parser("summarize", help="Summarize a handoff JSON file.")
    summarize.add_argument("--file", required=True, help="Path to handoff json file.")
    summarize.add_argument("--max-items", type=int, default=3)

    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.command == "template":
        template_payload = build_handoff_template(args.from_agent, args.to_agent, args.objective)
        print(json.dumps(template_payload, ensure_ascii=False, indent=2))
        return 0

    path = Path(args.file).expanduser().resolve()
    payload, errors = load_handoff_file(path)
    if payload is None:
        for err in errors:
            print(f"HANDOFF_ERROR: {err}")
        return 1

    if args.command == "validate":
        print("handoff: valid")
        return 0

    max_items = max(1, int(args.max_items))
    print(summarize_handoff(payload, max_items=max_items))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
