#!/usr/bin/env bash
set -euo pipefail

RUNTIME_ROOT="${RUNTIME_ROOT:-/opt/hub-optimus}"
REPO_URL="${REPO_URL:-https://github.com/Voxterrae/HUB_Optimus.git}"
REPO_DIR="${REPO_DIR:-${RUNTIME_ROOT}/repo}"
VENV_DIR="${VENV_DIR:-${RUNTIME_ROOT}/venv}"
OUTPUT_FILE="${OUTPUT_FILE:-${RUNTIME_ROOT}/outputs/analysis_result.json}"

log() {
  printf '[aws-dev-runtime] %s\n' "$1"
}

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    log "missing required command: $1"
    exit 1
  fi
}

if [ "$(id -u)" -ne 0 ]; then
  log "run this bootstrap with sudo or as root"
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

log "creating runtime directories"
mkdir -p "${RUNTIME_ROOT}/inputs" "${RUNTIME_ROOT}/outputs" "${RUNTIME_ROOT}/logs" "${RUNTIME_ROOT}/runs"

if [ ! -d "${REPO_DIR}/.git" ]; then
  log "cloning repository into ${REPO_DIR}"
  git clone "${REPO_URL}" "${REPO_DIR}"
else
  log "repository already exists; fetching latest main"
  git -C "${REPO_DIR}" fetch origin main
  git -C "${REPO_DIR}" checkout main
  git -C "${REPO_DIR}" pull --ff-only origin main
fi

log "creating Python virtual environment"
python3 -m venv "${VENV_DIR}"
# shellcheck disable=SC1091
source "${VENV_DIR}/bin/activate"

log "installing runtime test dependency"
python -m pip install --upgrade pip
python -m pip install pytest

log "running CLI smoke test"
cd "${REPO_DIR}"
python -m semantic_engine.cli analyze examples/semantic_engine/case_minimal.json --output "${OUTPUT_FILE}"

test -s "${OUTPUT_FILE}"
python -m json.tool "${OUTPUT_FILE}" >/dev/null

log "runtime ready"
log "output written to ${OUTPUT_FILE}"
