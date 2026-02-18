#!/usr/bin/env python3
"""Append a compact session-end summary from a log tail."""

from __future__ import annotations

import argparse
import datetime as dt
import os
import re
from typing import Iterable, List

DEFAULT_INPUT = "agent/test_tail.log"
DEFAULT_OUTPUT = "agent/session_ends.md"
DEFAULT_MAX_LINES = 50


SIGNAL_PATTERN = re.compile(
    r"\b(error|failed|failure|exception|traceback|warn|warning|fatal)\b",
    re.IGNORECASE,
)


def read_tail(path: str, max_lines: int) -> List[str]:
    if max_lines <= 0:
        return []
    try:
        with open(path, "r", encoding="utf-8") as handle:
            lines = handle.read().splitlines()
    except FileNotFoundError:
        return []
    return lines[-max_lines:]


def compact_line(line: str, limit: int = 200) -> str:
    trimmed = line.strip()
    if len(trimmed) <= limit:
        return trimmed
    return trimmed[: limit - 3].rstrip() + "..."


def summarize_context(lines: Iterable[str], input_path: str, max_lines: int) -> str:
    non_empty = [line for line in lines if line.strip()]
    last_line = compact_line(non_empty[-1]) if non_empty else "No log lines found."
    return (
        f"Input: {input_path} (last {max_lines} lines). "
        f"Last line: {last_line}"
    )


def summarize_signals(lines: Iterable[str]) -> List[str]:
    signals = []
    seen = set()
    for line in lines:
        if not SIGNAL_PATTERN.search(line):
            continue
        compact = compact_line(line)
        normalized = compact.lower()
        if compact and normalized not in seen:
            seen.add(normalized)
            signals.append(compact)
    if not signals:
        signals.append("No error or warning signals detected in tail.")
    return signals[:5]


def summarize_next_step(signals: Iterable[str]) -> str:
    has_issue = any("No error" not in signal for signal in signals)
    if has_issue:
        return "Review the signals above and address any failing step before continuing."
    return "Proceed with the next planned milestone or verification step."


def build_block(
    timestamp: str,
    context: str,
    signals: Iterable[str],
    next_step: str,
) -> str:
    lines = [
        f"## Session End ({timestamp} UTC)",
        "",
        "### Context",
        f"- {context}",
        "",
        "### Key signals",
    ]
    for signal in signals:
        lines.append(f"- {signal}")
    lines.extend(["", "### Next step", f"- {next_step}", ""])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default=DEFAULT_INPUT)
    parser.add_argument("--out", default=DEFAULT_OUTPUT)
    parser.add_argument("--max-lines", type=int, default=DEFAULT_MAX_LINES)
    args = parser.parse_args()

    tail_lines = read_tail(args.input, args.max_lines)
    timestamp = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    context = summarize_context(tail_lines, args.input, args.max_lines)
    signals = summarize_signals(tail_lines)
    next_step = summarize_next_step(signals)
    block = build_block(timestamp, context, signals, next_step)

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "a", encoding="utf-8") as handle:
        handle.write(block)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
