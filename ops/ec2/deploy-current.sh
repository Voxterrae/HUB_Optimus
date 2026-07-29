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

state_value() {
  local state_file="$1"
  local key="$2"
  if [ ! -f "$state_file" ]; then
    return 0
  fi
  sed -n "s/^${key}=//p" "$state_file" 2>/dev/null | head -n 1
}

write_previous_release_state() {
  local previous="$1"
  local previous_state="$previous/.hub-deployment/RELEASE_STATE"

  if [ -f "$previous_state" ]; then
    return
  fi

  local previous_release
  local previous_commit
  local previous_validated_at
  local previous_validation
  local previous_status

  previous_release="$(basename "$previous")"
  previous_commit="$(git -C "$previous" rev-parse HEAD)"
  previous_validated_at="$(
    state_value "$APP_ROOT/shared/RELEASE_STATE" "validated_at_utc"
  )"
  previous_validation="$(
    state_value "$APP_ROOT/shared/RELEASE_STATE" "validation"
  )"
  previous_status="$(
    state_value "$APP_ROOT/shared/RELEASE_STATE" "status"
  )"

  mkdir -p "$previous/.hub-deployment"
  chmod 0700 "$previous/.hub-deployment"
  if [ -d "$previous/.git/info" ]; then
    grep -qxF ".hub-deployment/" "$previous/.git/info/exclude" \
      || echo ".hub-deployment/" >> "$previous/.git/info/exclude"
  fi

  cat > "$previous_state" <<STATE
release=$previous_release
requested_ref=unrecorded-pre-1764
requested_ref_kind=legacy
commit=$previous_commit
path=$previous
validated_at_utc=${previous_validated_at:-unknown}
validation_command=unrecorded-pre-1764
validation_exit_code=unknown
validation_result=unverified legacy metadata: ${previous_validation:-not recorded}
status=${previous_status:-legacy-release}
provenance=adopted-pre-1764
STATE
  chmod 0600 "$previous_state"
}

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

echo "[deploy] Verifying hub-api launcher source"
if [ ! -f "$RELEASE_DIR/ops/ec2/hub-api.sh" ]; then
  echo "[deploy:error] Missing hub-api launcher source: $RELEASE_DIR/ops/ec2/hub-api.sh" >&2
  exit 1
fi

if [ -L "$APP_ROOT/current" ]; then
  PREVIOUS="$(readlink -f "$APP_ROOT/current")"
  write_previous_release_state "$PREVIOUS"
  echo "$PREVIOUS" > "$APP_ROOT/shared/previous_release"
  echo "[deploy] Previous release: $PREVIOUS"
else
  echo "[deploy] No previous release detected"
fi

echo "[deploy] Switching current symlink"
ln -sfn "$RELEASE_DIR" "$APP_ROOT/current.new"
mv -Tf "$APP_ROOT/current.new" "$APP_ROOT/current"

echo "[deploy] Syncing hub-api launcher"
install -m 0755 "$APP_ROOT/current/ops/ec2/hub-api.sh" "$APP_ROOT/shared/bin/hub-api"

install -m 0644 "$DEPLOYMENT_STATE" "$APP_ROOT/shared/RELEASE_STATE.new"
mv -Tf "$APP_ROOT/shared/RELEASE_STATE.new" "$APP_ROOT/shared/RELEASE_STATE"
echo "$RELEASE_ID" > "$APP_ROOT/shared/current_release"

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
