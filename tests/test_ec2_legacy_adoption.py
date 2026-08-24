from __future__ import annotations

import hashlib
import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
ADOPT = ROOT / "ops" / "ec2" / "adopt-legacy-current.sh"
PREFLIGHT = ROOT / "ops" / "ec2" / "preflight-deploy.sh"
LEGACY_FIXTURE = (
    ROOT / "tests" / "fixtures" / "ec2" / "legacy_release_state_9d677.txt"
)
LEGACY_COMMIT = "9d6771994095e4fc04e8fdbf2caa644ccb002ab1"
LEGACY_LAUNCHER_SHA256 = (
    "f29996d6078c0b7ecbd29699383fd0e71a05d5e35f7ecf3437dbd0cc0e87a219"
)


def _run(
    args: list[str | Path],
    *,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(arg) for arg in args],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def _git(repo: Path, *args: str) -> str:
    result = _run(["git", "-C", repo, *args])
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


def _state(path: Path) -> dict[str, str]:
    return dict(
        line.split("=", 1)
        for line in path.read_text(encoding="utf-8").splitlines()
    )


def _source_repository(
    path: Path,
    *,
    launcher_bytes: bytes | None = None,
) -> str:
    path.mkdir()
    assert _run(["git", "init", "-q", path]).returncode == 0
    _git(path, "config", "user.email", "tests@example.invalid")
    _git(path, "config", "user.name", "HUB tests")
    launcher = path / "ops" / "ec2" / "hub-api.sh"
    launcher.parent.mkdir(parents=True)
    launcher.write_bytes(
        launcher_bytes
        if launcher_bytes is not None
        else b"#!/usr/bin/env bash\necho legacy-api\n"
    )
    launcher.chmod(0o755)
    (path / "tracked.txt").write_text("reviewed release\n", encoding="utf-8")
    _git(path, "add", ".")
    _git(path, "commit", "-qm", "reviewed legacy release")
    return _git(path, "rev-parse", "HEAD")


def _legacy_environment(
    case_root: Path,
    *,
    launcher_bytes: bytes | None = None,
    fixture_format: bool = False,
) -> tuple[Path, Path, str, dict[str, str]]:
    source = case_root / "source"
    commit = _source_repository(source, launcher_bytes=launcher_bytes)
    app_root = case_root / "app"
    release = app_root / "releases" / "20260720T225606Z"
    release.parent.mkdir(parents=True)
    clone = _run(["git", "clone", "-q", "--no-hardlinks", source, release])
    assert clone.returncode == 0, clone.stderr
    _git(release, "checkout", "-q", "--detach", commit)

    shared = app_root / "shared"
    shared_launcher = shared / "bin" / "hub-api"
    shared_launcher.parent.mkdir(parents=True)
    shutil.copy2(release / "ops" / "ec2" / "hub-api.sh", shared_launcher)
    (app_root / "current").symlink_to(release, target_is_directory=True)
    (shared / "current_release").write_text(
        f"{release.name}\n",
        encoding="utf-8",
    )
    (shared / "previous_release").write_text(
        f"{app_root / 'releases' / 'historical-before-1831'}\n",
        encoding="utf-8",
    )
    if fixture_format:
        legacy_state = LEGACY_FIXTURE.read_text(encoding="utf-8")
        legacy_state = legacy_state.replace("/opt/hub-optimus", str(app_root))
        legacy_state = legacy_state.replace("commit=9d67719", f"commit={commit[:7]}")
    else:
        legacy_state = "\n".join(
            (
                f"release={release.name}",
                f"commit={commit[:7]}",
                f"path={release}",
                "validated_at_utc=2026-07-20T22:56:06Z",
                "validation=pytest 55 passed",
                "status=production-candidate-core",
                "",
            )
        )
    (shared / "RELEASE_STATE").write_text(legacy_state, encoding="utf-8")
    env = os.environ.copy()
    env["HUB_OPTIMUS_APP_ROOT"] = str(app_root)
    env["HUB_OPTIMUS_REPO_URL"] = str(source)
    return app_root, release, commit, env


def _snapshot(app_root: Path, release: Path) -> dict[str, object]:
    snapshot: dict[str, object] = {
        "deployment_dir_present": (release / ".hub-deployment").exists(),
    }
    for name, path in {
        "current": app_root / "current",
        "shared_launcher": app_root / "shared" / "bin" / "hub-api",
        "shared_state": app_root / "shared" / "RELEASE_STATE",
        "current_marker": app_root / "shared" / "current_release",
        "previous_pointer": app_root / "shared" / "previous_release",
        "release_state": release / ".hub-deployment" / "RELEASE_STATE",
        "legacy_evidence": (
            release / ".hub-deployment" / "LEGACY_RELEASE_STATE"
        ),
        "git_exclude": release / ".git" / "info" / "exclude",
    }.items():
        present = path.exists() or path.is_symlink()
        snapshot[f"{name}_present"] = present
        if not present:
            continue
        snapshot[f"{name}_mode"] = stat.S_IMODE(path.lstat().st_mode)
        if path.is_symlink():
            snapshot[f"{name}_target"] = os.readlink(path)
        else:
            snapshot[f"{name}_bytes"] = path.read_bytes()
    return snapshot


def _write_executable(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")
    path.chmod(0o755)


def test_adopts_9d677_format_and_is_idempotent(tmp_path: Path) -> None:
    fixture = LEGACY_FIXTURE.read_text(encoding="utf-8")
    assert "commit=9d67719\n" in fixture
    assert _git(ROOT, "rev-parse", "--short=7", LEGACY_COMMIT) == "9d67719"
    historical_launcher = subprocess.run(
        ["git", "-C", str(ROOT), "show", f"{LEGACY_COMMIT}:ops/ec2/hub-api.sh"],
        capture_output=True,
        check=True,
    ).stdout
    assert hashlib.sha256(historical_launcher).hexdigest() == LEGACY_LAUNCHER_SHA256
    app_root, release, commit, env = _legacy_environment(
        tmp_path,
        launcher_bytes=historical_launcher,
        fixture_format=True,
    )
    shared = app_root / "shared"
    shared_launcher = shared / "bin" / "hub-api"
    rendered_fixture = (shared / "RELEASE_STATE").read_text(encoding="utf-8")
    legacy_state_sha256 = hashlib.sha256(rendered_fixture.encode()).hexdigest()

    first = _run([ADOPT, commit], env=env)

    assert first.returncode == 0, first.stderr
    release_state_path = release / ".hub-deployment" / "RELEASE_STATE"
    state = _state(release_state_path)
    legacy_evidence = release / ".hub-deployment" / "LEGACY_RELEASE_STATE"
    assert state["commit"] == commit
    assert state["requested_ref"] == commit
    assert state["requested_ref_kind"] == "legacy-host-adoption"
    assert state["launcher_sha256"] == LEGACY_LAUNCHER_SHA256
    assert state["provenance"] == "adopted-legacy-current-v1"
    assert state["legacy_state_sha256"] == legacy_state_sha256
    assert state["legacy_commit_prefix"] == commit[:7]
    assert state["validation_command"] == "not-run-during-legacy-adoption"
    assert legacy_evidence.read_bytes() == rendered_fixture.encode()
    assert stat.S_IMODE(legacy_evidence.stat().st_mode) == 0o400
    assert (shared / "RELEASE_STATE").read_bytes() == release_state_path.read_bytes()
    assert hashlib.sha256(shared_launcher.read_bytes()).hexdigest() == (
        LEGACY_LAUNCHER_SHA256
    )
    exclude = (release / ".git" / "info" / "exclude").read_text(encoding="utf-8")
    assert exclude.splitlines().count(".hub-deployment/") == 1
    assert not list(shared.glob("legacy-adoption.*"))

    before_second_run = _snapshot(app_root, release)
    second = _run([ADOPT, commit], env=env)

    assert second.returncode == 0, second.stderr
    assert "already adopted and exact" in second.stdout
    assert _snapshot(app_root, release) == before_second_run
    assert not list(shared.glob("legacy-adoption.*"))


def test_success_is_postvalidated_before_transaction_closes() -> None:
    text = ADOPT.read_text(encoding="utf-8")
    publish = text.index("Publishing exact shared release state")
    postvalidate = text.index("validate_complete_adoption", publish)
    close = text.index("MUTATION_STARTED=0", postvalidate)

    assert publish < postvalidate < close
    assert 'LEGACY_RELEASE_STATE"' in text
    assert "install -m 0400" in text


def test_preflight_inventories_unattested_historical_pointer(
    tmp_path: Path,
) -> None:
    app_root, current, commit, env = _legacy_environment(tmp_path)
    adopted = _run([ADOPT, commit], env=env)
    assert adopted.returncode == 0, adopted.stderr

    source = Path(env["HUB_OPTIMUS_REPO_URL"])
    previous = app_root / "releases" / "historical-before-1831"
    clone = _run(["git", "clone", "-q", "--no-hardlinks", source, previous])
    assert clone.returncode == 0, clone.stderr
    _git(previous, "checkout", "-q", "--detach", commit)
    (app_root / "shared" / "previous_release").write_text(
        f"{previous}\n",
        encoding="utf-8",
    )
    assert not (previous / ".hub-deployment" / "RELEASE_STATE").exists()

    fake_bin = tmp_path / "preflight-bin"
    fake_bin.mkdir()
    real_awk = shutil.which("awk")
    assert real_awk is not None
    _write_executable(
        fake_bin / "awk",
        "#!/usr/bin/env bash\n"
        "if [ \"${2:-}\" = '/proc/loadavg' ]; then\n"
        "  printf '0.01\\n'\n"
        "else\n"
        f"  exec {real_awk} \"$@\"\n"
        "fi\n",
    )
    _write_executable(
        fake_bin / "df",
        "#!/usr/bin/env bash\n"
        "printf 'Filesystem blocks Used Available Capacity Mounted-on\\n'\n"
        "printf 'fixture 10000000 1 9000000 1%% /\\n'\n",
    )
    _write_executable(
        fake_bin / "free",
        "#!/usr/bin/env bash\n"
        "printf 'Mem: 1000000 1000 1000 0 0 900000\\n'\n",
    )
    for command_name in ("curl", "sudo", "systemctl"):
        _write_executable(fake_bin / command_name, "#!/usr/bin/env bash\nexit 0\n")
    env["PATH"] = f"{fake_bin}{os.pathsep}{env['PATH']}"

    result = _run([PREFLIGHT, "f" * 40, "https://example.com/article"], env=env)

    assert result.returncode == 0, result.stderr
    assert f"current_release={current}" in result.stdout
    assert f"previous_release={previous}" in result.stdout
    assert f"previous_commit={commit}" in result.stdout
    assert (
        "previous_state_status=legacy-unattested-not-deploy-rollback-target"
        in result.stdout
    )
    assert "[preflight] PASS" in result.stdout


@pytest.mark.parametrize(
    ("corruption", "expected_error"),
    (
        ("status=duplicate", "contains a duplicate field: status"),
        ("malformed-state-line", "contains a malformed state line"),
    ),
)
def test_preflight_rejects_matching_but_malformed_current_state(
    tmp_path: Path,
    corruption: str,
    expected_error: str,
) -> None:
    app_root, release, commit, env = _legacy_environment(tmp_path)
    adopted = _run([ADOPT, commit], env=env)
    assert adopted.returncode == 0, adopted.stderr

    release_state = release / ".hub-deployment" / "RELEASE_STATE"
    shared_state = app_root / "shared" / "RELEASE_STATE"
    corrupted = release_state.read_text(encoding="utf-8") + f"{corruption}\n"
    release_state.write_text(corrupted, encoding="utf-8")
    shared_state.write_text(corrupted, encoding="utf-8")

    fake_bin = tmp_path / "preflight-schema-bin"
    fake_bin.mkdir()
    for command_name in ("sudo", "systemctl"):
        _write_executable(fake_bin / command_name, "#!/usr/bin/env bash\nexit 0\n")
    env["PATH"] = f"{fake_bin}{os.pathsep}{env['PATH']}"

    result = _run(
        [PREFLIGHT, "f" * 40, "https://example.com/article"],
        env=env,
    )

    assert result.returncode == 1
    assert expected_error in result.stderr


@pytest.mark.parametrize(
    "stage",
    (
        "git-exclude",
        "deployment-dir",
        "legacy-state-evidence",
        "release-state",
        "shared-release-state",
    ),
)
def test_each_adoption_failpoint_restores_exact_legacy_state(
    tmp_path: Path,
    stage: str,
) -> None:
    app_root, release, commit, env = _legacy_environment(tmp_path)
    before = _snapshot(app_root, release)
    env["HUB_OPTIMUS_TEST_LEGACY_ADOPTION_FAIL_AFTER_MUTATION"] = stage

    failed = _run([ADOPT, commit], env=env)

    assert failed.returncode == 1
    assert f"injected test failure after mutation stage: {stage}" in failed.stderr
    assert "Pre-adoption state restored" in failed.stderr
    assert _snapshot(app_root, release) == before
    retained = list((app_root / "shared").glob("legacy-adoption.*"))
    assert len(retained) == 1
    assert (retained[0] / "pre-adoption-state").is_dir()
    assert "Pre-adoption state restored" in (
        retained[0] / "recovery.log"
    ).read_text(encoding="utf-8")


@pytest.mark.parametrize(
    "key",
    ("release", "commit", "path", "validated_at_utc", "validation", "status"),
)
def test_legacy_state_rejects_every_duplicate_field_before_mutation(
    tmp_path: Path,
    key: str,
) -> None:
    app_root, release, commit, env = _legacy_environment(tmp_path)
    state_path = app_root / "shared" / "RELEASE_STATE"
    value = _state(state_path)[key]
    with state_path.open("a", encoding="utf-8") as handle:
        handle.write(f"{key}={value}\n")
    before = _snapshot(app_root, release)

    failed = _run([ADOPT, commit], env=env)

    assert failed.returncode == 1
    assert f"must contain exactly one {key} field" in failed.stderr
    assert _snapshot(app_root, release) == before
    assert not list((app_root / "shared").glob("legacy-adoption.*"))


def test_failed_postvalidation_restores_exact_legacy_state(tmp_path: Path) -> None:
    app_root, release, commit, env = _legacy_environment(tmp_path)
    before = _snapshot(app_root, release)
    env[
        "HUB_OPTIMUS_TEST_LEGACY_ADOPTION_CORRUPT_BEFORE_POSTVALIDATE"
    ] = "shared-release-state"

    failed = _run([ADOPT, commit], env=env)

    assert failed.returncode == 1
    assert "differs from the adopted current state" in failed.stderr
    assert "Pre-adoption state restored" in failed.stderr
    assert _snapshot(app_root, release) == before


def test_adoption_still_restores_when_recovery_log_cannot_open(
    tmp_path: Path,
) -> None:
    app_root, release, commit, env = _legacy_environment(tmp_path)
    before = _snapshot(app_root, release)
    unusable_log = tmp_path / "recovery-log-is-a-directory"
    unusable_log.mkdir()
    env["HUB_OPTIMUS_TEST_LEGACY_ADOPTION_FAIL_AFTER_MUTATION"] = "release-state"
    env["HUB_OPTIMUS_TEST_LEGACY_ADOPTION_RECOVERY_LOG_PATH"] = str(
        unusable_log
    )

    failed = _run([ADOPT, commit], env=env)

    assert failed.returncode == 1
    assert _snapshot(app_root, release) == before
    assert "Restoring exact pre-adoption state" in failed.stderr
    assert "State restored, but recovery evidence could not be recorded" in (
        failed.stderr
    )
    assert "[legacy-adoption:recovery] Pre-adoption state restored" not in (
        failed.stderr
    )


@pytest.mark.parametrize(
    "invalid_case, expected_error",
    (
        ("commit", "Current full commit does not match"),
        ("origin", "origin does not match"),
        ("symlink", "outside the managed releases directory"),
        ("shared-launcher", "does not exactly match"),
        ("dirty-launcher", "worktree is not clean"),
    ),
)
def test_adoption_rejects_unattested_identity_before_mutation(
    tmp_path: Path,
    invalid_case: str,
    expected_error: str,
) -> None:
    app_root, release, commit, env = _legacy_environment(tmp_path)
    expected_commit = commit
    if invalid_case == "commit":
        expected_commit = "0" * 40
    elif invalid_case == "origin":
        _git(release, "remote", "set-url", "origin", str(tmp_path / "other"))
    elif invalid_case == "symlink":
        outside = tmp_path / "outside-release"
        outside.mkdir()
        (app_root / "current").unlink()
        (app_root / "current").symlink_to(outside, target_is_directory=True)
    elif invalid_case == "shared-launcher":
        launcher = app_root / "shared" / "bin" / "hub-api"
        launcher.write_text("#!/usr/bin/env bash\necho drift\n", encoding="utf-8")
        launcher.chmod(0o755)
    elif invalid_case == "dirty-launcher":
        (release / "ops" / "ec2" / "hub-api.sh").write_text(
            "#!/usr/bin/env bash\necho dirty\n",
            encoding="utf-8",
        )
    before = _snapshot(app_root, release)

    failed = _run([ADOPT, expected_commit], env=env)

    assert failed.returncode == 1
    assert expected_error in failed.stderr
    assert _snapshot(app_root, release) == before
    assert not list((app_root / "shared").glob("legacy-adoption.*"))
