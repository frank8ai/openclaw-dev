#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGENT_DIR = ROOT / "agent"

L0_PATH = AGENT_DIR / ".abstract.md"
L1_PATH = AGENT_DIR / ".overview.md"

TASK_PATH = AGENT_DIR / "TASK.md"
HOT_PATH = AGENT_DIR / "HOT.md"
WARM_PATH = AGENT_DIR / "WARM.md"
POLICY_PATH = AGENT_DIR / "POLICY.md"
STATUS_PATH = AGENT_DIR / "STATUS.json"
BLUEPRINT_PATH = AGENT_DIR / "BLUEPRINT.json"
DECISIONS_PATH = AGENT_DIR / "DECISIONS.md"

L0_LIMIT = 120
L1_LIMIT = 2000
TOKEN_RE = re.compile(r"\S+")


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


def parse_bullets(text: str) -> dict:
    data = {}
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("-"):
            continue
        line = line[1:].strip()
        if ":" in line:
            key, value = line.split(":", 1)
            data[key.strip()] = value.strip()
    return data


def collect_bullets_after(header: str, text: str) -> list[str]:
    lines = text.splitlines()
    items: list[str] = []
    capture = False
    for line in lines:
        stripped = line.strip()
        if capture:
            if stripped.startswith(("-", "*")):
                items.append(stripped[1:].strip())
                continue
            if stripped == "":
                if items:
                    break
                continue
            if re.match(r"^[A-Za-z].*?:", stripped):
                break
            break
        if stripped == header:
            capture = True
    return items


def parse_task(text: str) -> dict:
    goal_match = re.search(r"^Goal:\s*(.+)$", text, re.M)
    focus_match = re.search(r"^Current focus.*?:\s*(.+)$", text, re.M)
    goal = goal_match.group(1).strip() if goal_match else ""
    focus = focus_match.group(1).strip() if focus_match else ""
    acceptance = collect_bullets_after("Acceptance for this run:", text)
    constraints = collect_bullets_after("Constraints:", text)
    return {
        "goal": goal,
        "focus": focus,
        "acceptance": acceptance,
        "constraints": constraints,
    }


def parse_status(text: str) -> dict:
    if not text.strip():
        return {}
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {}


def parse_blueprint(text: str) -> dict[int, dict]:
    if not text.strip():
        return {}
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return {}
    steps = payload.get("steps", []) if isinstance(payload, dict) else []
    mapping: dict[int, dict] = {}
    for step in steps:
        if not isinstance(step, dict):
            continue
        step_id = step.get("id")
        if isinstance(step_id, int):
            mapping[step_id] = step
    return mapping


def parse_decisions(text: str) -> list[str]:
    items = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("- [ ]"):
            items.append(stripped[5:].strip())
    return items


def truncate_tokens(text: str, max_tokens: int) -> tuple[str, bool]:
    tokens = list(re.finditer(r"\S+", text))
    if len(tokens) <= max_tokens:
        return text, False
    if max_tokens <= 1:
        end_idx = tokens[max_tokens - 1].end() if max_tokens > 0 else 0
        return text[:end_idx].rstrip(), True
    keep = max_tokens - 1
    end_idx = tokens[keep - 1].end() if keep > 0 else 0
    truncated = text[:end_idx].rstrip()
    truncated = f"{truncated} TRUNCATED"
    return truncated, True


def format_l0(task: dict, hot: dict, policy_text: str) -> str:
    parts = []
    if task.get("goal"):
        parts.append(task["goal"])
    focus = task.get("focus") or hot.get("Current step")
    if focus:
        parts.append(f"Current focus: {focus}.")
    constraints = task.get("constraints")
    if constraints:
        constraint_text = "; ".join(constraints)
        parts.append(f"Constraints: {constraint_text}.")
    if not constraints and "TEST_CMD" in policy_text:
        parts.append("Constraints: run TEST_CMD after changes; no new dependencies.")
    if not parts:
        parts.append("OpenClaw dev task: maintain tiered memory artifacts and keep changes minimal.")
    abstract = " ".join(part.strip() for part in parts if part.strip())
    return abstract


def format_l1(
    task: dict,
    hot: dict,
    warm: dict,
    status: dict,
    blueprint_steps: dict[int, dict],
    decisions: list[str],
) -> str:
    lines: list[str] = []

    lines.append("Objective")
    if task.get("goal"):
        lines.append(f"- {task['goal']}")
    if task.get("focus"):
        lines.append(f"- Current focus: {task['focus']}")

    lines.append("")
    lines.append("Current step")
    if hot.get("Current step"):
        lines.append(f"- {hot['Current step']}")
    status_step = status.get("current_step")
    if isinstance(status_step, int) and status_step in blueprint_steps:
        step = blueprint_steps[status_step]
        step_name = step.get("name", "")
        objective = step.get("objective", "")
        if step_name or objective:
            label = f"Step {status_step}: {step_name}".strip()
            if objective:
                label = f"{label} — {objective}" if label else objective
            lines.append(f"- {label}")

    lines.append("")
    lines.append("Next actions")
    actions: list[str] = []
    actions.append("Create `scripts/update_tiers.py` and regenerate L0/L1 tier files.")
    actions.append("Run `python3 scripts/update_tiers.py` and capture output.")
    actions.append("Run `TEST_CMD` per policy and save the last 150 lines to `agent/test_tail.log`.")
    actions.append("Update `agent/HOT.md`, `agent/STATUS.json`, and `agent/RESULT.md` for finalize.")
    for action in actions:
        lines.append(f"- {action}")

    lines.append("")
    lines.append("Decisions")
    if decisions:
        for item in decisions:
            lines.append(f"- {item}")
    else:
        lines.append("- None")

    lines.append("")
    lines.append("Pitfalls")
    pitfalls: list[str] = []
    if task.get("constraints"):
        pitfalls.extend(task["constraints"])
    if hot.get("Constraints"):
        pitfalls.append(hot["Constraints"])
    if hot.get("Current error"):
        pitfalls.append(hot["Current error"])
    if not pitfalls:
        pitfalls.append("Run TEST_CMD after each change and avoid new dependencies.")
    for pitfall in pitfalls:
        lines.append(f"- {pitfall}")

    lines.append("")
    lines.append("Key links")
    links = [
        "agent/TASK.md",
        "agent/POLICY.md",
        "agent/HOT.md",
        "agent/STATUS.json",
        "scripts/update_tiers.py",
        "references/agent_templates.md",
    ]
    for link in links:
        lines.append(f"- {link}")

    return "\n".join(lines)


def write_file(path: Path, content: str) -> None:
    path.write_text(content.rstrip() + "\n", encoding="utf-8")


def main() -> int:
    task_text = read_text(TASK_PATH)
    hot_text = read_text(HOT_PATH)
    warm_text = read_text(WARM_PATH)
    policy_text = read_text(POLICY_PATH)
    status_text = read_text(STATUS_PATH)
    blueprint_text = read_text(BLUEPRINT_PATH)
    decisions_text = read_text(DECISIONS_PATH)

    task = parse_task(task_text)
    hot = parse_bullets(hot_text)
    warm = parse_bullets(warm_text)
    status = parse_status(status_text)
    blueprint_steps = parse_blueprint(blueprint_text)
    decisions = parse_decisions(decisions_text)

    l0 = format_l0(task, hot, policy_text)
    l1 = format_l1(task, hot, warm, status, blueprint_steps, decisions)

    l0, l0_truncated = truncate_tokens(l0, L0_LIMIT)
    l1, l1_truncated = truncate_tokens(l1, L1_LIMIT)

    write_file(L0_PATH, l0)
    write_file(L1_PATH, l1)

    print(f"Wrote {L0_PATH.relative_to(ROOT)} ({len(TOKEN_RE.findall(l0))} tokens)")
    if l0_truncated:
        print(f"- Truncated to {L0_LIMIT} tokens")
    print(f"Wrote {L1_PATH.relative_to(ROOT)} ({len(TOKEN_RE.findall(l1))} tokens)")
    if l1_truncated:
        print(f"- Truncated to {L1_LIMIT} tokens")

    return 0


if __name__ == "__main__":
    sys.exit(main())
