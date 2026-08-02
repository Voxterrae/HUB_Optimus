# Issue #1831 localhost intake runbook boundary

This document defines the reviewed shape of the replacement host runbook after
issue #1832. It is not an authorization to deploy its current repository
checkout. Issue #1831 must first be repinned to the exact merged `main` commit,
and the operator must replace `<fresh-reviewed-main-sha>` below with that full
lowercase 40-character SHA.

The operation remains local to the existing EC2 release layout. It does not
change DNS, TLS, nginx, a Security Group, public routing, providers, or the
host's reboot state.

## 1. Retain the reviewed tools checkout

The reviewed checkout must live under the managed shared directory until the
operation and any explicit rollback are complete. Do not put it behind an
`EXIT` trap that deletes it.

```bash
set -euo pipefail

TARGET_SHA='<fresh-reviewed-main-sha>'
LEGACY_CURRENT_SHA='9d6771994095e4fc04e8fdbf2caa644ccb002ab1'
REPO_URL='https://github.com/Voxterrae/HUB_Optimus.git'
APP_ROOT='/opt/hub-optimus'
REFERENCE_URL='https://amp.dw.com/es/los-grandes-capos-mexicanos-presos-en-estados-unidos/a-77973174'
TOOLS_ROOT="$APP_ROOT/shared/reviewed-tools/$TARGET_SHA"

[[ "$TARGET_SHA" =~ ^[0-9a-f]{40}$ ]]
REQUIRED_COMMANDS=(
  awk basename bash cat chmod cmp cp curl date df dirname flock free git grep
  head install ln mkdir mktemp mv python3 readlink rm rmdir sed sha256sum stat
  sudo systemctl tee timeout tr
)
for command_name in "${REQUIRED_COMMANDS[@]}"; do
  command -v "$command_name" >/dev/null
done
sudo -n true
install -d -m 0700 "$APP_ROOT/shared/reviewed-tools"
test ! -e "$TOOLS_ROOT"
git init --quiet "$TOOLS_ROOT"
git -C "$TOOLS_ROOT" remote add origin "$REPO_URL"
git -C "$TOOLS_ROOT" fetch --quiet --depth 1 origin "$TARGET_SHA"
git -C "$TOOLS_ROOT" checkout --quiet --detach FETCH_HEAD
test "$(git -C "$TOOLS_ROOT" rev-parse --verify HEAD)" = "$TARGET_SHA"

bash -n "$TOOLS_ROOT"/ops/ec2/*.sh
python3 -m py_compile "$TOOLS_ROOT/ops/ec2/intake-smoke-evidence.py"
```

Removal of this retained checkout is a separate post-operation cleanup choice;
failure handling never depends on recreating deleted tools.

## 2. Explicitly adopt the exact legacy current release

The confirmed legacy host state predates per-release deployment provenance. It
must be adopted before the strict preflight. Do not edit either release-state
file, the launcher, or a symlink by hand. The command is deliberately bound to
the known full current commit rather than the legacy state's short SHA:

```bash
HUB_OPTIMUS_APP_ROOT="$APP_ROOT" \
HUB_OPTIMUS_REPO_URL="$REPO_URL" \
  bash "$TOOLS_ROOT/ops/ec2/adopt-legacy-current.sh" \
    "$LEGACY_CURRENT_SHA"

ADOPTED_CURRENT="$(readlink -f "$APP_ROOT/current")"
ADOPTED_STATE="$ADOPTED_CURRENT/.hub-deployment/RELEASE_STATE"
LEGACY_EVIDENCE="$ADOPTED_CURRENT/.hub-deployment/LEGACY_RELEASE_STATE"

test "$(git -C "$ADOPTED_CURRENT" rev-parse --verify HEAD)" \
  = "$LEGACY_CURRENT_SHA"
cmp -s "$ADOPTED_CURRENT/ops/ec2/hub-api.sh" \
  "$APP_ROOT/shared/bin/hub-api"
cmp -s "$ADOPTED_STATE" "$APP_ROOT/shared/RELEASE_STATE"
test "$(stat -c '%a' "$LEGACY_EVIDENCE")" = '400'
test "$(sha256sum -- "$LEGACY_EVIDENCE" | awk '{print $1}')" \
  = "$(sed -n 's/^legacy_state_sha256=//p' "$ADOPTED_STATE")"
```

Adoption validates the managed symlink, exact repository origin, clean release
checkout, full commit, marker, and byte-identical versioned/shared launcher. It
does not re-assert the old `pytest 55 passed` claim. Instead it preserves the
original legacy state byte-for-byte as mode-`0400` evidence, records its
SHA-256 and short-commit prefix in a new full-SHA state, and postvalidates that
the per-release and shared states are identical before committing success.

The command is idempotent only when that complete evidence bundle remains
exact. A failure after mutation begins restores the pre-adoption state and
retains its snapshot and recovery log under `shared/legacy-adoption.*`. Stop
and inspect that evidence; do not repair or retry by hand.

## 3. Fail-closed host preflight

Run the versioned preflight before deployment:

```bash
HUB_OPTIMUS_APP_ROOT="$APP_ROOT" \
HUB_OPTIMUS_REPO_URL="$REPO_URL" \
  bash "$TOOLS_ROOT/ops/ec2/preflight-deploy.sh" \
    "$TARGET_SHA" \
    "$REFERENCE_URL"
```

The preflight stops unless all of the following are true:

- the target is one explicit full commit SHA;
- required tooling and `sudo -n` are available;
- `hub-api.service` is active;
- `current` has exact shared/per-release state parity and a launcher bound to
  its clean, managed repository checkout;
- any historical `previous_release` with deployment state is fully attested;
  an older pointer without per-release state is inventoried as
  `legacy-unattested-not-deploy-rollback-target` and is never trusted as the
  rollback target for this deploy (the adopted current release becomes that
  target when deployment switches);
- the current, historical previous, and shared launcher SHA-256 values and the
  previous-state status are printed;
- at least 3 GiB disk, 50,000 inodes, and 512 MiB available RAM remain;
- one-minute load is no greater than 2.00;
- GitHub and the HTTPS reference URL are reachable from the host.

Do not override a failed threshold or identity check inside the same operation.

## 4. Exact-SHA deploy and review

```bash
HUB_OPTIMUS_APP_ROOT="$APP_ROOT" \
HUB_OPTIMUS_REPO_URL="$REPO_URL" \
  bash "$TOOLS_ROOT/ops/ec2/deploy-current.sh" "$TARGET_SHA"

DEPLOYED_RELEASE="$(readlink -f "$APP_ROOT/current")"
test "$(git -C "$DEPLOYED_RELEASE" rev-parse --verify HEAD)" = "$TARGET_SHA"
DEPLOYED_RELEASE_STATE="$DEPLOYED_RELEASE/.hub-deployment/RELEASE_STATE"
cmp -s "$DEPLOYED_RELEASE_STATE" "$APP_ROOT/shared/RELEASE_STATE"

python3 - "$APP_ROOT" "$DEPLOYED_RELEASE" "$TARGET_SHA" <<'PY_DEPLOY_STATE'
import hashlib
import json
import re
import stat
import sys
from pathlib import Path

app_root = Path(sys.argv[1]).resolve()
deployed = Path(sys.argv[2]).resolve()
target = sys.argv[3]
required_keys = {
    "release",
    "requested_ref",
    "requested_ref_kind",
    "commit",
    "path",
    "validated_at_utc",
    "validation_command",
    "validation_exit_code",
    "validation_result",
    "validation_log",
    "validation_log_exit_code",
    "launcher_sha256",
    "status",
}

def require_regular(path, *, executable=False, mode=None):
    if path.is_symlink() or not path.is_file():
        raise SystemExit(f"not one regular file: {path}")
    actual_mode = stat.S_IMODE(path.stat().st_mode)
    if executable and actual_mode & 0o111 == 0:
        raise SystemExit(f"not executable: {path}")
    if mode is not None and actual_mode != mode:
        raise SystemExit(f"unexpected mode for {path}: {actual_mode:o}")

def exact_state(path, raw):
    try:
        lines = raw.decode("utf-8").splitlines()
    except UnicodeDecodeError as exc:
        raise SystemExit(f"release state is not UTF-8: {path}") from exc
    pairs = []
    for line in lines:
        if "=" not in line:
            raise SystemExit(f"malformed release-state line in {path}")
        key, value = line.split("=", 1)
        if not key:
            raise SystemExit(f"empty release-state key in {path}")
        pairs.append((key, value))
    keys = [key for key, _ in pairs]
    if len(keys) != len(set(keys)):
        raise SystemExit(f"duplicate release-state key in {path}")
    if set(keys) != required_keys:
        raise SystemExit(f"release state does not have the exact field set: {path}")
    return dict(pairs)

if deployed.parent != app_root / "releases":
    raise SystemExit("deployed release is outside the managed release root")
if not re.fullmatch(r"[0-9a-f]{40}", target):
    raise SystemExit("target is not one full lowercase commit SHA")
current = app_root / "current"
if not current.is_symlink() or current.resolve() != deployed:
    raise SystemExit("current does not resolve to the deployed release")

release_state_path = deployed / ".hub-deployment" / "RELEASE_STATE"
shared_state_path = app_root / "shared" / "RELEASE_STATE"
require_regular(release_state_path, mode=0o600)
require_regular(shared_state_path, mode=0o644)
release_state_raw = release_state_path.read_bytes()
shared_state_raw = shared_state_path.read_bytes()
if release_state_raw != shared_state_raw:
    raise SystemExit("shared and per-release RELEASE_STATE differ")
state = exact_state(release_state_path, release_state_raw)

if state["release"] != deployed.name:
    raise SystemExit("release state has the wrong release name")
if state["path"] != str(deployed):
    raise SystemExit("release state has the wrong release path")
if state["requested_ref"] != target or state["commit"] != target:
    raise SystemExit("release state is not target-bound")
if state["requested_ref_kind"] != "commit":
    raise SystemExit("release state was not created from an exact commit")
if not re.fullmatch(
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z",
    state["validated_at_utc"],
):
    raise SystemExit("release-state validation timestamp is invalid")
if state["validation_command"] != "python -m pytest -q":
    raise SystemExit("release-state validation command differs")
if state["validation_exit_code"] != "0" or state["validation_log_exit_code"] != "0":
    raise SystemExit("candidate validation did not pass")
if not state["validation_result"]:
    raise SystemExit("release-state validation result is empty")
expected_validation_log = deployed / ".hub-deployment" / "validation.log"
if state["validation_log"] != str(expected_validation_log):
    raise SystemExit("release-state validation log path differs")
require_regular(expected_validation_log, mode=0o600)
if not re.fullmatch(r"[0-9a-f]{64}", state["launcher_sha256"]):
    raise SystemExit("launcher identity is missing")
if state["status"] != "production-candidate-core":
    raise SystemExit("release state is not a production candidate")

versioned_launcher = deployed / "ops" / "ec2" / "hub-api.sh"
shared_launcher = app_root / "shared" / "bin" / "hub-api"
require_regular(versioned_launcher, executable=True)
require_regular(shared_launcher, executable=True)
versioned_launcher_raw = versioned_launcher.read_bytes()
shared_launcher_raw = shared_launcher.read_bytes()
versioned_hash = hashlib.sha256(versioned_launcher_raw).hexdigest()
shared_hash = hashlib.sha256(shared_launcher_raw).hexdigest()
if versioned_launcher_raw != shared_launcher_raw:
    raise SystemExit("shared and versioned launchers differ")
if state["launcher_sha256"] != versioned_hash or versioned_hash != shared_hash:
    raise SystemExit("launcher hashes do not match RELEASE_STATE")

current_marker = app_root / "shared" / "current_release"
require_regular(current_marker)
if current_marker.read_bytes() != f"{deployed.name}\n".encode():
    raise SystemExit("current-release marker differs from deployed release")

print(json.dumps({
    "commit": state["commit"],
    "launcher_sha256": state["launcher_sha256"],
    "path": state["path"],
    "release": state["release"],
    "release_state_sha256": hashlib.sha256(release_state_raw).hexdigest(),
    "validation_exit_code": state["validation_exit_code"],
    "validation_log_exit_code": state["validation_log_exit_code"],
}, indent=2, sort_keys=True))
PY_DEPLOY_STATE

EXPECTED_LAUNCHER_SHA256="$(
  sha256sum -- "$DEPLOYED_RELEASE/ops/ec2/hub-api.sh" | awk '{print $1}'
)"
[[ "$EXPECTED_LAUNCHER_SHA256" =~ ^[0-9a-f]{64}$ ]]
```

An internal failure after deployment mutation begins automatically restores the
exact pre-deploy `current` symlink, shared launcher, shared release state,
current-release marker, and previous-release pointer. The failed candidate,
validation log, snapshot, and recovery log remain under its release directory.
Do not restart or invoke rollback after a deployment failure that reports a
successful automatic restoration.

## 5. Explicit restart and process-bound status

Only after reviewing the release state:

```bash
sudo -n systemctl restart hub-api.service
sudo -n systemctl is-active --quiet hub-api.service

STATUS_RESPONSE="$(mktemp /tmp/hub-optimus-status.XXXXXX.json)"
curl -fsS --connect-timeout 2 --max-time 5 \
  -o "$STATUS_RESPONSE" \
  http://127.0.0.1:8080/status

python3 \
  - "$STATUS_RESPONSE" "$DEPLOYED_RELEASE" "$TARGET_SHA" \
  "$EXPECTED_LAUNCHER_SHA256" \
  <<'PY_STATUS'
import json
import re
import sys
from pathlib import Path

status = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
expected_release = str(Path(sys.argv[2]).resolve())
target = sys.argv[3]
expected_launcher_sha256 = sys.argv[4]
if not isinstance(status, dict):
    raise SystemExit("status response is not an object")
if not re.fullmatch(r"[0-9a-f]{40}", target):
    raise SystemExit("expected status commit is invalid")
if not re.fullmatch(r"[0-9a-f]{64}", expected_launcher_sha256):
    raise SystemExit("expected status launcher identity is invalid")
evidence = {
    "product": status.get("product"),
    "running_release": status.get("running_release"),
    "running_commit": status.get("running_commit"),
    "running_launcher_sha256": status.get("running_launcher_sha256"),
    "configured_current_release": status.get("configured_current_release"),
    "configured_current_commit": status.get("configured_current_commit"),
}
print(json.dumps(evidence, indent=2, sort_keys=True))
if evidence["running_release"] != expected_release:
    raise SystemExit("running process is not bound to the deployed release")
if evidence["configured_current_release"] != expected_release:
    raise SystemExit("configured current release is not the deployed release")
if evidence["running_commit"] != target:
    raise SystemExit("running process is not bound to the target commit")
if evidence["configured_current_commit"] != target:
    raise SystemExit("configured current release is not the target commit")
if evidence["running_launcher_sha256"] != expected_launcher_sha256:
    raise SystemExit("running launcher does not match RELEASE_STATE")
PY_STATUS
```

The status evidence deliberately omits `release_state` and every unknown field.
Changing `current` without restarting changes only the configured identity; it
cannot rewrite the process-bound running commit or launcher hash.

## 6. Controlled URL intake and strict evidence allowlist

Keep the raw response mode-private on the host. Only the allowlisted summary
produced by `intake-smoke-evidence.py` may be posted to GitHub.

```bash
EVIDENCE_DIR="$(mktemp -d "$APP_ROOT/shared/intake-smoke.XXXXXX")"
chmod 0700 "$EVIDENCE_DIR"
RESPONSE="$EVIDENCE_DIR/response.json"
install -m 0600 /dev/null "$RESPONSE"
PAYLOAD="$(
  python3 - "$REFERENCE_URL" <<'PY_REQUEST'
import json
import sys
print(json.dumps({"url": sys.argv[1]}, ensure_ascii=False))
PY_REQUEST
)"

set +e
HTTP_CODE="$(
  curl --silent --show-error \
    --fail-with-body \
    --connect-timeout 5 \
    --max-time 15 \
    --output "$RESPONSE" \
    --write-out '%{http_code}' \
    --request POST \
    http://127.0.0.1:8080/intake/url \
    --header 'Content-Type: application/json' \
    --data-binary "$PAYLOAD"
)"
CURL_RC=$?
set -e

python3 "$DEPLOYED_RELEASE/ops/ec2/intake-smoke-evidence.py" \
  "$RESPONSE" \
  "$HTTP_CODE" \
  "$CURL_RC" \
  "$TARGET_SHA"
```

The evidence helper constructs a new object from an explicit allowlist. It
never prints `text`, title, message, debug/body fields, redirects, extraction
notes, or an unknown response field. It emits only target/transport status,
stable application error code, source/final URL metadata, content metadata,
verification status, and text presence/count/SHA-256.

## 7. Failure after a successful deploy

If the explicit restart, status attestation, or intake smoke fails after the
deploy itself completed, retain the local response and use the rollback script
from the persistent deployed release, not a temporary checkout:

```bash
HUB_OPTIMUS_APP_ROOT="$APP_ROOT" \
  bash "$DEPLOYED_RELEASE/ops/ec2/rollback-current.sh"

ROLLED_BACK_RELEASE="$(readlink -f "$APP_ROOT/current")"
RESTORED_COMMIT="$(git -C "$ROLLED_BACK_RELEASE" rev-parse --verify HEAD)"
test "$RESTORED_COMMIT" = "$LEGACY_CURRENT_SHA"
RESTORED_RELEASE_STATE="$ROLLED_BACK_RELEASE/.hub-deployment/RELEASE_STATE"
cmp -s "$RESTORED_RELEASE_STATE" "$APP_ROOT/shared/RELEASE_STATE"
RESTORED_LAUNCHER_SHA256="$(
  sha256sum -- "$ROLLED_BACK_RELEASE/ops/ec2/hub-api.sh" | awk '{print $1}'
)"

python3 \
  - "$ROLLED_BACK_RELEASE" "$RESTORED_COMMIT" \
  "$RESTORED_LAUNCHER_SHA256" "$APP_ROOT" "$DEPLOYED_RELEASE" \
  "$TARGET_SHA" "$LEGACY_CURRENT_SHA" \
  <<'PY_ROLLBACK_STATE'
import hashlib
import json
import re
import stat
import sys
from pathlib import Path

restored = Path(sys.argv[1]).resolve()
restored_commit = sys.argv[2]
restored_launcher_sha256 = sys.argv[3]
app_root = Path(sys.argv[4]).resolve()
deployed = Path(sys.argv[5]).resolve()
deployed_commit = sys.argv[6]
legacy_commit = sys.argv[7]
adopted_keys = {
    "release",
    "requested_ref",
    "requested_ref_kind",
    "commit",
    "path",
    "adopted_at_utc",
    "validation_command",
    "validation_exit_code",
    "validation_result",
    "validation_log",
    "validation_log_exit_code",
    "launcher_sha256",
    "status",
    "provenance",
    "legacy_state_sha256",
    "legacy_commit_prefix",
}
legacy_keys = {
    "release",
    "commit",
    "path",
    "validated_at_utc",
    "validation",
    "status",
}
rollback_keys = {
    "rolled_back_at_utc",
    "from_release",
    "from_commit",
    "to_release",
    "to_commit",
    "to_launcher_sha256",
}

if restored.parent != app_root / "releases":
    raise SystemExit("rollback target is outside the managed release root")
if deployed.parent != app_root / "releases":
    raise SystemExit("rollback source is outside the managed release root")
if not re.fullmatch(r"[0-9a-f]{40}", restored_commit):
    raise SystemExit("restored commit is not one full SHA")
if not re.fullmatch(r"[0-9a-f]{40}", deployed_commit):
    raise SystemExit("deployed commit is not one full SHA")
if legacy_commit != restored_commit:
    raise SystemExit("rollback target is not the expected legacy commit")
if not re.fullmatch(r"[0-9a-f]{64}", restored_launcher_sha256):
    raise SystemExit("restored launcher identity is invalid")

def require_regular(path, *, executable=False, mode=None):
    if path.is_symlink() or not path.is_file():
        raise SystemExit(f"not one regular file: {path}")
    actual_mode = stat.S_IMODE(path.stat().st_mode)
    if executable and actual_mode & 0o111 == 0:
        raise SystemExit(f"not executable: {path}")
    if mode is not None and actual_mode != mode:
        raise SystemExit(f"unexpected mode for {path}: {actual_mode:o}")

def exact_state(path, raw, required):
    try:
        lines = raw.decode("utf-8").splitlines()
    except UnicodeDecodeError as exc:
        raise SystemExit(f"state is not UTF-8: {path}") from exc
    pairs = []
    for line in lines:
        if "=" not in line:
            raise SystemExit(f"malformed state line in {path}")
        key, value = line.split("=", 1)
        if not key:
            raise SystemExit(f"empty state key in {path}")
        pairs.append((key, value))
    keys = [key for key, _ in pairs]
    if len(keys) != len(set(keys)):
        raise SystemExit(f"duplicate state field in {path}")
    if set(keys) != required:
        raise SystemExit(f"state does not have the exact field set: {path}")
    return dict(pairs)

current = app_root / "current"
if not current.is_symlink() or current.resolve() != restored:
    raise SystemExit("current does not resolve to the rollback target")

release_state_path = restored / ".hub-deployment" / "RELEASE_STATE"
shared_state_path = app_root / "shared" / "RELEASE_STATE"
require_regular(release_state_path, mode=0o600)
require_regular(shared_state_path, mode=0o644)
release_state_raw = release_state_path.read_bytes()
shared_state_raw = shared_state_path.read_bytes()
if release_state_raw != shared_state_raw:
    raise SystemExit("shared and per-release rollback RELEASE_STATE differ")
release_state = exact_state(
    release_state_path,
    release_state_raw,
    adopted_keys,
)

if release_state["release"] != restored.name:
    raise SystemExit("restored release state has the wrong release name")
if release_state["path"] != str(restored):
    raise SystemExit("restored release state has the wrong release path")
if release_state["requested_ref"] != restored_commit:
    raise SystemExit("restored release requested ref differs")
if release_state["requested_ref_kind"] != "legacy-host-adoption":
    raise SystemExit("restored release is not an explicit legacy adoption")
if release_state["commit"] != restored_commit:
    raise SystemExit("restored release commit differs")
if not re.fullmatch(
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z",
    release_state["adopted_at_utc"],
):
    raise SystemExit("restored adoption timestamp is invalid")
if release_state["validation_command"] != "not-run-during-legacy-adoption":
    raise SystemExit("restored adoption validation command differs")
if release_state["validation_exit_code"] != "not-run":
    raise SystemExit("restored adoption validation exit differs")
if release_state["validation_result"] != (
    "legacy validation claim not re-attested; original state retained by SHA-256"
):
    raise SystemExit("restored adoption validation result differs")
if release_state["validation_log"] != "not-applicable":
    raise SystemExit("restored adoption validation log differs")
if release_state["validation_log_exit_code"] != "not-run":
    raise SystemExit("restored adoption log exit differs")
if release_state["status"] != "adopted-legacy-current":
    raise SystemExit("restored adoption status differs")
if release_state["provenance"] != "adopted-legacy-current-v1":
    raise SystemExit("restored adoption provenance differs")
if not re.fullmatch(r"[0-9a-f]{64}", release_state["legacy_state_sha256"]):
    raise SystemExit("restored legacy-state identity is invalid")
legacy_prefix = release_state["legacy_commit_prefix"]
if not re.fullmatch(r"[0-9a-f]{7,39}", legacy_prefix):
    raise SystemExit("restored legacy commit prefix is invalid")
if not restored_commit.startswith(legacy_prefix):
    raise SystemExit("restored legacy commit prefix differs")

legacy_state_path = restored / ".hub-deployment" / "LEGACY_RELEASE_STATE"
require_regular(legacy_state_path, mode=0o400)
legacy_state_raw = legacy_state_path.read_bytes()
if hashlib.sha256(legacy_state_raw).hexdigest() != release_state["legacy_state_sha256"]:
    raise SystemExit("retained legacy state does not match its recorded hash")
legacy_state = exact_state(legacy_state_path, legacy_state_raw, legacy_keys)
if legacy_state["release"] != restored.name:
    raise SystemExit("retained legacy state has the wrong release name")
if legacy_state["path"] != str(restored):
    raise SystemExit("retained legacy state has the wrong release path")
if legacy_state["commit"] != legacy_prefix:
    raise SystemExit("retained legacy state has the wrong commit prefix")
if not re.fullmatch(
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z",
    legacy_state["validated_at_utc"],
):
    raise SystemExit("retained legacy validation timestamp is invalid")
if not legacy_state["validation"]:
    raise SystemExit("retained legacy validation claim is empty")
if legacy_state["status"] != "production-candidate-core":
    raise SystemExit("retained legacy status differs")

shared_launcher = app_root / "shared" / "bin" / "hub-api"
versioned_launcher = restored / "ops" / "ec2" / "hub-api.sh"
require_regular(shared_launcher, executable=True)
require_regular(versioned_launcher, executable=True)
shared_launcher_raw = shared_launcher.read_bytes()
versioned_launcher_raw = versioned_launcher.read_bytes()
shared_hash = hashlib.sha256(shared_launcher_raw).hexdigest()
versioned_hash = hashlib.sha256(versioned_launcher_raw).hexdigest()
if shared_launcher_raw != versioned_launcher_raw:
    raise SystemExit("restored shared and versioned launchers differ")
if release_state["launcher_sha256"] != versioned_hash:
    raise SystemExit("restored launcher does not match RELEASE_STATE")
if restored_launcher_sha256 != versioned_hash or versioned_hash != shared_hash:
    raise SystemExit("restored shared/versioned launcher identity differs")

current_marker = app_root / "shared" / "current_release"
require_regular(current_marker)
if current_marker.read_bytes() != f"{restored.name}\n".encode():
    raise SystemExit("restored current-release marker differs")

rollback_state_path = app_root / "shared" / "ROLLBACK_STATE"
require_regular(rollback_state_path, mode=0o600)
rollback_state = exact_state(
    rollback_state_path,
    rollback_state_path.read_bytes(),
    rollback_keys,
)
if rollback_state["from_release"] != deployed.name:
    raise SystemExit("rollback source release differs")
if rollback_state["from_commit"] != deployed_commit:
    raise SystemExit("rollback source commit differs")
if rollback_state["to_release"] != restored.name:
    raise SystemExit("rollback target release differs")
if rollback_state["to_commit"] != restored_commit:
    raise SystemExit("rollback target commit differs")
if rollback_state["to_launcher_sha256"] != restored_launcher_sha256:
    raise SystemExit("rollback target launcher differs")
if not re.fullmatch(
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z",
    rollback_state["rolled_back_at_utc"],
):
    raise SystemExit("rollback timestamp is invalid")
last_rollback_from = app_root / "shared" / "last_rollback_from"
require_regular(last_rollback_from)
if last_rollback_from.read_bytes() != f"{deployed}\n".encode():
    raise SystemExit("rollback source pointer differs")
print(json.dumps({
    "from_commit": deployed_commit,
    "release_state_sha256": hashlib.sha256(release_state_raw).hexdigest(),
    "to_commit": restored_commit,
    "to_release": restored.name,
    "to_launcher_sha256": restored_launcher_sha256,
}, indent=2, sort_keys=True))
PY_ROLLBACK_STATE

sudo -n systemctl restart hub-api.service
sudo -n systemctl is-active --quiet hub-api.service

ROLLBACK_STATUS_RESPONSE="$(mktemp /tmp/hub-optimus-rollback-status.XXXXXX.json)"
curl -fsS --connect-timeout 2 --max-time 5 \
  -o "$ROLLBACK_STATUS_RESPONSE" \
  http://127.0.0.1:8080/status

python3 \
  - "$ROLLBACK_STATUS_RESPONSE" "$ROLLED_BACK_RELEASE" \
  "$RESTORED_COMMIT" "$RESTORED_LAUNCHER_SHA256" \
  <<'PY_ROLLBACK_STATUS'
import json
import re
import sys
from pathlib import Path

status = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
expected_release = str(Path(sys.argv[2]).resolve())
expected_commit = sys.argv[3]
expected_launcher_sha256 = sys.argv[4]
if not isinstance(status, dict):
    raise SystemExit("rollback status response is not an object")
if not re.fullmatch(r"[0-9a-f]{40}", expected_commit):
    raise SystemExit("expected rollback commit is invalid")
if not re.fullmatch(r"[0-9a-f]{64}", expected_launcher_sha256):
    raise SystemExit("expected rollback launcher identity is invalid")
evidence = {
    "product": status.get("product"),
    "running_release": status.get("running_release"),
    "running_commit": status.get("running_commit"),
    "running_launcher_sha256": status.get("running_launcher_sha256"),
    "configured_current_release": status.get("configured_current_release"),
    "configured_current_commit": status.get("configured_current_commit"),
}
print(json.dumps(evidence, indent=2, sort_keys=True))
if evidence["running_release"] != expected_release:
    raise SystemExit("running rollback release differs")
if evidence["configured_current_release"] != expected_release:
    raise SystemExit("configured rollback release differs")
if evidence["running_commit"] != expected_commit:
    raise SystemExit("running rollback commit differs")
if evidence["configured_current_commit"] != expected_commit:
    raise SystemExit("configured rollback commit differs")
if evidence["running_launcher_sha256"] != expected_launcher_sha256:
    raise SystemExit("running rollback launcher differs")
PY_ROLLBACK_STATUS
```

The rollback command stages its transition and snapshots every shared artifact
before mutation. If rollback itself fails, its exit handler restores the exact
pre-rollback state and retains the transaction snapshot and recovery log under
`$APP_ROOT/shared/rollback-transaction.*`; do not hand-edit around that result.

Only after the rollback command, complete disk-state attestation, explicit
restart, and process-bound status attestation all pass is rollback complete.
Record the allowlisted failure evidence and the versioned rollback transition.
Do not hand-edit symlinks. Do not proceed to DNS, TLS, nginx, public routing, or
a reboot in this operation.
