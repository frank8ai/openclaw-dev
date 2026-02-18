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
    namespace = {"tenant_id": "default", "agent_id": "main", "project_id": "demo"}
    context = supervisor.build_second_brain_context(repo, cfg, namespace)
    assert "[NAMESPACE]" in context
    assert "tenant_id=default" in context
    assert "[DAILY_INDEX]" in context
    assert "keep quality gates strict" in context
    assert "[SESSION:session_1010_demo.md]" in context
    assert "[MEMORY]" in context


def test_build_second_brain_context_strict_namespace_isolation(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir(parents=True, exist_ok=True)
    today = supervisor.datetime.now().strftime("%Y-%m-%d")

    project_a_daily = (
        repo
        / "brain"
        / "tenants"
        / "default"
        / "agents"
        / "researcher"
        / "projects"
        / "project-a"
        / "daily"
        / today
    )
    project_b_daily = (
        repo
        / "brain"
        / "tenants"
        / "default"
        / "agents"
        / "researcher"
        / "projects"
        / "project-b"
        / "daily"
        / today
    )
    project_a_sessions = project_a_daily.parent.parent / "sessions"
    project_b_sessions = project_b_daily.parent.parent / "sessions"
    project_a_daily.mkdir(parents=True, exist_ok=True)
    project_b_daily.mkdir(parents=True, exist_ok=True)
    project_a_sessions.mkdir(parents=True, exist_ok=True)
    project_b_sessions.mkdir(parents=True, exist_ok=True)

    (repo / "brain" / "tenants" / "default" / "global" / "MEMORY.md").parent.mkdir(parents=True, exist_ok=True)
    (repo / "brain" / "tenants" / "default" / "global" / "MEMORY.md").write_text(
        "Decision: global baseline\n",
        encoding="utf-8",
    )
    (project_a_daily / "_DAILY_INDEX.md").write_text("Decision: keep project-a isolated\n", encoding="utf-8")
    (project_b_daily / "_DAILY_INDEX.md").write_text("Decision: project-b private\n", encoding="utf-8")
    (project_a_sessions / "session_0900_a.md").write_text("Next: project-a step\n", encoding="utf-8")
    (project_b_sessions / "session_0900_b.md").write_text("Next: project-b step\n", encoding="utf-8")

    cfg = {
        "enabled": True,
        "root": ".",
        "include_memory_md": True,
        "max_chars": 2000,
        "max_sessions": 2,
        "max_lines_per_file": 20,
        "_namespace_enabled": True,
        "_namespace_root": ".",
        "_namespace_memory_template": "brain/tenants/{tenant_id}/global/MEMORY.md",
        "_namespace_daily_template": (
            "brain/tenants/{tenant_id}/agents/{agent_id}/projects/{project_id}/daily/{date}/_DAILY_INDEX.md"
        ),
        "_namespace_session_template": (
            "brain/tenants/{tenant_id}/agents/{agent_id}/projects/{project_id}/sessions/session_*.md"
        ),
    }
    namespace = {"tenant_id": "default", "agent_id": "researcher", "project_id": "project-a"}
    context = supervisor.build_second_brain_context(repo, cfg, namespace)
    assert "project-a" in context
    assert "project-b private" not in context
    assert "session_0900_b.md" not in context
