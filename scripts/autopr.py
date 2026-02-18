#!/usr/bin/env python3
"""Create an automated branch/commit/PR flow for finished supervisor runs."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

DEFAULT_EXCLUDE_PREFIXES = (
    "agent/checkpoints/",
    "memory/",
)

DEFAULT_EXCLUDE_FILES = {
    "agent/HOT.md",
    "agent/WARM.md",
    "agent/PLAN.md",
    "agent/RESULT.md",
    "agent/STATUS.json",
    "agent/test_tail.log",
    "agent/run_tests_tail.log",
    "agent/autopr_tail.log",
    "agent/sync_tail.log",
}


def run_cmd(cmd: list[str], cwd: Path, capture_output: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=str(cwd),
        check=False,
        text=True,
        capture_output=capture_output,
    )


def git_output(repo: Path, args: list[str]) -> tuple[int, str]:
    proc = run_cmd(["git", *args], repo, capture_output=True)
    output = (proc.stdout or "").strip() or (proc.stderr or "").strip()
    return proc.returncode, output


def _should_skip(path: str, exclude_prefixes: tuple[str, ...], exclude_files: set[str]) -> bool:
    if path in exclude_files:
        return True
    for prefix in exclude_prefixes:
        if path.startswith(prefix):
            return True
    return False


def collect_changed_paths(repo: Path, scope: str) -> list[str]:
    commands = [
        ["diff", "--name-only", "--", scope],
        ["diff", "--cached", "--name-only", "--", scope],
        ["ls-files", "--others", "--exclude-standard", "--", scope],
    ]
    seen: set[str] = set()
    merged: list[str] = []
    for cmd in commands:
        rc, output = git_output(repo, cmd)
        if rc not in (0, 1):
            continue
        for line in output.splitlines():
            path = line.strip()
            if not path or path in seen:
                continue
            seen.add(path)
            merged.append(path)
    return merged


def current_branch(repo: Path) -> str:
    rc, output = git_output(repo, ["rev-parse", "--abbrev-ref", "HEAD"])
    if rc != 0 or not output:
        return "HEAD"
    return output


def switch_to_work_branch(repo: Path, base: str, prefix: str) -> str:
    branch = current_branch(repo)
    if branch not in (base, "HEAD"):
        return branch
    timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    candidate = f"{prefix}/{timestamp}"
    rc = run_cmd(["git", "checkout", "-b", candidate], repo).returncode
    if rc != 0:
        candidate = f"{prefix}/{timestamp}-1"
        rc = run_cmd(["git", "checkout", "-b", candidate], repo).returncode
        if rc != 0:
            raise RuntimeError("unable to create work branch")
    return candidate


def has_staged_changes(repo: Path) -> bool:
    rc = run_cmd(["git", "diff", "--cached", "--quiet"], repo).returncode
    return rc == 1


def ensure_origin(repo: Path) -> None:
    rc = run_cmd(["git", "remote", "get-url", "origin"], repo).returncode
    if rc != 0:
        raise RuntimeError("git remote 'origin' is missing")


def read_body(body_file: Path) -> str:
    if not body_file.exists():
        return "Automated delivery by openclaw-dev."
    content = body_file.read_text(encoding="utf-8").strip()
    return content if content else "Automated delivery by openclaw-dev."


def find_existing_pr(base: str, head: str) -> str:
    proc = subprocess.run(
        ["gh", "pr", "list", "--base", base, "--head", head, "--json", "url", "--limit", "1"],
        check=False,
        text=True,
        capture_output=True,
    )
    if proc.returncode != 0:
        return ""
    try:
        data = json.loads(proc.stdout or "[]")
    except json.JSONDecodeError:
        return ""
    if isinstance(data, list) and data:
        first = data[0]
        if isinstance(first, dict):
            url = first.get("url")
            if isinstance(url, str):
                return url
    return ""


def create_or_get_pr(repo: Path, base: str, head: str, title: str, body: str) -> str:
    existing = find_existing_pr(base, head)
    if existing:
        return existing
    proc = run_cmd(
        ["gh", "pr", "create", "--base", base, "--head", head, "--title", title, "--body", body],
        repo,
        capture_output=True,
    )
    if proc.returncode != 0:
        detail = (proc.stdout or "").strip() or (proc.stderr or "").strip() or "gh pr create failed"
        raise RuntimeError(detail)
    output = (proc.stdout or "").strip()
    if output:
        return output.splitlines()[-1].strip()
    return ""


def auto_merge_pr(repo: Path, pr_url: str) -> None:
    target = pr_url if pr_url else ""
    cmd = ["gh", "pr", "merge", "--auto", "--squash", "--delete-branch"]
    if target:
        cmd.append(target)
    proc = run_cmd(cmd, repo, capture_output=True)
    if proc.returncode != 0:
        detail = (proc.stdout or "").strip() or (proc.stderr or "").strip() or "gh pr merge failed"
        raise RuntimeError(detail)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default=".", help="Repo root.")
    parser.add_argument("--scope", default=".", help="Git scope for staged files.")
    parser.add_argument("--base", default="master", help="Base branch name.")
    parser.add_argument("--branch-prefix", default="autodev", help="Auto branch prefix.")
    parser.add_argument("--title", default="chore: automated supervisor delivery", help="PR title.")
    parser.add_argument(
        "--commit-message",
        default="chore: automated supervisor delivery",
        help="Commit message for automated commit.",
    )
    parser.add_argument("--body-file", default="agent/RESULT.md", help="PR body source file.")
    parser.add_argument("--mode", default="dev", choices=["dev", "staging", "prod"])
    parser.add_argument("--auto-merge", action="store_true", help="Enable GH auto merge (dev mode only).")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo = Path(args.repo).expanduser().resolve()
    if not repo.exists():
        print("autopr: repo does not exist", file=sys.stderr)
        return 2

    changed = collect_changed_paths(repo, args.scope)
    eligible = [
        path
        for path in changed
        if not _should_skip(path, DEFAULT_EXCLUDE_PREFIXES, DEFAULT_EXCLUDE_FILES)
    ]

    if not eligible:
        print("autopr: no eligible changes")
        return 0

    try:
        ensure_origin(repo)
        branch = switch_to_work_branch(repo, args.base, args.branch_prefix)
    except RuntimeError as exc:
        print(f"autopr: {exc}", file=sys.stderr)
        return 2

    add_rc = run_cmd(["git", "add", "--", *eligible], repo).returncode
    if add_rc != 0:
        print("autopr: git add failed", file=sys.stderr)
        return 2

    if not has_staged_changes(repo):
        print("autopr: no staged changes after filtering")
        return 0

    commit_rc = run_cmd(["git", "commit", "-m", args.commit_message], repo).returncode
    if commit_rc != 0:
        print("autopr: git commit failed", file=sys.stderr)
        return 2

    push_rc = run_cmd(["git", "push", "-u", "origin", branch], repo).returncode
    if push_rc != 0:
        print("autopr: git push failed", file=sys.stderr)
        return 2

    if shutil.which("gh") is None:
        print("autopr: gh CLI not found", file=sys.stderr)
        return 127

    body = read_body(repo / args.body_file)
    try:
        pr_url = create_or_get_pr(repo, args.base, branch, args.title, body)
        if args.auto_merge and args.mode == "dev":
            auto_merge_pr(repo, pr_url)
    except RuntimeError as exc:
        print(f"autopr: {exc}", file=sys.stderr)
        return 3

    print(f"autopr: success branch={branch} pr={pr_url or 'created'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
