#!/usr/bin/env bash
set -euo pipefail

SERVICE="hub-api.service"
LOG_FILE="/opt/hub-optimus/shared/logs/hub-api.systemd.log"

usage() {
  cat <<USAGE
HUB_Optimus local API control

Usage:
  hub-api-control start
  hub-api-control stop
  hub-api-control restart
  hub-api-control status
  hub-api-control log
USAGE
}

status_api() {
  echo "[hub-api] systemd:"
  systemctl status "$SERVICE" --no-pager || true

  echo
  echo "[hub-api] active:"
  systemctl is-active "$SERVICE" || true

  echo
  echo "[hub-api] enabled:"
  systemctl is-enabled "$SERVICE" || true

  echo
  echo "[hub-api] port:"
  ss -ltnp | grep ':8080' || true

  echo
  echo "[hub-api] health:"
  curl -sS http://127.0.0.1:8080/health 2>/dev/null || true
  echo
}

log_api() {
  echo "[hub-api] journal:"
  journalctl -u "$SERVICE" -n 80 --no-pager || true

  echo
  echo "[hub-api] file log:"
  tail -80 "$LOG_FILE" 2>/dev/null || echo "[hub-api] no file log"
}

case "${1:-}" in
  start)
    sudo systemctl start "$SERVICE"
    status_api
    ;;
  stop)
    sudo systemctl stop "$SERVICE"
    echo "[hub-api] stopped"
    ;;
  restart)
    sudo systemctl restart "$SERVICE"
    sleep 1
    status_api
    ;;
  status)
    status_api
    ;;
  log|logs)
    log_api
    ;;
  ""|-h|--help|help)
    usage
    ;;
  *)
    echo "[hub-api-control:error] unknown command: $1"
    echo
    usage
    exit 1
    ;;
esac
