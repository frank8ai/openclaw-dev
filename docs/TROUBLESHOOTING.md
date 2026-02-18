# Troubleshooting

## Codex command not found
Install the Codex CLI or ensure it is on PATH.

## STATUS stuck in blocked
Check `agent/DECISIONS.md`, answer the questions, then re-run the supervisor loop.

## Tests always failing
Inspect `agent/test_tail.log` and fix the underlying issue in the target repo.

## Nothing happens on resume
Use `--start` once to force a fresh `codex exec` and initialize the session.

## Permission denied when syncing to ../skills/...
Cause: Codex sandbox only writes to repo by default.

Fix one:
- Add `supervisor.add_dirs` in `openclaw.json` (example: `../skills/openclaw-dev`)
- Or run supervisor with `--add-dir ../skills/openclaw-dev`
- Or run host sync directly: `python3 scripts/sync_to_skill.py --repo . --target ../skills/openclaw-dev`

## PLAN/HOT got rewritten during sync
Cause: older supervisor logic could route sync-only runs into Codex fallback behavior.

Fix:
- Upgrade to the latest `scripts/supervisor_loop.py` in this repo.
- Ensure sync step objective includes `sync` + `skill` so supervisor uses host sync path.

## Memory context appears mixed across projects
Cause: namespace IDs are missing or inconsistent between trigger, status, and config defaults.

Fix:
- Run trigger with explicit `--tenant-id --agent-id --project-id`.
- Ensure `agent/STATUS.json` contains namespace keys.
- Verify `openclaw.json` -> `supervisor.memory_namespace.strict_isolation=true`.
- Use `python3 scripts/memory_namespace.py ... resolve` to confirm effective paths.
