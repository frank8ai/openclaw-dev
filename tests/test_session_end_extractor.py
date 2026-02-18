from __future__ import annotations

from tests.load_script import load_script_module

extractor = load_script_module("scripts/session_end_extractor.py", "session_end_extractor")


def test_summarize_signals_deduplicates_and_limits() -> None:
    lines = [
        "INFO start",
        "ERROR failed to connect",
        "error failed to connect",
        "warning cache miss",
    ]
    signals = extractor.summarize_signals(lines)
    assert len(signals) == 2
    assert "ERROR failed to connect" in signals


def test_next_step_when_clean_log() -> None:
    next_step = extractor.summarize_next_step(["No error or warning signals detected in tail."])
    assert "Proceed with the next planned milestone" in next_step


def test_build_block_has_required_sections() -> None:
    block = extractor.build_block(
        "2026-02-18T00:00:00Z",
        "Input: agent/test_tail.log",
        ["error line"],
        "Do something next",
    )
    assert "### Context" in block
    assert "### Key signals" in block
    assert "### Next step" in block
