#!/usr/bin/env python3
"""
OpenClaw Dev Supervisor Loop
Resume Codex, run tests, update agent/STATUS.json.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

RESULT_TEMPLATE = """# Result
- 完成情况：{completion}
- 改动文件：{changed_files}
- diff --stat：{diff_stat}
- 验证：{verification}
- 风险点：{risks}
"""
DEFAULT_SCOPE = "."


def load_status(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def save_status(path: Path, status: dict) -> None:
    status["last_update"] = datetime.now().isoformat(timespec="seconds")
    path.write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run_cmd(cmd: list[str], cwd: Path, timeout_s: int | None = None) -> int:
    # Ensure Codex runs with a TTY-friendly environment even in non-interactive mode.
    env = os.environ.copy()
    env.setdefault("TERM", "xterm-256color")
    try:
        return subprocess.run(cmd, cwd=str(cwd), env=env, check=False, timeout=timeout_s).returncode
    except subprocess.TimeoutExpired:
        return 124
    except FileNotFoundError:
        return 127


def run_tests(agent_dir: Path) -> int:
    cmd = [
        "bash",
        "-lc",
        'source agent/COMMANDS.env && eval "$TEST_CMD" 2>&1 | tail -n 150 > agent/test_tail.log',
    ]
    return run_cmd(cmd, agent_dir.parent)


def build_prompt(step: dict | None) -> str:
    # Keep the prompt short and force file-based outputs to minimize token usage.
    step_desc = ""
    if step:
        step_desc = f"Current step: {step.get('name')} — {step.get('objective')}. "
    return (
        "You are running inside a repo. First, write a concrete 3-6 step plan to agent/PLAN.md and then immediately start executing it. "
        "Rules: follow agent/POLICY.md and agent/TASK.md; read agent/COMMANDS.env for TEST_CMD/LINT_CMD/TYPECHECK_CMD/BUILD_CMD. "
        "Update agent/HOT.md every run and agent/WARM.md on milestone completion; keep within agent/CONTEXT.json budgets. "
        "Update agent/STATUS.json after each step. Do NOT paste large logs; write only tail summaries. "
        "When acceptance passes (TEST_CMD), write agent/RESULT.md (files changed, git diff --stat, verification, risks) and set STATUS.state=done. "
        "If you need a human decision, write agent/DECISIONS.md and set STATUS.state=blocked. "
        f"{step_desc}"
    )


def _force_write_files_prompt() -> str:
    # Second-chance prompt when Codex gets stuck inspecting. Force a concrete write to PLAN.
    return (
        "Use the shell to overwrite agent/PLAN.md with a concrete numbered plan (3-6 steps) that matches agent/TASK.md. "
        "After writing PLAN.md, update agent/HOT.md and agent/STATUS.json (state=running, last_action='wrote plan'), then exit. "
        "Do not print large logs."
    )


def run_codex_start(
    agent_dir: Path,
    full_auto: bool,
    timeout_s: int,
    step: dict | None,
    add_dirs: list[str],
) -> int:
    prompt = build_prompt(step)
    cmd = ["codex", "exec"]
    if full_auto:
        cmd.append("--full-auto")
    for add_dir in add_dirs:
        cmd.extend(["--add-dir", add_dir])
    cmd.append(prompt)
    return run_cmd(cmd, agent_dir.parent, timeout_s=timeout_s)


def run_codex_resume(agent_dir: Path, timeout_s: int, step: dict | None) -> int:
    # Resume the most recent Codex exec run for this repo.
    prompt = build_prompt(step)
    cmd = [
        "codex",
        "exec",
        "resume",
        "--last",
    ]
    cmd.append(prompt)
    return run_cmd(cmd, agent_dir.parent, timeout_s=timeout_s)


def load_blueprint(agent_dir: Path) -> dict:
    path = agent_dir / "BLUEPRINT.json"
    if not path.exists():
        return {
            "version": "1.0",
            "steps": [
                {"id": 1, "name": "spec", "objective": "Write PLAN.md", "checkpoint": True},
                {"id": 2, "name": "implement", "objective": "Implement changes", "checkpoint": True},
                {"id": 3, "name": "verify", "objective": "Run tests", "checkpoint": False},
                {"id": 4, "name": "finalize", "objective": "Write RESULT.md", "checkpoint": False},
            ],
        }
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"version": "1.0", "steps": []}
    return data if isinstance(data, dict) else {"version": "1.0", "steps": []}


def get_step(blueprint: dict, current_step: int) -> dict | None:
    for step in blueprint.get("steps", []):
        if step.get("id") == current_step:
            return step
    return None


def step_requires_test(step: dict | None) -> bool:
    if not step:
        return True
    if isinstance(step.get("requires_test"), bool):
        return step["requires_test"]
    return step.get("name") in ("verify", "finalize")


def step_allows_checkpoint(step: dict | None) -> bool:
    if not step:
        return False
    return bool(step.get("checkpoint"))


def write_checkpoint(agent_dir: Path, step: dict) -> str:
    repo = agent_dir.parent
    checkpoints = agent_dir / "checkpoints"
    checkpoints.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    patch_path = checkpoints / f"step-{step.get('id')}-{ts}.patch"
    meta_path = checkpoints / f"step-{step.get('id')}-{ts}.json"

    diff = subprocess.run(
        ["git", "diff", "--binary"],
        cwd=str(repo),
        capture_output=True,
        text=True,
        check=False,
    )
    patch_path.write_text(diff.stdout, encoding="utf-8")

    untracked = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard"],
        cwd=str(repo),
        capture_output=True,
        text=True,
        check=False,
    )
    meta = {
        "step": step,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "patch": str(patch_path.name),
        "untracked": [line for line in untracked.stdout.splitlines() if line.strip()],
    }
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return meta_path.name


def load_supervisor_config(repo: Path) -> dict:
    config_path = repo / "openclaw.json"
    if not config_path.exists():
        return {}
    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def resolve_scope(repo: Path, scope_arg: str | None) -> str:
    if scope_arg and scope_arg.strip():
        return scope_arg.strip()
    config = load_supervisor_config(repo)
    supervisor = config.get("supervisor", {})
    if isinstance(supervisor, dict):
        default_scope = supervisor.get("default_scope")
        if isinstance(default_scope, str) and default_scope.strip():
            return default_scope.strip()
    return DEFAULT_SCOPE


def _resolve_add_dir(repo: Path, raw: str) -> str | None:
    candidate = Path(raw).expanduser()
    if not candidate.is_absolute():
        candidate = (repo / candidate).resolve()
    else:
        candidate = candidate.resolve()
    if candidate.exists() and candidate.is_dir():
        return str(candidate)
    return None


def resolve_add_dirs(repo: Path, cli_add_dirs: list[str] | None) -> list[str]:
    config = load_supervisor_config(repo)
    supervisor = config.get("supervisor", {})

    configured: list[str] = []
    if isinstance(supervisor, dict):
        maybe_add_dirs = supervisor.get("add_dirs")
        if isinstance(maybe_add_dirs, list):
            configured = [item for item in maybe_add_dirs if isinstance(item, str) and item.strip()]

    candidates: list[str] = [str((Path.home() / ".codex").resolve())]
    candidates.extend(cli_add_dirs or [])
    candidates.extend(configured)

    # Auto-detect common sync target: sibling skills/<name> when repo is "<name>-repo".
    if repo.name.endswith("-repo"):
        mirror = repo.parent / "skills" / repo.name[:-5]
        if mirror.exists() and mirror.is_dir():
            candidates.append(str(mirror))

    deduped: list[str] = []
    seen: set[str] = set()
    for raw in candidates:
        resolved = _resolve_add_dir(repo, raw)
        if not resolved or resolved in seen:
            continue
        seen.add(resolved)
        deduped.append(resolved)
    return deduped


def resolve_sync_target(add_dirs: list[str]) -> str | None:
    codex_home = str((Path.home() / ".codex").resolve())
    for path in add_dirs:
        if str(Path(path).resolve()) != codex_home:
            return path
    return None


def is_host_sync_step(step: dict | None) -> bool:
    if not step:
        return False
    text = f"{step.get('name', '')} {step.get('objective', '')}".lower()
    return ("sync" in text) and ("skill" in text or "../skills" in text)


def run_host_sync(repo: Path, target: str, agent_dir: Path, timeout_s: int = 180) -> int:
    script = repo / "scripts" / "sync_to_skill.py"
    if not script.exists():
        (agent_dir / "sync_tail.log").write_text("sync_to_skill.py missing\n", encoding="utf-8")
        return 127

    cmd = [sys.executable, str(script), "--repo", str(repo), "--target", target]
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(repo),
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_s,
        )
    except subprocess.TimeoutExpired:
        (agent_dir / "sync_tail.log").write_text("sync_to_skill.py timed out\n", encoding="utf-8")
        return 124

    output = "\n".join(part for part in ((proc.stdout or "").strip(), (proc.stderr or "").strip()) if part)
    tail = output.splitlines()[-150:] if output else []
    (agent_dir / "sync_tail.log").write_text(
        ("\n".join(tail) + "\n") if tail else "sync_to_skill.py produced no output\n",
        encoding="utf-8",
    )
    return proc.returncode


def _compact(value: str) -> str:
    parts = [line.strip() for line in value.splitlines() if line.strip()]
    return " ; ".join(parts) if parts else "无"


def _git_output(repo: Path, args: list[str]) -> tuple[int, str]:
    try:
        proc = subprocess.run(
            ["git", "-C", str(repo), *args],
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        return 127, ""
    output = (proc.stdout or "").strip() or (proc.stderr or "").strip()
    return proc.returncode, output


# 路径前缀，用于过滤自动生成/备份/临时文件
EXCLUDE_PATHS = (
    "memory/.vector_db",
    "memory/.vector_db_final",
    "skills/deepsea-nexus-backup",
    "skills/deepsea-nexus_backup",
    "skills/deepsea-nexus-v3.0",
    "skills/openclaw-dev-repo/agent/",
    "agent/",
    "openclaw-dev-repo/agent/",
)

def _is_excluded(path: str) -> bool:
    return any(path.startswith(p) for p in EXCLUDE_PATHS)

def collect_diff(repo: Path, scope: str) -> tuple[str, str, bool]:
    rc_files, files_raw = _git_output(repo, ["diff", "--name-only", "--", scope])
    changed_files = "无"
    diff_stat = "无"
    diff_written = False

    if rc_files == 0 and files_raw:
        all_files = [line.strip() for line in files_raw.splitlines() if line.strip()]
        files = [f for f in all_files if not _is_excluded(f)]
        if files:
            changed_files = ", ".join(files)

            rc_stat, stat_raw = _git_output(repo, ["diff", "--stat", "--", scope])
            if rc_stat == 0 and stat_raw:
                # 过滤 stat 行，仅保留属于 files 的条目
                stat_lines = stat_raw.splitlines()
                filtered_stat_lines = []
                for line in stat_lines:
                    if '|' in line:
                        path_part = line.split('|')[0].strip()
                        if path_part in files:
                            filtered_stat_lines.append(line)
                    else:
                        stripped = line.strip()
                        if any(stripped.startswith(f) for f in files):
                            filtered_stat_lines.append(line)
                diff_stat = "\n".join(filtered_stat_lines) if filtered_stat_lines else "无"
                diff_written = bool(filtered_stat_lines)
        else:
            changed_files = "无"
            diff_stat = "无"
            diff_written = False
    return changed_files, diff_stat, diff_written


def run_workspace_tests(repo: Path, agent_dir: Path, timeout_s: int = 180) -> tuple[str, bool]:
    test_script = repo / "run_tests.py"
    if not test_script.exists():
        return "run_tests.py: skipped (missing)", True
    try:
        proc = subprocess.run(
            [sys.executable, str(test_script)],
            cwd=str(repo),
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_s,
        )
    except subprocess.TimeoutExpired:
        (agent_dir / "run_tests_tail.log").write_text("run_tests.py timed out\n", encoding="utf-8")
        return "run_tests.py: timeout", False
    output = "\n".join(
        part for part in ((proc.stdout or "").strip(), (proc.stderr or "").strip()) if part
    )
    tail_lines = output.splitlines()[-150:] if output else []
    (agent_dir / "run_tests_tail.log").write_text(
        ("\n".join(tail_lines) + "\n") if tail_lines else "run_tests.py produced no output\n",
        encoding="utf-8",
    )
    ok = proc.returncode == 0
    if ok:
        return "run_tests.py: OK", True
    return f"run_tests.py: FAILED(exit={proc.returncode})", False


def write_result_summary(
    result_path: Path,
    completion: str,
    changed_files: str,
    diff_stat: str,
    verification: str,
    risks: str,
) -> None:
    result_path.write_text(
        RESULT_TEMPLATE.format(
            completion=_compact(completion),
            changed_files=_compact(changed_files),
            diff_stat=_compact(diff_stat),
            verification=_compact(verification),
            risks=_compact(risks),
        ),
        encoding="utf-8",
    )


def append_nightly_log(repo: Path, status: str, diff_written: bool, scope_used: str) -> None:
    log_path = repo / "memory" / "supervisor_nightly.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "status": status,
        "diff_written": bool(diff_written),
        "scope_used": scope_used,
    }
    with log_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")


def record_check_result(
    repo: Path,
    agent_dir: Path,
    scope_used: str,
    completion: str,
    risks: str,
    status_parts: list[str],
    *,
    test_rc: int | None,
    write_diff: bool,
) -> None:
    verification_parts = []
    if test_rc is None:
        verification_parts.append("TEST_CMD: 未执行")
    else:
        verification_parts.append("TEST_CMD: OK" if test_rc == 0 else f"TEST_CMD: FAILED(exit={test_rc})")

    workspace_test_summary, workspace_test_ok = run_workspace_tests(repo, agent_dir)
    verification_parts.append(workspace_test_summary)

    changed_files = "无"
    diff_stat = "无"
    diff_written = False
    if write_diff:
        changed_files, diff_stat, diff_written = collect_diff(repo, scope_used)

    write_result_summary(
        agent_dir / "RESULT.md",
        completion=completion,
        changed_files=changed_files,
        diff_stat=diff_stat,
        verification="; ".join(verification_parts),
        risks=risks,
    )

    final_status_parts = [part for part in status_parts if part]
    final_status_parts.append("run_tests_ok" if workspace_test_ok else "run_tests_failed")
    append_nightly_log(repo, ",".join(final_status_parts) if final_status_parts else "unknown", diff_written, scope_used)


def loop(
    repo: Path,
    interval: int,
    run_once: bool,
    full_auto: bool,
    force_start: bool,
    codex_timeout: int,
    scope_arg: str | None,
    cli_add_dirs: list[str] | None,
    max_attempts: int,
    attempt_sleep: int,
) -> None:
    agent_dir = repo / "agent"
    status_path = agent_dir / "STATUS.json"
    scope_used = resolve_scope(repo, scope_arg)
    add_dirs = resolve_add_dirs(repo, cli_add_dirs)
    sync_target = resolve_sync_target(add_dirs)
    primary_codex_dir = str((Path.home() / ".codex").resolve())
    has_external_add_dirs = any(Path(path).resolve() != Path(primary_codex_dir).resolve() for path in add_dirs)
    if not agent_dir.exists():
        raise SystemExit("agent/ directory not found. Run init_openclaw_dev.py first.")

    blueprint = load_blueprint(agent_dir)
    attempts = 0

    while True:
        status = load_status(status_path)
        state = status.get("state", "idle")

        if state in ("done", "blocked"):
            print(f"Status={state}. Exiting.")
            return

        if max_attempts > 0 and attempts >= max_attempts:
            status["state"] = "blocked"
            status["needs_human"] = True
            status["human_question"] = (
                f"Reached max_attempts={max_attempts} without completion. "
                "Likely repeated timeout/no-progress. Consider refining TASK.md or increasing --codex-timeout."
            )
            status["last_error_sig"] = "max_attempts"
            save_status(status_path, status)
            record_check_result(
                repo,
                agent_dir,
                scope_used,
                completion="巡检结束：达到最大尝试次数，已标记为 blocked。",
                risks=status["human_question"],
                status_parts=["max_attempts"],
                test_rc=None,
                write_diff=False,
            )
            return

        if not status.get("current_step"):
            status["current_step"] = 1
            save_status(status_path, status)

        step = get_step(blueprint, int(status.get("current_step", 1)))
        if step is None:
            status["state"] = "done"
            save_status(status_path, status)
            print("No more steps. Marked done.")
            return

        host_sync_step = is_host_sync_step(step)
        if host_sync_step and not sync_target:
            status["state"] = "blocked"
            status["needs_human"] = True
            status["human_question"] = (
                "Sync step detected but no writable sync target configured. "
                "Set openclaw.json supervisor.add_dirs (e.g. ../skills/openclaw-dev) "
                "or pass --add-dir."
            )
            status["last_error_sig"] = "sync_target_missing"
            save_status(status_path, status)
            record_check_result(
                repo,
                agent_dir,
                scope_used,
                completion="巡检结束：同步目标未配置，已标记为 blocked。",
                risks=status["human_question"],
                status_parts=["sync_target_missing"],
                test_rc=None,
                write_diff=False,
            )
            return

        start_needed = force_start or not status.get("last_cmd") or has_external_add_dirs

        status["state"] = "running"
        if host_sync_step:
            status["last_cmd"] = f"sync_to_skill.py --target {sync_target}"
        elif start_needed:
            status["last_cmd"] = "codex exec --full-auto" if full_auto else "codex exec"
        else:
            status["last_cmd"] = "codex exec resume --last"
        save_status(status_path, status)

        plan_path = agent_dir / "PLAN.md"
        result_path = agent_dir / "RESULT.md"
        plan_before = plan_path.stat().st_mtime if plan_path.exists() else 0
        result_before = result_path.stat().st_mtime if result_path.exists() else 0

        if host_sync_step:
            codex_rc = run_host_sync(repo, sync_target or "", agent_dir, timeout_s=min(codex_timeout, 300))
        elif start_needed:
            codex_rc = run_codex_start(
                agent_dir,
                full_auto=full_auto,
                timeout_s=codex_timeout,
                step=step,
                add_dirs=add_dirs,
            )
        else:
            codex_rc = run_codex_resume(
                agent_dir,
                timeout_s=codex_timeout,
                step=step,
            )
        attempts += 1

        plan_after = plan_path.stat().st_mtime if plan_path.exists() else 0
        result_after = result_path.stat().st_mtime if result_path.exists() else 0

        # Fallback: if Codex times out or makes no progress, force-write PLAN.md via shell.
        if (
            not host_sync_step
            and codex_rc in (124, 0)
            and plan_after == plan_before
            and result_after == result_before
        ):
            cmd = ["codex", "exec"]
            if full_auto:
                cmd.append("--full-auto")
            for add_dir in add_dirs:
                cmd.extend(["--add-dir", add_dir])
            cmd.append(_force_write_files_prompt())
            _rc2 = run_cmd(cmd, agent_dir.parent, timeout_s=codex_timeout)
            plan_after = plan_path.stat().st_mtime if plan_path.exists() else 0
            result_after = result_path.stat().st_mtime if result_path.exists() else 0
            codex_rc = _rc2

        if codex_rc == 124 and not host_sync_step:
            if plan_after > plan_before or result_after > result_before:
                status = load_status(status_path)
                status["state"] = "idle"
                status["needs_human"] = False
                status["human_question"] = ""
                status["last_error_sig"] = "codex_timeout_progress"
                status["last_action"] = "codex_timeout_with_progress"
                save_status(status_path, status)
                record_check_result(
                    repo,
                    agent_dir,
                    scope_used,
                    completion="巡检结束：codex exec 超时但已有产出，状态保持 idle。",
                    risks=(
                        f"codex exec timed out after {codex_timeout}s, but progress was detected; "
                        "建议增大 --codex-timeout（例如 300）以减少中断。"
                    ),
                    status_parts=["codex_timeout_progress"],
                    test_rc=None,
                    write_diff=False,
                )
                if run_once:
                    return
                time.sleep(attempt_sleep)
                continue
            if not run_once:
                time.sleep(attempt_sleep)
                continue
            status = load_status(status_path)
            status["state"] = "blocked"
            status["needs_human"] = True
            status["human_question"] = (
                f"codex exec timed out after {codex_timeout}s; "
                f"plan_updated={plan_after > plan_before}, result_updated={result_after > result_before}. "
                "Consider increasing --codex-timeout, refining TASK.md, or reducing repo scope."
            )
            status["last_error_sig"] = "codex_timeout"
            save_status(status_path, status)
            record_check_result(
                repo,
                agent_dir,
                scope_used,
                completion="巡检结束：codex exec 超时，已标记为 blocked。",
                risks=status["human_question"],
                status_parts=["codex_timeout"],
                test_rc=None,
                write_diff=False,
            )
            return

        if not host_sync_step and plan_after == plan_before and result_after == result_before:
            if not run_once:
                time.sleep(attempt_sleep)
                continue
            status = load_status(status_path)
            status["state"] = "blocked"
            status["needs_human"] = True
            status["human_question"] = (
                "codex exec finished but made no progress (PLAN.md/RESULT.md unchanged). "
                "Likely prompt too vague or codex stuck in inspection. Refine TASK.md with explicit file edits."
            )
            status["last_error_sig"] = "codex_no_progress"
            save_status(status_path, status)
            record_check_result(
                repo,
                agent_dir,
                scope_used,
                completion="巡检结束：codex 未产出有效变更，已标记为 blocked。",
                risks=status["human_question"],
                status_parts=["codex_no_progress"],
                test_rc=None,
                write_diff=False,
            )
            return

        status = load_status(status_path)
        if codex_rc != 0:
            if not run_once:
                time.sleep(attempt_sleep)
                continue
            status["state"] = "blocked"
            status["needs_human"] = True
            if host_sync_step:
                status["human_question"] = (
                    "sync_to_skill.py failed; inspect agent/sync_tail.log "
                    "and verify target path permissions."
                )
                status["last_error_sig"] = "sync_failed"
            else:
                status["human_question"] = "codex exec failed; inspect logs and agent/RESULT.md"
                status["last_error_sig"] = "codex_failed"
            save_status(status_path, status)
            record_check_result(
                repo,
                agent_dir,
                scope_used,
                completion=(
                    "巡检结束：同步脚本执行失败，已标记为 blocked。"
                    if host_sync_step
                    else "巡检结束：codex exec 执行失败，已标记为 blocked。"
                ),
                risks=status["human_question"],
                status_parts=["sync_failed" if host_sync_step else "codex_failed"],
                test_rc=None,
                write_diff=False,
            )
            return

        test_rc = run_tests(agent_dir)
        status["last_test_ok"] = (test_rc == 0)
        if status.get("state") not in ("blocked", "done"):
            status["state"] = "idle"
        save_status(status_path, status)

        step_ok = True
        if step_requires_test(step):
            step_ok = test_rc == 0

        if step_ok:
            if step_allows_checkpoint(step):
                status["checkpoint_id"] = write_checkpoint(agent_dir, step)
            status["current_step"] = int(status.get("current_step", 1)) + 1
            save_status(status_path, status)

        if test_rc == 0:
            completion = "巡检完成：codex 执行成功，TEST_CMD 通过。"
            risks = "无"
            status_parts = ["codex_ok", "tests_ok"]
        else:
            completion = "巡检完成：codex 执行成功，但 TEST_CMD 未通过。"
            risks = "TEST_CMD 未通过，需继续修复。"
            status_parts = ["codex_ok", "tests_failed"]

        record_check_result(
            repo,
            agent_dir,
            scope_used,
            completion=completion,
            risks=risks,
            status_parts=status_parts,
            test_rc=test_rc,
            write_diff=(test_rc == 0),
        )

        if run_once:
            return
        time.sleep(interval)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True, help="Repo root")
    parser.add_argument("--interval", type=int, default=1800)
    parser.add_argument("--run-once", action="store_true")
    parser.add_argument("--max-attempts", type=int, default=12, help="Max Codex attempts before marking blocked.")
    parser.add_argument("--attempt-sleep", type=int, default=20, help="Seconds to sleep between retries.")
    parser.add_argument("--full-auto", action="store_true")
    parser.add_argument("--start", action="store_true", help="Force a fresh codex exec")
    parser.add_argument("--codex-timeout", type=int, default=300, help="Timeout (seconds) for a single codex exec/resume call")
    parser.add_argument(
        "--add-dir",
        action="append",
        default=[],
        help="Extra writable directory for Codex sandbox (repeatable).",
    )
    parser.add_argument(
        "--scope",
        default=None,
        help="Git scope used for diff/risk summary. Defaults to openclaw.json supervisor.default_scope.",
    )
    args = parser.parse_args()

    loop(
        Path(args.repo).expanduser().resolve(),
        args.interval,
        args.run_once,
        args.full_auto,
        args.start,
        args.codex_timeout,
        args.scope,
        args.add_dir,
        args.max_attempts,
        args.attempt_sleep,
    )


if __name__ == "__main__":
    main()
