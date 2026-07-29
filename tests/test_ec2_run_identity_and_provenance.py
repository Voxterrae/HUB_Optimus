from __future__ import annotations

import json
import os
import re
import stat
import subprocess
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HUB_CORE = ROOT / "ops" / "ec2" / "hub-core.sh"
HUB_API = ROOT / "ops" / "ec2" / "hub-api.sh"
HUB_OPS = ROOT / "ops" / "ec2" / "hub-ops.sh"
DEPLOY = ROOT / "ops" / "ec2" / "deploy-current.sh"
ROLLBACK = ROOT / "ops" / "ec2" / "rollback-current.sh"
RUN_ID_RE = re.compile(r"^\d{8}T\d{6}Z\.[A-Za-z0-9]{6}$")


def _run(
    args: list[str | Path],
    *,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(arg) for arg in args],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def _git(repo: Path, *args: str) -> str:
    result = _run(["git", "-C", repo, *args])
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


def _init_git_repo(path: Path) -> str:
    path.mkdir(parents=True)
    assert _run(["git", "init", "-q", path]).returncode == 0
    _git(path, "config", "user.email", "tests@example.invalid")
    _git(path, "config", "user.name", "HUB tests")
    (path / "tracked.txt").write_text("release\n", encoding="utf-8")
    _git(path, "add", "tracked.txt")
    _git(path, "commit", "-qm", "test release")
    return _git(path, "rev-parse", "HEAD")


def _state(path: Path) -> dict[str, str]:
    return dict(
        line.split("=", 1)
        for line in path.read_text(encoding="utf-8").splitlines()
        if "=" in line
    )


def _load_embedded_api_namespace() -> dict:
    script = HUB_API.read_text(encoding="utf-8")
    embedded = script.split("<<'PY'\n", 1)[1].split("\nPY\n", 1)[0]
    namespace = {"__name__": "hub_api_run_identity_test"}
    exec(compile(embedded, str(HUB_API), "exec"), namespace)
    return namespace


def _fake_runtime_bin(path: Path) -> Path:
    bin_dir = path / "fake-bin"
    bin_dir.mkdir()
    python = bin_dir / "python"
    python.write_text(
        "#!/usr/bin/env bash\n"
        "printf 'fake pytest passed\\n'\n",
        encoding="utf-8",
    )
    python.chmod(0o755)

    date = bin_dir / "date"
    date.write_text(
        "#!/usr/bin/env bash\n"
        "case \"$*\" in\n"
        "  *+%Y%m%dT%H%M%SZ*) printf '20260729T120000Z\\n' ;;\n"
        "  *+%Y-%m-%dT%H:%M:%SZ*) printf '2026-07-29T12:00:00Z\\n' ;;\n"
        "  *) exec /bin/date \"$@\" ;;\n"
        "esac\n",
        encoding="utf-8",
    )
    date.chmod(0o755)
    return bin_dir


def test_same_second_hub_core_runs_get_exclusive_ids(tmp_path: Path) -> None:
    app_root = tmp_path / "app"
    release = app_root / "releases" / "current-release"
    commit = _init_git_repo(release)
    (release / ".venv" / "bin").mkdir(parents=True)
    (release / ".venv" / "bin" / "activate").write_text(
        "deactivate() { :; }\n",
        encoding="utf-8",
    )
    (app_root / "shared").mkdir(parents=True)
    (app_root / "current").symlink_to(release, target_is_directory=True)

    fake_bin = _fake_runtime_bin(tmp_path)
    env = os.environ.copy()
    env["HUB_OPTIMUS_APP_ROOT"] = str(app_root)
    env["PATH"] = f"{fake_bin}{os.pathsep}{env['PATH']}"

    processes = [
        subprocess.Popen(
            ["bash", str(HUB_CORE), "test"],
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        for _ in range(12)
    ]
    completed = [process.communicate(timeout=20) for process in processes]

    run_ids: list[str] = []
    for process, (stdout, stderr) in zip(processes, completed, strict=True):
        assert process.returncode == 0, stderr
        marker = re.search(r"^\[hub-core:run-id\] (\S+)$", stdout, re.MULTILINE)
        assert marker is not None
        run_ids.append(marker.group(1))

    assert len(set(run_ids)) == len(run_ids)
    assert all(run_id.startswith("20260729T120000Z.") for run_id in run_ids)
    assert all(RUN_ID_RE.fullmatch(run_id) for run_id in run_ids)

    for run_id in run_ids:
        run_dir = app_root / "shared" / "runs" / "test" / run_id
        run_state = _state(run_dir / "RUN_STATE")
        assert stat.S_IMODE(run_dir.stat().st_mode) == 0o700
        assert run_state["run_id"] == run_id
        assert run_state["commit"] == commit


def test_hub_core_pins_one_release_for_the_complete_run(
    tmp_path: Path,
) -> None:
    app_root = tmp_path / "app"
    release_a = app_root / "releases" / "release-a"
    release_b = app_root / "releases" / "release-b"
    commit_a = _init_git_repo(release_a)
    _init_git_repo(release_b)
    (release_b / "tracked.txt").write_text("release-b\n", encoding="utf-8")
    _git(release_b, "add", "tracked.txt")
    _git(release_b, "commit", "-qm", "different release")
    commit_b = _git(release_b, "rev-parse", "HEAD")
    assert commit_a != commit_b

    ready = tmp_path / "engine-ready"
    proceed = tmp_path / "engine-proceed"
    activate = release_a / ".venv" / "bin" / "activate"
    activate.parent.mkdir(parents=True)
    activate.write_text(
        "python() {\n"
        "  touch \"$HUB_TEST_ENGINE_READY\"\n"
        "  while [ ! -f \"$HUB_TEST_ENGINE_PROCEED\" ]; do sleep 0.01; done\n"
        "  local previous=''\n"
        "  local output=''\n"
        "  for argument in \"$@\"; do\n"
        "    if [ \"$previous\" = '--output' ]; then output=\"$argument\"; fi\n"
        "    previous=\"$argument\"\n"
        "  done\n"
        "  printf '{\"release_path\":\"%s\"}\\n' \"$PWD\" > \"$output\"\n"
        "}\n"
        "deactivate() { :; }\n",
        encoding="utf-8",
    )

    (app_root / "shared").mkdir(parents=True)
    current = app_root / "current"
    current.symlink_to(release_a, target_is_directory=True)
    input_path = tmp_path / "case.json"
    input_path.write_text("{}\n", encoding="utf-8")
    fake_bin = _fake_runtime_bin(tmp_path)
    env = os.environ.copy()
    env["HUB_OPTIMUS_APP_ROOT"] = str(app_root)
    env["HUB_TEST_ENGINE_READY"] = str(ready)
    env["HUB_TEST_ENGINE_PROCEED"] = str(proceed)
    env["PATH"] = f"{fake_bin}{os.pathsep}{env['PATH']}"

    process = subprocess.Popen(
        ["bash", str(HUB_CORE), "analyze", str(input_path)],
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    deadline = time.monotonic() + 5
    while not ready.exists() and process.poll() is None:
        if time.monotonic() >= deadline:
            process.kill()
            raise AssertionError("fake engine did not start")
        time.sleep(0.01)

    replacement = app_root / "current.new"
    replacement.symlink_to(release_b, target_is_directory=True)
    os.replace(replacement, current)
    proceed.touch()
    stdout, stderr = process.communicate(timeout=10)

    assert process.returncode == 0, stderr
    marker = re.search(r"^\[hub-core:run-id\] (\S+)$", stdout, re.MULTILINE)
    assert marker is not None
    run_dir = app_root / "shared" / "runs" / "analyze" / marker.group(1)
    run_state = _state(run_dir / "RUN_STATE")
    result = json.loads((run_dir / "analysis_result.json").read_text())
    assert current.resolve() == release_b
    assert run_state["path"] == str(release_a)
    assert run_state["release"] == "release-a"
    assert run_state["commit"] == commit_a
    assert run_state["input"] == str(run_dir / "input_case.json")
    assert result["release_path"] == str(release_a)


def test_api_uses_its_own_run_marker_and_cleans_private_input(
    tmp_path: Path,
) -> None:
    namespace = _load_embedded_api_namespace()
    shared = tmp_path / "shared"
    namespace["SHARED"] = shared
    target_run_id = "20260729T120000Z.Ab12Cd"
    unrelated_run_id = "20260729T120000Z.Zz99Yy"
    payload = {
        "case_id": "request-bound",
        "core_version_ref": "v1",
        "input_summary": "Request-owned input.",
    }
    seen_case_paths: list[Path] = []

    def fake_run_command(
        args: list[str],
        input_text: str | None = None,
    ) -> tuple[int, str, str]:
        assert input_text is None
        assert args[:2] == [
            "/opt/hub-optimus/shared/bin/hub-core",
            "analyze",
        ]
        case_path = Path(args[2])
        seen_case_paths.append(case_path)
        assert case_path.name.startswith("case-")
        assert case_path.name != "api-case.json"
        assert stat.S_IMODE(case_path.stat().st_mode) == 0o600
        assert json.loads(case_path.read_text(encoding="utf-8")) == payload

        target_dir = shared / "runs" / "analyze" / target_run_id
        unrelated_dir = shared / "runs" / "analyze" / unrelated_run_id
        target_dir.mkdir(parents=True)
        unrelated_dir.mkdir(parents=True)
        (target_dir / "analysis_result.json").write_text(
            '{"case_id":"request-bound","status":"draft"}\n',
            encoding="utf-8",
        )
        (unrelated_dir / "analysis_result.json").write_text(
            '{"case_id":"unrelated","status":"draft"}\n',
            encoding="utf-8",
        )
        return (
            0,
            f"[hub-core:run-id] {target_run_id}\n",
            "",
        )

    namespace["run_command"] = fake_run_command
    handler = object.__new__(namespace["Handler"])
    handler.read_json_body = lambda limit: payload
    responses: list[tuple[int, dict]] = []
    handler.send_json = lambda status_code, body: responses.append(
        (status_code, body)
    )

    handler.handle_analyze()

    assert len(seen_case_paths) == 1
    assert not seen_case_paths[0].exists()
    assert stat.S_IMODE(seen_case_paths[0].parent.stat().st_mode) == 0o700
    assert responses == [
        (
            200,
            {
                "status": "ok",
                "run_id": target_run_id,
                "run_path": str(
                    shared / "runs" / "analyze" / target_run_id
                ),
                "analysis_result": {
                    "case_id": "request-bound",
                    "status": "draft",
                },
            },
        )
    ]


def test_api_rejects_missing_ambiguous_or_unsafe_run_markers() -> None:
    namespace = _load_embedded_api_namespace()
    parse = namespace["core_run_id"]
    valid = "20260729T120000Z.Ab12Cd"

    assert parse(f"[hub-core:run-id] {valid}\n") == valid
    assert parse("") is None
    assert parse(
        f"[hub-core:run-id] {valid}\n[hub-core:run-id] {valid}\n"
    ) is None
    assert parse("[hub-core:run-id] ../../current\n") is None


def test_api_failure_keeps_its_run_identity_and_cleans_input(
    tmp_path: Path,
) -> None:
    namespace = _load_embedded_api_namespace()
    shared = tmp_path / "shared"
    namespace["SHARED"] = shared
    run_id = "20260729T120000Z.Fa11Ed"
    seen_case_path: Path | None = None

    def fake_run_command(
        args: list[str],
        input_text: str | None = None,
    ) -> tuple[int, str, str]:
        nonlocal seen_case_path
        assert input_text is None
        seen_case_path = Path(args[2])
        assert seen_case_path.exists()
        return 1, f"[hub-core:run-id] {run_id}\n", "engine failed"

    namespace["run_command"] = fake_run_command
    handler = object.__new__(namespace["Handler"])
    handler.read_json_body = lambda limit: {
        "case_id": "failed-request",
        "core_version_ref": "v1",
        "input_summary": "Failure fixture.",
    }
    responses: list[tuple[int, dict]] = []
    handler.send_json = lambda status_code, body: responses.append(
        (status_code, body)
    )

    handler.handle_analyze()

    assert seen_case_path is not None
    assert not seen_case_path.exists()
    assert responses == [
        (
            500,
            {
                "error": "analysis failed",
                "stderr": "engine failed",
                "stdout": f"[hub-core:run-id] {run_id}\n",
                "run_id": run_id,
                "run_path": str(shared / "runs" / "analyze" / run_id),
            },
        )
    ]


def _source_repository(path: Path) -> tuple[str, str]:
    path.mkdir()
    assert _run(["git", "init", "-q", path]).returncode == 0
    _git(path, "config", "user.email", "tests@example.invalid")
    _git(path, "config", "user.name", "HUB tests")

    (path / "ops" / "ec2").mkdir(parents=True)
    (path / "requirements-dev.txt").write_text("pytest\n", encoding="utf-8")
    launcher = path / "ops" / "ec2" / "hub-api.sh"
    launcher.write_text("#!/usr/bin/env bash\necho api-v1\n", encoding="utf-8")
    launcher.chmod(0o755)
    (path / "version.txt").write_text("reviewed\n", encoding="utf-8")
    _git(path, "add", ".")
    _git(path, "commit", "-qm", "reviewed release")
    reviewed_commit = _git(path, "rev-parse", "HEAD")
    _git(path, "tag", "reviewed-v1")

    launcher.write_text("#!/usr/bin/env bash\necho api-v2\n", encoding="utf-8")
    (path / "version.txt").write_text("newer-head\n", encoding="utf-8")
    _git(path, "add", ".")
    _git(path, "commit", "-qm", "newer branch head")
    head_commit = _git(path, "rev-parse", "HEAD")
    return reviewed_commit, head_commit


def _fake_deploy_python(path: Path) -> Path:
    bin_dir = path / "deploy-bin"
    bin_dir.mkdir()
    python3 = bin_dir / "python3"
    python3.write_text(
        "#!/usr/bin/env bash\n"
        "set -eu\n"
        "test \"${1:-}\" = '-m'\n"
        "test \"${2:-}\" = 'venv'\n"
        "mkdir -p \"$3/bin\"\n"
        "cat > \"$3/bin/activate\" <<'ACTIVATE'\n"
        "python() {\n"
        "  if [ \"${1:-}\" = '-m' ] && [ \"${2:-}\" = 'pytest' ]; then\n"
        "    printf '%s\\n' \"${HUB_TEST_VALIDATION_OUTPUT:-17 passed in 0.01s}\"\n"
        "    return \"${HUB_TEST_VALIDATION_EXIT:-0}\"\n"
        "  fi\n"
        "  return 0\n"
        "}\n"
        "deactivate() { :; }\n"
        "ACTIVATE\n",
        encoding="utf-8",
    )
    python3.chmod(0o755)
    return bin_dir


def _deploy_env(
    app_root: Path,
    source_repo: Path,
    fake_bin: Path,
) -> dict[str, str]:
    env = os.environ.copy()
    env["HUB_OPTIMUS_APP_ROOT"] = str(app_root)
    env["HUB_OPTIMUS_REPO_URL"] = str(source_repo)
    env["PATH"] = f"{fake_bin}{os.pathsep}{env['PATH']}"
    return env


def test_deploy_is_ref_bound_records_validation_and_rolls_back(
    tmp_path: Path,
) -> None:
    source_repo = tmp_path / "source"
    reviewed_commit, head_commit = _source_repository(source_repo)
    fake_bin = _fake_deploy_python(tmp_path)
    app_root = tmp_path / "app"
    env = _deploy_env(app_root, source_repo, fake_bin)

    first = _run([DEPLOY, "reviewed-v1"], env=env)
    assert first.returncode == 0, first.stderr
    first_release = (app_root / "current").resolve()
    assert _git(first_release, "rev-parse", "HEAD") == reviewed_commit
    first_state = _state(app_root / "shared" / "RELEASE_STATE")
    assert first_state["requested_ref"] == "reviewed-v1"
    assert first_state["requested_ref_kind"] == "tag"
    assert first_state["commit"] == reviewed_commit
    assert first_state["validation_command"] == "python -m pytest -q"
    assert first_state["validation_exit_code"] == "0"
    assert first_state["validation_log_exit_code"] == "0"
    assert first_state["validation_result"] == "17 passed in 0.01s"
    assert "55 passed" not in (app_root / "shared" / "RELEASE_STATE").read_text()

    second = _run([DEPLOY, head_commit], env=env)
    assert second.returncode == 0, second.stderr
    second_release = (app_root / "current").resolve()
    assert second_release != first_release
    assert _git(second_release, "rev-parse", "HEAD") == head_commit
    second_state = _state(app_root / "shared" / "RELEASE_STATE")
    assert second_state["requested_ref"] == head_commit
    assert second_state["requested_ref_kind"] == "commit"
    assert second_state["commit"] == head_commit
    assert (app_root / "shared" / "bin" / "hub-api").read_text(
        encoding="utf-8"
    ).endswith("echo api-v2\n")

    rolled_back = _run([ROLLBACK], env=env)
    assert rolled_back.returncode == 0, rolled_back.stderr
    assert (app_root / "current").resolve() == first_release
    restored_state = _state(app_root / "shared" / "RELEASE_STATE")
    assert restored_state["commit"] == reviewed_commit
    rollback_state = _state(app_root / "shared" / "ROLLBACK_STATE")
    assert rollback_state["from_commit"] == head_commit
    assert rollback_state["to_commit"] == reviewed_commit
    assert (app_root / "shared" / "bin" / "hub-api").read_text(
        encoding="utf-8"
    ).endswith("echo api-v1\n")


def test_failed_validation_is_recorded_without_switching_current(
    tmp_path: Path,
) -> None:
    source_repo = tmp_path / "source"
    reviewed_commit, _ = _source_repository(source_repo)
    fake_bin = _fake_deploy_python(tmp_path)
    app_root = tmp_path / "app"
    env = _deploy_env(app_root, source_repo, fake_bin)
    env["HUB_TEST_VALIDATION_EXIT"] = "1"
    env["HUB_TEST_VALIDATION_OUTPUT"] = "2 failed in 0.01s"

    result = _run([DEPLOY, reviewed_commit], env=env)

    assert result.returncode == 1
    assert "validation failed (exit 1): 2 failed in 0.01s" in result.stderr
    assert not (app_root / "current").exists()
    releases = list((app_root / "releases").iterdir())
    assert len(releases) == 1
    failed_state = _state(
        releases[0] / ".hub-deployment" / "RELEASE_STATE"
    )
    assert failed_state["commit"] == reviewed_commit
    assert failed_state["validation_command"] == "python -m pytest -q"
    assert failed_state["validation_exit_code"] == "1"
    assert failed_state["validation_result"] == "2 failed in 0.01s"
    assert failed_state["status"] == "validation-failed"


def test_deploy_requires_explicit_ref_and_hub_ops_forwards_it(
    tmp_path: Path,
) -> None:
    app_root = tmp_path / "app"
    env = os.environ.copy()
    env["HUB_OPTIMUS_APP_ROOT"] = str(app_root)

    result = _run([DEPLOY], env=env)

    assert result.returncode == 2
    assert not (app_root / "current").exists()
    hub_ops = HUB_OPS.read_text(encoding="utf-8")
    assert "  deploy)\n    shift\n" in hub_ops
    assert 'deploy-current" "$@"' in hub_ops
