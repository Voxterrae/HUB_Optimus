#!/usr/bin/env bash
set -euo pipefail

APP_ROOT="${HUB_OPTIMUS_APP_ROOT:-/opt/hub-optimus}"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
STATE_VALIDATOR="$SCRIPT_DIR/validate-release-state.sh"
OPERATION_LOCK_TOOL="$SCRIPT_DIR/operation-lock.py"
OPERATION_ENTRYPOINT="$SCRIPT_DIR/rollback-current.sh"
SOURCE_TREE_TOOL="$SCRIPT_DIR/verify-release-worktree.py"
VALIDATION_RUNNER="$SCRIPT_DIR/run-release-validation.py"

fail() {
  echo "[rollback:error] $*" >&2
  exit 1
}

verify_or_acquire_operation_lock() {
  [ -f "$OPERATION_LOCK_TOOL" ] && [ ! -L "$OPERATION_LOCK_TOOL" ] \
    || fail "Operation-lock helper is not one regular file: $OPERATION_LOCK_TOOL"
  if [ -z "${HUB_OPTIMUS_OPERATION_LOCK_FD:-}" ]; then
    exec /usr/bin/python3 -I \
      "$OPERATION_LOCK_TOOL" \
      exec \
      "$APP_ROOT" \
      "$OPERATION_ENTRYPOINT" \
      "$@"
  fi
  /usr/bin/python3 -I \
    "$OPERATION_LOCK_TOOL" \
    verify \
    "$APP_ROOT" \
    "$HUB_OPTIMUS_OPERATION_LOCK_FD" \
    || fail "Inherited operation lock could not be verified."
  unset HUB_OPTIMUS_OPERATION_LOCK_FD
}

validate_release_state_schema() {
  local state_file="$1"

  [ -f "$STATE_VALIDATOR" ] && [ ! -L "$STATE_VALIDATOR" ] \
    || fail "Release-state validator is not one regular file: $STATE_VALIDATOR"
  bash "$STATE_VALIDATOR" "$state_file" >/dev/null \
    || fail "Complete release-state validation failed: $state_file"
}

state_value() {
  local state_file="$1"
  local key="$2"
  sed -n "s/^${key}=//p" "$state_file" | head -n 1
}

required_state_value() {
  local state_file="$1"
  local key="$2"
  local count

  count="$(grep -c "^${key}=" "$state_file" 2>/dev/null || true)"
  [ "$count" -eq 1 ] \
    || fail "$state_file must contain exactly one $key field."
  state_value "$state_file" "$key"
}

sha256_file() {
  local path="$1"
  local digest

  digest="$(sha256sum -- "$path" | awk '{print $1}')"
  [[ "$digest" =~ ^[0-9a-f]{64}$ ]] \
    || fail "Could not calculate launcher SHA-256: $path"
  printf '%s\n' "$digest"
}

verify_release_head() {
  local release_path="$1"
  local commit="$2"
  local head_commit

  head_commit="$(
    /usr/bin/env -i \
      HOME=/nonexistent \
      LANG=C.UTF-8 \
      PATH=/usr/bin:/bin \
      GIT_CONFIG_GLOBAL=/dev/null \
      GIT_CONFIG_NOSYSTEM=1 \
      GIT_NO_REPLACE_OBJECTS=1 \
      /usr/bin/git --no-replace-objects \
        -C "$release_path" rev-parse --verify HEAD
  )" || fail "Release HEAD could not be resolved safely: $release_path"
  [[ "$head_commit" =~ ^[0-9a-f]{40}$ ]] \
    && [ "$head_commit" = "$commit" ] \
    || fail "Release HEAD differs from its recorded commit: $release_path"
}

release_source_evidence() {
  local release_path="$1"
  local commit="$2"
  local evidence

  verify_release_head "$release_path" "$commit"

  [ -f "$SOURCE_TREE_TOOL" ] && [ ! -L "$SOURCE_TREE_TOOL" ] \
    || fail "Source-tree verifier is not one regular file: $SOURCE_TREE_TOOL"
  evidence="$(
    /usr/bin/env -i \
      HOME=/nonexistent \
      LANG=C.UTF-8 \
      PATH=/usr/bin:/bin \
      /usr/bin/python3 -I \
        "$SOURCE_TREE_TOOL" \
        "$release_path" \
        "$commit" \
        --allow-generated .venv \
        --allow-generated .hub-deployment
  )" || fail "Release source tree differs from its reviewed commit: $release_path"
  [ -n "$evidence" ] \
    || fail "Source-tree verifier returned empty evidence."
  verify_release_head "$release_path" "$commit"
  printf '%s\n' "$evidence"
}

source_tree_digest() {
  local evidence="$1"
  local expected_commit="$2"

  /usr/bin/python3 -I - "$expected_commit" "$evidence" <<'PY_SOURCE_EVIDENCE'
import json
import re
import sys


expected_commit, raw = sys.argv[1:]
try:
    evidence = json.loads(raw)
except json.JSONDecodeError:
    raise SystemExit(1)
digest = evidence.get("source_tree_sha256")
if evidence.get("commit") != expected_commit or not isinstance(digest, str):
    raise SystemExit(1)
if re.fullmatch(r"[0-9a-f]{64}", digest) is None:
    raise SystemExit(1)
print(digest)
PY_SOURCE_EVIDENCE
}

release_venv_digest() {
  local release_path="$1"
  local digest

  [ -f "$VALIDATION_RUNNER" ] && [ ! -L "$VALIDATION_RUNNER" ] \
    || fail "Venv-manifest supervisor is not one regular file: $VALIDATION_RUNNER"
  digest="$(
    /usr/bin/env -i \
      HOME=/nonexistent \
      LANG=C.UTF-8 \
      PATH=/usr/bin:/bin \
      /usr/bin/python3 -I \
        "$VALIDATION_RUNNER" \
        manifest-venv \
        "$release_path"
  )" || fail "Release venv manifest verification failed: $release_path"
  [[ "$digest" =~ ^[0-9a-f]{64}$ ]] \
    || fail "Venv-manifest supervisor returned an invalid digest."
  printf '%s\n' "$digest"
}

verify_recorded_release_authority() {
  local release_path="$1"
  local state_file="$2"
  local label="$3"
  local commit
  local evidence
  local actual_source_tree_sha256
  local actual_venv_tree_sha256
  local recorded_source_tree_sha256
  local recorded_venv_tree_sha256

  commit="$(required_state_value "$state_file" commit)"
  recorded_source_tree_sha256="$(
    required_state_value "$state_file" source_tree_sha256
  )"
  recorded_venv_tree_sha256="$(
    required_state_value "$state_file" venv_tree_sha256
  )"
  [[ "$recorded_source_tree_sha256" =~ ^[0-9a-f]{64}$ ]] \
    || fail "$label RELEASE_STATE has no valid source-tree SHA-256."
  [[ "$recorded_venv_tree_sha256" =~ ^[0-9a-f]{64}$ ]] \
    || fail "$label RELEASE_STATE has no valid venv-tree SHA-256."

  evidence="$(release_source_evidence "$release_path" "$commit")"
  actual_source_tree_sha256="$(source_tree_digest "$evidence" "$commit")" \
    || fail "$label source-tree verifier returned invalid evidence."
  [ "$actual_source_tree_sha256" = "$recorded_source_tree_sha256" ] \
    || fail "$label source tree does not match RELEASE_STATE."

  actual_venv_tree_sha256="$(release_venv_digest "$release_path")"
  [ "$actual_venv_tree_sha256" = "$recorded_venv_tree_sha256" ] \
    || fail "$label venv does not match RELEASE_STATE."
  verify_release_head "$release_path" "$commit"
  printf '%s:%s\n' "$actual_source_tree_sha256" "$actual_venv_tree_sha256"
}

snapshot_item() {
  local source="$1"
  local name="$2"

  if [ -e "$source" ] || [ -L "$source" ]; then
    printf 'present\n' > "$RECOVERY_DIR/$name.presence"
    cp -a -- "$source" "$RECOVERY_DIR/$name"
  else
    printf 'absent\n' > "$RECOVERY_DIR/$name.presence"
  fi
}

restore_item() {
  local target="$1"
  local name="$2"
  local presence

  presence="$(cat "$RECOVERY_DIR/$name.presence")"
  if [ -d "$target" ] && [ ! -L "$target" ]; then
    echo "[rollback:recovery:error] Refusing to replace directory: $target" >&2
    return 1
  fi
  rm -f -- "$target"

  case "$presence" in
    present)
      cp -a -- "$RECOVERY_DIR/$name" "$target"
      ;;
    absent)
      ;;
    *)
      echo "[rollback:recovery:error] Invalid snapshot marker for $target" >&2
      return 1
      ;;
  esac
}

recovery_note() {
  local message="$1"
  local log_requirement="$2"

  if [ "$RECOVERY_LOG_READY" -eq 1 ]; then
    if ! printf '%s\n' "$message" >&8; then
      RECOVERY_LOG_FAILED=1
      RECOVERY_LOG_READY=0
      [ "$log_requirement" != "require-log" ] || return 1
    fi
  elif [ "$log_requirement" = "require-log" ]; then
    return 1
  fi
  printf '%s\n' "$message" >&2 || true
}

recover_pre_rollback_state() {
  local state_restore_failed=0
  local recovery_succeeded=0

  RECOVERY_LOG_READY=0
  RECOVERY_LOG_FAILED=0
  set +e

  if [ -n "$RECOVERY_LOG" ] \
    && { exec 8>> "$RECOVERY_LOG"; } 2>/dev/null; then
    RECOVERY_LOG_READY=1
    chmod 0600 "$RECOVERY_LOG" 2>/dev/null || RECOVERY_LOG_FAILED=1
  else
    RECOVERY_LOG_FAILED=1
  fi

  recovery_note \
    "[rollback:recovery] Restoring exact pre-rollback operational state" \
    allow-missing-log
  restore_item "$APP_ROOT/shared/last_rollback_from" "last-rollback-from" \
    || state_restore_failed=1
  restore_item "$APP_ROOT/shared/bin/hub-api" "shared-launcher" \
    || state_restore_failed=1
  restore_item "$APP_ROOT/shared/RELEASE_STATE" "shared-release-state" \
    || state_restore_failed=1
  restore_item "$APP_ROOT/shared/ROLLBACK_STATE" "rollback-state" \
    || state_restore_failed=1
  restore_item "$APP_ROOT/shared/current_release" "current-release-marker" \
    || state_restore_failed=1
  restore_item "$APP_ROOT/current" "current-symlink" \
    || state_restore_failed=1
  rm -f -- "$CURRENT_NEW" || state_restore_failed=1

  if [ "$state_restore_failed" -eq 0 ] \
    && [ "$RECOVERY_LOG_FAILED" -eq 0 ] \
    && recovery_note \
      "[rollback:recovery] Pre-rollback operational state restored" \
      require-log; then
    recovery_succeeded=1
  elif [ "$state_restore_failed" -eq 0 ]; then
    recovery_note \
      "[rollback:recovery:error] Operational state restored, but recovery evidence could not be recorded; treating recovery as failed" \
      allow-missing-log
  else
    recovery_note \
      "[rollback:recovery:error] Recovery was incomplete; inspect the retained snapshot" \
      allow-missing-log
  fi

  if [ "$RECOVERY_LOG_READY" -eq 1 ]; then
    exec 8>&-
  fi
  set -e
  [ "$recovery_succeeded" -eq 1 ]
}

on_exit() {
  local exit_code="$?"

  trap - EXIT
  if [ "$exit_code" -ne 0 ] && [ "$MUTATION_STARTED" -eq 1 ]; then
    recover_pre_rollback_state || exit_code=1
  fi
  exit "$exit_code"
}

inject_test_failure() {
  local stage="$1"

  if [ "${HUB_OPTIMUS_TEST_ROLLBACK_FAIL_AFTER_MUTATION:-}" = "$stage" ]; then
    fail "injected test failure after mutation stage: $stage"
  fi
}

MUTATION_STARTED=0
ROLLBACK_WORK_DIR=""
TRANSACTION_DIR=""
RECOVERY_DIR=""
RECOVERY_LOG="/dev/null"
RECOVERY_LOG_READY=0
RECOVERY_LOG_FAILED=0
CURRENT_NEW=""
trap on_exit EXIT

case "$APP_ROOT" in
  /*) ;;
  *) fail "HUB_OPTIMUS_APP_ROOT must be an absolute path." ;;
esac

verify_or_acquire_operation_lock "$@"

if [ ! -L "$APP_ROOT/current" ]; then
  fail "Current symlink does not exist."
fi
if [ ! -f "$APP_ROOT/shared/previous_release" ]; then
  fail "No previous release recorded."
fi

CURRENT="$(readlink -f "$APP_ROOT/current")"
PREVIOUS="$(readlink -f "$(cat "$APP_ROOT/shared/previous_release")")"

case "$CURRENT" in
  "$APP_ROOT/releases/"*) ;;
  *) fail "Current release is outside the managed releases directory: $CURRENT" ;;
esac
case "$PREVIOUS" in
  "$APP_ROOT/releases/"*) ;;
  *) fail "Previous release is outside the managed releases directory: $PREVIOUS" ;;
esac
[ -d "$CURRENT" ] || fail "Current release path does not exist: $CURRENT"
[ -d "$PREVIOUS" ] || fail "Previous release path does not exist: $PREVIOUS"

CURRENT_STATE="$CURRENT/.hub-deployment/RELEASE_STATE"
SHARED_STATE="$APP_ROOT/shared/RELEASE_STATE"
[ -f "$CURRENT_STATE" ] && [ ! -L "$CURRENT_STATE" ] \
  || fail "Current release has no regular per-release state: $CURRENT_STATE"
[ -f "$SHARED_STATE" ] && [ ! -L "$SHARED_STATE" ] \
  || fail "Current release has no regular shared state: $SHARED_STATE"
validate_release_state_schema "$CURRENT_STATE"
validate_release_state_schema "$SHARED_STATE"
cmp -s "$CURRENT_STATE" "$SHARED_STATE" \
  || fail "Shared RELEASE_STATE differs from current per-release state."

CURRENT_COMMIT="$(git -C "$CURRENT" rev-parse --verify HEAD)"
[[ "$CURRENT_COMMIT" =~ ^[0-9a-f]{40}$ ]] \
  || fail "Current release does not resolve to one full commit SHA."
[ "$(required_state_value "$CURRENT_STATE" "commit")" = "$CURRENT_COMMIT" ] \
  || fail "Current release commit does not match its deployment state."
[ "$(required_state_value "$CURRENT_STATE" "path")" = "$CURRENT" ] \
  || fail "Current release path does not match its deployment state."
[ "$(required_state_value "$CURRENT_STATE" "release")" = "$(basename "$CURRENT")" ] \
  || fail "Current release name does not match its deployment state."
[ -f "$CURRENT/ops/ec2/hub-api.sh" ] \
  || fail "Current release has no hub-api launcher: $CURRENT/ops/ec2/hub-api.sh"
CURRENT_LAUNCHER_SHA256="$(sha256_file "$CURRENT/ops/ec2/hub-api.sh")"
[ "$(required_state_value "$CURRENT_STATE" "launcher_sha256")" = "$CURRENT_LAUNCHER_SHA256" ] \
  || fail "Current release launcher does not match its deployment state."
verify_recorded_release_authority \
  "$CURRENT" \
  "$CURRENT_STATE" \
  "Current release" \
  >/dev/null

if [ "$CURRENT" = "$PREVIOUS" ]; then
  echo "[rollback] Current release already matches previous_release target:"
  echo "$CURRENT"
  exit 0
fi

PREVIOUS_STATE="$PREVIOUS/.hub-deployment/RELEASE_STATE"
[ -f "$PREVIOUS_STATE" ] && [ ! -L "$PREVIOUS_STATE" ] \
  || fail "Previous release has no recorded deployment state: $PREVIOUS_STATE"
[ -f "$PREVIOUS/ops/ec2/hub-api.sh" ] \
  || fail "Previous release has no hub-api launcher: $PREVIOUS/ops/ec2/hub-api.sh"

validate_release_state_schema "$PREVIOUS_STATE"

RECORDED_COMMIT="$(required_state_value "$PREVIOUS_STATE" "commit")"
RECORDED_PATH="$(required_state_value "$PREVIOUS_STATE" "path")"
RECORDED_RELEASE="$(required_state_value "$PREVIOUS_STATE" "release")"
RECORDED_LAUNCHER_SHA256="$(
  required_state_value "$PREVIOUS_STATE" "launcher_sha256"
)"
ACTUAL_COMMIT="$(git -C "$PREVIOUS" rev-parse --verify HEAD)"
[[ "$ACTUAL_COMMIT" =~ ^[0-9a-f]{40}$ ]] \
  || fail "Previous release does not resolve to one full commit SHA."
[ "$RECORDED_COMMIT" = "$ACTUAL_COMMIT" ] \
  || fail "Previous release commit does not match its deployment state."
[ "$RECORDED_PATH" = "$PREVIOUS" ] \
  || fail "Previous release path does not match its deployment state."
[ "$RECORDED_RELEASE" = "$(basename "$PREVIOUS")" ] \
  || fail "Previous release name does not match its deployment state."
[[ "$RECORDED_LAUNCHER_SHA256" =~ ^[0-9a-f]{64}$ ]] \
  || fail "Previous release state has no valid launcher SHA-256."
ACTUAL_LAUNCHER_SHA256="$(sha256_file "$PREVIOUS/ops/ec2/hub-api.sh")"
[ "$RECORDED_LAUNCHER_SHA256" = "$ACTUAL_LAUNCHER_SHA256" ] \
  || fail "Previous release launcher does not match its deployment state."
verify_recorded_release_authority \
  "$PREVIOUS" \
  "$PREVIOUS_STATE" \
  "Previous release" \
  >/dev/null

CURRENT_RELEASE="$(basename "$CURRENT")"
PREVIOUS_RELEASE="$(basename "$PREVIOUS")"

ROLLBACK_WORK_DIR="$(
  mktemp -d "$APP_ROOT/shared/rollback-transaction.$(date -u +%Y%m%dT%H%M%SZ).XXXXXX"
)"
TRANSACTION_DIR="$ROLLBACK_WORK_DIR/transaction"
RECOVERY_DIR="$ROLLBACK_WORK_DIR/pre-rollback-state"
RECOVERY_LOG="${HUB_OPTIMUS_TEST_ROLLBACK_RECOVERY_LOG_PATH:-$ROLLBACK_WORK_DIR/recovery.log}"
CURRENT_NEW="$APP_ROOT/current.rollback-new.$(basename "$ROLLBACK_WORK_DIR")"
mkdir -p "$TRANSACTION_DIR" "$RECOVERY_DIR"
chmod 0700 "$ROLLBACK_WORK_DIR" "$TRANSACTION_DIR" "$RECOVERY_DIR"

printf '%s\n' "$CURRENT" > "$TRANSACTION_DIR/last_rollback_from"
install -m 0755 \
  "$PREVIOUS/ops/ec2/hub-api.sh" \
  "$TRANSACTION_DIR/hub-api"
install -m 0644 "$PREVIOUS_STATE" "$TRANSACTION_DIR/RELEASE_STATE"
cat > "$TRANSACTION_DIR/ROLLBACK_STATE" <<STATE
rolled_back_at_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)
from_release=$CURRENT_RELEASE
from_commit=$CURRENT_COMMIT
to_release=$PREVIOUS_RELEASE
to_commit=$ACTUAL_COMMIT
to_launcher_sha256=$ACTUAL_LAUNCHER_SHA256
STATE
chmod 0600 "$TRANSACTION_DIR/ROLLBACK_STATE"
printf '%s\n' "$PREVIOUS_RELEASE" > "$TRANSACTION_DIR/current_release"

snapshot_item "$APP_ROOT/shared/last_rollback_from" "last-rollback-from"
snapshot_item "$APP_ROOT/shared/bin/hub-api" "shared-launcher"
snapshot_item "$APP_ROOT/shared/RELEASE_STATE" "shared-release-state"
snapshot_item "$APP_ROOT/shared/ROLLBACK_STATE" "rollback-state"
snapshot_item "$APP_ROOT/shared/current_release" "current-release-marker"
snapshot_item "$APP_ROOT/current" "current-symlink"

if [ -n "${HUB_OPTIMUS_TEST_ROLLBACK_BEFORE_AUTHORITY_READY:-}" ]; then
  touch "$HUB_OPTIMUS_TEST_ROLLBACK_BEFORE_AUTHORITY_READY"
  while [ ! -e "${HUB_OPTIMUS_TEST_ROLLBACK_BEFORE_AUTHORITY_PROCEED:-}" ]; do
    sleep 0.01
  done
fi
verify_recorded_release_authority \
  "$CURRENT" \
  "$CURRENT_STATE" \
  "Current release" \
  >/dev/null
verify_recorded_release_authority \
  "$PREVIOUS" \
  "$PREVIOUS_STATE" \
  "Previous release" \
  >/dev/null
verify_release_head "$CURRENT" "$CURRENT_COMMIT"
verify_release_head "$PREVIOUS" "$ACTUAL_COMMIT"

MUTATION_STARTED=1

echo "[rollback] Recording rollback source"
mv -Tf \
  "$TRANSACTION_DIR/last_rollback_from" \
  "$APP_ROOT/shared/last_rollback_from"
inject_test_failure "last-rollback-from"

echo "[rollback] Switching current symlink"
ln -s "$PREVIOUS" "$CURRENT_NEW"
mv -Tf "$CURRENT_NEW" "$APP_ROOT/current"
inject_test_failure "current"

echo "[rollback] Syncing hub-api launcher"
mv -Tf "$TRANSACTION_DIR/hub-api" "$APP_ROOT/shared/bin/hub-api"
inject_test_failure "launcher"

echo "[rollback] Publishing release state"
mv -Tf \
  "$TRANSACTION_DIR/RELEASE_STATE" \
  "$APP_ROOT/shared/RELEASE_STATE"
inject_test_failure "release-state"

echo "[rollback] Publishing rollback transition"
mv -Tf \
  "$TRANSACTION_DIR/ROLLBACK_STATE" \
  "$APP_ROOT/shared/ROLLBACK_STATE"
inject_test_failure "rollback-state"

echo "[rollback] Publishing current-release marker"
mv -Tf \
  "$TRANSACTION_DIR/current_release" \
  "$APP_ROOT/shared/current_release"
inject_test_failure "current-release"

echo "[rollback] Rolled back to:"
readlink -f "$APP_ROOT/current"
echo "[rollback] Release state:"
cat "$APP_ROOT/shared/RELEASE_STATE"
echo "[rollback] Rollback state:"
cat "$APP_ROOT/shared/ROLLBACK_STATE"
echo "[rollback] Done"

MUTATION_STARTED=0
if ! rm -rf -- "$ROLLBACK_WORK_DIR"; then
  echo "[rollback:warning] Could not remove completed transaction snapshot." >&2
fi
