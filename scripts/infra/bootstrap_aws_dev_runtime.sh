#!/usr/bin/env bash
set -euo pipefail

RUNTIME_ROOT="${RUNTIME_ROOT:-/opt/hub-optimus}"
REPO_URL="${REPO_URL:-https://github.com/Voxterrae/HUB_Optimus.git}"
REPO_DIR="${REPO_DIR:-${RUNTIME_ROOT}/repo}"
VENV_DIR="${VENV_DIR:-${RUNTIME_ROOT}/venv}"
OUTPUT_FILE="${OUTPUT_FILE:-${RUNTIME_ROOT}/outputs/analysis_result.json}"
RUNTIME_USER="${SUDO_USER:-${USER}}"

log() {
  printf '[aws-dev-runtime] %s\n' "$1"
}

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    log "missing required command: $1"
    exit 1
  fi
}

run_as_runtime_user() {
  sudo -u "${RUNTIME_USER}" -H bash -lc "$1"
}

require_python_version() {
  python3 - <<'PY'
import sys
if sys.version_info < (3, 11):
    raise SystemExit("Python >= 3.11 is required")
PY
}

if [ "$(id -u)" -ne 0 ]; then
  log "run this bootstrap with sudo or as root"
  exit 1
fi

if [ -z "${RUNTIME_USER}" ] || [ "${RUNTIME_USER}" = "root" ]; then
  log "run with sudo from a non-root SSH user so repo code does not execute as root"
  exit 1
fi

log "installing system packages"
apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y \
  git \
  python3 \
  python3-venv \
  python3-pip

require_command git
require_command python3
require_python_version

log "creating runtime directories"
mkdir -p "${RUNTIME_ROOT}/inputs" "${RUNTIME_ROOT}/outputs" "${RUNTIME_ROOT}/logs" "${RUNTIME_ROOT}/runs"
chown -R "${RUNTIME_USER}:${RUNTIME_USER}" "${RUNTIME_ROOT}"

if [ ! -d "${REPO_DIR}/.git" ]; then
  log "cloning repository into ${REPO_DIR}"
  run_as_runtime_user "git clone '${REPO_URL}' '${REPO_DIR}'"
else
  log "repository already exists; fetching latest main"
  run_as_runtime_user "git -C '${REPO_DIR}' fetch origin main"
  run_as_runtime_user "git -C '${REPO_DIR}' checkout main"
  run_as_runtime_user "git -C '${REPO_DIR}' pull --ff-only origin main"
fi

log "creating Python virtual environment"
run_as_runtime_user "python3 -m venv '${VENV_DIR}'"

log "installing repository development dependencies"
run_as_runtime_user "source '${VENV_DIR}/bin/activate' && python -m pip install --upgrade pip && python -m pip install -r '${REPO_DIR}/requirements-dev.txt'"

log "running CLI smoke test"
run_as_runtime_user "cd '${REPO_DIR}' && source '${VENV_DIR}/bin/activate' && python -m semantic_engine.cli analyze examples/semantic_engine/case_minimal.json --output '${OUTPUT_FILE}'"

test -s "${OUTPUT_FILE}"
run_as_runtime_user "python3 -m json.tool '${OUTPUT_FILE}' >/dev/null"

log "runtime ready"
log "output written to ${OUTPUT_FILE}"
