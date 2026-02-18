from __future__ import annotations

from tests.load_script import load_script_module

para_recall = load_script_module("scripts/para_recall.py", "para_recall")


def test_tokenize_and_score() -> None:
    tokens = para_recall._tokenize("Alpha beta BETA 123")
    assert tokens == ["alpha", "beta", "beta", "123"]
    score = para_recall._score_text("alpha gamma", {"alpha", "beta"})
    assert score == 1


def test_split_chunks_for_long_paragraph() -> None:
    text = "x" * (para_recall.MAX_CHUNK_CHARS + 100)
    chunks = para_recall._split_chunks(text)
    assert len(chunks) == 2
    assert all(chunk for chunk in chunks)


def test_render_markdown_contains_project_heading() -> None:
    chunk = para_recall.Chunk(project="demo", file="memory/demo.md", index=0, text="alpha", score=2)
    project = para_recall.ProjectRecall(name="demo", path=para_recall.MEMORY_ROOT, chunks=[chunk], score=2)
    output = para_recall.render_markdown("alpha", [project])
    assert "## demo (score 2)" in output
