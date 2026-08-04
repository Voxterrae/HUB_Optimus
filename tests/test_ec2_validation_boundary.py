from __future__ import annotations

import importlib.util
import json
import os
import pwd
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "ops" / "ec2" / "run-release-validation.py"
COMMIT = "a" * 40
PYTEST_MODULES = (
    "_pytest",
    "pytest",
    "pluggy",
    "iniconfig",
    "packaging",
    "pygments",
    "py",
)


def _copy_module(name: str, destination: Path) -> None:
    spec = importlib.util.find_spec(name)
    assert spec is not None
    if spec.submodule_search_locations:
        source = Path(next(iter(spec.submodule_search_locations)))
        shutil.copytree(source, destination / source.name, symlinks=True)
    else:
        assert spec.origin is not None
        source = Path(spec.origin)
        shutil.copy2(source, destination / source.name)


@pytest.fixture(scope="module")
def isolated_release() -> tuple[Path, Path, Path, Path]:
    fixture_root = Path(tempfile.mkdtemp(prefix="hub-1853-validation-", dir="/tmp"))
    fixture_root.chmod(0o755)
    release = fixture_root / "release"
    tests = release / "tests"
    site_packages = release / ".venv" / "site-packages"
    bin_directory = release / ".venv" / "bin"
    tests.mkdir(parents=True)
    site_packages.mkdir(parents=True)
    bin_directory.mkdir(parents=True)
    for module in PYTEST_MODULES:
        _copy_module(module, site_packages)

    base_python = Path(sys.executable).resolve()
    python = bin_directory / "python"
    python.write_text(
        "#!/bin/bash\n"
        "set -eu\n"
        f"export PYTHONPATH={site_packages!s}\n"
        "if [ \"${1:-}\" = '-I' ]; then shift; fi\n"
        f"exec {base_python!s} \"$@\"\n",
        encoding="utf-8",
    )
    python.chmod(0o755)
    for directory, _subdirectories, _files in os.walk(release):
        Path(directory).chmod(0o755)
    for path in release.rglob("*"):
        if path.is_file() and not path.is_symlink():
            mode = stat.S_IMODE(path.stat().st_mode)
            path.chmod((mode | 0o444) & ~0o022)

    verifier = fixture_root / "source-verifier.py"
    verifier.write_text(
        "import json\n"
        "import sys\n"
        "print(json.dumps({\n"
        "    'commit': sys.argv[2],\n"
        "    'source_tree_sha256': 'b' * 64,\n"
        "}, sort_keys=True, separators=(',', ':')))\n",
        encoding="utf-8",
    )
    verifier.chmod(0o644)
    # Instrument a private copy to exercise the supervisor, evidence,
    # subreaper and cleanup paths as the current UID.  This works both in the
    # root-only local sandbox and on an unprivileged hosted runner.  A separate
    # assertion below keeps the production root->nobody contract exact.
    runner = fixture_root / RUNNER.name
    runner_source = RUNNER.read_text(encoding="utf-8")
    direct_start = runner_source.index("def direct_children()")
    direct_end = runner_source.index("\ndef kill_and_reap_descendants", direct_start)
    runner_source = (
        runner_source[:direct_start]
        + "def direct_children() -> set[int]:\n"
        + "    registry = os.environ.get('HUB_1853_TEST_CHILD_PID')\n"
        + "    if not registry:\n"
        + "        return set()\n"
        + "    path = Path(registry)\n"
        + "    if not path.exists():\n"
        + "        return set()\n"
        + "    pid = int(path.read_text(encoding='ascii'))\n"
        + "    path.unlink()\n"
        + "    return {pid}\n"
        + runner_source[direct_end:]
    )
    start = runner_source.index("def worker_identity(")
    end = runner_source.index("\ndef make_preexec", start)
    preexec_end = runner_source.index("\ndef marker", end)
    runner.write_text(
        runner_source[:start]
        + "def worker_identity(release: Path, venv: Path) -> tuple[int, int]:\n"
        + "    del release, venv\n"
        + "    return os.getegid(), os.geteuid()\n"
        + "\n\ndef make_preexec(gid: int, uid: int):\n"
        + "    del gid, uid\n"
        + "    def prepare() -> None:\n"
        + "        no_new_privileges()\n"
        + "    return prepare\n"
        + runner_source[preexec_end:],
        encoding="utf-8",
    )
    runner.chmod(0o644)
    # The hosted runner owns this fixture.  Make the candidate root itself
    # non-writable so the test exercises the same read-only source boundary as
    # the production root->nobody transition instead of accidentally granting
    # the worker owner-write access.
    release.chmod(0o555)
    try:
        yield release, tests, verifier, runner
    finally:
        for directory, _subdirectories, _files in os.walk(release):
            Path(directory).chmod(0o755)
        shutil.rmtree(fixture_root, ignore_errors=True)


def _write_test(tests: Path, source: str) -> None:
    for path in tests.iterdir():
        if path.is_file():
            path.unlink()
    candidate = tests / "test_candidate.py"
    candidate.write_text(source, encoding="utf-8")
    candidate.chmod(0o644)


def _run_boundary(
    release: Path,
    verifier: Path,
    runner: Path,
    *,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            "/usr/bin/python3",
            "-I",
            str(runner),
            str(release),
            COMMIT,
            str(verifier),
            "--timeout",
            "10",
        ],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def _marker(stdout: str) -> dict[str, str]:
    line = stdout.rstrip().splitlines()[-1]
    assert line.startswith("HUB_OPTIMUS_VALIDATION_V1 ")
    return dict(field.split("=", 1) for field in line.split()[1:])


def test_production_supervisor_selects_nobody_when_root(
    isolated_release: tuple[Path, Path, Path, Path],
) -> None:
    release, _tests, _verifier, _runner = isolated_release
    spec = importlib.util.spec_from_file_location("validation_boundary", RUNNER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    gid, uid = module.worker_identity(release, release / ".venv")

    if os.geteuid() == 0:
        account = pwd.getpwnam("nobody")
        assert (gid, uid) == (account.pw_gid, account.pw_uid)
        source = RUNNER.read_text(encoding="utf-8")
        assert source.index("os.setgroups([])") < source.index("os.setgid(gid)")
        assert source.index("os.setgid(gid)") < source.index("os.setuid(uid)")
    else:
        assert (gid, uid) == (os.getegid(), os.geteuid())


def test_real_pytest_execution_ignores_ambient_poison_and_is_non_writable(
    isolated_release: tuple[Path, Path, Path, Path],
    tmp_path: Path,
) -> None:
    release, tests, verifier, runner = isolated_release
    _write_test(
        tests,
        "import os\n"
        "import pathlib\n"
        "import pytest\n"
        "def test_passes_under_restricted_uid(tmp_path):\n"
        "    assert tmp_path.is_dir()\n"
        "    if os.geteuid() != 0:\n"
        "        with pytest.raises(PermissionError):\n"
        "            pathlib.Path(__file__).parents[1].joinpath('poison').write_text('x')\n"
        "@pytest.mark.skip(reason='reviewed skip')\n"
        "def test_reviewed_skip():\n"
        "    pass\n",
    )
    sentinel = tmp_path / "sitecustomize-ran"
    poison = tmp_path / "poison"
    poison.mkdir()
    (poison / "sitecustomize.py").write_text(
        f"open({str(sentinel)!r}, 'w').write('poison')\n",
        encoding="utf-8",
    )
    env = os.environ.copy()
    env.update(
        {
            "PYTHONPATH": str(poison),
            "PYTEST_ADDOPTS": "--collect-only",
            "PYTEST_PLUGINS": "not_a_reviewed_plugin",
        }
    )

    result = _run_boundary(release, verifier, runner, env=env)

    assert result.returncode == 0, result.stderr
    assert not sentinel.exists()
    evidence = _marker(result.stdout)
    assert evidence["collected"] == "2"
    assert evidence["terminal"] == "2"
    assert evidence["passed"] == "1"
    assert evidence["skipped"] == "1"
    assert evidence["failed"] == "0"
    assert evidence["descendants"] == "0"
    assert evidence["result"] == "passed"
    assert evidence["worker_uid"] == str(os.geteuid())


@pytest.mark.parametrize(
    ("source", "expected_collected"),
    (
        ("# intentionally no tests\n", "0"),
        ("def test_failure():\n    assert False\n", "1"),
    ),
)
def test_zero_tests_and_failures_never_pass_boundary(
    isolated_release: tuple[Path, Path, Path, Path],
    source: str,
    expected_collected: str,
) -> None:
    release, tests, verifier, runner = isolated_release
    _write_test(tests, source)

    result = _run_boundary(release, verifier, runner)

    assert result.returncode == 1
    evidence = _marker(result.stdout)
    assert evidence["collected"] == expected_collected
    assert evidence["result"] == "failed"


def test_double_fork_style_delayed_descendant_is_killed_and_rejected(
    isolated_release: tuple[Path, Path, Path, Path],
) -> None:
    release, tests, verifier, runner = isolated_release
    token = uuid.uuid4().hex
    pid_path = Path("/tmp") / f"hub-1853-{token}.pid"
    sentinel = Path("/tmp") / f"hub-1853-{token}.sentinel"
    child_code = (
        "import os,time;"
        f"open({str(pid_path)!r}, 'w').write(str(os.getpid()));"
        "time.sleep(2);"
        f"open({str(sentinel)!r}, 'w').write('late')"
    )
    _write_test(
        tests,
        "import pathlib\n"
        "import subprocess\n"
        "import sys\n"
        "import time\n"
        f"CODE = {child_code!r}\n"
        f"PID_PATH = pathlib.Path({str(pid_path)!r})\n"
        "def test_spawns_delayed_descendant():\n"
        "    subprocess.Popen([sys.executable, '-c', CODE], start_new_session=True)\n"
        "    deadline = time.monotonic() + 5\n"
        "    while not PID_PATH.exists():\n"
        "        assert time.monotonic() < deadline\n"
        "        time.sleep(0.01)\n",
    )
    try:
        environment = os.environ.copy()
        environment["HUB_1853_TEST_CHILD_PID"] = str(pid_path)
        result = _run_boundary(release, verifier, runner, env=environment)
        assert result.returncode == 1, result.stderr
        evidence = _marker(result.stdout)
        assert int(evidence["descendants"]) >= 1
        assert evidence["result"] == "failed"
        time.sleep(2.1)
        assert not sentinel.exists()
    finally:
        pid_path.unlink(missing_ok=True)
        sentinel.unlink(missing_ok=True)


def test_manifest_mode_detects_venv_drift(
    isolated_release: tuple[Path, Path, Path, Path],
) -> None:
    release, _tests, _verifier, _runner = isolated_release
    command = [
        "/usr/bin/python3",
        "-I",
        str(RUNNER),
        "manifest-venv",
        str(release),
    ]
    before = subprocess.run(command, capture_output=True, text=True, check=False)
    assert before.returncode == 0, before.stderr
    target = release / ".venv" / "manifest-poison"
    target.write_bytes(b"poison\n")
    target.chmod(0o644)
    after = subprocess.run(command, capture_output=True, text=True, check=False)
    assert after.returncode == 0, after.stderr
    assert before.stdout != after.stdout
    target.unlink()
