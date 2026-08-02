from __future__ import annotations

import hashlib
import json
import re
import stat
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
RUNBOOK = ROOT / "ops" / "ec2" / "ISSUE_1831_RUNBOOK.md"


def _heredoc(name: str) -> str:
    text = RUNBOOK.read_text(encoding="utf-8")
    match = re.search(rf"<<'{name}'\n(.*?)\n{name}", text, re.DOTALL)
    assert match is not None, name
    return match.group(1)


def _run_heredoc(name: str, *args: str | Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-", *(str(arg) for arg in args)],
        input=_heredoc(name),
        capture_output=True,
        text=True,
        check=False,
    )


def _write_bytes(path: Path, data: bytes, mode: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    path.chmod(mode)


def _state_bytes(fields: dict[str, str]) -> bytes:
    return ("\n".join(f"{key}={value}" for key, value in fields.items()) + "\n").encode()


def _replace_state_pair(
    release_state: Path,
    shared_state: Path,
    transform,
) -> None:
    updated = transform(release_state.read_bytes())
    release_state.write_bytes(updated)
    shared_state.write_bytes(updated)


def _deploy_fixture(tmp_path: Path) -> dict[str, object]:
    app_root = tmp_path / "app"
    release = app_root / "releases" / "20260802T120000Z.fixture"
    commit = "a" * 40
    launcher = b"#!/usr/bin/env bash\necho deployed\n"
    launcher_sha256 = hashlib.sha256(launcher).hexdigest()
    versioned_launcher = release / "ops" / "ec2" / "hub-api.sh"
    shared_launcher = app_root / "shared" / "bin" / "hub-api"
    _write_bytes(versioned_launcher, launcher, 0o755)
    _write_bytes(shared_launcher, launcher, 0o755)
    (app_root / "current").symlink_to(release, target_is_directory=True)

    deployment_dir = release / ".hub-deployment"
    validation_log = deployment_dir / "validation.log"
    _write_bytes(validation_log, b"692 passed\n", 0o600)
    fields = {
        "release": release.name,
        "requested_ref": commit,
        "requested_ref_kind": "commit",
        "commit": commit,
        "path": str(release),
        "validated_at_utc": "2026-08-02T12:00:00Z",
        "validation_command": "python -m pytest -q",
        "validation_exit_code": "0",
        "validation_result": "692 passed in 30.45s",
        "validation_log": str(validation_log),
        "validation_log_exit_code": "0",
        "launcher_sha256": launcher_sha256,
        "status": "production-candidate-core",
    }
    state_raw = _state_bytes(fields)
    release_state = deployment_dir / "RELEASE_STATE"
    shared_state = app_root / "shared" / "RELEASE_STATE"
    _write_bytes(release_state, state_raw, 0o600)
    _write_bytes(shared_state, state_raw, 0o644)
    _write_bytes(
        app_root / "shared" / "current_release",
        f"{release.name}\n".encode(),
        0o644,
    )
    return {
        "app_root": app_root,
        "commit": commit,
        "launcher_sha256": launcher_sha256,
        "release": release,
        "release_state": release_state,
        "shared_launcher": shared_launcher,
        "shared_state": shared_state,
        "versioned_launcher": versioned_launcher,
    }


def test_post_deploy_disk_attestation_accepts_exact_release(tmp_path: Path) -> None:
    fixture = _deploy_fixture(tmp_path)

    result = _run_heredoc(
        "PY_DEPLOY_STATE",
        fixture["app_root"],
        fixture["release"],
        fixture["commit"],
    )

    assert result.returncode == 0, result.stderr
    evidence = json.loads(result.stdout)
    assert evidence["release"] == Path(fixture["release"]).name
    assert evidence["commit"] == fixture["commit"]
    assert evidence["launcher_sha256"] == fixture["launcher_sha256"]


@pytest.mark.parametrize(
    "invalid_case, expected_error",
    (
        ("state-parity", "shared and per-release RELEASE_STATE differ"),
        ("duplicate", "duplicate release-state key"),
        ("malformed", "malformed release-state line"),
        ("extra-field", "exact field set"),
        ("release", "wrong release name"),
        ("path", "wrong release path"),
        ("state-launcher", "launcher hashes do not match"),
        ("versioned-launcher", "shared and versioned launchers differ"),
        ("shared-launcher", "shared and versioned launchers differ"),
    ),
)
def test_post_deploy_disk_attestation_rejects_every_identity_drift(
    tmp_path: Path,
    invalid_case: str,
    expected_error: str,
) -> None:
    fixture = _deploy_fixture(tmp_path)
    release_state = Path(fixture["release_state"])
    shared_state = Path(fixture["shared_state"])
    if invalid_case == "state-parity":
        shared_state.write_bytes(shared_state.read_bytes() + b"status=drift\n")
    elif invalid_case == "duplicate":
        _replace_state_pair(
            release_state,
            shared_state,
            lambda raw: raw + f"commit={fixture['commit']}\n".encode(),
        )
    elif invalid_case == "malformed":
        _replace_state_pair(
            release_state,
            shared_state,
            lambda raw: raw + b"malformed-line\n",
        )
    elif invalid_case == "extra-field":
        _replace_state_pair(
            release_state,
            shared_state,
            lambda raw: raw + b"unexpected=value\n",
        )
    elif invalid_case == "release":
        _replace_state_pair(
            release_state,
            shared_state,
            lambda raw: raw.replace(
                f"release={Path(fixture['release']).name}\n".encode(),
                b"release=wrong\n",
            ),
        )
    elif invalid_case == "path":
        _replace_state_pair(
            release_state,
            shared_state,
            lambda raw: raw.replace(
                f"path={fixture['release']}\n".encode(),
                b"path=/tmp/wrong\n",
            ),
        )
    elif invalid_case == "state-launcher":
        _replace_state_pair(
            release_state,
            shared_state,
            lambda raw: raw.replace(
                f"launcher_sha256={fixture['launcher_sha256']}\n".encode(),
                f"launcher_sha256={'0' * 64}\n".encode(),
            ),
        )
    elif invalid_case == "versioned-launcher":
        _write_bytes(
            Path(fixture["versioned_launcher"]),
            b"#!/usr/bin/env bash\necho versioned-drift\n",
            0o755,
        )
    elif invalid_case == "shared-launcher":
        _write_bytes(
            Path(fixture["shared_launcher"]),
            b"#!/usr/bin/env bash\necho shared-drift\n",
            0o755,
        )

    result = _run_heredoc(
        "PY_DEPLOY_STATE",
        fixture["app_root"],
        fixture["release"],
        fixture["commit"],
    )

    assert result.returncode == 1
    assert expected_error in result.stderr


def _status_fixture(tmp_path: Path) -> dict[str, object]:
    release = tmp_path / "app" / "releases" / "release"
    release.mkdir(parents=True)
    commit = "b" * 40
    launcher_sha256 = "c" * 64
    status = {
        "product": "HUB_Optimus",
        "running_release": str(release),
        "running_commit": commit,
        "running_launcher_sha256": launcher_sha256,
        "configured_current_release": str(release),
        "configured_current_commit": commit,
    }
    response = tmp_path / "status.json"
    response.write_text(json.dumps(status), encoding="utf-8")
    return {
        "commit": commit,
        "launcher_sha256": launcher_sha256,
        "release": release,
        "response": response,
        "status": status,
    }


@pytest.mark.parametrize("block", ("PY_STATUS", "PY_ROLLBACK_STATUS"))
def test_process_attestation_accepts_exact_release_identity(
    tmp_path: Path,
    block: str,
) -> None:
    fixture = _status_fixture(tmp_path)

    result = _run_heredoc(
        block,
        fixture["response"],
        fixture["release"],
        fixture["commit"],
        fixture["launcher_sha256"],
    )

    assert result.returncode == 0, result.stderr
    evidence = json.loads(result.stdout)
    assert evidence["running_release"] == str(fixture["release"])
    assert evidence["configured_current_release"] == str(fixture["release"])


@pytest.mark.parametrize("block", ("PY_STATUS", "PY_ROLLBACK_STATUS"))
@pytest.mark.parametrize(
    "field",
    ("running_release", "configured_current_release"),
)
def test_process_attestation_rejects_wrong_release_identity(
    tmp_path: Path,
    block: str,
    field: str,
) -> None:
    fixture = _status_fixture(tmp_path)
    status = dict(fixture["status"])
    status[field] = str(tmp_path / "app" / "releases" / "wrong")
    Path(fixture["response"]).write_text(json.dumps(status), encoding="utf-8")

    result = _run_heredoc(
        block,
        fixture["response"],
        fixture["release"],
        fixture["commit"],
        fixture["launcher_sha256"],
    )

    assert result.returncode == 1
    assert "release" in result.stderr


def _rollback_fixture(tmp_path: Path) -> dict[str, object]:
    app_root = tmp_path / "app"
    restored = app_root / "releases" / "legacy"
    deployed = app_root / "releases" / "deployed"
    deployed.mkdir(parents=True)
    restored_commit = "d" * 40
    deployed_commit = "e" * 40
    legacy_prefix = restored_commit[:7]
    launcher = b"#!/usr/bin/env bash\necho restored\n"
    launcher_sha256 = hashlib.sha256(launcher).hexdigest()
    versioned_launcher = restored / "ops" / "ec2" / "hub-api.sh"
    shared_launcher = app_root / "shared" / "bin" / "hub-api"
    _write_bytes(versioned_launcher, launcher, 0o755)
    _write_bytes(shared_launcher, launcher, 0o755)
    (app_root / "current").symlink_to(restored, target_is_directory=True)

    legacy_fields = {
        "release": restored.name,
        "commit": legacy_prefix,
        "path": str(restored),
        "validated_at_utc": "2026-07-20T22:56:06Z",
        "validation": "pytest 55 passed",
        "status": "production-candidate-core",
    }
    legacy_raw = _state_bytes(legacy_fields)
    legacy_state = restored / ".hub-deployment" / "LEGACY_RELEASE_STATE"
    _write_bytes(legacy_state, legacy_raw, 0o400)
    adopted_fields = {
        "release": restored.name,
        "requested_ref": restored_commit,
        "requested_ref_kind": "legacy-host-adoption",
        "commit": restored_commit,
        "path": str(restored),
        "adopted_at_utc": "2026-08-02T12:00:00Z",
        "validation_command": "not-run-during-legacy-adoption",
        "validation_exit_code": "not-run",
        "validation_result": (
            "legacy validation claim not re-attested; original state retained by SHA-256"
        ),
        "validation_log": "not-applicable",
        "validation_log_exit_code": "not-run",
        "launcher_sha256": launcher_sha256,
        "status": "adopted-legacy-current",
        "provenance": "adopted-legacy-current-v1",
        "legacy_state_sha256": hashlib.sha256(legacy_raw).hexdigest(),
        "legacy_commit_prefix": legacy_prefix,
    }
    adopted_raw = _state_bytes(adopted_fields)
    release_state = restored / ".hub-deployment" / "RELEASE_STATE"
    shared_state = app_root / "shared" / "RELEASE_STATE"
    _write_bytes(release_state, adopted_raw, 0o600)
    _write_bytes(shared_state, adopted_raw, 0o644)
    _write_bytes(
        app_root / "shared" / "current_release",
        f"{restored.name}\n".encode(),
        0o644,
    )
    rollback_fields = {
        "rolled_back_at_utc": "2026-08-02T12:10:00Z",
        "from_release": deployed.name,
        "from_commit": deployed_commit,
        "to_release": restored.name,
        "to_commit": restored_commit,
        "to_launcher_sha256": launcher_sha256,
    }
    _write_bytes(
        app_root / "shared" / "ROLLBACK_STATE",
        _state_bytes(rollback_fields),
        0o600,
    )
    _write_bytes(
        app_root / "shared" / "last_rollback_from",
        f"{deployed}\n".encode(),
        0o644,
    )
    return {
        "app_root": app_root,
        "deployed": deployed,
        "deployed_commit": deployed_commit,
        "launcher_sha256": launcher_sha256,
        "legacy_state": legacy_state,
        "release_state": release_state,
        "restored": restored,
        "restored_commit": restored_commit,
        "shared_launcher": shared_launcher,
        "shared_state": shared_state,
        "versioned_launcher": versioned_launcher,
    }


def test_post_rollback_disk_attestation_accepts_complete_state(
    tmp_path: Path,
) -> None:
    fixture = _rollback_fixture(tmp_path)

    result = _run_heredoc(
        "PY_ROLLBACK_STATE",
        fixture["restored"],
        fixture["restored_commit"],
        fixture["launcher_sha256"],
        fixture["app_root"],
        fixture["deployed"],
        fixture["deployed_commit"],
        fixture["restored_commit"],
    )

    assert result.returncode == 0, result.stderr
    evidence = json.loads(result.stdout)
    assert evidence["to_commit"] == fixture["restored_commit"]
    assert evidence["to_launcher_sha256"] == fixture["launcher_sha256"]


@pytest.mark.parametrize(
    "invalid_case, expected_error",
    (
        ("state-parity", "shared and per-release rollback RELEASE_STATE differ"),
        ("duplicate", "duplicate state field"),
        ("malformed", "malformed state line"),
        ("missing-field", "exact field set"),
        ("release", "wrong release name"),
        ("path", "wrong release path"),
        ("legacy-evidence", "retained legacy state does not match"),
        ("versioned-launcher", "restored shared and versioned launchers differ"),
        ("shared-launcher", "restored shared and versioned launchers differ"),
    ),
)
def test_post_rollback_disk_attestation_rejects_incomplete_or_drifted_state(
    tmp_path: Path,
    invalid_case: str,
    expected_error: str,
) -> None:
    fixture = _rollback_fixture(tmp_path)
    release_state = Path(fixture["release_state"])
    shared_state = Path(fixture["shared_state"])
    if invalid_case == "state-parity":
        shared_state.write_bytes(shared_state.read_bytes() + b"status=drift\n")
    elif invalid_case == "duplicate":
        _replace_state_pair(
            release_state,
            shared_state,
            lambda raw: raw + f"commit={fixture['restored_commit']}\n".encode(),
        )
    elif invalid_case == "malformed":
        _replace_state_pair(
            release_state,
            shared_state,
            lambda raw: raw + b"malformed-line\n",
        )
    elif invalid_case == "missing-field":
        _replace_state_pair(
            release_state,
            shared_state,
            lambda raw: b"\n".join(
                line
                for line in raw.splitlines()
                if not line.startswith(b"provenance=")
            )
            + b"\n",
        )
    elif invalid_case == "release":
        _replace_state_pair(
            release_state,
            shared_state,
            lambda raw: raw.replace(
                f"release={Path(fixture['restored']).name}\n".encode(),
                b"release=wrong\n",
            ),
        )
    elif invalid_case == "path":
        _replace_state_pair(
            release_state,
            shared_state,
            lambda raw: raw.replace(
                f"path={fixture['restored']}\n".encode(),
                b"path=/tmp/wrong\n",
            ),
        )
    elif invalid_case == "legacy-evidence":
        legacy_state = Path(fixture["legacy_state"])
        legacy_state.chmod(0o600)
        legacy_state.write_bytes(legacy_state.read_bytes() + b"drift=1\n")
        legacy_state.chmod(0o400)
    elif invalid_case == "versioned-launcher":
        _write_bytes(
            Path(fixture["versioned_launcher"]),
            b"#!/usr/bin/env bash\necho versioned-drift\n",
            0o755,
        )
    elif invalid_case == "shared-launcher":
        _write_bytes(
            Path(fixture["shared_launcher"]),
            b"#!/usr/bin/env bash\necho shared-drift\n",
            0o755,
        )

    result = _run_heredoc(
        "PY_ROLLBACK_STATE",
        fixture["restored"],
        fixture["restored_commit"],
        fixture["launcher_sha256"],
        fixture["app_root"],
        fixture["deployed"],
        fixture["deployed_commit"],
        fixture["restored_commit"],
    )

    assert result.returncode == 1
    assert expected_error in result.stderr


def test_runbook_and_preflight_inventory_include_all_mutating_tools() -> None:
    runbook = RUNBOOK.read_text(encoding="utf-8")
    preflight = (ROOT / "ops" / "ec2" / "preflight-deploy.sh").read_text(
        encoding="utf-8"
    )
    for command in (
        "basename",
        "chmod",
        "cmp",
        "cp",
        "date",
        "dirname",
        "install",
        "ln",
        "mkdir",
        "mktemp",
        "mv",
        "rm",
        "rmdir",
        "stat",
        "tee",
        "tr",
    ):
        assert command in runbook.split(")", 1)[0]
        assert command in preflight.split("; do", 1)[0]
