#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 1 ]; then
  echo "[release-state:error] Usage: validate-release-state <state-file>" >&2
  exit 1
fi

STATE_FILE="$1"

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

  if [ "$transitional" = "yes" ]; then
    require_exact_keys \
      release requested_ref requested_ref_kind commit path validated_at_utc \
      validation_command validation_exit_code validation_result validation_log \
      validation_log_exit_code launcher_sha256 status provenance
    [ "$(state_value provenance)" = "adopted-pre-1832" ] \
      || fail "$STATE_FILE has unsupported transitional provenance."
    schema="transitional-adopted-pre-1832"
  else
    require_exact_keys \
      release requested_ref requested_ref_kind commit path validated_at_utc \
      validation_command validation_exit_code validation_result validation_log \
      validation_log_exit_code launcher_sha256 status
    schema="production"
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
  [ "$(state_value validation_command)" = "python -m pytest -q" ] \
    || fail "$STATE_FILE has an unexpected validation command."
  [ "$(state_value validation_exit_code)" = "0" ] \
    && [ "$(state_value validation_log_exit_code)" = "0" ] \
    || fail "$STATE_FILE does not record successful validation."
  [ -n "$(state_value validation_result)" ] \
    && [ -n "$(state_value validation_log)" ] \
    || fail "$STATE_FILE has incomplete validation evidence."
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
