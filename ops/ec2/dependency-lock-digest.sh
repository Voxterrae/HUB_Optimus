#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 1 ]; then
  echo "[dependency-lock:error] Usage: dependency-lock-digest <release-path>" >&2
  exit 1
fi

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
exec /usr/bin/python3 -I \
  "$SCRIPT_DIR/verify-installed-dependencies.py" \
  digest \
  "$1"
