from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = ROOT / "scripts" / "session_end_extractor.py"
SPEC = importlib.util.spec_from_file_location("session_end_extractor_eval", SCRIPT_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load session_end_extractor.py")
extractor = importlib.util.module_from_spec(SPEC)
sys.modules["session_end_extractor_eval"] = extractor
SPEC.loader.exec_module(extractor)


def test_eval_detects_failure_signal() -> None:
    lines = [
        "step 1 ok",
        "Traceback (most recent call last):",
        "RuntimeError: boom",
    ]
    signals = extractor.summarize_signals(lines)
    next_step = extractor.summarize_next_step(signals)
    assert any("Traceback" in signal for signal in signals)
    assert "address any failing step" in next_step


def test_eval_clean_tail_has_safe_next_step() -> None:
    lines = ["all checks passed", "done"]
    signals = extractor.summarize_signals(lines)
    next_step = extractor.summarize_next_step(signals)
    assert signals == ["No error or warning signals detected in tail."]
    assert "Proceed with the next planned milestone" in next_step
