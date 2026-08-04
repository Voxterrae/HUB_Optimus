from __future__ import annotations

import hashlib
import json
import os
import re
import shlex
import shutil
import stat
import subprocess
import time
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
HUB_CORE = ROOT / "ops" / "ec2" / "hub-core.sh"
HUB_API = ROOT / "ops" / "ec2" / "hub-api.sh"
HUB_OPS = ROOT / "ops" / "ec2" / "hub-ops.sh"
DEPLOY = ROOT / "ops" / "ec2" / "deploy-current.sh"
ROLLBACK = ROOT / "ops" / "ec2" / "rollback-current.sh"
DEPENDENCY_LOCKS = (
    ROOT / "ops" / "ec2" / "requirements-runtime.lock",
    ROOT / "ops" / "ec2" / "requirements-validation.lock",
)
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


def test_api_status_identity_is_bound_to_process_start(
    tmp_path: Path,
) -> None:
    namespace = _load_embedded_api_namespace()
    app_root = tmp_path / "app"
    release_a = app_root / "releases" / "release-a"
    release_b = app_root / "releases" / "release-b"
    commit_a = _init_git_repo(release_a)
    _init_git_repo(release_b)
    (release_b / "tracked.txt").write_text("release-b\n", encoding="utf-8")
    _git(release_b, "add", "tracked.txt")
    _git(release_b, "commit", "-qm", "different configured release")
    commit_b = _git(release_b, "rev-parse", "HEAD")
    assert commit_a != commit_b

    shared = app_root / "shared"
    shared.mkdir(parents=True)
    (shared / "RELEASE_STATE").write_text(
        f"commit={commit_a}\n",
        encoding="utf-8",
    )
    current = app_root / "current"
    current.symlink_to(release_a, target_is_directory=True)
    running_launcher_sha256 = "a" * 64

    namespace["CURRENT"] = current
    namespace["SHARED"] = shared
    namespace["RUNNING_RELEASE"] = str(release_a)
    namespace["RUNNING_COMMIT"] = commit_a
    namespace["RUNNING_LAUNCHER_SHA256"] = running_launcher_sha256

    before_switch = namespace["product_status"]()
    replacement = app_root / "current.new"
    replacement.symlink_to(release_b, target_is_directory=True)
    os.replace(replacement, current)
    (shared / "RELEASE_STATE").write_text(
        f"commit={commit_b}\n",
        encoding="utf-8",
    )
    after_switch = namespace["product_status"]()

    for status in (before_switch, after_switch):
        assert status["current"] == str(release_a)
        assert status["commit"] == commit_a
        assert status["running_release"] == str(release_a)
        assert status["running_commit"] == commit_a
        assert status["running_launcher_sha256"] == running_launcher_sha256
        assert len(status["running_commit"]) == 40

    assert before_switch["configured_current_release"] == str(release_a)
    assert before_switch["configured_current_commit"] == commit_a
    assert after_switch["configured_current_release"] == str(release_b)
    assert after_switch["configured_current_commit"] == commit_b

    launcher = HUB_API.read_text(encoding="utf-8")
    assert 'sha256sum -- "$0"' in launcher
    assert 'export HUB_OPTIMUS_API_RUNNING_COMMIT="$RUNNING_COMMIT"' in launcher
    assert '"--short"' not in launcher


def test_api_launcher_captures_real_process_identity_at_start(
    tmp_path: Path,
) -> None:
    app_root = tmp_path / "app"
    release = app_root / "releases" / "release-a"
    commit = _init_git_repo(release)
    shared_launcher = app_root / "shared" / "bin" / "hub-api"
    shared_launcher.parent.mkdir(parents=True)
    shared_launcher.write_bytes(HUB_API.read_bytes())
    shared_launcher.chmod(0o755)
    (app_root / "current").symlink_to(release, target_is_directory=True)

    fake_bin = tmp_path / "fake-api-bin"
    fake_bin.mkdir()
    fake_python = fake_bin / "python3"
    fake_python.write_text(
        "#!/usr/bin/env bash\n"
        "printf 'app_root=%s\\n' \"$HUB_OPTIMUS_API_APP_ROOT\"\n"
        "printf 'running_release=%s\\n' \"$HUB_OPTIMUS_API_RUNNING_RELEASE\"\n"
        "printf 'running_commit=%s\\n' \"$HUB_OPTIMUS_API_RUNNING_COMMIT\"\n"
        "printf 'launcher_sha256=%s\\n' \"$HUB_OPTIMUS_API_RUNNING_LAUNCHER_SHA256\"\n",
        encoding="utf-8",
    )
    fake_python.chmod(0o755)
    env = os.environ.copy()
    env["HUB_OPTIMUS_APP_ROOT"] = str(app_root)
    env["PATH"] = f"{fake_bin}{os.pathsep}{env['PATH']}"

    result = _run(["bash", shared_launcher], env=env)

    assert result.returncode == 0, result.stderr
    identity = dict(
        line.split("=", 1)
        for line in result.stdout.splitlines()
        if "=" in line
    )
    assert identity["app_root"] == str(app_root)
    assert identity["running_release"] == str(release)
    assert identity["running_commit"] == commit
    assert identity["launcher_sha256"] == hashlib.sha256(
        shared_launcher.read_bytes()
    ).hexdigest()


def _source_repository(path: Path) -> tuple[str, str]:
    path.mkdir()
    assert _run(["git", "init", "-q", path]).returncode == 0
    _git(path, "config", "user.email", "tests@example.invalid")
    _git(path, "config", "user.name", "HUB tests")

    (path / "ops" / "ec2").mkdir(parents=True)
    (path / "requirements-dev.txt").write_text("pytest\n", encoding="utf-8")
    for source in DEPENDENCY_LOCKS:
        shutil.copyfile(source, path / "ops" / "ec2" / source.name)
    shutil.copyfile(
        ROOT / "ops" / "ec2" / "verify-release-worktree.py",
        path / "ops" / "ec2" / "verify-release-worktree.py",
    )
    validation_runner = path / "ops" / "ec2" / "run-release-validation.py"
    validation_runner.write_text(
        "import hashlib\n"
        "import json\n"
        "import os\n"
        "import subprocess\n"
        "import sys\n"
        "from pathlib import Path\n"
        "def controls(release):\n"
        "    return Path((release / '.hub-deployment' / 'test-controls').read_text().strip())\n"
        "def venv_digest(release):\n"
        "    digest = hashlib.sha256()\n"
        "    for item in sorted((release / '.venv').rglob('*')):\n"
        "        relative = str(item.relative_to(release / '.venv')).encode()\n"
        "        digest.update(len(relative).to_bytes(8, 'big')); digest.update(relative)\n"
        "        if item.is_file(): digest.update(item.read_bytes())\n"
        "    return digest.hexdigest()\n"
        "if sys.argv[1] == 'manifest-venv':\n"
        "    print(venv_digest(Path(sys.argv[2])))\n"
        "    raise SystemExit(0)\n"
        "release = Path(sys.argv[1]); commit = sys.argv[2]; control = controls(release)\n"
        "if (control / 'swap-lock-during-pytest').exists():\n"
        "    lock = release / 'ops/ec2/requirements-validation.lock'\n"
        "    original = lock.read_bytes(); lock.write_bytes(original + b'# changed\\n'); lock.write_bytes(original)\n"
        "    (control / 'lock-was-swapped').touch()\n"
        "source = subprocess.run([\n"
        "    '/usr/bin/python3', '-I', str(Path(__file__).with_name('verify-release-worktree.py')),\n"
        "    str(release), commit, '--allow-generated', '.venv',\n"
        "    '--allow-generated', '.hub-deployment',\n"
        "], env={'HOME':'/nonexistent','LANG':'C.UTF-8','PATH':'/usr/bin:/bin'},\n"
        "capture_output=True, text=True, check=False)\n"
        "if source.returncode != 0:\n"
        "    sys.stderr.write(source.stderr); raise SystemExit(1)\n"
        "source_digest = json.loads(source.stdout)['source_tree_sha256']\n"
        "exit_path = control / 'pytest.exit'\n"
        "exit_code = int(exit_path.read_text()) if exit_path.exists() else 0\n"
        "output_path = control / 'pytest.output'\n"
        "if output_path.exists(): print(output_path.read_text(), end='')\n"
        "else: print('17 passed in 0.01s')\n"
        "collected = 17 if exit_code == 0 else 2\n"
        "passed = collected if exit_code == 0 else 0\n"
        "failed = 0 if exit_code == 0 else collected\n"
        "result = 'passed' if exit_code == 0 else 'failed'\n"
        "nodeids = 'd' * 64\n"
        "print(\n"
        "    'HUB_OPTIMUS_VALIDATION_V1 '\n"
        "    f'collected={collected} terminal={collected} passed={passed} skipped=0 '\n"
        "    f'failed={failed} pytest_exit_code={exit_code} nodeids_sha256={nodeids} '\n"
        "    f'descendants=0 source_tree_sha256={source_digest} '\n"
        "    f'venv_tree_sha256={venv_digest(release)} worker_uid=65534 result={result}'\n"
        ")\n"
        "raise SystemExit(exit_code)\n",
        encoding="utf-8",
    )
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


def _locked_dependency_inventory() -> str:
    inventory: dict[str, str] = {}
    for lock in DEPENDENCY_LOCKS:
        for raw_line in lock.read_text(encoding="ascii").splitlines():
            line = raw_line.strip()
            if not line or line.startswith(("#", "-r ")) or "==" not in line:
                continue
            name, version = line.removesuffix("\\").strip().split("==", 1)
            normalized_name = re.sub(r"[-_.]+", "-", name).lower()
            inventory[normalized_name] = version
    assert inventory
    return json.dumps(
        [
            {"name": name, "version": inventory[name]}
            for name in sorted(inventory)
        ],
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )


def _deploy_fixture(path: Path) -> tuple[Path, Path]:
    fixture_root = path / "deploy-fixture"
    fixture_ec2 = fixture_root / "ops" / "ec2"
    shutil.copytree(ROOT / "ops" / "ec2", fixture_ec2)

    controls = fixture_root / "controls"
    controls.mkdir()
    (controls / "inventory.output").write_text(
        f"{_locked_dependency_inventory()}\n",
        encoding="ascii",
    )

    fake_system_python = fixture_root / "fake-system-python"
    fake_venv_python = fixture_root / "fake-venv-python"
    quoted_controls = shlex.quote(str(controls))
    quoted_system_python = shlex.quote(str(fake_system_python))
    fake_venv_python.write_text(
        "#!/bin/bash\n"
        "set -eu\n"
        f"CONTROL_DIR={quoted_controls}\n"
        f"SYSTEM_PYTHON={quoted_system_python}\n"
        "control_exit() {\n"
        "  if [ -f \"$CONTROL_DIR/$1.exit\" ]; then\n"
        "    /bin/cat \"$CONTROL_DIR/$1.exit\"\n"
        "  else\n"
        "    printf '%s\\n' \"$2\"\n"
        "  fi\n"
        "}\n"
        "swap_lock_hash_and_restore() {\n"
        "  lock=$HOME/ops/ec2/requirements-validation.lock\n"
        "  /bin/cp -- \"$lock\" \"$CONTROL_DIR/original.lock\"\n"
        "  /bin/sed '0,/sha256:[0-9a-f]/s//sha256:0/' \\\n"
        "    \"$CONTROL_DIR/original.lock\" > \"$CONTROL_DIR/replacement.lock\"\n"
        "  /bin/mv -- \"$CONTROL_DIR/replacement.lock\" \"$lock\"\n"
        "  /bin/cp -- \"$CONTROL_DIR/original.lock\" \\\n"
        "    \"$CONTROL_DIR/restored.lock\"\n"
        "  /bin/mv -- \"$CONTROL_DIR/restored.lock\" \"$lock\"\n"
        "  : > \"$CONTROL_DIR/lock-was-swapped\"\n"
        "}\n"
        "isolated=0\n"
        "if [ \"${1:-}\" = '-I' ]; then\n"
        "  isolated=1\n"
        "  shift\n"
        "fi\n"
        "if [ \"${1:-}\" = '-m' ]; then\n"
        "  module=\"${2:-}\"\n"
        "  action=\"${3:-}\"\n"
        "  case \"$module:$action\" in\n"
        "    pip:install)\n"
        "      test \"$isolated\" -eq 1\n"
        "      if [ -f \"$CONTROL_DIR/swap-lock-during-pip\" ]; then\n"
        "        swap_lock_hash_and_restore\n"
        "      fi\n"
        "      exit \"$(control_exit pip-install 0)\"\n"
        "      ;;\n"
        "    pip:check)\n"
        "      test \"$isolated\" -eq 1\n"
        "      exit \"$(control_exit pip-check 0)\"\n"
        "      ;;\n"
        "    pip:uninstall)\n"
        "      test \"$isolated\" -eq 1\n"
        "      exit \"$(control_exit pip-uninstall 0)\"\n"
        "      ;;\n"
        "    pytest:*)\n"
        "      test \"$isolated\" -eq 0\n"
        "      if [ -f \"$CONTROL_DIR/swap-lock-during-pytest\" ]; then\n"
        "        swap_lock_hash_and_restore\n"
        "      fi\n"
        "      if [ -f \"$CONTROL_DIR/pytest.output\" ]; then\n"
        "        /bin/cat \"$CONTROL_DIR/pytest.output\"\n"
        "      else\n"
        "        printf '17 passed in 0.01s\\n'\n"
        "      fi\n"
        "      exit \"$(control_exit pytest 0)\"\n"
        "      ;;\n"
        "    *) exit 2 ;;\n"
        "  esac\n"
        "fi\n"
        "tool=\"${1:-}\"\n"
        "operation=\"${2:-}\"\n"
        "release=\"${3:-}\"\n"
        "system_python=\"${4:-}\"\n"
        "digest=\"${5:-}\"\n"
        "token=\"${6:-}\"\n"
        "test \"$isolated\" -eq 1\n"
        "test \"${tool##*/}\" = 'verify-installed-dependencies.py'\n"
        "test \"$operation\" = 'verify'\n"
        "test -d \"$release\"\n"
        "test \"$system_python\" = \"$SYSTEM_PYTHON\"\n"
        "test \"${#digest}\" -eq 64\n"
        "test \"${#token}\" -eq 64\n"
        "if [ -f \"$CONTROL_DIR/lock-was-swapped\" ]; then\n"
        "  echo '[dependency-lock:error] dependency-lock paths changed since capture' >&2\n"
        "  exit 1\n"
        "fi\n"
        "/bin/cat \"$CONTROL_DIR/inventory.output\"\n"
        "exit \"$(control_exit inventory 0)\"\n",
        encoding="utf-8",
    )
    fake_venv_python.chmod(0o755)

    fake_system_python.write_text(
        "#!/bin/bash\n"
        "set -eu\n"
        f"VENV_PYTHON={shlex.quote(str(fake_venv_python))}\n"
        "if [ \"${1:-}\" = '-I' ] && [ \"${2:-}\" = '-' ]; then\n"
        "  exit 0\n"
        "fi\n"
        "if [ \"${1:-}\" = '-I' ] \\\n"
        "  && [ \"${2##*/}\" = 'verify-installed-dependencies.py' ]; then\n"
        "  exec /usr/bin/python3 \"$@\"\n"
        "fi\n"
        "test \"${1:-}\" = '-I'\n"
        "test \"${2:-}\" = '-m'\n"
        "test \"${3:-}\" = 'venv'\n"
        "test \"$#\" -eq 4\n"
        "/bin/mkdir -p \"$4/bin\"\n"
        "/bin/cp -- \"$VENV_PYTHON\" \"$4/bin/python\"\n"
        "/bin/chmod 0755 \"$4/bin/python\"\n",
        encoding="utf-8",
    )
    fake_system_python.chmod(0o755)

    deploy = fixture_ec2 / "deploy-current.sh"
    deploy_text = deploy.read_text(encoding="utf-8")
    assignment = 'SYSTEM_PYTHON="/usr/bin/python3"'
    assert deploy_text.count(assignment) == 1
    assert '"$SYSTEM_PYTHON" -I -m venv' in deploy_text
    assert '"$CANDIDATE_VALIDATION_RUNNER" \\\n' in deploy_text
    assert '"$VENV_PYTHON" -m pytest' not in deploy_text
    assert "HUB_OPTIMUS_TEST_MODE" not in deploy_text
    assert "HUB_TEST_" not in deploy_text
    deployment_marker = 'chmod 0700 "$DEPLOYMENT_DIR"\n'
    assert deploy_text.count(deployment_marker) == 1
    deploy_text = deploy_text.replace(
        deployment_marker,
        deployment_marker
        + f"printf '%s\\n' {quoted_controls} > "
        + '"$DEPLOYMENT_DIR/test-controls"\n',
        1,
    )
    deploy.write_text(
        deploy_text.replace(
            assignment,
            f'SYSTEM_PYTHON="{fake_system_python}"',
            1,
        ),
        encoding="utf-8",
    )
    return deploy, controls


def _deploy_env(
    app_root: Path,
    source_repo: Path,
) -> dict[str, str]:
    shared = app_root / "shared"
    shared.mkdir(parents=True, exist_ok=True)
    app_root.chmod(0o755)
    shared.chmod(0o755)
    operation_lock = shared / "deploy.lock"
    if not operation_lock.exists():
        operation_lock.write_bytes(b"test-operation-lock-sentinel\n")
        operation_lock.chmod(0o600)
    env = os.environ.copy()
    for name in tuple(env):
        if name.startswith("PIP_"):
            env.pop(name)
    env["HUB_OPTIMUS_APP_ROOT"] = str(app_root)
    env["HUB_OPTIMUS_REPO_URL"] = str(source_repo)
    return env


def _expected_validation_command(release: Path) -> str:
    commit = _git(release, "rev-parse", "HEAD")
    return (
        "/usr/bin/env -i HOME=/nonexistent LANG=C.UTF-8 PATH=/usr/bin:/bin "
        f"/usr/bin/python3 -I {release}/ops/ec2/run-release-validation.py "
        f"{release} {commit} {release}/ops/ec2/verify-release-worktree.py"
    )


def _operational_snapshot(app_root: Path) -> dict[str, object]:
    snapshot: dict[str, object] = {
        "current_target": os.readlink(app_root / "current"),
        "current_resolved": (app_root / "current").resolve(),
    }
    for name, path in {
        "launcher": app_root / "shared" / "bin" / "hub-api",
        "release_state": app_root / "shared" / "RELEASE_STATE",
        "current_release": app_root / "shared" / "current_release",
        "previous_release": app_root / "shared" / "previous_release",
        "rollback_state": app_root / "shared" / "ROLLBACK_STATE",
        "last_rollback_from": app_root / "shared" / "last_rollback_from",
    }.items():
        snapshot[f"{name}_present"] = path.exists()
        if path.exists():
            snapshot[f"{name}_bytes"] = path.read_bytes()
            snapshot[f"{name}_mode"] = stat.S_IMODE(path.stat().st_mode)
    return snapshot


def test_deploy_is_ref_bound_records_validation_and_rolls_back(
    tmp_path: Path,
) -> None:
    source_repo = tmp_path / "source"
    reviewed_commit, head_commit = _source_repository(source_repo)
    deploy, controls = _deploy_fixture(tmp_path)
    app_root = tmp_path / "app"
    env = _deploy_env(app_root, source_repo)

    first = _run([deploy, "reviewed-v1"], env=env)
    assert first.returncode == 0, first.stderr
    first_release = (app_root / "current").resolve()
    assert _git(first_release, "rev-parse", "HEAD") == reviewed_commit
    first_state = _state(app_root / "shared" / "RELEASE_STATE")
    assert first_state["requested_ref"] == "reviewed-v1"
    assert first_state["requested_ref_kind"] == "tag"
    assert first_state["commit"] == reviewed_commit
    assert first_state["validation_command"] == _expected_validation_command(
        first_release
    )
    assert first_state["dependency_tier"] == "runtime+validation-v1"
    assert first_state["dependency_lock"] == str(
        first_release / "ops" / "ec2" / "requirements-validation.lock"
    )
    assert re.fullmatch(r"[0-9a-f]{64}", first_state["dependency_lock_sha256"])
    assert first_state["validation_exit_code"] == "0"
    assert first_state["validation_log_exit_code"] == "0"
    assert first_state["validation_protocol"] == "isolated-pytest-v1"
    assert first_state["validation_collected"] == "17"
    assert first_state["validation_terminal"] == "17"
    assert first_state["validation_passed"] == "17"
    assert first_state["validation_skipped"] == "0"
    assert first_state["validation_failed"] == "0"
    assert first_state["validation_descendants"] == "0"
    assert first_state["validation_result"].startswith(
        "HUB_OPTIMUS_VALIDATION_V1 collected=17 terminal=17 passed=17 "
    )
    assert re.fullmatch(r"[0-9a-f]{64}", first_state["source_tree_sha256"])
    assert re.fullmatch(r"[0-9a-f]{64}", first_state["venv_tree_sha256"])
    first_validation_log = first_release / ".hub-deployment" / "validation.log"
    assert first_state["validation_log_sha256"] == hashlib.sha256(
        first_validation_log.read_bytes()
    ).hexdigest()
    assert "55 passed" not in (app_root / "shared" / "RELEASE_STATE").read_text()

    second = _run([deploy, head_commit], env=env)
    assert second.returncode == 0, second.stderr
    second_release = (app_root / "current").resolve()
    assert second_release != first_release
    assert _git(second_release, "rev-parse", "HEAD") == head_commit
    second_state = _state(app_root / "shared" / "RELEASE_STATE")
    assert second_state["requested_ref"] == head_commit
    assert second_state["requested_ref_kind"] == "commit"
    assert second_state["commit"] == head_commit
    assert re.fullmatch(r"[0-9a-f]{64}", second_state["launcher_sha256"])
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


def test_every_injected_post_switch_failure_restores_exact_state(
    tmp_path: Path,
) -> None:
    stages = (
        "previous-release",
        "current",
        "launcher",
        "release-state",
        "current-release",
    )

    for stage in stages:
        case_root = tmp_path / stage
        case_root.mkdir()
        source_repo = case_root / "source"
        reviewed_commit, head_commit = _source_repository(source_repo)
        deploy, controls = _deploy_fixture(case_root)
        app_root = case_root / "app"
        env = _deploy_env(app_root, source_repo)

        first = _run([deploy, reviewed_commit], env=env)
        assert first.returncode == 0, first.stderr
        before = _operational_snapshot(app_root)

        env["HUB_OPTIMUS_TEST_FAIL_AFTER_MUTATION"] = stage
        failed = _run([deploy, head_commit], env=env)

        assert failed.returncode == 1
        assert f"injected test failure after mutation stage: {stage}" in failed.stderr
        assert "Pre-deploy operational state restored" in failed.stderr
        assert _operational_snapshot(app_root) == before

        candidates = [
            release
            for release in (app_root / "releases").iterdir()
            if (release / ".hub-deployment" / "RELEASE_STATE").is_file()
            and _state(release / ".hub-deployment" / "RELEASE_STATE").get(
                "commit"
            )
            == head_commit
        ]
        assert len(candidates) == 1
        candidate = candidates[0]
        assert (candidate / ".hub-deployment" / "validation.log").is_file()
        recovery_log = candidate / ".hub-deployment" / "recovery.log"
        assert "Pre-deploy operational state restored" in recovery_log.read_text(
            encoding="utf-8"
        )
        assert (candidate / ".hub-deployment" / "pre-deploy-state").is_dir()


def test_deploy_recovery_runs_when_recovery_log_cannot_open(
    tmp_path: Path,
) -> None:
    source_repo = tmp_path / "source"
    reviewed_commit, head_commit = _source_repository(source_repo)
    deploy, controls = _deploy_fixture(tmp_path)
    app_root = tmp_path / "app"
    env = _deploy_env(app_root, source_repo)

    first = _run([deploy, reviewed_commit], env=env)
    assert first.returncode == 0, first.stderr
    before = _operational_snapshot(app_root)
    unusable_log = tmp_path / "recovery-log-is-a-directory"
    unusable_log.mkdir()
    env["HUB_OPTIMUS_TEST_FAIL_AFTER_MUTATION"] = "current"
    env["HUB_OPTIMUS_TEST_RECOVERY_LOG_PATH"] = str(unusable_log)

    failed = _run([deploy, head_commit], env=env)

    assert failed.returncode == 1
    assert _operational_snapshot(app_root) == before
    assert "Restoring exact pre-deploy operational state" in failed.stderr
    assert "Operational state restored, but recovery evidence could not be recorded" in failed.stderr
    assert "[deploy:recovery] Pre-deploy operational state restored" not in failed.stderr


def test_injected_legacy_state_completion_is_recovered(
    tmp_path: Path,
) -> None:
    source_repo = tmp_path / "source"
    reviewed_commit, head_commit = _source_repository(source_repo)
    deploy, controls = _deploy_fixture(tmp_path)
    app_root = tmp_path / "app"
    env = _deploy_env(app_root, source_repo)

    first = _run([deploy, reviewed_commit], env=env)
    assert first.returncode == 0, first.stderr
    current_release = (app_root / "current").resolve()
    legacy_state = current_release / ".hub-deployment" / "RELEASE_STATE"
    legacy_state.unlink()
    before = _operational_snapshot(app_root)

    env["HUB_OPTIMUS_TEST_FAIL_AFTER_MUTATION"] = "previous-release-state"
    result = _run([deploy, head_commit], env=env)

    assert result.returncode == 1
    assert "injected test failure after mutation stage: previous-release-state" in result.stderr
    assert "Pre-deploy operational state restored" in result.stderr
    assert _operational_snapshot(app_root) == before
    assert not legacy_state.exists()


def test_rollback_rejects_launcher_drift_before_switching(
    tmp_path: Path,
) -> None:
    source_repo = tmp_path / "source"
    reviewed_commit, head_commit = _source_repository(source_repo)
    deploy, controls = _deploy_fixture(tmp_path)
    app_root = tmp_path / "app"
    env = _deploy_env(app_root, source_repo)

    first = _run([deploy, reviewed_commit], env=env)
    assert first.returncode == 0, first.stderr
    first_release = (app_root / "current").resolve()
    second = _run([deploy, head_commit], env=env)
    assert second.returncode == 0, second.stderr
    before = _operational_snapshot(app_root)
    (first_release / "ops" / "ec2" / "hub-api.sh").write_text(
        "#!/usr/bin/env bash\necho tampered\n",
        encoding="utf-8",
    )

    result = _run([ROLLBACK], env=env)

    assert result.returncode == 1
    assert "launcher does not match its deployment state" in result.stderr
    assert _operational_snapshot(app_root) == before


def test_every_injected_rollback_failure_restores_exact_state(
    tmp_path: Path,
) -> None:
    stages = (
        "last-rollback-from",
        "current",
        "launcher",
        "release-state",
        "rollback-state",
        "current-release",
    )

    for stage in stages:
        case_root = tmp_path / stage
        case_root.mkdir()
        source_repo = case_root / "source"
        reviewed_commit, head_commit = _source_repository(source_repo)
        deploy, controls = _deploy_fixture(case_root)
        app_root = case_root / "app"
        env = _deploy_env(app_root, source_repo)

        first = _run([deploy, reviewed_commit], env=env)
        assert first.returncode == 0, first.stderr
        second = _run([deploy, head_commit], env=env)
        assert second.returncode == 0, second.stderr
        before = _operational_snapshot(app_root)
        env["HUB_OPTIMUS_TEST_ROLLBACK_FAIL_AFTER_MUTATION"] = stage

        failed = _run([ROLLBACK], env=env)

        assert failed.returncode == 1
        assert f"injected test failure after mutation stage: {stage}" in failed.stderr
        assert "Pre-rollback operational state restored" in failed.stderr
        assert _operational_snapshot(app_root) == before
        recovery_roots = list(
            (app_root / "shared").glob("rollback-transaction.*")
        )
        assert len(recovery_roots) == 1
        recovery_log = recovery_roots[0] / "recovery.log"
        assert "Pre-rollback operational state restored" in recovery_log.read_text(
            encoding="utf-8"
        )
        assert (recovery_roots[0] / "pre-rollback-state").is_dir()


def test_rollback_recovery_runs_when_recovery_log_cannot_open(
    tmp_path: Path,
) -> None:
    source_repo = tmp_path / "source"
    reviewed_commit, head_commit = _source_repository(source_repo)
    deploy, controls = _deploy_fixture(tmp_path)
    app_root = tmp_path / "app"
    env = _deploy_env(app_root, source_repo)

    assert _run([deploy, reviewed_commit], env=env).returncode == 0
    assert _run([deploy, head_commit], env=env).returncode == 0
    before = _operational_snapshot(app_root)
    unusable_log = tmp_path / "rollback-log-is-a-directory"
    unusable_log.mkdir()
    env["HUB_OPTIMUS_TEST_ROLLBACK_FAIL_AFTER_MUTATION"] = "current"
    env["HUB_OPTIMUS_TEST_ROLLBACK_RECOVERY_LOG_PATH"] = str(unusable_log)

    failed = _run([ROLLBACK], env=env)

    assert failed.returncode == 1
    assert _operational_snapshot(app_root) == before
    assert "Restoring exact pre-rollback operational state" in failed.stderr
    assert "Operational state restored, but recovery evidence could not be recorded" in failed.stderr
    assert "[rollback:recovery] Pre-rollback operational state restored" not in failed.stderr


def test_rollback_state_parser_rejects_duplicate_identity_keys(
    tmp_path: Path,
) -> None:
    for key in ("commit", "path", "release", "launcher_sha256"):
        case_root = tmp_path / key
        case_root.mkdir()
        source_repo = case_root / "source"
        reviewed_commit, head_commit = _source_repository(source_repo)
        deploy, controls = _deploy_fixture(case_root)
        app_root = case_root / "app"
        env = _deploy_env(app_root, source_repo)

        assert _run([deploy, reviewed_commit], env=env).returncode == 0
        first_release = (app_root / "current").resolve()
        assert _run([deploy, head_commit], env=env).returncode == 0
        previous_state_path = (
            first_release / ".hub-deployment" / "RELEASE_STATE"
        )
        state = _state(previous_state_path)
        with previous_state_path.open("a", encoding="utf-8") as handle:
            handle.write(f"{key}={state[key]}\n")
        before = _operational_snapshot(app_root)

        result = _run([ROLLBACK], env=env)

        assert result.returncode == 1
        assert f"contains a duplicate field: {key}" in result.stderr
        assert _operational_snapshot(app_root) == before
        assert not list((app_root / "shared").glob("rollback-transaction.*"))


@pytest.mark.parametrize(
    "state_location",
    ("current", "shared", "matching-current-and-shared", "previous"),
)
def test_rollback_rejects_malformed_managed_state_before_mutation(
    tmp_path: Path,
    state_location: str,
) -> None:
    source_repo = tmp_path / "source"
    reviewed_commit, head_commit = _source_repository(source_repo)
    deploy, controls = _deploy_fixture(tmp_path)
    app_root = tmp_path / "app"
    env = _deploy_env(app_root, source_repo)

    assert _run([deploy, reviewed_commit], env=env).returncode == 0
    previous_release = (app_root / "current").resolve()
    assert _run([deploy, head_commit], env=env).returncode == 0
    current_release = (app_root / "current").resolve()
    current_state = current_release / ".hub-deployment" / "RELEASE_STATE"
    shared_state = app_root / "shared" / "RELEASE_STATE"
    previous_state = previous_release / ".hub-deployment" / "RELEASE_STATE"

    targets = {
        "current": (current_state,),
        "shared": (shared_state,),
        "matching-current-and-shared": (current_state, shared_state),
        "previous": (previous_state,),
    }[state_location]
    for target in targets:
        with target.open("a", encoding="utf-8") as handle:
            handle.write("status=production-candidate-core\n")
    before = _operational_snapshot(app_root)

    result = _run([ROLLBACK], env=env)

    assert result.returncode == 1
    assert "contains a duplicate field: status" in result.stderr
    assert _operational_snapshot(app_root) == before
    assert not list((app_root / "shared").glob("rollback-transaction.*"))


def test_invalid_rollback_target_state_fails_before_mutation(
    tmp_path: Path,
) -> None:
    source_repo = tmp_path / "source"
    reviewed_commit, head_commit = _source_repository(source_repo)
    deploy, controls = _deploy_fixture(tmp_path)
    app_root = tmp_path / "app"
    env = _deploy_env(app_root, source_repo)

    first = _run([deploy, reviewed_commit], env=env)
    assert first.returncode == 0, first.stderr
    current_release = (app_root / "current").resolve()
    current_state_path = current_release / ".hub-deployment" / "RELEASE_STATE"
    current_state = current_state_path.read_text(encoding="utf-8")
    current_state_path.write_text(
        current_state.replace(
            f"commit={reviewed_commit}",
            f"commit={'0' * 40}",
        ),
        encoding="utf-8",
    )
    before = _operational_snapshot(app_root)

    result = _run([deploy, head_commit], env=env)

    assert result.returncode == 1
    assert "requested commit differs from its resolved commit" in result.stderr
    assert "Restoring exact pre-deploy" not in result.stderr
    assert _operational_snapshot(app_root) == before


@pytest.mark.parametrize(
    ("corruption", "expected_error"),
    (
        ("malformed", "contains a malformed state line"),
        (
            "valid-but-divergent",
            "Shared RELEASE_STATE differs from current per-release state",
        ),
    ),
)
def test_deploy_rejects_shared_only_state_drift_before_mutation(
    tmp_path: Path,
    corruption: str,
    expected_error: str,
) -> None:
    source_repo = tmp_path / "source"
    reviewed_commit, head_commit = _source_repository(source_repo)
    deploy, controls = _deploy_fixture(tmp_path)
    app_root = tmp_path / "app"
    env = _deploy_env(app_root, source_repo)

    first = _run([deploy, reviewed_commit], env=env)
    assert first.returncode == 0, first.stderr
    shared_state = app_root / "shared" / "RELEASE_STATE"
    if corruption == "malformed":
        with shared_state.open("a", encoding="utf-8") as handle:
            handle.write("malformed-state-line\n")
    else:
        shared_state.write_text(
            re.sub(
                r"(?m)^validated_at_utc=.*$",
                "validated_at_utc=2000-01-01T00:00:00Z",
                shared_state.read_text(encoding="utf-8"),
            ),
            encoding="utf-8",
        )
    before = _operational_snapshot(app_root)

    result = _run([deploy, head_commit], env=env)

    assert result.returncode == 1
    assert expected_error in result.stderr
    assert "Restoring exact pre-deploy operational state" not in result.stderr
    assert _operational_snapshot(app_root) == before


def test_failed_validation_is_recorded_without_switching_current(
    tmp_path: Path,
) -> None:
    source_repo = tmp_path / "source"
    reviewed_commit, head_commit = _source_repository(source_repo)
    deploy, controls = _deploy_fixture(tmp_path)
    app_root = tmp_path / "app"
    env = _deploy_env(app_root, source_repo)

    first = _run([deploy, reviewed_commit], env=env)
    assert first.returncode == 0, first.stderr
    before = _operational_snapshot(app_root)

    (controls / "pytest.exit").write_text("1\n", encoding="ascii")
    (controls / "pytest.output").write_text(
        "2 failed in 0.01s\n",
        encoding="utf-8",
    )

    result = _run([deploy, head_commit], env=env)

    assert result.returncode == 1
    assert "validation failed (exit 1): HUB_OPTIMUS_VALIDATION_V1" in result.stderr
    assert _operational_snapshot(app_root) == before
    failed_releases = [
        release
        for release in (app_root / "releases").iterdir()
        if (release / ".hub-deployment" / "RELEASE_STATE").is_file()
        and _state(release / ".hub-deployment" / "RELEASE_STATE").get(
            "status"
        )
        == "validation-failed"
    ]
    assert len(failed_releases) == 1
    failed_state_path = (
        failed_releases[0] / ".hub-deployment" / "RELEASE_STATE"
    )
    failed_state = _state(failed_state_path)
    assert failed_state["commit"] == head_commit
    assert failed_state["validation_command"] == _expected_validation_command(
        failed_releases[0]
    )
    assert failed_state["validation_exit_code"] == "1"
    assert failed_state["validation_result"].startswith(
        "HUB_OPTIMUS_VALIDATION_V1 collected=2 terminal=2 passed=0 "
    )
    assert failed_state["validation_failed"] == "2"
    failed_validation_log = (
        failed_releases[0] / ".hub-deployment" / "validation.log"
    )
    assert failed_state["validation_log_sha256"] == hashlib.sha256(
        failed_validation_log.read_bytes()
    ).hexdigest()
    assert failed_state["status"] == "validation-failed"
    assert (failed_releases[0] / ".hub-deployment" / "validation.log").is_file()


@pytest.mark.parametrize(
    "setting",
    (
        "PIP_INDEX_URL",
        "PIP_EXTRA_INDEX_URL",
        "PIP_CONFIG_FILE",
        "PIP_FIND_LINKS",
        "PIP_TRUSTED_HOST",
    ),
)
def test_ambient_pip_settings_fail_before_host_mutation(
    tmp_path: Path,
    setting: str,
) -> None:
    source_repo = tmp_path / "source"
    reviewed_commit, _ = _source_repository(source_repo)
    deploy, controls = _deploy_fixture(tmp_path)
    app_root = tmp_path / "app"
    env = _deploy_env(app_root, source_repo)
    env[setting] = "poisoned"

    result = _run([deploy, reviewed_commit], env=env)

    assert result.returncode == 1
    assert f"ambient pip setting is not allowed: {setting}" in result.stderr
    assert (app_root / "shared" / "deploy.lock").read_bytes() == (
        b"test-operation-lock-sentinel\n"
    )
    assert not (app_root / "releases").exists()
    assert not (app_root / "current").exists()


def test_dependency_install_failure_preserves_operational_state(
    tmp_path: Path,
) -> None:
    source_repo = tmp_path / "source"
    reviewed_commit, head_commit = _source_repository(source_repo)
    deploy, controls = _deploy_fixture(tmp_path)
    app_root = tmp_path / "app"
    env = _deploy_env(app_root, source_repo)

    first = _run([deploy, reviewed_commit], env=env)
    assert first.returncode == 0, first.stderr
    before = _operational_snapshot(app_root)
    (controls / "pip-install.exit").write_text("23\n", encoding="ascii")

    result = _run([deploy, head_commit], env=env)

    assert result.returncode == 23
    assert _operational_snapshot(app_root) == before
    assert "Switching current symlink" not in result.stdout


@pytest.mark.parametrize("stage", ("pip", "pytest"))
def test_temporary_lock_replacement_cannot_publish_a_candidate(
    tmp_path: Path,
    stage: str,
) -> None:
    source_repo = tmp_path / "source"
    reviewed_commit, head_commit = _source_repository(source_repo)
    deploy, controls = _deploy_fixture(tmp_path)
    app_root = tmp_path / "app"
    env = _deploy_env(app_root, source_repo)

    first = _run([deploy, reviewed_commit], env=env)
    assert first.returncode == 0, first.stderr
    before = _operational_snapshot(app_root)
    (controls / f"swap-lock-during-{stage}").touch()

    result = _run([deploy, head_commit], env=env)

    assert result.returncode == 1
    assert "lock" in result.stderr
    assert "changed" in result.stderr
    assert _operational_snapshot(app_root) == before
    assert "Switching current symlink" not in result.stdout
    published = [
        path
        for path in (app_root / "releases").iterdir()
        if (path / ".hub-deployment" / "RELEASE_STATE").is_file()
        and _state(path / ".hub-deployment" / "RELEASE_STATE").get("commit")
        == head_commit
    ]
    assert published == []


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
    assert hub_ops.startswith("#!/usr/bin/python3 -I\n")
    assert 'MUTATING_OPERATIONS = frozenset({"adopt", "deploy", "preflight", "rollback"})' in hub_ops
    assert 'dispatcher = tools / "run-reviewed-operation.py"' in hub_ops
    assert "run_operation(command, remaining)" in hub_ops
