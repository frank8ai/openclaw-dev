#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

TARGET_REPO="${OPENCLAW_TARGET_REPO:-${REPO_ROOT}}"
INTERVAL="${OPENCLAW_SUPERVISOR_INTERVAL:-1800}"
CODEX_TIMEOUT="${OPENCLAW_CODEX_TIMEOUT:-300}"
MAX_ATTEMPTS="${OPENCLAW_MAX_ATTEMPTS:-12}"
ADD_DIR="${OPENCLAW_ADD_DIR:-}"

cmd=(
  python3
  "${REPO_ROOT}/scripts/supervisor_loop.py"
  --repo "${TARGET_REPO}"
  --interval "${INTERVAL}"
  --full-auto
  --codex-timeout "${CODEX_TIMEOUT}"
  --max-attempts "${MAX_ATTEMPTS}"
)

if [[ -n "${ADD_DIR}" ]]; then
  cmd+=(--add-dir "${ADD_DIR}")
fi

exec "${cmd[@]}"
