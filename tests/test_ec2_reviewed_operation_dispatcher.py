from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
DISPATCHER = ROOT / "ops" / "ec2" / "run-reviewed-operation.py"
HUB_OPS = ROOT / "ops" / "ec2" / "hub-ops.sh"
POISONED_NAMES = (
    "BASH_ENV",
    "BASH_FUNC_git%%",
    "GIT_CONFIG_GLOBAL",
    "GIT_DIR",
    "PIP_CONFIG_FILE",
    "PYTHONPATH",
    "PYTEST_ADDOPTS",
    "PYTEST_PLUGINS",
    "HUB_OPTIMUS_TEST_FAIL_AFTER_MUTATION",
)


def _run(
    arguments: list[str | Path],
    *,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(argument) for argument in arguments],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def _fixture(tmp_path: Path) -> tuple[Path, Path]:
    ops = tmp_path / "ops"
    ops.mkdir()
    dispatcher = ops / DISPATCHER.name
    shutil.copy2(DISPATCHER, dispatcher)
    probe = ops / "deploy-current.sh"
    probe.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        "/usr/bin/python3 -I - \"$1\" <<'PY'\n"
        "import json\n"
        "import os\n"
        "import sys\n"
        "with open(sys.argv[1], 'w', encoding='utf-8') as stream:\n"
        "    json.dump(dict(os.environ), stream, sort_keys=True)\n"
        "PY\n",
        encoding="utf-8",
    )
    probe.chmod(0o755)
    return dispatcher, probe


def _operational_snapshot(root: Path) -> tuple[tuple[object, ...], ...]:
    records: list[tuple[object, ...]] = []
    for path in sorted((root, *root.rglob("*")), key=lambda item: str(item)):
        info = path.lstat()
        relative = "." if path == root else str(path.relative_to(root))
        if path.is_symlink():
            payload: object = ("symlink", os.readlink(path))
        elif path.is_file():
            payload = ("file", path.read_bytes())
        else:
            payload = ("directory",)
        records.append(
            (
                relative,
                info.st_mode,
                info.st_uid,
                info.st_gid,
                info.st_nlink,
                payload,
            )
        )
    return tuple(records)


def _hub_ops_fixture(tmp_path: Path) -> tuple[Path, Path, Path]:
    dispatcher, _probe = _fixture(tmp_path)
    ops = dispatcher.parent
    hub_ops = ops / HUB_OPS.name
    source = HUB_OPS.read_text(encoding="utf-8")
    app_root = tmp_path / "app-root"
    source = source.replace(
        'APP_ROOT = Path("/opt/hub-optimus")',
        f"APP_ROOT = Path({str(app_root)!r})",
        1,
    )
    hub_ops.write_text(source, encoding="utf-8")
    hub_ops.chmod(0o755)
    (app_root / "shared").mkdir(parents=True)
    (app_root / "releases").mkdir()
    (app_root / "shared" / "RELEASE_STATE").write_text(
        "status=stable\n",
        encoding="ascii",
    )
    return hub_ops, app_root, ops


def test_dispatcher_prevents_bash_env_and_ambient_tool_poisoning(
    tmp_path: Path,
) -> None:
    dispatcher, probe = _fixture(tmp_path)
    sentinel = tmp_path / "bash-env-ran"
    bash_env = tmp_path / "bash-env.sh"
    bash_env.write_text(
        f"printf poison > {sentinel}\n",
        encoding="utf-8",
    )
    output = tmp_path / "environment.json"
    app_root = tmp_path / "app"
    repository = tmp_path / "repo"
    env = os.environ.copy()
    for name in POISONED_NAMES:
        env[name] = str(bash_env) if name == "BASH_ENV" else "poison"

    poisoned_direct = _run(["/bin/bash", probe, tmp_path / "direct.json"], env=env)
    assert poisoned_direct.returncode == 0, poisoned_direct.stderr
    assert sentinel.read_bytes() == b"poison"
    sentinel.unlink()

    result = _run(
        [
            "/usr/bin/python3",
            "-I",
            dispatcher,
            "--app-root",
            app_root,
            "--repo-url",
            repository,
            "deploy",
            output,
        ],
        env=env,
    )

    assert result.returncode == 0, result.stderr
    assert not sentinel.exists()
    observed = json.loads(output.read_text(encoding="utf-8"))
    assert all(name not in observed for name in POISONED_NAMES)
    assert observed["HUB_OPTIMUS_APP_ROOT"] == str(app_root)
    assert observed["HUB_OPTIMUS_REPO_URL"] == str(repository)
    assert observed["PATH"] == "/usr/bin:/bin"


@pytest.mark.parametrize("unsafe", ("symlink", "hardlink", "writable"))
def test_dispatcher_rejects_unsafe_operation_script(
    tmp_path: Path,
    unsafe: str,
) -> None:
    dispatcher, probe = _fixture(tmp_path)
    if unsafe == "symlink":
        target = tmp_path / "target.sh"
        probe.replace(target)
        probe.symlink_to(target)
    elif unsafe == "hardlink":
        os.link(probe, tmp_path / "second-link.sh")
    else:
        probe.chmod(0o777)

    result = _run(
        [
            "/usr/bin/python3",
            "-I",
            dispatcher,
            "--app-root",
            tmp_path / "app",
            "--repo-url",
            tmp_path / "repo",
            "deploy",
            tmp_path / "unused",
        ]
    )

    assert result.returncode == 1
    assert "reviewed-operation:error" in result.stderr


def test_dispatcher_rejects_wrong_operation_arity(tmp_path: Path) -> None:
    dispatcher, _probe = _fixture(tmp_path)
    result = _run(
        [
            "/usr/bin/python3",
            "-I",
            dispatcher,
            "--app-root",
            tmp_path / "app",
            "--repo-url",
            tmp_path / "repo",
            "rollback",
            "unexpected",
        ]
    )
    assert result.returncode == 1
    assert "rollback requires exactly 0" in result.stderr


def test_supported_hub_ops_entrypoint_never_exposes_bash_startup_poison(
    tmp_path: Path,
) -> None:
    hub_ops, app_root, _ops = _hub_ops_fixture(tmp_path)
    marker = app_root / "bash-env-ran"
    bash_env = tmp_path / "bash-env.sh"
    bash_env.write_text(
        f"printf poison > {marker}\n",
        encoding="utf-8",
    )
    output = tmp_path / "environment.json"
    environment = os.environ.copy()
    environment.update(
        {
            "BASH_ENV": str(bash_env),
            "BASH_FUNC_git%%": "() { printf function-poison; }",
            "PYTHONPATH": str(tmp_path / "python-poison"),
            "PYTEST_ADDOPTS": "--collect-only",
            "GIT_DIR": str(tmp_path / "git-poison"),
        }
    )
    before = _operational_snapshot(app_root)

    result = _run([hub_ops, "deploy", output], env=environment)

    assert result.returncode == 0, result.stderr
    assert not marker.exists()
    assert _operational_snapshot(app_root) == before
    observed = json.loads(output.read_text(encoding="utf-8"))
    assert "BASH_ENV" not in observed
    assert "BASH_FUNC_git%%" not in observed
    assert "PYTHONPATH" not in observed
    assert "PYTEST_ADDOPTS" not in observed
    assert "GIT_DIR" not in observed
    assert HUB_OPS.read_text(encoding="utf-8").startswith("#!/usr/bin/python3 -I\n")
