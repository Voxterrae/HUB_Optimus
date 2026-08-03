#!/usr/bin/env bash
set -euo pipefail

APP_ROOT="${HUB_OPTIMUS_APP_ROOT:-/opt/hub-optimus}"
REPO_URL="${HUB_OPTIMUS_REPO_URL:-https://github.com/Voxterrae/HUB_Optimus.git}"
EXPECTED_COMMIT="${1:-}"

usage() {
  cat <<USAGE
HUB_Optimus explicit legacy-current adoption

Usage:
  adopt-legacy-current <expected-full-current-commit-sha>

This command adopts only the already configured current release. It does not
deploy, switch current, restart a service, or infer identity from a short SHA.
USAGE
}

fail() {
  echo "[legacy-adoption:error] $*" >&2
  exit 1
}

sha256_file() {
  local path="$1"
  local digest

  digest="$(sha256sum -- "$path" | awk '{print $1}')"
  [[ "$digest" =~ ^[0-9a-f]{64}$ ]] \
    || fail "Could not calculate SHA-256 for $path"
  printf '%s\n' "$digest"
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
    echo "[legacy-adoption:recovery:error] Refusing to replace directory: $target" >&2
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
      echo "[legacy-adoption:recovery:error] Invalid snapshot marker for $target" >&2
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

recover_legacy_adoption() {
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
    "[legacy-adoption:recovery] Restoring exact pre-adoption state" \
    allow-missing-log
  restore_item "$APP_ROOT/shared/RELEASE_STATE" "shared-release-state" \
    || state_restore_failed=1
  restore_item "$CURRENT_DEPLOYMENT_STATE" "current-release-state" \
    || state_restore_failed=1
  restore_item "$CURRENT_LEGACY_STATE" "legacy-release-state" \
    || state_restore_failed=1
  restore_item "$CURRENT_GIT_EXCLUDE" "current-git-exclude" \
    || state_restore_failed=1
  restore_item "$APP_ROOT/shared/current_release" "current-release-marker" \
    || state_restore_failed=1
  restore_item "$APP_ROOT/shared/bin/hub-api" "shared-launcher" \
    || state_restore_failed=1
  restore_item "$APP_ROOT/shared/previous_release" "previous-release-pointer" \
    || state_restore_failed=1
  restore_item "$APP_ROOT/current" "current-symlink" \
    || state_restore_failed=1
  rm -f -- "$CURRENT_DEPLOYMENT_STATE_NEW" || state_restore_failed=1
  rm -f -- "$CURRENT_LEGACY_STATE_NEW" || state_restore_failed=1
  if [ "$DEPLOYMENT_DIR_EXISTED" -eq 0 ] \
    && [ -d "$CURRENT_DEPLOYMENT_DIR" ]; then
    rmdir "$CURRENT_DEPLOYMENT_DIR" 2>/dev/null || state_restore_failed=1
  fi

  if [ "$state_restore_failed" -eq 0 ] \
    && [ "$RECOVERY_LOG_FAILED" -eq 0 ] \
    && recovery_note \
      "[legacy-adoption:recovery] Pre-adoption state restored" \
      require-log; then
    recovery_succeeded=1
  elif [ "$state_restore_failed" -eq 0 ]; then
    recovery_note \
      "[legacy-adoption:recovery:error] State restored, but recovery evidence could not be recorded; treating recovery as failed" \
      allow-missing-log
  else
    recovery_note \
      "[legacy-adoption:recovery:error] Recovery was incomplete; inspect the retained snapshot" \
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
    recover_legacy_adoption || exit_code=1
  fi
  exit "$exit_code"
}

inject_test_failure() {
  local stage="$1"

  if [ "${HUB_OPTIMUS_TEST_LEGACY_ADOPTION_FAIL_AFTER_MUTATION:-}" = "$stage" ]; then
    fail "injected test failure after mutation stage: $stage"
  fi
}

validate_legacy_state() {
  local state_file="$1"
  local legacy_commit
  local legacy_path
  local legacy_release
  local legacy_status

  [ -f "$state_file" ] && [ ! -L "$state_file" ] \
    || fail "Legacy release state is not one regular file: $state_file"
  validate_exact_state_keys \
    "$state_file" \
    release commit path validated_at_utc validation status
  legacy_release="$(required_state_value "$state_file" "release")"
  legacy_commit="$(required_state_value "$state_file" "commit")"
  legacy_path="$(required_state_value "$state_file" "path")"
  legacy_status="$(required_state_value "$state_file" "status")"
  [ "$legacy_release" = "$CURRENT_RELEASE_ID" ] \
    || fail "Legacy release field does not match current."
  [ "$legacy_path" = "$CURRENT_RELEASE" ] \
    || fail "Legacy path field does not match current."
  [[ "$legacy_commit" =~ ^[0-9a-f]{7,39}$ ]] \
    || fail "Legacy commit field is not an explicit short SHA."
  case "$ACTUAL_COMMIT" in
    "$legacy_commit"*) ;;
    *) fail "Legacy short commit does not prefix the real full commit." ;;
  esac
  [ "$legacy_status" = "production-candidate-core" ] \
    || fail "Legacy status is not the expected production-candidate marker."
}

validate_adopted_state() {
  local state_file="$1"
  local adopted_at
  local legacy_state_sha256
  local legacy_commit_prefix

  validate_exact_state_keys \
    "$state_file" \
    release requested_ref requested_ref_kind commit path adopted_at_utc \
    validation_command validation_exit_code validation_result validation_log \
    validation_log_exit_code launcher_sha256 status provenance \
    legacy_state_sha256 legacy_commit_prefix

  [ "$(required_state_value "$state_file" "release")" = "$CURRENT_RELEASE_ID" ] \
    || fail "Adopted state release does not match current."
  [ "$(required_state_value "$state_file" "requested_ref")" = "$EXPECTED_COMMIT" ] \
    || fail "Adopted state requested ref does not match the expected commit."
  [ "$(required_state_value "$state_file" "requested_ref_kind")" = "legacy-host-adoption" ] \
    || fail "Adopted state has an unexpected requested-ref kind."
  [ "$(required_state_value "$state_file" "commit")" = "$ACTUAL_COMMIT" ] \
    || fail "Adopted state commit does not match current."
  [ "$(required_state_value "$state_file" "path")" = "$CURRENT_RELEASE" ] \
    || fail "Adopted state path does not match current."
  [ "$(required_state_value "$state_file" "launcher_sha256")" = "$CURRENT_LAUNCHER_SHA256" ] \
    || fail "Adopted state launcher does not match current."
  [ "$(required_state_value "$state_file" "status")" = "adopted-legacy-current" ] \
    || fail "Adopted state status is invalid."
  [ "$(required_state_value "$state_file" "provenance")" = "adopted-legacy-current-v1" ] \
    || fail "Adopted state provenance is invalid."
  adopted_at="$(required_state_value "$state_file" "adopted_at_utc")"
  legacy_state_sha256="$(required_state_value "$state_file" "legacy_state_sha256")"
  legacy_commit_prefix="$(required_state_value "$state_file" "legacy_commit_prefix")"
  [[ "$adopted_at" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$ ]] \
    || fail "Adopted state timestamp is invalid."
  [[ "$legacy_state_sha256" =~ ^[0-9a-f]{64}$ ]] \
    || fail "Adopted state legacy-state SHA-256 is invalid."
  [[ "$legacy_commit_prefix" =~ ^[0-9a-f]{7,39}$ ]] \
    || fail "Adopted state legacy commit prefix is invalid."
  case "$ACTUAL_COMMIT" in
    "$legacy_commit_prefix"*) ;;
    *) fail "Adopted state legacy commit prefix does not match current." ;;
  esac
}

validate_complete_adoption() {
  local recorded_legacy_sha256

  validate_adopted_state "$CURRENT_DEPLOYMENT_STATE"
  cmp -s "$CURRENT_DEPLOYMENT_STATE" "$LEGACY_STATE" \
    || fail "Shared release state differs from the adopted current state."
  validate_legacy_state "$CURRENT_LEGACY_STATE"
  [ "$(stat -c '%a' "$CURRENT_LEGACY_STATE")" = "400" ] \
    || fail "Retained legacy release state is not mode 0400."
  recorded_legacy_sha256="$(
    required_state_value "$CURRENT_DEPLOYMENT_STATE" "legacy_state_sha256"
  )"
  [ "$(sha256_file "$CURRENT_LEGACY_STATE")" = "$recorded_legacy_sha256" ] \
    || fail "Retained legacy release state does not match its recorded SHA-256."
  if [ -n "$RECOVERY_DIR" ]; then
    cmp -s "$CURRENT_LEGACY_STATE" "$RECOVERY_DIR/shared-release-state" \
      || fail "Retained legacy release state differs from the pre-adoption snapshot."
  fi
  if [ -n "$TRANSACTION_DIR" ] \
    && [ -f "$TRANSACTION_DIR/RELEASE_STATE.source" ]; then
    cmp -s \
      "$CURRENT_DEPLOYMENT_STATE" \
      "$TRANSACTION_DIR/RELEASE_STATE.source" \
      || fail "Published adopted state differs from the staged state."
  fi
}

MUTATION_STARTED=0
ADOPTION_WORK_DIR=""
TRANSACTION_DIR=""
RECOVERY_DIR=""
RECOVERY_LOG="/dev/null"
RECOVERY_LOG_READY=0
RECOVERY_LOG_FAILED=0
CURRENT_RELEASE=""
CURRENT_RELEASE_ID=""
CURRENT_DEPLOYMENT_DIR=""
CURRENT_DEPLOYMENT_STATE=""
CURRENT_DEPLOYMENT_STATE_NEW=""
CURRENT_LEGACY_STATE=""
CURRENT_LEGACY_STATE_NEW=""
CURRENT_GIT_EXCLUDE=""
DEPLOYMENT_DIR_EXISTED=0
trap on_exit EXIT

case "$APP_ROOT" in
  /*) ;;
  *) fail "HUB_OPTIMUS_APP_ROOT must be an absolute path." ;;
esac
case "$EXPECTED_COMMIT" in
  ""|-h|--help|help)
    usage
    if [ -z "$EXPECTED_COMMIT" ]; then
      exit 2
    fi
    exit 0
    ;;
esac
[ "$#" -eq 1 ] || fail "Exactly one expected full commit SHA is required."
[[ "$EXPECTED_COMMIT" =~ ^[0-9a-f]{40}$ ]] \
  || fail "Expected current commit must be one full lowercase SHA."

exec 9> "$APP_ROOT/shared/deploy.lock"
flock -n 9 || fail "another deploy, rollback, or adoption is active."

[ -L "$APP_ROOT/current" ] || fail "Current release is not a symlink."
CURRENT_RELEASE="$(readlink -f "$APP_ROOT/current")"
case "$CURRENT_RELEASE" in
  "$APP_ROOT/releases/"*) ;;
  *) fail "Current release is outside the managed releases directory: $CURRENT_RELEASE" ;;
esac
[ -d "$CURRENT_RELEASE" ] \
  || fail "Current release directory does not exist: $CURRENT_RELEASE"
CURRENT_RELEASE_ID="$(basename "$CURRENT_RELEASE")"

[ "$(git -C "$CURRENT_RELEASE" rev-parse --is-inside-work-tree)" = "true" ] \
  || fail "Current release is not a Git worktree."
[ "$(git -C "$CURRENT_RELEASE" rev-parse --show-toplevel)" = "$CURRENT_RELEASE" ] \
  || fail "Current release is not the Git worktree root."
[ "$(git -C "$CURRENT_RELEASE" remote get-url origin)" = "$REPO_URL" ] \
  || fail "Current release origin does not match the reviewed repository."
ACTUAL_COMMIT="$(git -C "$CURRENT_RELEASE" rev-parse --verify HEAD)"
[[ "$ACTUAL_COMMIT" =~ ^[0-9a-f]{40}$ ]] \
  || fail "Current release does not resolve to one full commit SHA."
[ "$ACTUAL_COMMIT" = "$EXPECTED_COMMIT" ] \
  || fail "Current full commit does not match the explicit expected commit."
[ -z "$(git -C "$CURRENT_RELEASE" status --porcelain --untracked-files=normal)" ] \
  || fail "Current release worktree is not clean."

CURRENT_LAUNCHER="$CURRENT_RELEASE/ops/ec2/hub-api.sh"
SHARED_LAUNCHER="$APP_ROOT/shared/bin/hub-api"
[ -f "$CURRENT_LAUNCHER" ] && [ ! -L "$CURRENT_LAUNCHER" ] \
  && [ -x "$CURRENT_LAUNCHER" ] \
  || fail "Current release launcher is not one executable regular file."
[ -f "$SHARED_LAUNCHER" ] && [ ! -L "$SHARED_LAUNCHER" ] \
  && [ -x "$SHARED_LAUNCHER" ] \
  || fail "Shared launcher is not one executable regular file."
cmp -s "$CURRENT_LAUNCHER" "$SHARED_LAUNCHER" \
  || fail "Shared launcher does not exactly match the versioned current launcher."
CURRENT_LAUNCHER_SHA256="$(sha256_file "$CURRENT_LAUNCHER")"
[ "$(sha256_file "$SHARED_LAUNCHER")" = "$CURRENT_LAUNCHER_SHA256" ] \
  || fail "Shared launcher SHA-256 does not match current."

CURRENT_MARKER_FILE="$APP_ROOT/shared/current_release"
[ -f "$CURRENT_MARKER_FILE" ] && [ ! -L "$CURRENT_MARKER_FILE" ] \
  || fail "Current-release marker is not one regular file."
[ "$(cat "$CURRENT_MARKER_FILE")" = "$CURRENT_RELEASE_ID" ] \
  || fail "Current-release marker does not match the current symlink."

LEGACY_STATE="$APP_ROOT/shared/RELEASE_STATE"
[ -f "$LEGACY_STATE" ] && [ ! -L "$LEGACY_STATE" ] \
  || fail "Shared release state is not one regular file."
CURRENT_DEPLOYMENT_DIR="$CURRENT_RELEASE/.hub-deployment"
CURRENT_DEPLOYMENT_STATE="$CURRENT_DEPLOYMENT_DIR/RELEASE_STATE"
CURRENT_LEGACY_STATE="$CURRENT_DEPLOYMENT_DIR/LEGACY_RELEASE_STATE"
CURRENT_GIT_EXCLUDE="$CURRENT_RELEASE/.git/info/exclude"
[ -f "$CURRENT_GIT_EXCLUDE" ] && [ ! -L "$CURRENT_GIT_EXCLUDE" ] \
  || fail "Current Git exclude file is not one regular file."

if [ -f "$CURRENT_DEPLOYMENT_STATE" ]; then
  [ -d "$CURRENT_DEPLOYMENT_DIR" ] && [ ! -L "$CURRENT_DEPLOYMENT_DIR" ] \
    || fail "Current deployment directory is not one real directory."
  [ ! -L "$CURRENT_DEPLOYMENT_STATE" ] \
    || fail "Current deployment state must not be a symlink."
  validate_complete_adoption
  echo "[legacy-adoption] Current release is already adopted and exact."
  echo "[legacy-adoption] Commit: $ACTUAL_COMMIT"
  echo "[legacy-adoption] Launcher SHA-256: $CURRENT_LAUNCHER_SHA256"
  exit 0
fi
[ ! -e "$CURRENT_DEPLOYMENT_DIR" ] \
  || fail "Current deployment directory exists without an adopted release state."

validate_legacy_state "$LEGACY_STATE"
LEGACY_COMMIT="$(required_state_value "$LEGACY_STATE" "commit")"
LEGACY_STATE_SHA256="$(sha256_file "$LEGACY_STATE")"

ADOPTION_WORK_DIR="$(
  mktemp -d "$APP_ROOT/shared/legacy-adoption.$(date -u +%Y%m%dT%H%M%SZ).XXXXXX"
)"
TRANSACTION_DIR="$ADOPTION_WORK_DIR/transaction"
RECOVERY_DIR="$ADOPTION_WORK_DIR/pre-adoption-state"
RECOVERY_LOG="${HUB_OPTIMUS_TEST_LEGACY_ADOPTION_RECOVERY_LOG_PATH:-$ADOPTION_WORK_DIR/recovery.log}"
CURRENT_DEPLOYMENT_STATE_NEW="$CURRENT_DEPLOYMENT_DIR/RELEASE_STATE.new.$(basename "$ADOPTION_WORK_DIR")"
CURRENT_LEGACY_STATE_NEW="$CURRENT_DEPLOYMENT_DIR/LEGACY_RELEASE_STATE.new.$(basename "$ADOPTION_WORK_DIR")"
mkdir -p "$TRANSACTION_DIR" "$RECOVERY_DIR"
chmod 0700 "$ADOPTION_WORK_DIR" "$TRANSACTION_DIR" "$RECOVERY_DIR"

cat > "$TRANSACTION_DIR/RELEASE_STATE.source" <<STATE
release=$CURRENT_RELEASE_ID
requested_ref=$EXPECTED_COMMIT
requested_ref_kind=legacy-host-adoption
commit=$ACTUAL_COMMIT
path=$CURRENT_RELEASE
adopted_at_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)
validation_command=not-run-during-legacy-adoption
validation_exit_code=not-run
validation_result=legacy validation claim not re-attested; original state retained by SHA-256
validation_log=not-applicable
validation_log_exit_code=not-run
launcher_sha256=$CURRENT_LAUNCHER_SHA256
status=adopted-legacy-current
provenance=adopted-legacy-current-v1
legacy_state_sha256=$LEGACY_STATE_SHA256
legacy_commit_prefix=$LEGACY_COMMIT
STATE
install -m 0600 \
  "$TRANSACTION_DIR/RELEASE_STATE.source" \
  "$TRANSACTION_DIR/current-RELEASE_STATE"
install -m 0644 \
  "$TRANSACTION_DIR/RELEASE_STATE.source" \
  "$TRANSACTION_DIR/shared-RELEASE_STATE"
install -m 0400 \
  "$LEGACY_STATE" \
  "$TRANSACTION_DIR/LEGACY_RELEASE_STATE"

cp -a -- "$CURRENT_GIT_EXCLUDE" "$TRANSACTION_DIR/git-exclude"
EXCLUDE_COUNT="$(
  grep -c '^\.hub-deployment/$' "$TRANSACTION_DIR/git-exclude" 2>/dev/null \
    || true
)"
[ "$EXCLUDE_COUNT" -le 1 ] \
  || fail "Current Git exclude has duplicate .hub-deployment entries."
if [ "$EXCLUDE_COUNT" -eq 0 ]; then
  printf '.hub-deployment/\n' >> "$TRANSACTION_DIR/git-exclude"
fi

snapshot_item "$APP_ROOT/current" "current-symlink"
snapshot_item "$SHARED_LAUNCHER" "shared-launcher"
snapshot_item "$APP_ROOT/shared/previous_release" "previous-release-pointer"
snapshot_item "$CURRENT_MARKER_FILE" "current-release-marker"
snapshot_item "$LEGACY_STATE" "shared-release-state"
snapshot_item "$CURRENT_DEPLOYMENT_STATE" "current-release-state"
snapshot_item "$CURRENT_LEGACY_STATE" "legacy-release-state"
snapshot_item "$CURRENT_GIT_EXCLUDE" "current-git-exclude"

MUTATION_STARTED=1

echo "[legacy-adoption] Publishing Git exclude boundary"
mv -Tf "$TRANSACTION_DIR/git-exclude" "$CURRENT_GIT_EXCLUDE"
inject_test_failure "git-exclude"

echo "[legacy-adoption] Creating per-release deployment state"
mkdir -p "$CURRENT_DEPLOYMENT_DIR"
chmod 0700 "$CURRENT_DEPLOYMENT_DIR"
inject_test_failure "deployment-dir"
mv -Tf \
  "$TRANSACTION_DIR/LEGACY_RELEASE_STATE" \
  "$CURRENT_LEGACY_STATE_NEW"
mv -Tf "$CURRENT_LEGACY_STATE_NEW" "$CURRENT_LEGACY_STATE"
inject_test_failure "legacy-state-evidence"
install -m 0600 \
  "$TRANSACTION_DIR/current-RELEASE_STATE" \
  "$CURRENT_DEPLOYMENT_STATE_NEW"
mv -Tf "$CURRENT_DEPLOYMENT_STATE_NEW" "$CURRENT_DEPLOYMENT_STATE"
inject_test_failure "release-state"

echo "[legacy-adoption] Publishing exact shared release state"
mv -Tf \
  "$TRANSACTION_DIR/shared-RELEASE_STATE" \
  "$APP_ROOT/shared/RELEASE_STATE"
inject_test_failure "shared-release-state"

if [ \
  "${HUB_OPTIMUS_TEST_LEGACY_ADOPTION_CORRUPT_BEFORE_POSTVALIDATE:-}" \
  = "shared-release-state" \
]; then
  printf 'test_corruption=1\n' >> "$APP_ROOT/shared/RELEASE_STATE"
fi
validate_complete_adoption

echo "[legacy-adoption] Adopted current legacy release."
echo "[legacy-adoption] Release: $CURRENT_RELEASE"
echo "[legacy-adoption] Commit: $ACTUAL_COMMIT"
echo "[legacy-adoption] Launcher SHA-256: $CURRENT_LAUNCHER_SHA256"
echo "[legacy-adoption] Done"

MUTATION_STARTED=0
if ! rm -rf -- "$ADOPTION_WORK_DIR"; then
  echo "[legacy-adoption:warning] Could not remove completed adoption snapshot." >&2
fi
