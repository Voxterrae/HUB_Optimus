from __future__ import annotations

import fcntl
import importlib.util
import json
import os
import shutil
import socket
import stat
import subprocess
import sys
import time
from pathlib import Path
from types import ModuleType

import pytest


ROOT = Path(__file__).resolve().parents[1]
LOCK_TOOL = ROOT / "ops" / "ec2" / "operation-lock.py"
DEPLOY = ROOT / "ops" / "ec2" / "deploy-current.sh"
ROLLBACK = ROOT / "ops" / "ec2" / "rollback-current.sh"
ADOPT = ROOT / "ops" / "ec2" / "adopt-legacy-current.sh"
LOCK_ENVIRONMENT = "HUB_OPTIMUS_OPERATION_LOCK_FD"
SENTINEL = b"operation-lock-sentinel\n"
ENTRYPOINTS = (
    ("deploy", DEPLOY, ("a" * 40,)),
    ("rollback", ROLLBACK, ()),
    ("adopt", ADOPT, ("a" * 40,)),
)


def _run(
    arguments: list[str | Path],
    *,
    env: dict[str, str] | None = None,
    pass_fds: tuple[int, ...] = (),
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(argument) for argument in arguments],
        env=env,
        pass_fds=pass_fds,
        capture_output=True,
        text=True,
        check=False,
    )


def _app_root(tmp_path: Path) -> Path:
    app_root = tmp_path / "app"
    shared = app_root / "shared"
    shared.mkdir(parents=True)
    app_root.chmod(0o755)
    shared.chmod(0o755)
    (app_root / "guard").write_bytes(b"app-root-guard\n")
    (shared / "guard").write_bytes(b"shared-guard\n")
    return app_root


def _environment(app_root: Path) -> dict[str, str]:
    env = os.environ.copy()
    env.pop(LOCK_ENVIRONMENT, None)
    env["HUB_OPTIMUS_APP_ROOT"] = str(app_root)
    return env


def _tree_snapshot(root: Path) -> dict[str, tuple[object, ...]]:
    snapshot: dict[str, tuple[object, ...]] = {}
    pending = [root]
    while pending:
        directory = pending.pop()
        for path in sorted(directory.iterdir(), key=lambda item: item.name):
            info = path.lstat()
            relative = str(path.relative_to(root))
            common: tuple[object, ...] = (
                stat.S_IMODE(info.st_mode),
                info.st_uid,
                info.st_gid,
                info.st_nlink,
            )
            if stat.S_ISDIR(info.st_mode):
                snapshot[relative] = ("directory", *common)
                pending.append(path)
            elif stat.S_ISREG(info.st_mode):
                snapshot[relative] = ("regular", *common, path.read_bytes())
            elif stat.S_ISLNK(info.st_mode):
                snapshot[relative] = ("symlink", *common, os.readlink(path))
            elif stat.S_ISFIFO(info.st_mode):
                snapshot[relative] = ("fifo", *common)
            elif stat.S_ISSOCK(info.st_mode):
                snapshot[relative] = ("socket", *common)
            else:
                snapshot[relative] = ("other", *common, info.st_mode)
    return snapshot


def _write_probe(path: Path, *, hold: bool = False) -> None:
    hold_logic = ""
    if hold:
        hold_logic = (
            "ready = Path(sys.argv[3])\n"
            "proceed = Path(sys.argv[4])\n"
            "ready.write_text(str(descriptor), encoding='ascii')\n"
            "deadline = time.monotonic() + 10\n"
            "while not proceed.exists():\n"
            "    if time.monotonic() >= deadline:\n"
            "        raise SystemExit('timed out waiting for release')\n"
            "    time.sleep(0.01)\n"
        )
    else:
        hold_logic = (
            "Path(sys.argv[3]).write_text(str(descriptor), encoding='ascii')\n"
        )
    path.write_text(
        "from pathlib import Path\n"
        "import os\n"
        "import subprocess\n"
        "import sys\n"
        "import time\n"
        "descriptor = int(os.environ.pop('HUB_OPTIMUS_OPERATION_LOCK_FD'))\n"
        "assert descriptor >= 100\n"
        "assert os.get_inheritable(descriptor)\n"
        "os.fstat(descriptor)\n"
        "verified = subprocess.run(\n"
        "    [\n"
        "        '/usr/bin/python3', '-I', sys.argv[1], 'verify',\n"
        "        sys.argv[2], str(descriptor),\n"
        "    ],\n"
        "    pass_fds=(descriptor,),\n"
        "    capture_output=True,\n"
        "    text=True,\n"
        "    check=False,\n"
        ")\n"
        "if verified.returncode != 0:\n"
        "    sys.stderr.write(verified.stderr)\n"
        "    raise SystemExit(verified.returncode)\n"
        "assert 'HUB_OPTIMUS_OPERATION_LOCK_FD' not in os.environ\n"
        "os.fstat(descriptor)\n"
        f"{hold_logic}",
        encoding="utf-8",
    )


def _exec_probe(
    app_root: Path,
    probe: Path,
    marker: Path,
) -> subprocess.CompletedProcess[str]:
    return _run(
        [
            "/usr/bin/python3",
            "-I",
            LOCK_TOOL,
            "exec",
            app_root,
            "/usr/bin/python3",
            probe,
            LOCK_TOOL,
            app_root,
            marker,
        ],
        env=_environment(app_root),
    )


def _load_lock_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "hub_optimus_operation_lock",
        LOCK_TOOL,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _install_unsafe_lock(app_root: Path, kind: str, tmp_path: Path) -> None:
    lock = app_root / "shared" / "deploy.lock"
    if kind == "symlink":
        target = tmp_path / "symlink-sentinel"
        target.write_bytes(SENTINEL)
        target.chmod(0o600)
        lock.symlink_to(target)
    elif kind == "hardlink":
        target = tmp_path / "hardlink-sentinel"
        target.write_bytes(SENTINEL)
        target.chmod(0o600)
        os.link(target, lock)
    elif kind == "fifo":
        os.mkfifo(lock, 0o600)
    elif kind == "socket":
        try:
            listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        except PermissionError:
            pytest.skip("sandbox does not permit creating a Unix socket")
        try:
            listener.bind(str(lock))
        finally:
            listener.close()
        lock.chmod(0o600)
    elif kind == "directory":
        lock.mkdir(mode=0o700)
    else:
        raise AssertionError(f"unsupported unsafe lock kind: {kind}")


@pytest.mark.parametrize("preexisting", (False, True))
def test_lock_creation_and_existing_sentinel_are_safe(
    tmp_path: Path,
    preexisting: bool,
) -> None:
    app_root = _app_root(tmp_path)
    lock = app_root / "shared" / "deploy.lock"
    if preexisting:
        lock.write_bytes(SENTINEL)
        lock.chmod(0o600)
    probe = tmp_path / "probe.py"
    marker = tmp_path / "verified-fd"
    _write_probe(probe)

    result = _exec_probe(app_root, probe, marker)

    assert result.returncode == 0, result.stderr
    assert int(marker.read_text(encoding="ascii")) >= 100
    assert stat.S_IMODE(lock.stat().st_mode) == 0o600
    assert lock.stat().st_uid == os.geteuid()
    assert lock.stat().st_nlink == 1
    assert lock.read_bytes() == (SENTINEL if preexisting else b"")


@pytest.mark.parametrize("kind", ("symlink", "hardlink", "fifo", "socket", "directory"))
@pytest.mark.parametrize(
    ("entrypoint_name", "entrypoint", "arguments"),
    ENTRYPOINTS,
)
def test_unsafe_lock_object_rejects_every_entrypoint_without_mutation(
    tmp_path: Path,
    kind: str,
    entrypoint_name: str,
    entrypoint: Path,
    arguments: tuple[str, ...],
) -> None:
    del entrypoint_name
    app_root = _app_root(tmp_path)
    _install_unsafe_lock(app_root, kind, tmp_path)
    before = _tree_snapshot(app_root)

    result = _run(
        [entrypoint, *arguments],
        env=_environment(app_root),
    )

    assert result.returncode == 1
    assert "operation-lock:error" in result.stderr
    assert _tree_snapshot(app_root) == before
    sentinel = tmp_path / f"{kind}-sentinel"
    if sentinel.exists():
        assert sentinel.read_bytes() == SENTINEL


@pytest.mark.parametrize(
    ("entrypoint_name", "entrypoint", "arguments"),
    ENTRYPOINTS,
)
def test_wrong_lock_mode_rejects_every_entrypoint_without_truncation(
    tmp_path: Path,
    entrypoint_name: str,
    entrypoint: Path,
    arguments: tuple[str, ...],
) -> None:
    del entrypoint_name
    app_root = _app_root(tmp_path)
    lock = app_root / "shared" / "deploy.lock"
    lock.write_bytes(SENTINEL)
    lock.chmod(0o644)
    before = _tree_snapshot(app_root)

    result = _run(
        [entrypoint, *arguments],
        env=_environment(app_root),
    )

    assert result.returncode == 1
    assert "does not have mode 0600" in result.stderr
    assert _tree_snapshot(app_root) == before
    assert lock.read_bytes() == SENTINEL
    assert stat.S_IMODE(lock.stat().st_mode) == 0o644


def test_uid_and_directory_policy_is_explicitly_enforced(tmp_path: Path) -> None:
    module = _load_lock_module()
    app_root = _app_root(tmp_path)
    lock = app_root / "shared" / "deploy.lock"
    lock.write_bytes(SENTINEL)
    lock.chmod(0o600)
    lock_info = lock.stat()
    directory_info = app_root.stat()

    with pytest.raises(module.OperationLockError, match="effective user"):
        module.validate_lock(lock_info, lock_info.st_uid + 1)
    with pytest.raises(module.OperationLockError, match="effective user"):
        module.validate_directory(
            directory_info,
            "APP_ROOT",
            directory_info.st_uid + 1,
        )


@pytest.mark.parametrize("directory", ("app-root", "shared"))
def test_writable_directory_is_rejected_before_lock_creation(
    tmp_path: Path,
    directory: str,
) -> None:
    app_root = _app_root(tmp_path)
    unsafe = app_root if directory == "app-root" else app_root / "shared"
    unsafe.chmod(0o777)
    before = _tree_snapshot(app_root)
    marker = tmp_path / "should-not-exist"
    probe = tmp_path / "probe.py"
    _write_probe(probe)

    result = _exec_probe(app_root, probe, marker)

    assert result.returncode == 1
    assert "group- or world-writable" in result.stderr
    assert _tree_snapshot(app_root) == before
    assert not (app_root / "shared" / "deploy.lock").exists()
    assert not marker.exists()


@pytest.mark.parametrize(
    ("entrypoint_name", "entrypoint", "arguments"),
    ENTRYPOINTS,
)
def test_correct_lock_file_but_unlocked_fd_cannot_skip_bootstrap(
    tmp_path: Path,
    entrypoint_name: str,
    entrypoint: Path,
    arguments: tuple[str, ...],
) -> None:
    del entrypoint_name
    app_root = _app_root(tmp_path)
    lock = app_root / "shared" / "deploy.lock"
    lock.write_bytes(SENTINEL)
    lock.chmod(0o600)
    opened = os.open(lock, os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK)
    descriptor = fcntl.fcntl(opened, fcntl.F_DUPFD_CLOEXEC, 100)
    os.close(opened)
    os.set_inheritable(descriptor, True)
    env = _environment(app_root)
    env[LOCK_ENVIRONMENT] = str(descriptor)
    before = _tree_snapshot(app_root)
    try:
        result = _run(
            [entrypoint, *arguments],
            env=env,
            pass_fds=(descriptor,),
        )
    finally:
        os.close(descriptor)

    assert result.returncode == 1
    assert "does not retain the exclusive flock" in result.stderr
    assert _tree_snapshot(app_root) == before


def test_unlocked_correct_fd_is_rejected_while_another_holder_owns_lock(
    tmp_path: Path,
) -> None:
    app_root = _app_root(tmp_path)
    probe = tmp_path / "hold.py"
    ready = tmp_path / "ready"
    proceed = tmp_path / "proceed"
    _write_probe(probe, hold=True)
    holder = subprocess.Popen(
        [
            "/usr/bin/python3",
            "-I",
            str(LOCK_TOOL),
            "exec",
            str(app_root),
            "/usr/bin/python3",
            str(probe),
            str(LOCK_TOOL),
            str(app_root),
            str(ready),
            str(proceed),
        ],
        env=_environment(app_root),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    deadline = time.monotonic() + 10
    while not ready.exists() and holder.poll() is None:
        if time.monotonic() >= deadline:
            holder.kill()
            raise AssertionError("lock holder did not become ready")
        time.sleep(0.01)
    assert holder.poll() is None

    lock = app_root / "shared" / "deploy.lock"
    opened = os.open(lock, os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK)
    descriptor = fcntl.fcntl(opened, fcntl.F_DUPFD_CLOEXEC, 100)
    os.close(opened)
    os.set_inheritable(descriptor, True)
    env = _environment(app_root)
    env[LOCK_ENVIRONMENT] = str(descriptor)
    before = _tree_snapshot(app_root)
    try:
        result = _run([ROLLBACK], env=env, pass_fds=(descriptor,))
    finally:
        os.close(descriptor)
        proceed.touch()
        stdout, stderr = holder.communicate(timeout=10)

    assert holder.returncode == 0, f"{stdout}\n{stderr}"
    assert result.returncode == 1
    assert "is not the exclusive lock owner" in result.stderr
    assert _tree_snapshot(app_root) == before


@pytest.mark.parametrize(
    ("entrypoint_name", "entrypoint", "arguments"),
    ENTRYPOINTS,
)
def test_concurrent_operation_is_rejected_without_mutation(
    tmp_path: Path,
    entrypoint_name: str,
    entrypoint: Path,
    arguments: tuple[str, ...],
) -> None:
    del entrypoint_name
    app_root = _app_root(tmp_path)
    probe = tmp_path / "hold.py"
    ready = tmp_path / "ready"
    proceed = tmp_path / "proceed"
    _write_probe(probe, hold=True)
    holder = subprocess.Popen(
        [
            "/usr/bin/python3",
            "-I",
            str(LOCK_TOOL),
            "exec",
            str(app_root),
            "/usr/bin/python3",
            str(probe),
            str(LOCK_TOOL),
            str(app_root),
            str(ready),
            str(proceed),
        ],
        env=_environment(app_root),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    deadline = time.monotonic() + 10
    while not ready.exists() and holder.poll() is None:
        if time.monotonic() >= deadline:
            holder.kill()
            raise AssertionError("lock holder did not become ready")
        time.sleep(0.01)
    assert holder.poll() is None
    before = _tree_snapshot(app_root)
    try:
        blocked = _run(
            [entrypoint, *arguments],
            env=_environment(app_root),
        )
    finally:
        proceed.touch()
        stdout, stderr = holder.communicate(timeout=10)

    assert holder.returncode == 0, f"{stdout}\n{stderr}"
    assert blocked.returncode == 1
    assert "another deploy, rollback, or adoption operation is active" in (
        blocked.stderr
    )
    assert _tree_snapshot(app_root) == before


def test_entrypoints_reexec_and_verify_before_mutation() -> None:
    first_mutations = {
        DEPLOY: 'mkdir -p "$APP_ROOT/releases"',
        ROLLBACK: 'ROLLBACK_WORK_DIR="$(\n  mktemp -d',
        ADOPT: 'ADOPTION_WORK_DIR="$(\n  mktemp -d',
    }
    for entrypoint, first_mutation in first_mutations.items():
        source = entrypoint.read_text(encoding="utf-8")
        bootstrap = source.index('verify_or_acquire_operation_lock "$@"')
        assert bootstrap < source.index(first_mutation)
        assert 'exec /usr/bin/python3 -I \\\n' in source
        assert '"$OPERATION_LOCK_TOOL" \\\n    verify' in source
        verify_call = source.index('"$HUB_OPTIMUS_OPERATION_LOCK_FD" \\\n')
        unset_call = source.index("unset HUB_OPTIMUS_OPERATION_LOCK_FD")
        assert verify_call < unset_call < bootstrap
        assert 'exec 9> "$APP_ROOT/shared/deploy.lock"' not in source
        assert "flock -n 9" not in source


@pytest.mark.parametrize(
    ("raw_descriptor", "descriptor_kind"),
    (
        ("not-a-number", "none"),
        ("100", "closed"),
        (None, "pipe"),
        (None, "other-file"),
    ),
)
def test_forged_inherited_descriptor_cannot_skip_bootstrap(
    tmp_path: Path,
    raw_descriptor: str | None,
    descriptor_kind: str,
) -> None:
    app_root = _app_root(tmp_path)
    lock = app_root / "shared" / "deploy.lock"
    lock.write_bytes(SENTINEL)
    lock.chmod(0o600)
    env = _environment(app_root)
    descriptors: list[int] = []
    passed: tuple[int, ...] = ()

    if descriptor_kind == "pipe":
        read_fd, write_fd = os.pipe()
        descriptors.extend((read_fd, write_fd))
        inherited = fcntl.fcntl(read_fd, fcntl.F_DUPFD_CLOEXEC, 100)
        descriptors.append(inherited)
        os.set_inheritable(inherited, True)
        raw_descriptor = str(inherited)
        passed = (inherited,)
    elif descriptor_kind == "other-file":
        other = tmp_path / "other.lock"
        other.write_bytes(SENTINEL)
        other.chmod(0o600)
        opened = os.open(other, os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK)
        descriptors.append(opened)
        inherited = fcntl.fcntl(opened, fcntl.F_DUPFD_CLOEXEC, 100)
        descriptors.append(inherited)
        os.set_inheritable(inherited, True)
        fcntl.flock(inherited, fcntl.LOCK_EX | fcntl.LOCK_NB)
        raw_descriptor = str(inherited)
        passed = (inherited,)

    assert raw_descriptor is not None
    env[LOCK_ENVIRONMENT] = raw_descriptor
    before = _tree_snapshot(app_root)
    try:
        result = _run([ROLLBACK], env=env, pass_fds=passed)
    finally:
        for descriptor in reversed(descriptors):
            try:
                os.close(descriptor)
            except OSError:
                pass

    assert result.returncode == 1
    assert "operation-lock:error" in result.stderr
    assert _tree_snapshot(app_root) == before


@pytest.mark.parametrize("parent_kind", ("app-root", "shared"))
@pytest.mark.parametrize(
    ("entrypoint_name", "entrypoint", "arguments"),
    ENTRYPOINTS,
)
def test_symlinked_lock_parent_is_rejected_without_mutation(
    tmp_path: Path,
    parent_kind: str,
    entrypoint_name: str,
    entrypoint: Path,
    arguments: tuple[str, ...],
) -> None:
    del entrypoint_name
    real_root = _app_root(tmp_path)
    if parent_kind == "app-root":
        app_root = tmp_path / "linked-app"
        app_root.symlink_to(real_root, target_is_directory=True)
    else:
        external_shared = tmp_path / "external-shared"
        external_shared.mkdir(mode=0o755)
        shutil.rmtree(real_root / "shared")
        (real_root / "shared").symlink_to(
            external_shared,
            target_is_directory=True,
        )
        app_root = real_root
    before = _tree_snapshot(tmp_path)

    result = _run(
        [entrypoint, *arguments],
        env=_environment(app_root),
    )

    assert result.returncode == 1
    assert "operation-lock:error" in result.stderr
    assert _tree_snapshot(tmp_path) == before


def _instrument_entrypoints(source: Path, destination: Path) -> dict[str, Path]:
    shutil.copytree(source, destination)
    instrumented: dict[str, Path] = {}
    injection = (
        'verify_or_acquire_operation_lock "$@"\n'
        'printf "ready\\n" > "$HUB_LOCK_TEST_READY"\n'
        'while [ ! -e "$HUB_LOCK_TEST_PROCEED" ]; do\n'
        '  /bin/sleep 0.01\n'
        'done\n'
    )
    for name, entrypoint, _arguments in ENTRYPOINTS:
        target = destination / entrypoint.name
        source_text = target.read_text(encoding="utf-8")
        marker = 'verify_or_acquire_operation_lock "$@"\n'
        assert source_text.count(marker) == 1
        target.write_text(
            source_text.replace(marker, injection, 1),
            encoding="utf-8",
        )
        target.chmod(0o755)
        instrumented[name] = target
    return instrumented


@pytest.mark.parametrize(
    ("holder_name", "holder_entrypoint", "holder_arguments"),
    ENTRYPOINTS,
)
@pytest.mark.parametrize(
    ("contender_name", "contender_entrypoint", "contender_arguments"),
    ENTRYPOINTS,
)
def test_every_supported_operation_pair_is_mutually_exclusive(
    tmp_path: Path,
    holder_name: str,
    holder_entrypoint: Path,
    holder_arguments: tuple[str, ...],
    contender_name: str,
    contender_entrypoint: Path,
    contender_arguments: tuple[str, ...],
) -> None:
    del holder_entrypoint, contender_entrypoint
    app_root = _app_root(tmp_path)
    copied = _instrument_entrypoints(
        ROOT / "ops" / "ec2",
        tmp_path / f"ops-{holder_name}-{contender_name}",
    )
    ready = tmp_path / "holder-ready"
    proceed = tmp_path / "holder-proceed"
    holder_env = _environment(app_root)
    holder_env["HUB_LOCK_TEST_READY"] = str(ready)
    holder_env["HUB_LOCK_TEST_PROCEED"] = str(proceed)
    holder = subprocess.Popen(
        [str(copied[holder_name]), *holder_arguments],
        env=holder_env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    deadline = time.monotonic() + 10
    while not ready.exists() and holder.poll() is None:
        if time.monotonic() >= deadline:
            holder.kill()
            raise AssertionError("supported operation did not retain the lock")
        time.sleep(0.01)
    assert holder.poll() is None
    before = _tree_snapshot(app_root)
    try:
        contender_env = _environment(app_root)
        contender_env["HUB_LOCK_TEST_READY"] = str(tmp_path / "contender-ready")
        contender_env["HUB_LOCK_TEST_PROCEED"] = str(proceed)
        blocked = _run(
            [copied[contender_name], *contender_arguments],
            env=contender_env,
        )
        after = _tree_snapshot(app_root)
    finally:
        holder.terminate()
        try:
            holder.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            holder.kill()
            holder.communicate(timeout=10)

    assert blocked.returncode == 1
    assert "another deploy, rollback, or adoption operation is active" in (
        blocked.stderr
    )
    assert after == before


def test_verified_parent_does_not_delegate_lock_to_a_descendant(
    tmp_path: Path,
) -> None:
    app_root = _app_root(tmp_path)
    result_file = tmp_path / "descendant-result.json"
    probe = tmp_path / "descendant-probe.py"
    probe.write_text(
        "import json\n"
        "import os\n"
        "import subprocess\n"
        "import sys\n"
        "descriptor = int(os.environ.pop('HUB_OPTIMUS_OPERATION_LOCK_FD'))\n"
        "verified = subprocess.run(\n"
        "    ['/usr/bin/python3', '-I', sys.argv[1], 'verify', sys.argv[2], str(descriptor)],\n"
        "    pass_fds=(descriptor,), capture_output=True, text=True, check=False,\n"
        ")\n"
        "assert verified.returncode == 0, verified.stderr\n"
        "environment = os.environ.copy()\n"
        "environment.pop('HUB_OPTIMUS_OPERATION_LOCK_FD', None)\n"
        "child = subprocess.run(\n"
        "    [sys.argv[3]], env=environment, pass_fds=(descriptor,),\n"
        "    capture_output=True, text=True, check=False,\n"
        ")\n"
        "with open(sys.argv[4], 'w', encoding='utf-8') as stream:\n"
        "    json.dump({'returncode': child.returncode, 'stderr': child.stderr}, stream)\n",
        encoding="utf-8",
    )
    parent = _run(
        [
            "/usr/bin/python3",
            "-I",
            LOCK_TOOL,
            "exec",
            app_root,
            "/usr/bin/python3",
            probe,
            LOCK_TOOL,
            app_root,
            ROLLBACK,
            result_file,
        ],
        env=_environment(app_root),
    )

    assert parent.returncode == 0, parent.stderr
    outcome = json.loads(result_file.read_text(encoding="utf-8"))
    assert outcome["returncode"] == 1
    assert "another deploy, rollback, or adoption operation is active" in (
        outcome["stderr"]
    )
    assert not (app_root / "current").exists()
