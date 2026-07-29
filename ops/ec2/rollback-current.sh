#!/usr/bin/env bash
set -euo pipefail

APP_ROOT="${HUB_OPTIMUS_APP_ROOT:-/opt/hub-optimus}"

fail() {
  echo "[rollback:error] $*" >&2
  exit 1
}

state_value() {
  local state_file="$1"
  local key="$2"
  sed -n "s/^${key}=//p" "$state_file" | head -n 1
}

case "$APP_ROOT" in
  /*) ;;
  *) fail "HUB_OPTIMUS_APP_ROOT must be an absolute path." ;;
esac

exec 9> "$APP_ROOT/shared/deploy.lock"
flock -n 9 || fail "another deploy or rollback operation is active."

if [ ! -L "$APP_ROOT/current" ]; then
  fail "Current symlink does not exist."
fi

if [ ! -f "$APP_ROOT/shared/previous_release" ]; then
  fail "No previous release recorded."
fi

CURRENT="$(readlink -f "$APP_ROOT/current")"
PREVIOUS="$(readlink -f "$(cat "$APP_ROOT/shared/previous_release")")"

case "$PREVIOUS" in
  "$APP_ROOT/releases/"*) ;;
  *) fail "Previous release is outside the managed releases directory: $PREVIOUS" ;;
esac

if [ ! -d "$PREVIOUS" ]; then
  fail "Previous release path does not exist: $PREVIOUS"
fi

if [ "$CURRENT" = "$PREVIOUS" ]; then
  echo "[rollback] Current release already matches previous_release target:"
  echo "$CURRENT"
  exit 0
fi

PREVIOUS_STATE="$PREVIOUS/.hub-deployment/RELEASE_STATE"
if [ ! -f "$PREVIOUS_STATE" ]; then
  fail "Previous release has no recorded deployment state: $PREVIOUS_STATE"
fi

if [ ! -f "$PREVIOUS/ops/ec2/hub-api.sh" ]; then
  fail "Previous release has no hub-api launcher: $PREVIOUS/ops/ec2/hub-api.sh"
fi

RECORDED_COMMIT="$(state_value "$PREVIOUS_STATE" "commit")"
ACTUAL_COMMIT="$(git -C "$PREVIOUS" rev-parse HEAD)"
if [ -z "$RECORDED_COMMIT" ] || [ "$RECORDED_COMMIT" != "$ACTUAL_COMMIT" ]; then
  fail "Previous release commit does not match its deployment state."
fi

CURRENT_COMMIT="$(git -C "$CURRENT" rev-parse HEAD)"
CURRENT_RELEASE="$(basename "$CURRENT")"
PREVIOUS_RELEASE="$(basename "$PREVIOUS")"

echo "$CURRENT" > "$APP_ROOT/shared/last_rollback_from"

ln -sfn "$PREVIOUS" "$APP_ROOT/current.new"
mv -Tf "$APP_ROOT/current.new" "$APP_ROOT/current"

install -m 0755 \
  "$APP_ROOT/current/ops/ec2/hub-api.sh" \
  "$APP_ROOT/shared/bin/hub-api"
install -m 0644 "$PREVIOUS_STATE" "$APP_ROOT/shared/RELEASE_STATE.new"
mv -Tf "$APP_ROOT/shared/RELEASE_STATE.new" "$APP_ROOT/shared/RELEASE_STATE"

cat > "$APP_ROOT/shared/ROLLBACK_STATE.new" <<STATE
rolled_back_at_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)
from_release=$CURRENT_RELEASE
from_commit=$CURRENT_COMMIT
to_release=$PREVIOUS_RELEASE
to_commit=$ACTUAL_COMMIT
STATE
chmod 0600 "$APP_ROOT/shared/ROLLBACK_STATE.new"
mv -Tf "$APP_ROOT/shared/ROLLBACK_STATE.new" "$APP_ROOT/shared/ROLLBACK_STATE"

echo "$PREVIOUS_RELEASE" > "$APP_ROOT/shared/current_release"

echo "[rollback] Rolled back to:"
readlink -f "$APP_ROOT/current"

echo "[rollback] Release state:"
cat "$APP_ROOT/shared/RELEASE_STATE"

echo "[rollback] Rollback state:"
cat "$APP_ROOT/shared/ROLLBACK_STATE"
