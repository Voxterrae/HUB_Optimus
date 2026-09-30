#!/usr/bin/env bash
set -euo pipefail

APP_ROOT="${HUB_OPTIMUS_APP_ROOT:-/opt/hub-optimus}"
REPO_URL="${HUB_OPTIMUS_REPO_URL:-https://github.com/Voxterrae/HUB_Optimus.git}"
TARGET_SHA="${1:-}"
REFERENCE_URL="${2:-}"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
STATE_VALIDATOR="$SCRIPT_DIR/validate-release-state.sh"
SOURCE_TREE_TOOL="$SCRIPT_DIR/verify-release-worktree.py"

# Fail-closed floor for the reviewed t3.small deployment operation.
MIN_DISK_KIB=3145728
MIN_FREE_INODES=50000
MIN_AVAILABLE_MEMORY_KIB=524288
MAX_LOAD_1M=2.00

fail() {
  echo "[preflight:error] $*" >&2
  exit 1
}

validate_release_state_schema() {
  local state_file="$1"

  [ -f "$STATE_VALIDATOR" ] && [ ! -L "$STATE_VALIDATOR" ] \
    || fail "Release-state validator is not one regular file: $STATE_VALIDATOR"
  bash "$STATE_VALIDATOR" "$state_file" >/dev/null \
    || fail "Complete release-state validation failed: $state_file"
}

required_state_value() {
  local state_file="$1"
  local key="$2"
  local count

  count="$(grep -c "^${key}=" "$state_file" 2>/dev/null || true)"
  [ "$count" -eq 1 ] \
    || fail "$state_file must contain exactly one $key field."
  sed -n "s/^${key}=//p" "$state_file"
}

sha256_file() {
  local path="$1"
  local digest

  digest="$(sha256sum -- "$path" | awk '{print $1}')"
  [[ "$digest" =~ ^[0-9a-f]{64}$ ]] \
    || fail "Could not calculate SHA-256 for $path"
  printf '%s\n' "$digest"
}

inspect_release_directory() {
  local release_path="$1"
  local actual_commit
  local actual_launcher_sha256

  case "$release_path" in
    "$APP_ROOT/releases/"*) ;;
    *) fail "Release is outside the managed releases directory: $release_path" ;;
  esac
  [ -d "$release_path" ] \
    || fail "Release directory does not exist: $release_path"
  [ "$(git -C "$release_path" rev-parse --is-inside-work-tree)" = "true" ] \
    || fail "Release is not a Git worktree: $release_path"
  [ "$(git -C "$release_path" rev-parse --show-toplevel)" = "$release_path" ] \
    || fail "Release is not the Git worktree root: $release_path"
  [ "$(git -C "$release_path" remote get-url origin)" = "$REPO_URL" ] \
    || fail "Release origin is not the reviewed repository: $release_path"
  [ -f "$release_path/ops/ec2/hub-api.sh" ] \
    && [ ! -L "$release_path/ops/ec2/hub-api.sh" ] \
    && [ -x "$release_path/ops/ec2/hub-api.sh" ] \
    || fail "Release launcher is not one executable regular file: $release_path"

  actual_commit="$(git -C "$release_path" rev-parse --verify HEAD)"
  [[ "$actual_commit" =~ ^[0-9a-f]{40}$ ]] \
    || fail "Release does not resolve to one full commit SHA: $release_path"
  [ -f "$SOURCE_TREE_TOOL" ] && [ ! -L "$SOURCE_TREE_TOOL" ] \
    || fail "Source-tree verifier is not one regular file: $SOURCE_TREE_TOOL"
  /usr/bin/env -i \
    HOME=/nonexistent \
    LANG=C.UTF-8 \
    PATH=/usr/bin:/bin \
    /usr/bin/python3 -I \
      "$SOURCE_TREE_TOOL" \
      "$release_path" \
      "$actual_commit" \
      --allow-generated .venv \
      --allow-generated .hub-deployment \
      >/dev/null \
    || fail "Release source tree differs from its commit: $release_path"
  actual_launcher_sha256="$(sha256_file "$release_path/ops/ec2/hub-api.sh")"

  printf '%s\t%s\n' "$actual_commit" "$actual_launcher_sha256"
}

validate_release() {
  local release_path="$1"
  local state_file="$2"
  local require_recorded_launcher="$3"
  local actual_commit
  local actual_launcher_sha256
  local recorded_commit
  local recorded_path
  local recorded_release
  local recorded_launcher_sha256

  [ -f "$state_file" ] && [ ! -L "$state_file" ] \
    || fail "Release state is not one regular file: $state_file"
  validate_release_state_schema "$state_file"

  IFS=$'\t' read -r actual_commit actual_launcher_sha256 < <(
    inspect_release_directory "$release_path"
  )
  recorded_commit="$(required_state_value "$state_file" "commit")"
  recorded_path="$(required_state_value "$state_file" "path")"
  recorded_release="$(required_state_value "$state_file" "release")"

  [ "$recorded_commit" = "$actual_commit" ] \
    || fail "Release commit does not match $state_file"
  [ "$recorded_path" = "$release_path" ] \
    || fail "Release path does not match $state_file"
  [ "$recorded_release" = "$(basename "$release_path")" ] \
    || fail "Release name does not match $state_file"

  recorded_launcher_sha256="$(
    sed -n 's/^launcher_sha256=//p' "$state_file"
  )"
  if [ "$require_recorded_launcher" = "yes" ]; then
    [[ "$recorded_launcher_sha256" =~ ^[0-9a-f]{64}$ ]] \
      || fail "Release state has no valid launcher SHA-256: $state_file"
  fi
  if [ -n "$recorded_launcher_sha256" ] \
    && [ "$recorded_launcher_sha256" != "$actual_launcher_sha256" ]; then
    fail "Release launcher does not match $state_file"
  fi

  printf '%s\t%s\n' "$actual_commit" "$actual_launcher_sha256"
}

case "$APP_ROOT" in
  /*) ;;
  *) fail "HUB_OPTIMUS_APP_ROOT must be an absolute path." ;;
esac
[[ "$TARGET_SHA" =~ ^[0-9a-f]{40}$ ]] \
  || fail "One exact lowercase 40-character target commit is required."
case "$REFERENCE_URL" in
  https://*) ;;
  *) fail "One HTTPS reference URL is required for the egress check." ;;
esac

for command_name in \
  awk basename bash cat chmod cmp cp curl date df dirname flock free git grep \
  head install ln mkdir mktemp mv python3 readlink rm rmdir sed sha256sum stat \
  sudo systemctl tee timeout tr; do
  command -v "$command_name" >/dev/null 2>&1 \
    || fail "Required tool is unavailable: $command_name"
done

[ -d "$APP_ROOT/shared" ] || fail "Shared directory is missing: $APP_ROOT/shared"
[ -L "$APP_ROOT/current" ] || fail "Current release is not a symlink."
[ -f "$APP_ROOT/shared/bin/hub-api" ] \
  && [ ! -L "$APP_ROOT/shared/bin/hub-api" ] \
  && [ -x "$APP_ROOT/shared/bin/hub-api" ] \
  || fail "Shared hub-api launcher is not one executable regular file."
[ -f "$APP_ROOT/shared/current_release" ] \
  && [ ! -L "$APP_ROOT/shared/current_release" ] \
  || fail "Current-release marker is not one regular file."

sudo -n true >/dev/null 2>&1 \
  || fail "Passwordless non-interactive sudo is unavailable."
sudo -n systemctl is-active --quiet hub-api.service \
  || fail "hub-api.service is not active."

CURRENT_RELEASE="$(readlink -f "$APP_ROOT/current")"
SHARED_RELEASE_STATE="$APP_ROOT/shared/RELEASE_STATE"
[ -f "$SHARED_RELEASE_STATE" ] && [ ! -L "$SHARED_RELEASE_STATE" ] \
  || fail "Shared release state is not one regular file: $SHARED_RELEASE_STATE"
IFS=$'\t' read -r CURRENT_COMMIT CURRENT_LAUNCHER_SHA256 < <(
  validate_release "$CURRENT_RELEASE" "$SHARED_RELEASE_STATE" "yes"
)

CURRENT_RELEASE_STATE="$CURRENT_RELEASE/.hub-deployment/RELEASE_STATE"
[ -f "$CURRENT_RELEASE_STATE" ] \
  || fail "Current per-release state is missing; run explicit legacy adoption first."
IFS=$'\t' read -r RELEASE_COMMIT RELEASE_LAUNCHER_SHA256 < <(
  validate_release "$CURRENT_RELEASE" "$CURRENT_RELEASE_STATE" "yes"
)
[ "$RELEASE_COMMIT" = "$CURRENT_COMMIT" ] \
  && [ "$RELEASE_LAUNCHER_SHA256" = "$CURRENT_LAUNCHER_SHA256" ] \
  && cmp -s "$CURRENT_RELEASE_STATE" "$SHARED_RELEASE_STATE" \
  || fail "Shared RELEASE_STATE is not the exact current release state."

CURRENT_MARKER="$(cat "$APP_ROOT/shared/current_release")"
[ "$CURRENT_MARKER" = "$(basename "$CURRENT_RELEASE")" ] \
  || fail "Current-release marker does not match the current symlink."
SHARED_LAUNCHER_SHA256="$(sha256_file "$APP_ROOT/shared/bin/hub-api")"
[ "$SHARED_LAUNCHER_SHA256" = "$CURRENT_LAUNCHER_SHA256" ] \
  || fail "Shared launcher does not match the current release launcher."

PREVIOUS_RELEASE="none"
PREVIOUS_COMMIT="none"
PREVIOUS_LAUNCHER_SHA256="none"
PREVIOUS_STATE_STATUS="none"
if [ -L "$APP_ROOT/shared/previous_release" ]; then
  fail "Previous-release pointer must not be a symlink."
elif [ -f "$APP_ROOT/shared/previous_release" ]; then
  PREVIOUS_RELEASE="$(readlink -f "$(cat "$APP_ROOT/shared/previous_release")")"
  if [ -f "$PREVIOUS_RELEASE/.hub-deployment/RELEASE_STATE" ]; then
    IFS=$'\t' read -r PREVIOUS_COMMIT PREVIOUS_LAUNCHER_SHA256 < <(
      validate_release \
        "$PREVIOUS_RELEASE" \
        "$PREVIOUS_RELEASE/.hub-deployment/RELEASE_STATE" \
        "yes"
    )
    PREVIOUS_STATE_STATUS="attested"
  else
    # This historical pointer is not the rollback target created by the next
    # deploy. Inventory its real checkout and launcher without manufacturing
    # provenance from an ambiguous legacy state file.
    IFS=$'\t' read -r PREVIOUS_COMMIT PREVIOUS_LAUNCHER_SHA256 < <(
      inspect_release_directory "$PREVIOUS_RELEASE"
    )
    PREVIOUS_STATE_STATUS="legacy-unattested-not-deploy-rollback-target"
  fi
fi

DISK_AVAILABLE_KIB="$(df -Pk "$APP_ROOT" | awk 'NR == 2 {print $4}')"
[[ "$DISK_AVAILABLE_KIB" =~ ^[0-9]+$ ]] \
  || fail "Could not determine available disk space."
[ "$DISK_AVAILABLE_KIB" -ge "$MIN_DISK_KIB" ] \
  || fail "Available disk is below ${MIN_DISK_KIB} KiB."

FREE_INODES="$(df -Pi "$APP_ROOT" | awk 'NR == 2 {print $4}')"
[[ "$FREE_INODES" =~ ^[0-9]+$ ]] \
  || fail "Could not determine available inodes."
[ "$FREE_INODES" -ge "$MIN_FREE_INODES" ] \
  || fail "Available inodes are below $MIN_FREE_INODES."

AVAILABLE_MEMORY_KIB="$(free -k | awk '/^Mem:/ {print $7}')"
[[ "$AVAILABLE_MEMORY_KIB" =~ ^[0-9]+$ ]] \
  || fail "Could not determine available memory."
[ "$AVAILABLE_MEMORY_KIB" -ge "$MIN_AVAILABLE_MEMORY_KIB" ] \
  || fail "Available memory is below ${MIN_AVAILABLE_MEMORY_KIB} KiB."

LOAD_1M="$(awk '{print $1}' /proc/loadavg)"
awk -v actual="$LOAD_1M" -v maximum="$MAX_LOAD_1M" \
  'BEGIN { exit !(actual + 0 <= maximum + 0) }' \
  || fail "One-minute load $LOAD_1M exceeds $MAX_LOAD_1M."

GIT_TERMINAL_PROMPT=0 timeout 15 git ls-remote "$REPO_URL" HEAD >/dev/null \
  || fail "Git repository egress check failed."
curl \
  --proto '=https' \
  --tlsv1.2 \
  --fail \
  --silent \
  --show-error \
  --connect-timeout 5 \
  --max-time 15 \
  --range 0-0 \
  --output /dev/null \
  "$REFERENCE_URL" \
  || fail "Reference URL egress check failed."

printf 'target_commit=%s\n' "$TARGET_SHA"
printf 'current_release=%s\n' "$CURRENT_RELEASE"
printf 'current_commit=%s\n' "$CURRENT_COMMIT"
printf 'current_launcher_sha256=%s\n' "$CURRENT_LAUNCHER_SHA256"
printf 'shared_launcher_sha256=%s\n' "$SHARED_LAUNCHER_SHA256"
printf 'previous_release=%s\n' "$PREVIOUS_RELEASE"
printf 'previous_commit=%s\n' "$PREVIOUS_COMMIT"
printf 'previous_launcher_sha256=%s\n' "$PREVIOUS_LAUNCHER_SHA256"
printf 'previous_state_status=%s\n' "$PREVIOUS_STATE_STATUS"
printf 'disk_available_kib=%s (minimum=%s)\n' "$DISK_AVAILABLE_KIB" "$MIN_DISK_KIB"
printf 'free_inodes=%s (minimum=%s)\n' "$FREE_INODES" "$MIN_FREE_INODES"
printf 'available_memory_kib=%s (minimum=%s)\n' \
  "$AVAILABLE_MEMORY_KIB" "$MIN_AVAILABLE_MEMORY_KIB"
printf 'load_1m=%s (maximum=%s)\n' "$LOAD_1M" "$MAX_LOAD_1M"
printf '[preflight] PASS\n'
