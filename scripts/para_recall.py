#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MEMORY_ROOT = ROOT / "memory"

ALLOWED_SUFFIXES = {
    ".md",
    ".txt",
    ".log",
    ".json",
    ".jsonl",
    ".yaml",
    ".yml",
    ".csv",
}
EXCLUDED_NAMES = {".vector_db", ".vector_db_final"}
MAX_FILE_BYTES = 1_000_000
MAX_CHUNK_CHARS = 800
MAX_SNIPPET_CHARS = 220
DEFAULT_TOP_PROJECTS = 3
DEFAULT_TOP_CHUNKS = 3
DEFAULT_TRACE_PATH = ROOT / "logs" / "retrieval_trace.jsonl"
WORD_RE = re.compile(r"[A-Za-z0-9]+")


@dataclass
class Chunk:
    project: str
    file: str
    index: int
    text: str
    score: int = 0


@dataclass
class ProjectRecall:
    name: str
    path: Path
    chunks: list[Chunk]
    score: int = 0


def _tokenize(text: str) -> list[str]:
    return WORD_RE.findall(text.lower())


def _score_text(text: str, query_tokens: set[str]) -> int:
    if not query_tokens:
        return 0
    tokens = _tokenize(text)
    return sum(1 for token in tokens if token in query_tokens)


def _safe_read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _clean_text(text: str) -> str:
    return " ".join(part.strip() for part in text.splitlines() if part.strip())


def _split_chunks(text: str) -> list[str]:
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n+", text) if p.strip()]
    chunks: list[str] = []
    for para in paragraphs:
        if len(para) <= MAX_CHUNK_CHARS:
            chunks.append(para)
            continue
        for idx in range(0, len(para), MAX_CHUNK_CHARS):
            chunk = para[idx : idx + MAX_CHUNK_CHARS].strip()
            if chunk:
                chunks.append(chunk)
    return chunks


def _iter_project_dirs(memory_root: Path) -> list[Path]:
    if not memory_root.exists():
        return []
    projects_dir = memory_root / "projects"
    candidates: list[Path] = []
    if projects_dir.is_dir():
        candidates = [p for p in projects_dir.iterdir() if p.is_dir() and not p.name.startswith(".")]
    if not candidates:
        candidates = [
            p
            for p in memory_root.iterdir()
            if p.is_dir() and not p.name.startswith(".") and p.name not in EXCLUDED_NAMES
        ]
    if not candidates:
        candidates = [memory_root]
    return candidates


def _iter_files(root: Path) -> list[Path]:
    files: list[Path] = []
    if root.is_file():
        return [root]
    for path in root.rglob("*"):
        if path.is_dir():
            continue
        if any(part.startswith(".") for part in path.parts):
            continue
        if path.name in EXCLUDED_NAMES:
            continue
        if path.suffix and path.suffix.lower() not in ALLOWED_SUFFIXES:
            continue
        try:
            if path.stat().st_size > MAX_FILE_BYTES:
                continue
        except OSError:
            continue
        files.append(path)
    return files


def _collect_project(project_path: Path, project_name: str, query_tokens: set[str]) -> ProjectRecall:
    chunks: list[Chunk] = []
    for file_path in _iter_files(project_path):
        text = _safe_read(file_path)
        if not text.strip():
            continue
        relative = file_path.relative_to(ROOT).as_posix()
        for idx, chunk_text in enumerate(_split_chunks(text)):
            cleaned = _clean_text(chunk_text)
            if not cleaned:
                continue
            chunk = Chunk(project=project_name, file=relative, index=idx, text=cleaned)
            chunk.score = _score_text(cleaned, query_tokens)
            chunks.append(chunk)
    project = ProjectRecall(name=project_name, path=project_path, chunks=chunks)
    if chunks:
        project.score = max(chunk.score for chunk in chunks)
    return project


def _select_projects(projects: list[ProjectRecall], limit: int) -> list[ProjectRecall]:
    if not projects:
        return []
    ordered = sorted(projects, key=lambda p: (-p.score, p.name))
    return ordered[:limit]


def _select_chunks(project: ProjectRecall, limit: int) -> list[Chunk]:
    if not project.chunks:
        return []
    ordered = sorted(project.chunks, key=lambda c: (-c.score, c.file, c.index))
    return ordered[:limit]


def _truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def _append_trace(
    trace_path: Path,
    query: str,
    chunks: list[Chunk],
    projects: list[ProjectRecall],
) -> None:
    try:
        trace_path.parent.mkdir(parents=True, exist_ok=True)
    except OSError:
        return

    timestamp = datetime.now(timezone.utc).isoformat()
    entries: list[dict[str, object]] = []
    if chunks:
        for chunk in chunks:
            entries.append(
                {
                    "timestamp": timestamp,
                    "query": query,
                    "project": chunk.project,
                    "file": chunk.file,
                    "chunk_index": chunk.index,
                    "score": chunk.score,
                }
            )
    else:
        project_name = projects[0].name if projects else "none"
        entries.append(
            {
                "timestamp": timestamp,
                "query": query,
                "project": project_name,
                "file": "",
                "chunk_index": -1,
                "score": 0,
            }
        )

    try:
        with trace_path.open("a", encoding="utf-8") as handle:
            for entry in entries:
                handle.write(json.dumps(entry, ensure_ascii=True) + "\n")
    except OSError:
        return


def render_markdown(query: str, projects: list[ProjectRecall]) -> str:
    lines: list[str] = []
    lines.append("# Para Recall")
    lines.append(f"- Query: `{query}`")
    lines.append(f"- Projects scanned: {len(projects)}")
    if not projects:
        lines.append("")
        lines.append("No memory found.")
        return "\n".join(lines)

    for project in projects:
        lines.append("")
        lines.append(f"## {project.name} (score {project.score})")
        chunks = _select_chunks(project, DEFAULT_TOP_CHUNKS)
        if not chunks:
            lines.append("- No chunks available.")
            continue
        for chunk in chunks:
            snippet = _truncate(chunk.text, MAX_SNIPPET_CHARS)
            lines.append(f"- `{chunk.file}` (score {chunk.score}): {snippet}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Hierarchical recall over project memory.")
    parser.add_argument("--query", required=True, help="Search query")
    parser.add_argument(
        "--top-projects",
        type=int,
        default=DEFAULT_TOP_PROJECTS,
        help="Number of top projects to return",
    )
    parser.add_argument(
        "--trace",
        default=str(DEFAULT_TRACE_PATH),
        help="JSONL trace output path",
    )
    args = parser.parse_args(argv)

    query = args.query.strip()
    if not query:
        print("Query must be non-empty.", file=sys.stderr)
        return 2

    query_tokens = set(_tokenize(query))
    project_paths = _iter_project_dirs(MEMORY_ROOT)
    projects: list[ProjectRecall] = []
    for path in project_paths:
        name = path.name if path != MEMORY_ROOT else "memory-root"
        projects.append(_collect_project(path, name, query_tokens))

    top_projects = _select_projects(projects, max(1, args.top_projects))
    selected_chunks: list[Chunk] = []
    for project in top_projects:
        selected_chunks.extend(_select_chunks(project, DEFAULT_TOP_CHUNKS))
    if args.trace:
        _append_trace(Path(args.trace), query, selected_chunks, top_projects)
    output = render_markdown(query, top_projects)
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
