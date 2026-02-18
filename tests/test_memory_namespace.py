from __future__ import annotations

from pathlib import Path

from tests.load_script import load_script_module

memory_namespace = load_script_module("scripts/memory_namespace.py", "memory_namespace")


def test_resolve_paths_includes_namespace_segments(tmp_path: Path) -> None:
    namespace = memory_namespace.build_namespace("Tenant A", "Research Agent", "Project X", "2026-02-18")
    paths = memory_namespace.resolve_paths(str(tmp_path), namespace)
    assert "tenant-a" in str(paths["global_memory"])
    assert "research-agent" in str(paths["daily_index"])
    assert "project-x" in str(paths["daily_index"])
    assert "2026-02-18" in str(paths["daily_index"])


def test_init_namespace_creates_expected_files(tmp_path: Path) -> None:
    namespace = memory_namespace.build_namespace("default", "main", "demo", "2026-02-18")
    paths = memory_namespace.init_namespace(str(tmp_path), namespace, force=False)
    assert paths["global_memory"].exists()
    assert paths["daily_index"].exists()
    assert (paths["session_dir"] / ".gitkeep").exists()
    assert (paths["card_dir"] / ".gitkeep").exists()
    assert (paths["pack_dir"] / ".gitkeep").exists()
