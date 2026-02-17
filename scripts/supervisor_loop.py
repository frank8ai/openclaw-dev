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


def run_codex_start(agent_dir: Path, full_auto: bool, timeout_s: int, step: dict | None) -> int:
    prompt = build_prompt(step)
    cmd = ["codex", "exec"]
    if full_auto:
        cmd.append("--full-auto")
    # Allow Codex to write to its own config/sessions dir even under sandbox
    cmd.extend(["--add-dir", str(Path.home() / ".codex")])
    cmd.append(prompt)
    return run_cmd(cmd, agent_dir.parent, timeout_s=timeout_s)


def run_codex_resume(agent_dir: Path, timeout_s: int, step: dict | None) -> int:
    # Resume the most recent Codex exec run for this repo.
    cmd = [
        "codex",
        "exec",
        "resume",
        "--last",
        build_prompt(step),
    ]
    cmd.extend(["--add-dir", str(Path.home() / ".codex")])
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
        return "run_tests.py: missing", False
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
    ok = proc.returncode == 0 and "OK" in (proc.stdout or "")
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
) -> None:
    agent_dir = repo / "agent"
    status_path = agent_dir / "STATUS.json"
    scope_used = resolve_scope(repo, scope_arg)
    if not agent_dir.exists():
        raise SystemExit("agent/ directory not found. Run init_openclaw_dev.py first.")

    blueprint = load_blueprint(agent_dir)

    while True:
        status = load_status(status_path)
        state = status.get("state", "idle")

        if state in ("done", "blocked"):
            print(f"Status={state}. Exiting.")
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

        start_needed = force_start or not status.get("last_cmd")

        status["state"] = "running"
        status["last_cmd"] = "codex exec --full-auto" if start_needed and full_auto else "codex exec resume --last"
        save_status(status_path, status)

        plan_path = agent_dir / "PLAN.md"
        result_path = agent_dir / "RESULT.md"
        plan_before = plan_path.stat().st_mtime if plan_path.exists() else 0
        result_before = result_path.stat().st_mtime if result_path.exists() else 0

        if start_needed:
            codex_rc = run_codex_start(agent_dir, full_auto=full_auto, timeout_s=codex_timeout, step=step)
        else:
            codex_rc = run_codex_resume(agent_dir, timeout_s=codex_timeout, step=step)

        plan_after = plan_path.stat().st_mtime if plan_path.exists() else 0
        result_after = result_path.stat().st_mtime if result_path.exists() else 0

        # Fallback: if Codex times out or makes no progress, force-write PLAN.md via shell.
        if codex_rc in (124, 0) and plan_after == plan_before and result_after == result_before:
            cmd = ["codex", "exec"]
            if full_auto:
                cmd.append("--full-auto")
            cmd.append(_force_write_files_prompt())
            _rc2 = run_cmd(cmd, agent_dir.parent, timeout_s=codex_timeout)
            plan_after = plan_path.stat().st_mtime if plan_path.exists() else 0
            result_after = result_path.stat().st_mtime if result_path.exists() else 0
            codex_rc = _rc2

        if codex_rc == 124:
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

        if plan_after == plan_before and result_after == result_before:
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
            status["state"] = "blocked"
            status["needs_human"] = True
            status["human_question"] = "codex exec failed; inspect logs and agent/RESULT.md"
            status["last_error_sig"] = "codex_failed"
            save_status(status_path, status)
            record_check_result(
                repo,
                agent_dir,
                scope_used,
                completion="巡检结束：codex exec 执行失败，已标记为 blocked。",
                risks=status["human_question"],
                status_parts=["codex_failed"],
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
    parser.add_argument("--full-auto", action="store_true")
    parser.add_argument("--start", action="store_true", help="Force a fresh codex exec")
    parser.add_argument("--codex-timeout", type=int, default=180, help="Timeout (seconds) for a single codex exec/resume call")
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
    )


if __name__ == "__main__":
    main()
