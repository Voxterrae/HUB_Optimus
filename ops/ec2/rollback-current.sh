#!/usr/bin/env bash
set -euo pipefail

APP_ROOT="/opt/hub-optimus"

if [ ! -L "$APP_ROOT/current" ]; then
  echo "[rollback:error] Current symlink does not exist."
  exit 1
fi

if [ ! -f "$APP_ROOT/shared/previous_release" ]; then
  echo "[rollback] No previous release recorded."
  exit 1
fi

CURRENT="$(readlink -f "$APP_ROOT/current")"
PREVIOUS="$(cat "$APP_ROOT/shared/previous_release")"

if [ ! -d "$PREVIOUS" ]; then
  echo "[rollback:error] Previous release path does not exist: $PREVIOUS"
  exit 1
fi

if [ "$CURRENT" = "$PREVIOUS" ]; then
  echo "[rollback] Current release already matches previous_release target:"
  echo "$CURRENT"
  exit 0
fi

echo "$CURRENT" > "$APP_ROOT/shared/last_rollback_from"

ln -sfn "$PREVIOUS" "$APP_ROOT/current.new"
mv -Tf "$APP_ROOT/current.new" "$APP_ROOT/current"

cd "$APP_ROOT/current"

RELEASE="$(basename "$(readlink -f "$APP_ROOT/current")")"
COMMIT="$(git rev-parse --short HEAD)"
CURRENT_PATH="$(readlink -f "$APP_ROOT/current")"

cat > "$APP_ROOT/shared/RELEASE_STATE" <<STATE
release=$RELEASE
commit=$COMMIT
path=$CURRENT_PATH
validated_at_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)
validation=rollback to previously validated release
status=production-candidate-core
STATE

echo "$RELEASE" > "$APP_ROOT/shared/current_release"

echo "[rollback] Rolled back to:"
readlink -f "$APP_ROOT/current"

echo "[rollback] Release state:"
cat "$APP_ROOT/shared/RELEASE_STATE"
