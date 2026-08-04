#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 1 ]; then
  echo "[release-state:error] Usage: validate-release-state <state-file>" >&2
  exit 1
fi

STATE_FILE="$1"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
DEPENDENCY_LOCK_TOOL="$SCRIPT_DIR/dependency-lock-digest.sh"

fail() {
  echo "[release-state:error] $*" >&2
  exit 1
}

[ -f "$STATE_FILE" ] && [ ! -L "$STATE_FILE" ] \
  || fail "State is not one regular file: $STATE_FILE"

validate_canonical_state_text() {
  /usr/bin/python3 -I - "$STATE_FILE" <<'PY_CANONICAL_STATE' \
    || fail "State is not canonical UTF-8/LF text: $STATE_FILE"
import re
import sys
from pathlib import Path


path = Path(sys.argv[1])
raw = path.read_bytes()
if not raw or not raw.endswith(b"\n"):
    raise SystemExit(1)
try:
    text = raw.decode("utf-8")
except UnicodeDecodeError:
    raise SystemExit(1)

for character in text:
    codepoint = ord(character)
    if character == "\n":
        continue
    if codepoint < 0x20 or 0x7F <= codepoint <= 0x9F:
        raise SystemExit(1)
    if character in {"\u2028", "\u2029"}:
        raise SystemExit(1)

for line in text[:-1].split("\n"):
    if "=" not in line:
        continue
    key = line.split("=", 1)[0]
    if not re.fullmatch(r"[a-z][a-z0-9_]*", key):
        raise SystemExit(1)
PY_CANONICAL_STATE
}

validate_canonical_state_text

declare -A SEEN_STATE_KEYS=()
STATE_LINE_COUNT=0
while IFS= read -r line || [ -n "$line" ]; do
  STATE_LINE_COUNT=$((STATE_LINE_COUNT + 1))
  [[ "$line" == *=* ]] \
    || fail "$STATE_FILE contains a malformed state line at $STATE_LINE_COUNT."
  key="${line%%=*}"
  [ -n "$key" ] \
    || fail "$STATE_FILE contains an empty field name at $STATE_LINE_COUNT."
  if [[ -n "${SEEN_STATE_KEYS[$key]+present}" ]]; then
    fail "$STATE_FILE contains a duplicate field: $key"
  fi
  SEEN_STATE_KEYS["$key"]=1
done < "$STATE_FILE"

state_value() {
  local key="$1"
  sed -n "s/^${key}=//p" "$STATE_FILE"
}

require_exact_keys() {
  local expected=" $* "
  local expected_count="$#"
  local key

  for key in "${!SEEN_STATE_KEYS[@]}"; do
    case "$expected" in
      *" $key "*) ;;
      *) fail "$STATE_FILE contains an unsupported field: $key" ;;
    esac
  done
  [ "$STATE_LINE_COUNT" -eq "$expected_count" ] \
    || fail "$STATE_FILE does not contain the exact expected field set."
  for key in "$@"; do
    [[ -n "${SEEN_STATE_KEYS[$key]+present}" ]] \
      || fail "$STATE_FILE does not contain the exact expected field set."
  done
}

require_common_identity() {
  [ -n "$(state_value release)" ] \
    || fail "$STATE_FILE has an empty release field."
  [[ "$(state_value path)" == /* ]] \
    || fail "$STATE_FILE has an invalid release path."
}

validate_production() {
  local transitional="$1"
  local commit
  local requested_ref
  local requested_ref_kind
  local digest_bound="no"
  local dependency_bound="no"
  local isolated_bound="no"
  local validation_log
  local validation_log_sha256
  local dependency_lock_sha256
  local expected_validation_command
  local validation_collected
  local validation_terminal
  local validation_passed
  local validation_skipped
  local validation_failed

  if [ "$transitional" = "yes" ]; then
    if [[ -n "${SEEN_STATE_KEYS[validation_protocol]+present}" ]]; then
      require_exact_keys \
        release requested_ref requested_ref_kind commit path validated_at_utc \
        validation_command validation_exit_code validation_result validation_log \
        validation_log_exit_code validation_log_sha256 validation_protocol \
        validation_collected validation_terminal validation_passed \
        validation_skipped validation_failed validation_pytest_exit_code \
        validation_nodeids_sha256 validation_descendants validation_worker_uid \
        source_tree_sha256 venv_tree_sha256 dependency_tier dependency_lock \
        dependency_lock_sha256 launcher_sha256 status provenance
      digest_bound="yes"
      dependency_bound="yes"
      isolated_bound="yes"
    elif [[ -n "${SEEN_STATE_KEYS[dependency_lock_sha256]+present}" ]]; then
      require_exact_keys \
        release requested_ref requested_ref_kind commit path validated_at_utc \
        validation_command validation_exit_code validation_result validation_log \
        validation_log_exit_code validation_log_sha256 dependency_tier \
        dependency_lock dependency_lock_sha256 launcher_sha256 status provenance
      digest_bound="yes"
      dependency_bound="yes"
    elif [[ -n "${SEEN_STATE_KEYS[validation_log_sha256]+present}" ]]; then
      require_exact_keys \
        release requested_ref requested_ref_kind commit path validated_at_utc \
        validation_command validation_exit_code validation_result validation_log \
        validation_log_exit_code validation_log_sha256 launcher_sha256 status \
        provenance
      digest_bound="yes"
    else
      require_exact_keys \
        release requested_ref requested_ref_kind commit path validated_at_utc \
        validation_command validation_exit_code validation_result validation_log \
        validation_log_exit_code launcher_sha256 status provenance
    fi
    [ "$(state_value provenance)" = "adopted-pre-1832" ] \
      || fail "$STATE_FILE has unsupported transitional provenance."
    schema="transitional-adopted-pre-1832"
  else
    require_exact_keys \
      release requested_ref requested_ref_kind commit path validated_at_utc \
      validation_command validation_exit_code validation_result validation_log \
      validation_log_exit_code validation_log_sha256 validation_protocol \
      validation_collected validation_terminal validation_passed \
      validation_skipped validation_failed validation_pytest_exit_code \
      validation_nodeids_sha256 validation_descendants validation_worker_uid \
      source_tree_sha256 venv_tree_sha256 dependency_tier dependency_lock \
      dependency_lock_sha256 launcher_sha256 status
    schema="production"
    digest_bound="yes"
    dependency_bound="yes"
    isolated_bound="yes"
  fi

  require_common_identity
  commit="$(state_value commit)"
  requested_ref="$(state_value requested_ref)"
  requested_ref_kind="$(state_value requested_ref_kind)"
  [[ "$commit" =~ ^[0-9a-f]{40}$ ]] \
    || fail "$STATE_FILE has no full lowercase commit identity."
  case "$requested_ref_kind" in
    commit)
      [[ "$requested_ref" =~ ^[0-9a-fA-F]{40}$ ]] \
        || fail "$STATE_FILE has an invalid requested commit."
      [ "${requested_ref,,}" = "$commit" ] \
        || fail "$STATE_FILE requested commit differs from its resolved commit."
      ;;
    tag)
      [ -n "$requested_ref" ] \
        || fail "$STATE_FILE has an empty requested tag."
      git check-ref-format "refs/tags/$requested_ref" >/dev/null 2>&1 \
        || fail "$STATE_FILE has an invalid requested tag."
      ;;
    *) fail "$STATE_FILE has an unsupported requested_ref_kind." ;;
  esac
  [[ "$(state_value validated_at_utc)" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$ ]] \
    || fail "$STATE_FILE has an invalid validation timestamp."
  if [ "$isolated_bound" = "yes" ]; then
    printf -v expected_validation_command \
      '/usr/bin/env -i HOME=/nonexistent LANG=C.UTF-8 PATH=/usr/bin:/bin /usr/bin/python3 -I %q %q %q %q' \
      "$(state_value path)/ops/ec2/run-release-validation.py" \
      "$(state_value path)" \
      "$commit" \
      "$(state_value path)/ops/ec2/verify-release-worktree.py"
  elif [ "$dependency_bound" = "yes" ]; then
    printf -v expected_validation_command \
      '/usr/bin/env -i HOME=%q LANG=C.UTF-8 PATH=/usr/bin:/bin PYTHONNOUSERSITE=1 %q -m pytest -q' \
      "$(state_value path)" \
      "$(state_value path)/.venv/bin/python"
  else
    expected_validation_command="python -m pytest -q"
  fi
  [ "$(state_value validation_command)" = "$expected_validation_command" ] \
    || fail "$STATE_FILE has an unexpected validation command."
  [ "$(state_value validation_exit_code)" = "0" ] \
    && [ "$(state_value validation_log_exit_code)" = "0" ] \
    || fail "$STATE_FILE does not record successful validation."
  [ -n "$(state_value validation_result)" ] \
    && [ -n "$(state_value validation_log)" ] \
    || fail "$STATE_FILE has incomplete validation evidence."

  if [ "$isolated_bound" = "yes" ]; then
    [ "$(state_value validation_protocol)" = "isolated-pytest-v1" ] \
      || fail "$STATE_FILE has an unsupported validation protocol."
    validation_collected="$(state_value validation_collected)"
    validation_terminal="$(state_value validation_terminal)"
    validation_passed="$(state_value validation_passed)"
    validation_skipped="$(state_value validation_skipped)"
    validation_failed="$(state_value validation_failed)"
    for value in \
      "$validation_collected" \
      "$validation_terminal" \
      "$validation_passed" \
      "$validation_skipped" \
      "$validation_failed" \
      "$(state_value validation_pytest_exit_code)" \
      "$(state_value validation_descendants)" \
      "$(state_value validation_worker_uid)"; do
      [[ "$value" =~ ^[0-9]+$ ]] \
        || fail "$STATE_FILE has non-numeric validation evidence."
    done
    [ "$validation_collected" -gt 0 ] \
      && [ "$validation_terminal" -eq "$validation_collected" ] \
      && [ "$validation_failed" -eq 0 ] \
      && [ "$(state_value validation_pytest_exit_code)" -eq 0 ] \
      && [ "$(state_value validation_descendants)" -eq 0 ] \
      && [ $((validation_passed + validation_skipped)) -eq "$validation_terminal" ] \
      || fail "$STATE_FILE does not attest one completed pytest execution."
    [[ "$(state_value validation_nodeids_sha256)" =~ ^[0-9a-f]{64}$ ]] \
      && [[ "$(state_value source_tree_sha256)" =~ ^[0-9a-f]{64}$ ]] \
      && [[ "$(state_value venv_tree_sha256)" =~ ^[0-9a-f]{64}$ ]] \
      || fail "$STATE_FILE has invalid validation-tree evidence."
    [ "$(state_value validation_result)" = \
      "HUB_OPTIMUS_VALIDATION_V1 collected=$validation_collected terminal=$validation_terminal passed=$validation_passed skipped=$validation_skipped failed=$validation_failed pytest_exit_code=$(state_value validation_pytest_exit_code) nodeids_sha256=$(state_value validation_nodeids_sha256) descendants=$(state_value validation_descendants) source_tree_sha256=$(state_value source_tree_sha256) venv_tree_sha256=$(state_value venv_tree_sha256) worker_uid=$(state_value validation_worker_uid) result=passed" ] \
      || fail "Validation result does not match its structured evidence: $STATE_FILE"
  fi

  if [ "$digest_bound" = "yes" ]; then
    validation_log="$(state_value validation_log)"
    [ "$validation_log" = "$(state_value path)/.hub-deployment/validation.log" ] \
      || fail "$STATE_FILE has the wrong validation-log path."
    [ -f "$validation_log" ] && [ ! -L "$validation_log" ] \
      || fail "Validation log is not one regular file: $validation_log"
    validation_log_sha256="$(state_value validation_log_sha256)"
    [[ "$validation_log_sha256" =~ ^[0-9a-f]{64}$ ]] \
      || fail "$STATE_FILE has no valid validation-log SHA-256."
    /usr/bin/python3 -I - \
      "$validation_log" \
      "$validation_log_sha256" \
      "$(state_value validation_result)" <<'PY_VALIDATION_LOG' \
      || fail "Validation-log attestation failed: $validation_log"
import hashlib
import os
import stat
import sys


path, expected_sha256, expected_result = sys.argv[1:]


def fail(message: str) -> None:
    print(f"[release-state:error] {message}", file=sys.stderr)
    raise SystemExit(1)


flags = os.O_RDONLY | os.O_CLOEXEC
if not hasattr(os, "O_NOFOLLOW"):
    fail("O_NOFOLLOW is unavailable for validation-log attestation.")
flags |= os.O_NOFOLLOW
try:
    descriptor = os.open(path, flags)
except OSError as exc:
    fail(f"Could not open validation log without following links: {path}: {exc}")

try:
    opened = os.fstat(descriptor)
    if not stat.S_ISREG(opened.st_mode):
        fail(f"Validation log is not one regular file: {path}")
    if stat.S_IMODE(opened.st_mode) != 0o600:
        fail(f"Validation log has an unexpected mode: {path}")
    chunks = []
    while True:
        chunk = os.read(descriptor, 1024 * 1024)
        if not chunk:
            break
        chunks.append(chunk)
    raw = b"".join(chunks)

    if hashlib.sha256(raw).hexdigest() != expected_sha256:
        fail(f"Validation log does not match {path}")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        fail(f"Validation log is not UTF-8: {path}")
    if not raw.endswith(b"\n"):
        fail(f"Validation log has no terminal LF: {path}")
    for character in text:
        codepoint = ord(character)
        if character in {"\n", "\t"}:
            continue
        if codepoint < 0x20 or 0x7F <= codepoint <= 0x9F:
            fail(f"Validation log is not canonical UTF-8/LF text: {path}")
        if character in {"\u2028", "\u2029"}:
            fail(f"Validation log is not canonical UTF-8/LF text: {path}")
    result_lines = [
        line for line in text[:-1].split("\n") if line.split()
    ]
    if not result_lines:
        fail(f"Validation log has no non-empty result line: {path}")
    if result_lines[-1] != expected_result:
        fail("Validation result does not match the validation log.")

    finished = os.fstat(descriptor)
    visible = os.stat(path, follow_symlinks=False)
    identity_fields = (
        "st_dev",
        "st_ino",
        "st_mode",
        "st_size",
        "st_mtime_ns",
        "st_ctime_ns",
    )
    if any(
        getattr(opened, field) != getattr(finished, field)
        for field in identity_fields
    ):
        fail(f"Validation log changed while it was being attested: {path}")
    if any(
        getattr(finished, field) != getattr(visible, field)
        for field in identity_fields
    ):
        fail(f"Validation log path changed while it was being attested: {path}")
finally:
    os.close(descriptor)
PY_VALIDATION_LOG
  fi

  if [ "$dependency_bound" = "yes" ]; then
    [ "$(state_value dependency_tier)" = "runtime+validation-v1" ] \
      || fail "$STATE_FILE has an unsupported dependency tier."
    [ "$(state_value dependency_lock)" = "$(state_value path)/ops/ec2/requirements-validation.lock" ] \
      || fail "$STATE_FILE has the wrong dependency-lock path."
    dependency_lock_sha256="$(state_value dependency_lock_sha256)"
    [[ "$dependency_lock_sha256" =~ ^[0-9a-f]{64}$ ]] \
      || fail "$STATE_FILE has no valid dependency-lock SHA-256."
    [ -f "$DEPENDENCY_LOCK_TOOL" ] && [ ! -L "$DEPENDENCY_LOCK_TOOL" ] \
      || fail "Dependency-lock validator is not one regular file: $DEPENDENCY_LOCK_TOOL"
    [ "$(/bin/bash "$DEPENDENCY_LOCK_TOOL" "$(state_value path)")" = "$dependency_lock_sha256" ] \
      || fail "$STATE_FILE dependency lock does not match its reviewed release."
  fi

  [[ "$(state_value launcher_sha256)" =~ ^[0-9a-f]{64}$ ]] \
    || fail "$STATE_FILE has no valid launcher SHA-256."
  [ "$(state_value status)" = "production-candidate-core" ] \
    || fail "$STATE_FILE is not a production candidate."
}

validate_adopted_legacy() {
  local commit
  local prefix

  require_exact_keys \
    release requested_ref requested_ref_kind commit path adopted_at_utc \
    validation_command validation_exit_code validation_result validation_log \
    validation_log_exit_code launcher_sha256 status provenance \
    legacy_state_sha256 legacy_commit_prefix
  require_common_identity
  commit="$(state_value commit)"
  prefix="$(state_value legacy_commit_prefix)"
  [[ "$commit" =~ ^[0-9a-f]{40}$ ]] \
    || fail "$STATE_FILE has no full lowercase commit identity."
  [ "$(state_value requested_ref)" = "$commit" ] \
    || fail "$STATE_FILE legacy adoption is not commit-bound."
  [[ "$(state_value adopted_at_utc)" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$ ]] \
    || fail "$STATE_FILE has an invalid adoption timestamp."
  [ "$(state_value validation_command)" = "not-run-during-legacy-adoption" ] \
    && [ "$(state_value validation_exit_code)" = "not-run" ] \
    && [ "$(state_value validation_result)" = "legacy validation claim not re-attested; original state retained by SHA-256" ] \
    && [ "$(state_value validation_log)" = "not-applicable" ] \
    && [ "$(state_value validation_log_exit_code)" = "not-run" ] \
    || fail "$STATE_FILE has invalid legacy-adoption validation metadata."
  [ "$(state_value status)" = "adopted-legacy-current" ] \
    && [ "$(state_value provenance)" = "adopted-legacy-current-v1" ] \
    || fail "$STATE_FILE has invalid legacy-adoption provenance."
  [[ "$(state_value launcher_sha256)" =~ ^[0-9a-f]{64}$ ]] \
    || fail "$STATE_FILE has no valid launcher SHA-256."
  [[ "$(state_value legacy_state_sha256)" =~ ^[0-9a-f]{64}$ ]] \
    || fail "$STATE_FILE has an invalid legacy-state SHA-256."
  [[ "$prefix" =~ ^[0-9a-f]{7,39}$ ]] \
    && [[ "$commit" == "$prefix"* ]] \
    || fail "$STATE_FILE has an invalid legacy commit prefix."
  schema="adopted-legacy"
}

validate_legacy() {
  require_exact_keys release commit path validated_at_utc validation status
  require_common_identity
  [[ "$(state_value commit)" =~ ^[0-9a-f]{7,39}$ ]] \
    || fail "$STATE_FILE has an invalid legacy commit prefix."
  [[ "$(state_value validated_at_utc)" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$ ]] \
    || fail "$STATE_FILE has an invalid validation timestamp."
  [ -n "$(state_value validation)" ] \
    || fail "$STATE_FILE has an empty validation claim."
  [ "$(state_value status)" = "production-candidate-core" ] \
    || fail "$STATE_FILE is not a legacy production candidate."
  schema="legacy"
}

if [[ -n "${SEEN_STATE_KEYS[requested_ref_kind]+present}" ]]; then
  case "$(state_value requested_ref_kind)" in
    commit|tag)
      if [[ -n "${SEEN_STATE_KEYS[provenance]+present}" ]]; then
        validate_production yes
      else
        validate_production no
      fi
      ;;
    legacy-host-adoption) validate_adopted_legacy ;;
    *) fail "$STATE_FILE has an unsupported requested_ref_kind." ;;
  esac
else
  validate_legacy
fi

printf '[release-state] PASS %s %s\n' "$schema" "$STATE_FILE"
