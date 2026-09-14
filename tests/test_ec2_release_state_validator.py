from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "ops" / "ec2" / "validate-release-state.sh"
PREFLIGHT = ROOT / "ops" / "ec2" / "preflight-deploy.sh"
DEPLOY = ROOT / "ops" / "ec2" / "deploy-current.sh"
ROLLBACK = ROOT / "ops" / "ec2" / "rollback-current.sh"

COMMIT = "b" * 40
LAUNCHER_SHA256 = "c" * 64
LEGACY_SHA256 = "d" * 64
VALIDATION_RESULT = "719 passed in 30.45s"
VALIDATION_LOG_RAW = f"collecting tests\n{VALIDATION_RESULT}\n\n".encode()
ADOPTION_RESULT = (
    "legacy validation claim not re-attested; original state retained by SHA-256"
)


def _run(path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(VALIDATOR), str(path)],
        capture_output=True,
        text=True,
        check=False,
    )


def _write_state(path: Path, fields: list[tuple[str, str]]) -> None:
    path.write_text(
        "".join(f"{key}={value}\n" for key, value in fields),
        encoding="utf-8",
    )


def _production_fields(*, transitional: bool = False) -> list[tuple[str, str]]:
    fields = [
        ("release", "20260803T120000Z.ABC123"),
        ("requested_ref", COMMIT),
        ("requested_ref_kind", "commit"),
        ("commit", COMMIT),
        ("path", "/opt/hub-optimus/releases/20260803T120000Z.ABC123"),
        ("validated_at_utc", "2026-08-03T12:00:00Z"),
        ("validation_command", "python -m pytest -q"),
        ("validation_exit_code", "0"),
        ("validation_result", VALIDATION_RESULT),
        (
            "validation_log",
            "/opt/hub-optimus/releases/20260803T120000Z.ABC123/"
            ".hub-deployment/validation.log",
        ),
        ("validation_log_exit_code", "0"),
    ]
    if not transitional:
        fields.append(
            (
                "validation_log_sha256",
                hashlib.sha256(VALIDATION_LOG_RAW).hexdigest(),
            )
        )
    fields.extend(
        (
            ("launcher_sha256", LAUNCHER_SHA256),
            ("status", "production-candidate-core"),
        )
    )
    if transitional:
        fields.append(("provenance", "adopted-pre-1832"))
    return fields


def _replace_field(
    fields: list[tuple[str, str]],
    field: str,
    value: str,
) -> list[tuple[str, str]]:
    return [
        (key, value if key == field else original)
        for key, original in fields
    ]


def _production_fixture(
    tmp_path: Path,
) -> tuple[Path, Path, list[tuple[str, str]]]:
    release = tmp_path / "releases" / "20260803T120000Z.ABC123"
    validation_log = release / ".hub-deployment" / "validation.log"
    validation_log.parent.mkdir(parents=True)
    validation_log.write_bytes(VALIDATION_LOG_RAW)
    validation_log.chmod(0o600)
    fields = _production_fields()
    fields = _replace_field(fields, "release", release.name)
    fields = _replace_field(fields, "path", str(release))
    fields = _replace_field(fields, "validation_log", str(validation_log))
    state = validation_log.parent / "RELEASE_STATE"
    _write_state(state, fields)
    return state, validation_log, fields


def _adopted_fields() -> list[tuple[str, str]]:
    return [
        ("release", "20260720T225606Z"),
        ("requested_ref", COMMIT),
        ("requested_ref_kind", "legacy-host-adoption"),
        ("commit", COMMIT),
        ("path", "/opt/hub-optimus/releases/20260720T225606Z"),
        ("adopted_at_utc", "2026-08-03T12:00:00Z"),
        ("validation_command", "not-run-during-legacy-adoption"),
        ("validation_exit_code", "not-run"),
        ("validation_result", ADOPTION_RESULT),
        ("validation_log", "not-applicable"),
        ("validation_log_exit_code", "not-run"),
        ("launcher_sha256", LAUNCHER_SHA256),
        ("status", "adopted-legacy-current"),
        ("provenance", "adopted-legacy-current-v1"),
        ("legacy_state_sha256", LEGACY_SHA256),
        ("legacy_commit_prefix", COMMIT[:7]),
    ]


def _legacy_fields() -> list[tuple[str, str]]:
    return [
        ("release", "20260720T225606Z"),
        ("commit", COMMIT[:7]),
        ("path", "/opt/hub-optimus/releases/20260720T225606Z"),
        ("validated_at_utc", "2026-07-20T22:56:06Z"),
        ("validation", "pytest 55 passed"),
        ("status", "production-candidate-core"),
    ]


@pytest.mark.parametrize(
    ("schema_name", "expected_kind", "fields"),
    (
        ("production", "production", _production_fields()),
        (
            "transitional",
            "transitional-adopted-pre-1832",
            _production_fields(transitional=True),
        ),
        ("adopted-legacy", "adopted-legacy", _adopted_fields()),
        ("six-field-legacy", "legacy", _legacy_fields()),
    ),
)
def test_validator_accepts_each_supported_exact_schema(
    tmp_path: Path,
    schema_name: str,
    expected_kind: str,
    fields: list[tuple[str, str]],
) -> None:
    if schema_name == "production":
        state, _, fields = _production_fixture(tmp_path)
    else:
        state = tmp_path / schema_name
        _write_state(state, fields)

    result = _run(state)

    assert result.returncode == 0, result.stderr
    assert f"PASS {expected_kind}" in result.stdout


def test_validator_accepts_an_exact_tag_state(tmp_path: Path) -> None:
    state, _, fields = _production_fixture(tmp_path)
    fields = _replace_field(fields, "requested_ref", "v2.3.4")
    fields = _replace_field(fields, "requested_ref_kind", "tag")
    _write_state(state, fields)

    result = _run(state)

    assert result.returncode == 0, result.stderr
    assert "PASS production" in result.stdout


def test_validator_accepts_digest_bound_transitional_state(tmp_path: Path) -> None:
    state, _, fields = _production_fixture(tmp_path)
    fields.append(("provenance", "adopted-pre-1832"))
    _write_state(state, fields)

    result = _run(state)

    assert result.returncode == 0, result.stderr
    assert "PASS transitional-adopted-pre-1832" in result.stdout


def test_validator_rejects_an_invalid_tag_name(tmp_path: Path) -> None:
    fields = _production_fields()
    fields[1] = ("requested_ref", "not a valid git tag")
    fields[2] = ("requested_ref_kind", "tag")
    state = tmp_path / "invalid-tag-state"
    _write_state(state, fields)

    result = _run(state)

    assert result.returncode == 1
    assert "invalid requested tag" in result.stderr


@pytest.mark.parametrize(
    "fields",
    (
        _production_fields(),
        _production_fields(transitional=True),
        _adopted_fields(),
        _legacy_fields(),
    ),
    ids=("production", "transitional", "adopted-legacy", "six-field-legacy"),
)
@pytest.mark.parametrize(
    "corruption",
    (
        "nul",
        "invalid-utf8",
        "crlf",
        "nel",
        "line-separator",
        "paragraph-separator",
        "control-byte",
        "missing-terminal-lf",
        "noncanonical-key",
    ),
)
def test_validator_rejects_noncanonical_state_bytes_for_every_schema(
    tmp_path: Path,
    fields: list[tuple[str, str]],
    corruption: str,
) -> None:
    state = tmp_path / f"noncanonical-{corruption}"
    _write_state(state, fields)
    raw = state.read_bytes()
    free_text_key = (
        b"validation_result="
        if b"validation_result=" in raw
        else b"validation="
    )

    if corruption == "nul":
        raw = raw.replace(b"status=", b"status=\x00", 1)
    elif corruption == "invalid-utf8":
        raw = raw.replace(free_text_key, free_text_key + b"\xff", 1)
    elif corruption == "crlf":
        raw = raw.replace(b"\n", b"\r\n", 1)
    elif corruption == "nel":
        raw = raw.replace(free_text_key, free_text_key + "\u0085".encode(), 1)
    elif corruption == "line-separator":
        raw = raw.replace(free_text_key, free_text_key + "\u2028".encode(), 1)
    elif corruption == "paragraph-separator":
        raw = raw.replace(free_text_key, free_text_key + "\u2029".encode(), 1)
    elif corruption == "control-byte":
        raw = raw.replace(free_text_key, free_text_key + b"\x01", 1)
    elif corruption == "missing-terminal-lf":
        raw = raw[:-1]
    else:
        raw = raw.replace(b"release=", b"Release=", 1)
    state.write_bytes(raw)

    result = _run(state)

    assert result.returncode == 1
    assert "not canonical UTF-8/LF text" in result.stderr


@pytest.mark.parametrize(
    ("corruption", "expected_error"),
    (
        ("duplicate", "duplicate field: status"),
        ("malformed", "malformed state line"),
        ("unknown", "unsupported field: unexpected"),
        ("partial", "exact expected field set"),
        ("mixed", "unsupported field: validation"),
    ),
)
def test_validator_rejects_malformed_duplicate_unknown_partial_and_mixed_state(
    tmp_path: Path,
    corruption: str,
    expected_error: str,
) -> None:
    fields = _production_fields()
    state = tmp_path / "corrupted-state"
    if corruption == "duplicate":
        fields.append(("status", "production-candidate-core"))
        _write_state(state, fields)
    elif corruption == "malformed":
        _write_state(state, fields)
        state.write_text(
            state.read_text(encoding="utf-8") + "malformed-state-line\n",
            encoding="utf-8",
        )
    elif corruption == "unknown":
        fields.append(("unexpected", "value"))
        _write_state(state, fields)
    elif corruption == "partial":
        _write_state(state, fields[:-1])
    else:
        fields.append(("validation", "legacy-only-field"))
        _write_state(state, fields)

    result = _run(state)

    assert result.returncode == 1
    assert expected_error in result.stderr


def test_pre_digest_production_state_is_not_silently_accepted(
    tmp_path: Path,
) -> None:
    state, _, fields = _production_fixture(tmp_path)
    fields = [
        (key, value)
        for key, value in fields
        if key != "validation_log_sha256"
    ]
    _write_state(state, fields)

    result = _run(state)

    assert result.returncode == 1
    assert "exact expected field set" in result.stderr


@pytest.mark.parametrize(
    ("corruption", "expected_error"),
    (
        ("truncated", "Validation log does not match"),
        ("replaced", "Validation log does not match"),
        ("digest", "Validation log does not match"),
        ("result", "Validation result does not match"),
        ("empty", "no non-empty result line"),
        ("path", "wrong validation-log path"),
        ("invalid-utf8", "Validation log is not UTF-8"),
        ("nul", "not canonical UTF-8/LF text"),
        ("crlf", "not canonical UTF-8/LF text"),
        ("line-separator", "not canonical UTF-8/LF text"),
        ("missing-terminal-lf", "has no terminal LF"),
        ("mode", "unexpected mode"),
    ),
)
def test_validator_rejects_validation_log_or_result_drift(
    tmp_path: Path,
    corruption: str,
    expected_error: str,
) -> None:
    state, validation_log, fields = _production_fixture(tmp_path)
    if corruption == "truncated":
        validation_log.write_bytes(VALIDATION_LOG_RAW[:-8])
    elif corruption == "replaced":
        validation_log.write_bytes(f"replacement\n{VALIDATION_RESULT}\n\n".encode())
    elif corruption == "digest":
        fields = _replace_field(fields, "validation_log_sha256", "0" * 64)
        _write_state(state, fields)
    elif corruption == "result":
        fields = _replace_field(fields, "validation_result", "forged result")
        _write_state(state, fields)
    elif corruption == "empty":
        validation_log.write_bytes(b"\n \t\n")
        fields = _replace_field(
            fields,
            "validation_log_sha256",
            hashlib.sha256(validation_log.read_bytes()).hexdigest(),
        )
        _write_state(state, fields)
    elif corruption in {
        "invalid-utf8",
        "nul",
        "crlf",
        "line-separator",
        "missing-terminal-lf",
    }:
        prefix = {
            "invalid-utf8": b"context=\xff\n",
            "nul": b"context=has\x00nul\n",
            "crlf": b"context uses CRLF\r\n",
            "line-separator": "context uses LS\u2028\n".encode(),
            "missing-terminal-lf": b"context without terminal LF\n",
        }[corruption]
        raw = prefix + f"{VALIDATION_RESULT}\n".encode()
        if corruption == "missing-terminal-lf":
            raw = raw[:-1]
        validation_log.write_bytes(raw)
        fields = _replace_field(
            fields,
            "validation_log_sha256",
            hashlib.sha256(raw).hexdigest(),
        )
        _write_state(state, fields)
    elif corruption == "mode":
        validation_log.chmod(0o644)
    else:
        fields = _replace_field(
            fields,
            "validation_log",
            str(tmp_path / "replacement-validation.log"),
        )
        _write_state(state, fields)

    result = _run(state)

    assert result.returncode == 1
    assert expected_error in result.stderr


def test_validation_log_attestation_uses_one_stable_descriptor_snapshot() -> None:
    source = VALIDATOR.read_text(encoding="utf-8")

    assert "flags |= os.O_NOFOLLOW" in source
    assert "descriptor = os.open(path, flags)" in source
    assert "opened = os.fstat(descriptor)" in source
    assert "finished = os.fstat(descriptor)" in source
    assert "visible = os.stat(path, follow_symlinks=False)" in source
    assert 'raw = b"".join(chunks)' in source
    assert "hashlib.sha256(raw).hexdigest()" in source
    assert 'text = raw.decode("utf-8")' in source
    assert 'sha256sum -- "$validation_log"' not in source
    assert "NF { result=$0; found=1 }" not in source


@pytest.mark.parametrize(
    ("field", "value", "expected_error"),
    (
        ("provenance", "forged", "unsupported transitional provenance"),
        ("validation_exit_code", "1", "does not record successful validation"),
        ("status", "validation-failed", "not a production candidate"),
    ),
)
def test_validator_rejects_semantically_invalid_transitional_state(
    tmp_path: Path,
    field: str,
    value: str,
    expected_error: str,
) -> None:
    fields = [
        (key, value if key == field else original)
        for key, original in _production_fields(transitional=True)
    ]
    state = tmp_path / "invalid-transitional"
    _write_state(state, fields)

    result = _run(state)

    assert result.returncode == 1
    assert expected_error in result.stderr


def test_preflight_deploy_and_rollback_use_the_shared_validator() -> None:
    for script in (PREFLIGHT, DEPLOY, ROLLBACK):
        source = script.read_text(encoding="utf-8")
        assert 'STATE_VALIDATOR="$SCRIPT_DIR/validate-release-state.sh"' in source
        assert 'bash "$STATE_VALIDATOR" "$state_file"' in source


def test_attestation_scope_excludes_operational_hardening() -> None:
    sources = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (VALIDATOR, PREFLIGHT, DEPLOY, ROLLBACK)
    )

    assert "validation_log_sha256" in sources
    assert "validate-release-worktree" not in sources
    assert "recovery-snapshot" not in sources
    assert "PYTEST_ADDOPTS" not in sources
