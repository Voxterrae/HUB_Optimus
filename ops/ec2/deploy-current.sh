#!/usr/bin/env bash
set -euo pipefail

APP_ROOT="${HUB_OPTIMUS_APP_ROOT:-/opt/hub-optimus}"
REPO_URL="${HUB_OPTIMUS_REPO_URL:-https://github.com/Voxterrae/HUB_Optimus.git}"
DEPLOY_REF="${1:-}"
VALIDATION_COMMAND_TEXT="python -m pytest -q"

usage() {
  cat <<USAGE
HUB_Optimus explicit release deploy

Usage:
  deploy-current <full-commit-sha-or-tag>

The requested ref must be a full 40-character commit SHA or an exact tag name.
Branches and implicit repository HEAD are not deployment inputs.
USAGE
}

fail() {
  echo "[deploy:error] $*" >&2
  exit 1
}

sha256_file() {
  local path="$1"
  local digest

  digest="$(sha256sum -- "$path" | awk '{print $1}')"
  if [[ ! "$digest" =~ ^[0-9a-f]{64}$ ]]; then
    fail "could not calculate SHA-256 for $path"
  fi
  printf '%s\n' "$digest"
}

state_value() {
  local state_file="$1"
  local key="$2"
  if [ ! -f "$state_file" ]; then
    return 0
  fi
  sed -n "s/^${key}=//p" "$state_file" 2>/dev/null | head -n 1
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

validate_release_state() {
  local previous="$1"
  local state_file="$2"
  local actual_commit="$3"
  local actual_launcher_sha256="$4"
  local recorded_release
  local recorded_commit
  local recorded_path
  local recorded_launcher_sha256

  [ -f "$state_file" ] \
    || fail "Rollback target has no deployment state: $state_file"

  recorded_release="$(required_state_value "$state_file" "release")"
  recorded_commit="$(required_state_value "$state_file" "commit")"
  recorded_path="$(required_state_value "$state_file" "path")"
  recorded_launcher_sha256="$(
    state_value "$state_file" "launcher_sha256"
  )"
  if [ "$(grep -c '^launcher_sha256=' "$state_file" 2>/dev/null || true)" -gt 1 ]; then
    fail "$state_file contains duplicate launcher_sha256 fields."
  fi

  [ "$recorded_release" = "$(basename "$previous")" ] \
    || fail "Rollback target release does not match its deployment state."
  [ "$recorded_commit" = "$actual_commit" ] \
    || fail "Rollback target commit does not match its deployment state."
  [ "$recorded_path" = "$previous" ] \
    || fail "Rollback target path does not match its deployment state."

  if [ -n "$recorded_launcher_sha256" ] \
    && [ "$recorded_launcher_sha256" != "$actual_launcher_sha256" ]; then
    fail "Rollback target launcher does not match its deployment state."
  fi
}

prepare_previous_release_state() {
  local previous="$1"
  local previous_state="$previous/.hub-deployment/RELEASE_STATE"
  local shared_state="$APP_ROOT/shared/RELEASE_STATE"
  local previous_release
  local previous_commit
  local previous_launcher_sha256
  local source_state
  local recorded_launcher_sha256

  previous_release="$(basename "$previous")"
  previous_commit="$(git -C "$previous" rev-parse --verify HEAD)"
  [[ "$previous_commit" =~ ^[0-9a-f]{40}$ ]] \
    || fail "Rollback target does not resolve to one full commit SHA."

  [ -f "$previous/ops/ec2/hub-api.sh" ] \
    || fail "Rollback target has no hub-api launcher: $previous/ops/ec2/hub-api.sh"
  previous_launcher_sha256="$(sha256_file "$previous/ops/ec2/hub-api.sh")"

  if [ -f "$previous_state" ]; then
    source_state="$previous_state"
  else
    source_state="$shared_state"
  fi

  validate_release_state \
    "$previous" \
    "$source_state" \
    "$previous_commit" \
    "$previous_launcher_sha256"

  PREVIOUS_STATE_PATH="$previous_state"
  recorded_launcher_sha256="$(
    state_value "$source_state" "launcher_sha256"
  )"
  if [ "$source_state" = "$previous_state" ] \
    && [ -n "$recorded_launcher_sha256" ]; then
    PREVIOUS_STATE_INSTALL_SOURCE=""
    return
  fi

  PREVIOUS_STATE_INSTALL_SOURCE="$DEPLOYMENT_DIR/PREVIOUS_RELEASE_STATE"
  sed '/^launcher_sha256=/d' \
    "$source_state" \
    > "$PREVIOUS_STATE_INSTALL_SOURCE"
  printf 'launcher_sha256=%s\n' "$previous_launcher_sha256" \
    >> "$PREVIOUS_STATE_INSTALL_SOURCE"
  if [ "$source_state" = "$shared_state" ]; then
    printf 'provenance=adopted-pre-1832\n' \
      >> "$PREVIOUS_STATE_INSTALL_SOURCE"
  fi
  chmod 0600 "$PREVIOUS_STATE_INSTALL_SOURCE"
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
    echo "[deploy:recovery:error] Refusing to replace directory: $target" >&2
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
      echo "[deploy:recovery:error] Invalid snapshot marker for $target" >&2
      return 1
      ;;
  esac
}

recover_predeploy_state() {
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
    "[deploy:recovery] Restoring exact pre-deploy operational state" \
    allow-missing-log
  if [ -n "$PREVIOUS_STATE_PATH" ]; then
    restore_item "$PREVIOUS_STATE_PATH" "previous-release-state" \
      || state_restore_failed=1
  fi
  restore_item "$APP_ROOT/shared/bin/hub-api" "shared-launcher" \
    || state_restore_failed=1
  restore_item "$APP_ROOT/shared/RELEASE_STATE" "shared-release-state" \
    || state_restore_failed=1
  restore_item "$APP_ROOT/shared/current_release" "current-release-marker" \
    || state_restore_failed=1
  restore_item "$APP_ROOT/shared/previous_release" "previous-release-pointer" \
    || state_restore_failed=1
  restore_item "$APP_ROOT/current" "current-symlink" \
    || state_restore_failed=1
  rm -f -- "$CURRENT_NEW" || state_restore_failed=1
  if [ -n "$PREVIOUS_STATE_NEW" ]; then
    rm -f -- "$PREVIOUS_STATE_NEW" || state_restore_failed=1
  fi

  if [ "$state_restore_failed" -eq 0 ] \
    && [ "$RECOVERY_LOG_FAILED" -eq 0 ] \
    && recovery_note \
      "[deploy:recovery] Pre-deploy operational state restored" \
      require-log; then
    recovery_succeeded=1
  elif [ "$state_restore_failed" -eq 0 ]; then
    recovery_note \
      "[deploy:recovery:error] Operational state restored, but recovery evidence could not be recorded; treating recovery as failed" \
      allow-missing-log
  else
    recovery_note \
      "[deploy:recovery:error] Recovery was incomplete; inspect the retained snapshot" \
      allow-missing-log
  fi

  if [ "$RECOVERY_LOG_READY" -eq 1 ]; then
    exec 8>&-
  fi
  set -e
  [ "$recovery_succeeded" -eq 1 ]
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

on_exit() {
  local exit_code="$?"

  trap - EXIT
  if [ "$exit_code" -ne 0 ] && [ "$MUTATION_STARTED" -eq 1 ]; then
    recover_predeploy_state || exit_code=1
  fi
  exit "$exit_code"
}

inject_test_failure() {
  local stage="$1"

  if [ "${HUB_OPTIMUS_TEST_FAIL_AFTER_MUTATION:-}" = "$stage" ]; then
    fail "injected test failure after mutation stage: $stage"
  fi
}

MUTATION_STARTED=0
PREVIOUS_STATE_PATH=""
PREVIOUS_STATE_INSTALL_SOURCE=""
RECOVERY_DIR=""
RECOVERY_LOG="/dev/null"
RECOVERY_LOG_READY=0
RECOVERY_LOG_FAILED=0
CURRENT_NEW=""
PREVIOUS_STATE_NEW=""
trap on_exit EXIT

case "$APP_ROOT" in
  /*) ;;
  *) fail "HUB_OPTIMUS_APP_ROOT must be an absolute path." ;;
esac

case "$DEPLOY_REF" in
  ""|-h|--help|help)
    usage
    if [ -z "$DEPLOY_REF" ]; then
      exit 2
    fi
    exit 0
    ;;
esac

if [ "$#" -ne 1 ]; then
  usage >&2
  fail "exactly one full commit SHA or tag is required."
fi

if [[ "$DEPLOY_REF" =~ ^[0-9a-fA-F]{40}$ ]]; then
  REF_KIND="commit"
  FETCH_REF="$DEPLOY_REF"
else
  REF_KIND="tag"
  git check-ref-format "refs/tags/$DEPLOY_REF" >/dev/null 2>&1 \
    || fail "invalid tag name: $DEPLOY_REF"
  FETCH_REF="refs/tags/$DEPLOY_REF"
fi

echo "[deploy] Starting HUB_Optimus deploy"
echo "[deploy] Requested $REF_KIND: $DEPLOY_REF"

mkdir -p "$APP_ROOT/releases" "$APP_ROOT/shared/logs" "$APP_ROOT/shared/bin"
exec 9> "$APP_ROOT/shared/deploy.lock"
flock -n 9 || fail "another deploy or rollback operation is active."
RELEASE_DIR="$(mktemp -d "$APP_ROOT/releases/$(date -u +%Y%m%dT%H%M%SZ).XXXXXX")"
RELEASE_ID="$(basename "$RELEASE_DIR")"
DEPLOYMENT_DIR="$RELEASE_DIR/.hub-deployment"
DEPLOYMENT_STATE="$DEPLOYMENT_DIR/RELEASE_STATE"
VALIDATION_LOG="$DEPLOYMENT_DIR/validation.log"

echo "[deploy] Release: $RELEASE_ID"
echo "[deploy] Fetching explicit selected ref"
git init --quiet "$RELEASE_DIR"
git -C "$RELEASE_DIR" remote add origin "$REPO_URL"
git -C "$RELEASE_DIR" fetch --quiet --depth 1 origin "$FETCH_REF"

RESOLVED_COMMIT="$(
  git -C "$RELEASE_DIR" rev-parse --verify 'FETCH_HEAD^{commit}'
)"

if [ "$REF_KIND" = "commit" ]; then
  NORMALIZED_REF="$(printf '%s' "$DEPLOY_REF" | tr 'A-F' 'a-f')"
  if [ "$RESOLVED_COMMIT" != "$NORMALIZED_REF" ]; then
    fail "fetched commit does not match requested SHA."
  fi
fi

git -C "$RELEASE_DIR" checkout --quiet --detach "$RESOLVED_COMMIT"

echo "[deploy] Resolved commit: $RESOLVED_COMMIT"
echo "[deploy] Verifying hub-api launcher source"
if [ ! -f "$RELEASE_DIR/ops/ec2/hub-api.sh" ]; then
  fail "Missing hub-api launcher source: $RELEASE_DIR/ops/ec2/hub-api.sh"
fi
CANDIDATE_LAUNCHER_SHA256="$(
  sha256_file "$RELEASE_DIR/ops/ec2/hub-api.sh"
)"
echo "[deploy] Candidate launcher SHA-256: $CANDIDATE_LAUNCHER_SHA256"

echo "[deploy] Creating venv"
cd "$RELEASE_DIR"
python3 -m venv .venv
source .venv/bin/activate

echo "[deploy] Installing dependencies"
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt

mkdir -p "$DEPLOYMENT_DIR"
chmod 0700 "$DEPLOYMENT_DIR"

echo "[deploy] Running validation: $VALIDATION_COMMAND_TEXT"
set +e
python -m pytest -q 2>&1 | tee "$VALIDATION_LOG"
VALIDATION_PIPE_STATUS=("${PIPESTATUS[@]}")
set -e
VALIDATION_EXIT_CODE="${VALIDATION_PIPE_STATUS[0]}"
VALIDATION_LOG_EXIT_CODE="${VALIDATION_PIPE_STATUS[1]}"

deactivate

VALIDATION_RESULT="$(
  awk 'NF { result=$0 } END { print result == "" ? "no output" : result }' \
    "$VALIDATION_LOG"
)"

if [ "$VALIDATION_EXIT_CODE" -eq 0 ] \
  && [ "$VALIDATION_LOG_EXIT_CODE" -eq 0 ]; then
  RELEASE_STATUS="production-candidate-core"
else
  RELEASE_STATUS="validation-failed"
fi

cat > "$DEPLOYMENT_STATE" <<STATE
release=$RELEASE_ID
requested_ref=$DEPLOY_REF
requested_ref_kind=$REF_KIND
commit=$RESOLVED_COMMIT
path=$RELEASE_DIR
validated_at_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)
validation_command=$VALIDATION_COMMAND_TEXT
validation_exit_code=$VALIDATION_EXIT_CODE
validation_result=$VALIDATION_RESULT
validation_log=$VALIDATION_LOG
validation_log_exit_code=$VALIDATION_LOG_EXIT_CODE
launcher_sha256=$CANDIDATE_LAUNCHER_SHA256
status=$RELEASE_STATUS
STATE
chmod 0600 "$DEPLOYMENT_STATE" "$VALIDATION_LOG"

echo "[deploy] Hiding local deployment files from git status"
for excluded_path in ".venv/" ".hub-deployment/"; do
  grep -qxF "$excluded_path" "$RELEASE_DIR/.git/info/exclude" \
    || echo "$excluded_path" >> "$RELEASE_DIR/.git/info/exclude"
done

if [ "$VALIDATION_LOG_EXIT_CODE" -ne 0 ]; then
  fail "validation output could not be recorded (tee exit $VALIDATION_LOG_EXIT_CODE)."
fi

if [ "$VALIDATION_EXIT_CODE" -ne 0 ]; then
  fail "validation failed (exit $VALIDATION_EXIT_CODE): $VALIDATION_RESULT"
fi

PREVIOUS=""
if [ -L "$APP_ROOT/current" ]; then
  PREVIOUS="$(readlink -f "$APP_ROOT/current")"
  case "$PREVIOUS" in
    "$APP_ROOT/releases/"*) ;;
    *) fail "Rollback target is outside the managed releases directory: $PREVIOUS" ;;
  esac
  [ -d "$PREVIOUS" ] \
    || fail "Rollback target directory does not exist: $PREVIOUS"
  prepare_previous_release_state "$PREVIOUS"
  echo "[deploy] Previous release: $PREVIOUS"
elif [ -e "$APP_ROOT/current" ]; then
  fail "Current exists but is not a symlink: $APP_ROOT/current"
else
  echo "[deploy] No previous release detected"
fi

TRANSACTION_DIR="$DEPLOYMENT_DIR/transaction"
RECOVERY_DIR="$DEPLOYMENT_DIR/pre-deploy-state"
RECOVERY_LOG="${HUB_OPTIMUS_TEST_RECOVERY_LOG_PATH:-$DEPLOYMENT_DIR/recovery.log}"
CURRENT_NEW="$APP_ROOT/current.new.$RELEASE_ID"
mkdir -p "$TRANSACTION_DIR" "$RECOVERY_DIR"
chmod 0700 "$TRANSACTION_DIR" "$RECOVERY_DIR"

install -m 0755 \
  "$RELEASE_DIR/ops/ec2/hub-api.sh" \
  "$TRANSACTION_DIR/hub-api"
install -m 0644 "$DEPLOYMENT_STATE" "$TRANSACTION_DIR/RELEASE_STATE"
printf '%s\n' "$RELEASE_ID" > "$TRANSACTION_DIR/current_release"
if [ -n "$PREVIOUS" ]; then
  printf '%s\n' "$PREVIOUS" > "$TRANSACTION_DIR/previous_release"
fi

snapshot_item "$APP_ROOT/current" "current-symlink"
snapshot_item "$APP_ROOT/shared/bin/hub-api" "shared-launcher"
snapshot_item "$APP_ROOT/shared/RELEASE_STATE" "shared-release-state"
snapshot_item "$APP_ROOT/shared/current_release" "current-release-marker"
snapshot_item "$APP_ROOT/shared/previous_release" "previous-release-pointer"
if [ -n "$PREVIOUS_STATE_PATH" ]; then
  snapshot_item "$PREVIOUS_STATE_PATH" "previous-release-state"
fi

MUTATION_STARTED=1

if [ -n "$PREVIOUS_STATE_INSTALL_SOURCE" ]; then
  echo "[deploy] Completing rollback-target deployment state"
  mkdir -p "$(dirname "$PREVIOUS_STATE_PATH")"
  chmod 0700 "$(dirname "$PREVIOUS_STATE_PATH")"
  PREVIOUS_STATE_NEW="$PREVIOUS_STATE_PATH.new.$RELEASE_ID"
  install -m 0600 \
    "$PREVIOUS_STATE_INSTALL_SOURCE" \
    "$PREVIOUS_STATE_NEW"
  mv -Tf \
    "$PREVIOUS_STATE_NEW" \
    "$PREVIOUS_STATE_PATH"
  inject_test_failure "previous-release-state"
fi

if [ -n "$PREVIOUS" ]; then
  echo "[deploy] Recording rollback target"
  mv -Tf \
    "$TRANSACTION_DIR/previous_release" \
    "$APP_ROOT/shared/previous_release"
  inject_test_failure "previous-release"
fi

echo "[deploy] Switching current symlink"
ln -s "$RELEASE_DIR" "$CURRENT_NEW"
mv -Tf "$CURRENT_NEW" "$APP_ROOT/current"
inject_test_failure "current"

echo "[deploy] Syncing hub-api launcher"
mv -Tf "$TRANSACTION_DIR/hub-api" "$APP_ROOT/shared/bin/hub-api"
inject_test_failure "launcher"

echo "[deploy] Publishing release state"
mv -Tf \
  "$TRANSACTION_DIR/RELEASE_STATE" \
  "$APP_ROOT/shared/RELEASE_STATE"
inject_test_failure "release-state"

echo "[deploy] Publishing current-release marker"
mv -Tf \
  "$TRANSACTION_DIR/current_release" \
  "$APP_ROOT/shared/current_release"
inject_test_failure "current-release"

cd "$APP_ROOT/current"

echo "[deploy] Current release:"
readlink -f "$APP_ROOT/current"

echo "[deploy] Git commit:"
git rev-parse HEAD

echo "[deploy] Git status:"
git status --short

echo "[deploy] Release state:"
cat "$APP_ROOT/shared/RELEASE_STATE"

echo "[deploy] Done"
MUTATION_STARTED=0
if ! rm -rf -- "$RECOVERY_DIR" "$TRANSACTION_DIR"; then
  echo "[deploy:warning] Could not remove completed transaction snapshot." >&2
fi
