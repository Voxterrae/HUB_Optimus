#!/usr/bin/env bash
set -euo pipefail

APP_ROOT="/opt/hub-optimus"

usage() {
  cat <<USAGE
HUB_Optimus EC2 ops

Usage:
  hub-ops status
  hub-ops validate
  hub-ops deploy
  hub-ops rollback

Commands:
  status    Show current release, previous release, state, commit, git status, releases and disk usage.
  validate  Run pytest on current release and show commit/status.
  deploy    Run deploy-current.
  rollback  Run rollback-current.
USAGE
}

status_current() {
  echo "[status] HUB_Optimus EC2"
  echo

  echo "[status] current:"
  readlink -f "$APP_ROOT/current" 2>/dev/null || echo "none"
  echo

  echo "[status] previous:"
  cat "$APP_ROOT/shared/previous_release" 2>/dev/null || echo "none"
  echo

  echo "[status] current_release:"
  cat "$APP_ROOT/shared/current_release" 2>/dev/null || echo "none"
  echo

  echo "[status] release_state:"
  cat "$APP_ROOT/shared/RELEASE_STATE" 2>/dev/null || echo "none"
  echo

  echo "[status] last_rollback_from:"
  cat "$APP_ROOT/shared/last_rollback_from" 2>/dev/null || echo "none"
  echo

  echo "[status] git commit:"
  if [ -L "$APP_ROOT/current" ]; then
    cd "$APP_ROOT/current"
    git rev-parse --short HEAD
  else
    echo "none"
  fi
  echo

  echo "[status] git status:"
  if [ -L "$APP_ROOT/current" ]; then
    cd "$APP_ROOT/current"
    git status --short
  else
    echo "none"
  fi
  echo

  echo "[status] releases:"
  ls -1 "$APP_ROOT/releases" 2>/dev/null | sort || echo "none"
  echo

  echo "[status] disk:"
  df -h "$APP_ROOT" | tail -n 1
}

validate_current() {
  if [ ! -L "$APP_ROOT/current" ]; then
    echo "[validate:error] current symlink does not exist."
    exit 1
  fi

  cd "$APP_ROOT/current"

  if [ ! -d ".venv" ]; then
    echo "[validate:error] .venv does not exist in current release."
    exit 1
  fi

  source .venv/bin/activate

  echo "[validate] Running pytest"
  python -m pytest -q

  deactivate

  echo "[validate] Git status"
  git status --short

  echo "[validate] Commit"
  git rev-parse --short HEAD

  echo "[validate] Done"
}

case "${1:-}" in
  status)
    status_current
    ;;
  validate)
    validate_current
    ;;
  deploy)
    exec "$APP_ROOT/shared/bin/deploy-current"
    ;;
  rollback)
    exec "$APP_ROOT/shared/bin/rollback-current"
    ;;
  ""|-h|--help|help)
    usage
    ;;
  *)
    echo "[hub-ops:error] Unknown command: $1"
    echo
    usage
    exit 1
    ;;
esac
