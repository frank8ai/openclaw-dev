#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
VENV_DIR="${ROOT_DIR}/.venv"
PYTHON_BIN="${PYTHON_BIN:-python3}"

create_venv_if_missing() {
  if [[ ! -x "${VENV_DIR}/bin/python" ]]; then
    "${PYTHON_BIN}" -m venv "${VENV_DIR}"
  fi
}

install_deps() {
  "${VENV_DIR}/bin/python" -m pip install --upgrade pip >/dev/null
  "${VENV_DIR}/bin/pip" install -r "${ROOT_DIR}/requirements-dev.txt" >/dev/null
}

run_lint() {
  "${VENV_DIR}/bin/ruff" check scripts tests
}

run_typecheck() {
  "${VENV_DIR}/bin/mypy" scripts
}

run_tests() {
  "${VENV_DIR}/bin/pytest" -q tests
}

run_eval() {
  "${VENV_DIR}/bin/pytest" -q tests/eval
}

run_security() {
  "${VENV_DIR}/bin/bandit" -q -ii -c "${ROOT_DIR}/bandit.yaml" -r "${ROOT_DIR}/scripts"
}

run_review() {
  "${VENV_DIR}/bin/python" "${ROOT_DIR}/scripts/qa/review_gate.py"
}

main() {
  local gate="${1:-all}"
  create_venv_if_missing
  install_deps

  case "${gate}" in
    setup)
      ;;
    lint)
      run_lint
      ;;
    typecheck)
      run_typecheck
      ;;
    tests)
      run_tests
      ;;
    eval)
      run_eval
      ;;
    security)
      run_security
      ;;
    review)
      run_review
      ;;
    all)
      run_lint
      run_typecheck
      run_tests
      run_eval
      run_security
      run_review
      ;;
    *)
      echo "Unknown gate: ${gate}" >&2
      exit 2
      ;;
  esac
}

main "$@"
