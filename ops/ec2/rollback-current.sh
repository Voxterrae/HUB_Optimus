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

required_state_value() {
  local state_file="$1"
  local key="$2"
  local count

  count="$(grep -c "^${key}=" "$state_file" 2>/dev/null || true)"
  [ "$count" -eq 1 ] \
    || fail "$state_file must contain exactly one $key field."
  state_value "$state_file" "$key"
}

validate_exact_state_keys() {
  local state_file="$1"
  shift
  local allowed=" $* "
  local line
  local key
  local expected_count="$#"
  local actual_count=0

  while IFS= read -r line || [ -n "$line" ]; do
    actual_count=$((actual_count + 1))
    [[ "$line" == *=* ]] \
      || fail "$state_file contains a malformed state line."
    key="${line%%=*}"
    case "$allowed" in
      *" $key "*) ;;
      *) fail "$state_file contains an unsupported field: $key" ;;
    esac
  done < "$state_file"

  for key in "$@"; do
    required_state_value "$state_file" "$key" >/dev/null
  done
  [ "$actual_count" -eq "$expected_count" ] \
    || fail "$state_file does not contain the exact expected field set."
}

validate_release_state_schema() {
  local state_file="$1"
  local requested_ref_kind
  local provenance_count
  local legacy_commit_prefix
  local legacy_state_sha256
  local recorded_commit

  requested_ref_kind="$(
    required_state_value "$state_file" "requested_ref_kind"
  )"
  case "$requested_ref_kind" in
    commit|tag)
      provenance_count="$(
        grep -c '^provenance=' "$state_file" 2>/dev/null || true
      )"
      case "$provenance_count" in
        0)
          validate_exact_state_keys \
            "$state_file" \
            release requested_ref requested_ref_kind commit path \
            validated_at_utc validation_command validation_exit_code \
            validation_result validation_log validation_log_exit_code \
            launcher_sha256 status
          ;;
        1)
          [ "$(required_state_value "$state_file" "provenance")" \
            = "adopted-pre-1832" ] \
            || fail "$state_file has unsupported transitional provenance."
          validate_exact_state_keys \
            "$state_file" \
            release requested_ref requested_ref_kind commit path \
            validated_at_utc validation_command validation_exit_code \
            validation_result validation_log validation_log_exit_code \
            launcher_sha256 status provenance
          ;;
        *)
          fail "$state_file contains duplicate provenance fields."
          ;;
      esac
      ;;
    legacy-host-adoption)
      validate_exact_state_keys \
        "$state_file" \
        release requested_ref requested_ref_kind commit path adopted_at_utc \
        validation_command validation_exit_code validation_result validation_log \
        validation_log_exit_code launcher_sha256 status provenance \
        legacy_state_sha256 legacy_commit_prefix
      ;;
    *)
      fail "$state_file has an unsupported requested_ref_kind."
      ;;
  esac

  case "$requested_ref_kind" in
    commit|tag)
      [ "$(required_state_value "$state_file" "validation_command")" \
        = "python -m pytest -q" ] \
        || fail "$state_file has an unexpected validation command."
      [ "$(required_state_value "$state_file" "validation_exit_code")" = "0" ] \
        && [ "$(required_state_value "$state_file" "validation_log_exit_code")" = "0" ] \
        || fail "$state_file does not record successful validation."
      [ -n "$(required_state_value "$state_file" "validation_result")" ] \
        || fail "$state_file has an empty validation result."
      [ "$(required_state_value "$state_file" "status")" \
        = "production-candidate-core" ] \
        || fail "$state_file is not a production candidate."
      ;;
    legacy-host-adoption)
      recorded_commit="$(required_state_value "$state_file" "commit")"
      legacy_commit_prefix="$(
        required_state_value "$state_file" "legacy_commit_prefix"
      )"
      legacy_state_sha256="$(
        required_state_value "$state_file" "legacy_state_sha256"
      )"
      [ "$(required_state_value "$state_file" "requested_ref")" \
        = "$recorded_commit" ] \
        || fail "$state_file legacy adoption is not commit-bound."
      [ "$(required_state_value "$state_file" "validation_command")" \
        = "not-run-during-legacy-adoption" ] \
        && [ "$(required_state_value "$state_file" "validation_exit_code")" \
          = "not-run" ] \
        && [ "$(required_state_value "$state_file" "validation_log")" \
          = "not-applicable" ] \
        && [ "$(required_state_value "$state_file" "validation_log_exit_code")" \
          = "not-run" ] \
        || fail "$state_file has invalid legacy-adoption validation metadata."
      [ "$(required_state_value "$state_file" "status")" \
        = "adopted-legacy-current" ] \
        && [ "$(required_state_value "$state_file" "provenance")" \
          = "adopted-legacy-current-v1" ] \
        || fail "$state_file has invalid legacy-adoption provenance."
      [[ "$legacy_state_sha256" =~ ^[0-9a-f]{64}$ ]] \
        || fail "$state_file has an invalid legacy-state SHA-256."
      [[ "$legacy_commit_prefix" =~ ^[0-9a-f]{7,39}$ ]] \
        || fail "$state_file has an invalid legacy commit prefix."
      case "$recorded_commit" in
        "$legacy_commit_prefix"*) ;;
        *) fail "$state_file legacy commit prefix does not match commit." ;;
      esac
      ;;
  esac
}

sha256_file() {
  local path="$1"
  local digest

  digest="$(sha256sum -- "$path" | awk '{print $1}')"
  [[ "$digest" =~ ^[0-9a-f]{64}$ ]] \
    || fail "Could not calculate launcher SHA-256: $path"
  printf '%s\n' "$digest"
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

CURRENT_COMMIT="$(git -C "$CURRENT" rev-parse --verify HEAD)"
[[ "$CURRENT_COMMIT" =~ ^[0-9a-f]{40}$ ]] \
  || fail "Current release does not resolve to one full commit SHA."
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
