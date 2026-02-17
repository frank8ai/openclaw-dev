#!/usr/bin/env python3
"""
Sync tracked files from openclaw-dev-repo to a local skill copy directory.
This runs on host Python and does not depend on Codex sandbox writable dirs.
"""
from __future__ import annotations

import argparse
import filecmp
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


DEFAULT_EXCLUDE_PREFIXES = (
    ".git/",
    "agent/",
    "logs/",
    "memory/",
    "__pycache__/",
)

DEFAULT_EXCLUDE_FILES = {
    "openclaw.json",
}


def _run_git_ls_files(repo: Path) -> list[str]:
    proc = subprocess.run(
        ["git", "-C", str(repo), "ls-files"],
        check=False,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "").strip()
        raise RuntimeError(f"git ls-files failed: {err}")
    return [line.strip() for line in proc.stdout.splitlines() if line.strip()]


def _load_openclaw_add_dirs(repo: Path) -> list[str]:
    config_path = repo / "openclaw.json"
    if not config_path.exists():
        return []
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    supervisor = config.get("supervisor", {})
    if not isinstance(supervisor, dict):
        return []
    add_dirs = supervisor.get("add_dirs")
    if not isinstance(add_dirs, list):
        return []
    return [entry for entry in add_dirs if isinstance(entry, str) and entry.strip()]


def _resolve_target(repo: Path, target: str | None) -> Path:
    if target:
        raw = target
    else:
        add_dirs = _load_openclaw_add_dirs(repo)
        if not add_dirs:
            raise RuntimeError(
                "No --target provided and openclaw.json supervisor.add_dirs is empty."
            )
        raw = add_dirs[0]

    p = Path(raw).expanduser()
    if not p.is_absolute():
        p = (repo / p).resolve()
    else:
        p = p.resolve()
    return p


def _should_skip(relpath: str, exclude_prefixes: tuple[str, ...], exclude_files: set[str]) -> bool:
    if relpath in exclude_files:
        return True
    if any(relpath.startswith(prefix) for prefix in exclude_prefixes):
        return True
    if "/__pycache__/" in relpath or relpath.endswith(".pyc"):
        return True
    return False


def _copy_tree(repo: Path, target: Path, dry_run: bool, verbose: bool) -> tuple[int, int, int, int]:
    tracked = _run_git_ls_files(repo)
    exclude_prefixes = tuple(DEFAULT_EXCLUDE_PREFIXES)
    exclude_files = set(DEFAULT_EXCLUDE_FILES)

    copied = 0
    unchanged = 0
    skipped = 0

    for rel in tracked:
        if _should_skip(rel, exclude_prefixes, exclude_files):
            skipped += 1
            continue

        src = repo / rel
        dst = target / rel

        if not src.is_file():
            skipped += 1
            continue

        same = dst.exists() and filecmp.cmp(str(src), str(dst), shallow=False)
        if same:
            unchanged += 1
            continue

        copied += 1
        if verbose:
            action = "would-copy" if dry_run else "copy"
            print(f"{action}: {rel}")
        if dry_run:
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)

    return len(tracked), copied, unchanged, skipped


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default=".", help="Source repo root (default: current dir).")
    parser.add_argument(
        "--target",
        default=None,
        help="Target skill directory. If omitted, use openclaw.json supervisor.add_dirs[0].",
    )
    parser.add_argument("--dry-run", action="store_true", help="Show what would be copied.")
    parser.add_argument("--verbose", action="store_true", help="Print each copied file.")
    args = parser.parse_args()

    repo = Path(args.repo).expanduser().resolve()
    if not (repo / ".git").exists():
        print(f"ERROR: not a git repo: {repo}", file=sys.stderr)
        return 2

    try:
        target = _resolve_target(repo, args.target)
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if target == repo:
        print("ERROR: target cannot be the same as repo.", file=sys.stderr)
        return 2

    if not args.dry_run:
        target.mkdir(parents=True, exist_ok=True)

    tracked_count, copied, unchanged, skipped = _copy_tree(
        repo=repo,
        target=target,
        dry_run=args.dry_run,
        verbose=args.verbose,
    )

    mode = "DRY-RUN" if args.dry_run else "SYNC"
    print(
        f"{mode} done: repo={repo} target={target} "
        f"tracked={tracked_count} copied={copied} unchanged={unchanged} skipped={skipped}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
