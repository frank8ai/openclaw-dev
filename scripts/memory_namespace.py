#!/usr/bin/env python3
"""Manage namespaced second-brain paths for multi-agent, multi-project isolation."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path

DEFAULT_TEMPLATES = {
    "global_memory_template": "brain/tenants/{tenant_id}/global/MEMORY.md",
    "daily_index_template": (
        "brain/tenants/{tenant_id}/agents/{agent_id}/projects/{project_id}/daily/{date}/_DAILY_INDEX.md"
    ),
    "session_glob_template": (
        "brain/tenants/{tenant_id}/agents/{agent_id}/projects/{project_id}/sessions/session_*.md"
    ),
    "card_dir_template": "brain/tenants/{tenant_id}/agents/{agent_id}/projects/{project_id}/cards/{date}",
    "pack_dir_template": "brain/tenants/{tenant_id}/agents/{agent_id}/projects/{project_id}/packs/{date}",
}


def normalize_identifier(value: object, fallback: str) -> str:
    if not isinstance(value, str):
        return fallback
    cleaned = value.strip().lower()
    if not cleaned:
        return fallback
    return re.sub(r"[^a-z0-9._-]+", "-", cleaned)


def _resolve_root(root: str) -> Path:
    root_path = Path(root).expanduser()
    if not root_path.is_absolute():
        root_path = (Path.cwd() / root_path).resolve()
    return root_path


def _format_template(template: str, namespace: dict[str, str]) -> str:
    try:
        return template.format(**namespace)
    except KeyError:
        return template


def build_namespace(tenant_id: str, agent_id: str, project_id: str, date_value: str | None) -> dict[str, str]:
    return {
        "tenant_id": normalize_identifier(tenant_id, "default"),
        "agent_id": normalize_identifier(agent_id, "main"),
        "project_id": normalize_identifier(project_id, "default"),
        "date": (date_value or datetime.now().strftime("%Y-%m-%d")).strip() or datetime.now().strftime("%Y-%m-%d"),
    }


def resolve_paths(
    root: str,
    namespace: dict[str, str],
    templates: dict[str, str] | None = None,
) -> dict[str, Path]:
    merged_templates = dict(DEFAULT_TEMPLATES)
    if templates:
        merged_templates.update(templates)

    root_path = _resolve_root(root)
    global_memory = (root_path / _format_template(merged_templates["global_memory_template"], namespace)).resolve()
    daily_index = (root_path / _format_template(merged_templates["daily_index_template"], namespace)).resolve()
    session_glob = (root_path / _format_template(merged_templates["session_glob_template"], namespace)).resolve()
    card_dir = (root_path / _format_template(merged_templates["card_dir_template"], namespace)).resolve()
    pack_dir = (root_path / _format_template(merged_templates["pack_dir_template"], namespace)).resolve()

    return {
        "root": root_path,
        "global_memory": global_memory,
        "daily_index": daily_index,
        "session_glob": session_glob,
        "session_dir": session_glob.parent,
        "card_dir": card_dir,
        "pack_dir": pack_dir,
    }


def _write_if_missing(path: Path, content: str, force: bool) -> None:
    if path.exists() and not force:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _touch_gitkeep(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    if any(path.iterdir()):
        return
    (path / ".gitkeep").write_text("", encoding="utf-8")


def init_namespace(
    root: str,
    namespace: dict[str, str],
    force: bool,
    templates: dict[str, str] | None = None,
) -> dict[str, Path]:
    paths = resolve_paths(root, namespace, templates=templates)
    now_iso = datetime.now().isoformat(timespec="seconds")
    _write_if_missing(
        paths["global_memory"],
        (
            "# Root Memory\n"
            f"- tenant_id: {namespace['tenant_id']}\n"
            f"- last_update: {now_iso}\n"
        ),
        force=force,
    )
    _write_if_missing(
        paths["daily_index"],
        (
            "# Daily Index\n"
            f"- tenant_id: {namespace['tenant_id']}\n"
            f"- agent_id: {namespace['agent_id']}\n"
            f"- project_id: {namespace['project_id']}\n"
            "\n"
            "## #GOLD\n"
            "- \n"
            "\n"
            "## Active Sessions\n"
            "- \n"
        ),
        force=force,
    )
    _touch_gitkeep(paths["session_dir"])
    _touch_gitkeep(paths["card_dir"])
    _touch_gitkeep(paths["pack_dir"])
    return paths


def _to_jsonable(paths: dict[str, Path], namespace: dict[str, str]) -> dict[str, str]:
    payload: dict[str, str] = {
        "tenant_id": namespace["tenant_id"],
        "agent_id": namespace["agent_id"],
        "project_id": namespace["project_id"],
        "date": namespace["date"],
    }
    for key, value in paths.items():
        payload[key] = str(value)
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".", help="Workspace root used to resolve templates.")
    parser.add_argument("--tenant-id", default="default", help="Tenant namespace id.")
    parser.add_argument("--agent-id", default="main", help="Agent namespace id.")
    parser.add_argument("--project-id", default="default", help="Project namespace id.")
    parser.add_argument("--date", default=None, help="Date shard (YYYY-MM-DD), defaults to today.")
    parser.add_argument(
        "--global-memory-template",
        default=DEFAULT_TEMPLATES["global_memory_template"],
        help="Template for global memory path.",
    )
    parser.add_argument(
        "--daily-index-template",
        default=DEFAULT_TEMPLATES["daily_index_template"],
        help="Template for daily index path.",
    )
    parser.add_argument(
        "--session-glob-template",
        default=DEFAULT_TEMPLATES["session_glob_template"],
        help="Template for session glob path.",
    )
    parser.add_argument(
        "--card-dir-template",
        default=DEFAULT_TEMPLATES["card_dir_template"],
        help="Template for card directory path.",
    )
    parser.add_argument(
        "--pack-dir-template",
        default=DEFAULT_TEMPLATES["pack_dir_template"],
        help="Template for pack directory path.",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("resolve", help="Resolve namespace paths and print JSON.")
    init_parser = subparsers.add_parser("init", help="Create namespace directories/files.")
    init_parser.add_argument("--force", action="store_true", help="Overwrite generated markdown files.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    namespace = build_namespace(args.tenant_id, args.agent_id, args.project_id, args.date)
    templates = {
        "global_memory_template": args.global_memory_template,
        "daily_index_template": args.daily_index_template,
        "session_glob_template": args.session_glob_template,
        "card_dir_template": args.card_dir_template,
        "pack_dir_template": args.pack_dir_template,
    }

    if args.command == "init":
        paths = init_namespace(args.root, namespace, force=bool(args.force), templates=templates)
    else:
        paths = resolve_paths(args.root, namespace, templates=templates)

    print(json.dumps(_to_jsonable(paths, namespace), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
