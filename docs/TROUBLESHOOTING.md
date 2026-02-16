# Troubleshooting

## Codex command not found
Install the Codex CLI or ensure it is on PATH.

## STATUS stuck in blocked
Check `agent/DECISIONS.md`, answer the questions, then re-run the supervisor loop.

## Tests always failing
Inspect `agent/test_tail.log` and fix the underlying issue in the target repo.

## Nothing happens on resume
Use `--start` once to force a fresh `codex exec` and initialize the session.
