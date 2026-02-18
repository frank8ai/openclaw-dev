from __future__ import annotations

from pathlib import Path

from tests.load_script import load_script_module

supervisor = load_script_module("scripts/supervisor_loop.py", "supervisor_loop_ctx")


def test_extract_priority_lines_prefers_tagged_lines() -> None:
    text = "\n".join(
        [
            "normal line",
            "#GOLD decision A",
            "another line",
            "Risk: high",
            "Decision: choose B",
        ]
    )
    out = supervisor._extract_priority_lines(text, max_lines=3)
    assert "#GOLD decision A" in out
    assert "Decision: choose B" in out


def test_build_second_brain_context_reads_daily_and_session(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir(parents=True, exist_ok=True)
    today = supervisor.datetime.now().strftime("%Y-%m-%d")
    day_dir = repo / "90_Memory" / today
    day_dir.mkdir(parents=True, exist_ok=True)

    (day_dir / "_DAILY_INDEX.md").write_text(
        "#GOLD: keep quality gates strict\nDecision: keep auto-pr optional\n",
        encoding="utf-8",
    )
    (day_dir / "session_1010_demo.md").write_text(
        "Next: implement context injection\nRisk: token overflow\n",
        encoding="utf-8",
    )
    (repo / "MEMORY.md").write_text("Decision: prefer lightweight context slices\n", encoding="utf-8")

    cfg = {
        "enabled": True,
        "root": ".",
        "daily_index_template": "90_Memory/{date}/_DAILY_INDEX.md",
        "session_glob_template": "90_Memory/{date}/session_*.md",
        "include_memory_md": True,
        "max_chars": 1200,
        "max_sessions": 1,
        "max_lines_per_file": 20,
    }
    context = supervisor.build_second_brain_context(repo, cfg)
    assert "[DAILY_INDEX]" in context
    assert "keep quality gates strict" in context
    assert "[SESSION:session_1010_demo.md]" in context
    assert "[MEMORY]" in context
