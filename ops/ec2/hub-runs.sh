#!/usr/bin/env bash
set -euo pipefail

RUN_ROOT="/opt/hub-optimus/shared/runs"

usage() {
  cat <<USAGE
HUB_Optimus run registry

Usage:
  hub-runs list
  hub-runs latest <command>
  hub-runs show <command> <run_id>

Examples:
  hub-runs list
  hub-runs latest semantic-smoke
  hub-runs show scenario-smoke 20260629T125443Z
USAGE
}

list_runs() {
  if [ ! -d "$RUN_ROOT" ]; then
    echo "[runs] no runs directory"
    exit 0
  fi

  echo "[runs] available:"
  find "$RUN_ROOT" -mindepth 2 -maxdepth 2 -type d \
    | sed "s#$RUN_ROOT/##" \
    | sort
}

latest_run() {
  local command="${1:-}"

  if [ -z "$command" ]; then
    echo "[runs:error] command name required"
    exit 1
  fi

  local command_dir="$RUN_ROOT/$command"

  if [ ! -d "$command_dir" ]; then
    echo "[runs:error] no runs for command: $command"
    exit 1
  fi

  ls -1 "$command_dir" | sort | tail -n 1
}

show_run() {
  local command="${1:-}"
  local run_id="${2:-}"

  if [ -z "$command" ] || [ -z "$run_id" ]; then
    echo "[runs:error] command and run_id required"
    exit 1
  fi

  local dir="$RUN_ROOT/$command/$run_id"

  if [ ! -d "$dir" ]; then
    echo "[runs:error] run not found: $command/$run_id"
    exit 1
  fi

  echo "[runs] path:"
  echo "$dir"
  echo

  echo "[runs] files:"
  find "$dir" -maxdepth 1 -type f -printf "%f\n" | sort
  echo

  if [ -f "$dir/RUN_STATE" ]; then
    echo "[runs] RUN_STATE:"
    cat "$dir/RUN_STATE"
    echo
  fi

  for file in "$dir"/*.json "$dir"/*.md "$dir"/*.log; do
    if [ -f "$file" ]; then
      echo "[runs] --- $(basename "$file") ---"
      cat "$file"
      echo
    fi
  done
}

case "${1:-}" in
  list)
    list_runs
    ;;
  latest)
    latest_run "${2:-}"
    ;;
  show)
    show_run "${2:-}" "${3:-}"
    ;;
  ""|-h|--help|help)
    usage
    ;;
  *)
    echo "[runs:error] unknown command: $1"
    echo
    usage
    exit 1
    ;;
esac
