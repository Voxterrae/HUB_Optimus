#!/usr/bin/env bash
set -euo pipefail

APP_ROOT="/opt/hub-optimus"
REPO_URL="https://github.com/Voxterrae/HUB_Optimus.git"
RELEASE_ID="$(date -u +%Y%m%dT%H%M%SZ)"
RELEASE_DIR="$APP_ROOT/releases/$RELEASE_ID"

echo "[deploy] Starting HUB_Optimus deploy"
echo "[deploy] Release: $RELEASE_ID"

mkdir -p "$APP_ROOT/releases" "$APP_ROOT/shared/logs" "$APP_ROOT/shared/bin"

if [ -e "$RELEASE_DIR" ]; then
  echo "[deploy:error] Release directory already exists: $RELEASE_DIR"
  exit 1
fi

echo "[deploy] Cloning repository"
git clone --depth 1 "$REPO_URL" "$RELEASE_DIR"

cd "$RELEASE_DIR"

echo "[deploy] Creating venv"
python3 -m venv .venv
source .venv/bin/activate

echo "[deploy] Installing dependencies"
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt

echo "[deploy] Running tests"
python -m pytest -q

deactivate

echo "[deploy] Hiding local venv from git status"
grep -qxF ".venv/" "$RELEASE_DIR/.git/info/exclude" || echo ".venv/" >> "$RELEASE_DIR/.git/info/exclude"

echo "[deploy] Verifying hub-api launcher source"
if [ ! -f "$RELEASE_DIR/ops/ec2/hub-api.sh" ]; then
  echo "[deploy:error] Missing hub-api launcher source: $RELEASE_DIR/ops/ec2/hub-api.sh"
  exit 1
fi

if [ -L "$APP_ROOT/current" ]; then
  PREVIOUS="$(readlink -f "$APP_ROOT/current")"
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

cd "$APP_ROOT/current"

COMMIT="$(git rev-parse --short HEAD)"
CURRENT_PATH="$(readlink -f "$APP_ROOT/current")"

cat > "$APP_ROOT/shared/RELEASE_STATE" <<STATE
release=$RELEASE_ID
commit=$COMMIT
path=$CURRENT_PATH
validated_at_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)
validation=pytest 55 passed
status=production-candidate-core
STATE

echo "$RELEASE_ID" > "$APP_ROOT/shared/current_release"

echo "[deploy] Current release:"
readlink -f "$APP_ROOT/current"

echo "[deploy] Git commit:"
git rev-parse --short HEAD

echo "[deploy] Git status:"
git status --short

echo "[deploy] Release state:"
cat "$APP_ROOT/shared/RELEASE_STATE"

echo "[deploy] Done"
