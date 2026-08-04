#!/usr/bin/env python3
"""Run candidate pytest validation behind an isolated Linux supervisor."""

from __future__ import annotations

import argparse
import ctypes
import errno
import fcntl
import hashlib
import json
import os
import pwd
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import time
from pathlib import Path


PR_SET_CHILD_SUBREAPER = 36
PR_SET_NO_NEW_PRIVS = 38
IDENTITY_FIELDS = (
    "st_dev",
    "st_ino",
    "st_mode",
    "st_nlink",
    "st_uid",
    "st_gid",
    "st_size",
    "st_mtime_ns",
    "st_ctime_ns",
)
WORKER_SOURCE = r'''from __future__ import annotations

import hashlib
import json
import os
import sys

import pytest


class Evidence:
    def __init__(self):
        self.nodeids = []
        self.outcomes = {}

    def pytest_collection_finish(self, session):
        self.nodeids = [item.nodeid for item in session.items]

    def pytest_runtest_logreport(self, report):
        terminal = report.when == "call" or (
            report.when == "setup" and report.outcome in {"failed", "skipped"}
        )
        if terminal and report.nodeid not in self.outcomes:
            self.outcomes[report.nodeid] = report.outcome


def main():
    release, result_path = sys.argv[1:]
    plugin = Evidence()
    # Import pytest before exposing the reviewed source tree on sys.path. This
    # prevents a tracked top-level pytest.py from replacing the installed tool.
    sys.path.insert(0, release)
    exit_code = int(pytest.main([
        "-q",
        "-c", "/dev/null",
        "-o", "addopts=",
        "-p", "no:cacheprovider",
        os.path.join(release, "tests"),
    ], plugins=[plugin]))
    nodeids = plugin.nodeids
    outcomes = plugin.outcomes
    terminal = len(outcomes)
    passed = sum(value == "passed" for value in outcomes.values())
    skipped = sum(value == "skipped" for value in outcomes.values())
    failed = sum(value == "failed" for value in outcomes.values())
    digest = hashlib.sha256()
    for nodeid in nodeids:
        raw = nodeid.encode("utf-8")
        digest.update(len(raw).to_bytes(8, "big"))
        digest.update(raw)
    evidence = {
        "collected": len(nodeids),
        "failed": failed,
        "nodeids_sha256": digest.hexdigest(),
        "passed": passed,
        "pytest_exit_code": exit_code,
        "skipped": skipped,
        "terminal": terminal,
    }
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(result_path, flags, 0o600)
    try:
        raw = (json.dumps(evidence, sort_keys=True, separators=(",", ":")) + "\n").encode("ascii")
        view = memoryview(raw)
        written = 0
        while written < len(view):
            written += os.write(descriptor, view[written:])
    finally:
        os.close(descriptor)
    valid = (
        exit_code == 0
        and len(nodeids) > 0
        and terminal == len(nodeids)
        and failed == 0
        and passed + skipped == terminal
        and set(outcomes) == set(nodeids)
    )
    raise SystemExit(0 if valid else 1)


main()
'''


class ValidationError(RuntimeError):
    pass


def fail(message: str) -> None:
    raise ValidationError(message)


def same_identity(left: os.stat_result, right: os.stat_result) -> bool:
    return all(
        getattr(left, field) == getattr(right, field)
        for field in IDENTITY_FIELDS
    )


def canonical_directory(raw: str, label: str) -> Path:
    if not os.path.isabs(raw) or os.path.abspath(raw) != raw:
        fail(f"{label} must be one canonical absolute path")
    path = Path(raw)
    try:
        visible = path.lstat()
    except OSError as exc:
        fail(f"cannot inspect {label}: {exc}")
    if path.is_symlink() or not stat.S_ISDIR(visible.st_mode):
        fail(f"{label} is not one real directory")
    if stat.S_IMODE(visible.st_mode) & 0o022:
        fail(f"{label} is group- or world-writable")
    return path


def open_regular(path: Path) -> tuple[bytes, os.stat_result]:
    flags = os.O_RDONLY | os.O_CLOEXEC | os.O_NONBLOCK
    if not hasattr(os, "O_NOFOLLOW"):
        fail("O_NOFOLLOW is unavailable")
    flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        fail(f"cannot safely open venv file {path}: {exc}")
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
            fail(f"venv path is not one regular single-link file: {path}")
        if stat.S_IMODE(before.st_mode) & 0o022:
            fail(f"venv path is group- or world-writable: {path}")
        chunks: list[bytes] = []
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    visible = path.stat(follow_symlinks=False)
    if not same_identity(before, after) or not same_identity(after, visible):
        fail(f"venv path changed while it was read: {path}")
    return b"".join(chunks), after


def venv_manifest(venv: Path, forbidden_owner: int | None) -> str:
    root = canonical_directory(str(venv), "candidate venv")
    digest = hashlib.sha256()
    pending = [root]
    records: list[tuple[str, bytes, os.stat_result]] = []
    while pending:
        directory = pending.pop()
        info = directory.stat(follow_symlinks=False)
        if not stat.S_ISDIR(info.st_mode):
            fail(f"venv directory changed type: {directory}")
        if stat.S_IMODE(info.st_mode) & 0o022:
            fail(f"venv directory is group- or world-writable: {directory}")
        if forbidden_owner is not None and info.st_uid == forbidden_owner:
            if stat.S_IMODE(info.st_mode) & 0o200:
                fail(f"validation worker owns a writable venv directory: {directory}")
        relative_directory = str(directory.relative_to(root)) or "."
        records.append((relative_directory + "/", b"directory", info))
        try:
            entries = sorted(os.scandir(directory), key=lambda item: item.name)
        except OSError as exc:
            fail(f"cannot enumerate candidate venv {directory}: {exc}")
        for entry in entries:
            path = Path(entry.path)
            entry_info = entry.stat(follow_symlinks=False)
            relative = str(path.relative_to(root))
            if stat.S_ISDIR(entry_info.st_mode):
                pending.append(path)
            elif stat.S_ISREG(entry_info.st_mode):
                raw, stable = open_regular(path)
                if forbidden_owner is not None and stable.st_uid == forbidden_owner:
                    if stat.S_IMODE(stable.st_mode) & 0o200:
                        fail(f"validation worker owns a writable venv file: {path}")
                records.append((relative, raw, stable))
            elif stat.S_ISLNK(entry_info.st_mode):
                target = os.readlink(path)
                second = path.stat(follow_symlinks=False)
                if not same_identity(entry_info, second):
                    fail(f"venv symlink changed while it was read: {path}")
                records.append((relative, ("symlink:" + target).encode(), second))
            else:
                fail(f"unsupported special file in candidate venv: {path}")
    for relative, raw, info in sorted(records, key=lambda record: record[0]):
        encoded = relative.encode("utf-8")
        digest.update(len(encoded).to_bytes(8, "big"))
        digest.update(encoded)
        digest.update(len(raw).to_bytes(8, "big"))
        digest.update(raw)
        for field in IDENTITY_FIELDS:
            digest.update(int(getattr(info, field)).to_bytes(16, "big", signed=False))
    return digest.hexdigest()


def sealed_worker() -> int:
    if not hasattr(os, "memfd_create"):
        fail("memfd_create is unavailable")
    flags = getattr(os, "MFD_CLOEXEC", 0x0001) | getattr(
        os,
        "MFD_ALLOW_SEALING",
        0x0002,
    )
    descriptor = os.memfd_create("hub-optimus-validation-worker", flags)
    raw = WORKER_SOURCE.encode("utf-8")
    try:
        view = memoryview(raw)
        written = 0
        while written < len(view):
            written += os.write(descriptor, view[written:])
        os.lseek(descriptor, 0, os.SEEK_SET)
        os.fchmod(descriptor, 0o400)
        seals = (
            getattr(fcntl, "F_SEAL_SEAL", 0x0001)
            | getattr(fcntl, "F_SEAL_SHRINK", 0x0002)
            | getattr(fcntl, "F_SEAL_GROW", 0x0004)
            | getattr(fcntl, "F_SEAL_WRITE", 0x0008)
        )
        fcntl.fcntl(descriptor, getattr(fcntl, "F_ADD_SEALS", 1033), seals)
        if fcntl.fcntl(descriptor, getattr(fcntl, "F_GET_SEALS", 1034)) != seals:
            fail("validation worker memfd is not fully sealed")
    except BaseException:
        os.close(descriptor)
        raise
    return descriptor


def set_subreaper() -> None:
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.prctl(PR_SET_CHILD_SUBREAPER, 1, 0, 0, 0) != 0:
        error = ctypes.get_errno()
        fail(f"cannot enable child subreaper: {os.strerror(error)}")


def no_new_privileges() -> None:
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.prctl(PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0) != 0:
        error = ctypes.get_errno()
        raise OSError(error, os.strerror(error))


def direct_children() -> set[int]:
    try:
        tasks = list(Path("/proc/self/task").iterdir())
    except OSError as exc:
        fail(f"cannot enumerate supervisor tasks for descendant cleanup: {exc}")
    if not tasks:
        fail("cannot observe supervisor tasks for descendant cleanup")
    children: set[int] = set()
    for task in tasks:
        path = task / "children"
        try:
            raw = path.read_text(encoding="ascii").strip()
        except OSError as exc:
            fail(f"cannot observe validation descendants through {path}: {exc}")
        try:
            children.update(int(value) for value in raw.split())
        except ValueError:
            fail(f"kernel returned invalid validation descendants through {path}")
    return children


def kill_and_reap_descendants() -> set[int]:
    observed: set[int] = set()
    deadline = time.monotonic() + 5.0
    while time.monotonic() < deadline:
        children = direct_children()
        if not children:
            break
        observed.update(children)
        for child in children:
            try:
                os.kill(child, signal.SIGKILL)
            except ProcessLookupError:
                pass
        while True:
            try:
                waited, _status = os.waitpid(-1, os.WNOHANG)
            except ChildProcessError:
                break
            if waited == 0:
                break
        time.sleep(0.01)
    if direct_children():
        fail("could not reap all validation descendants")
    return observed


def clean_worker_environment(home: Path) -> dict[str, str]:
    return {
        "HOME": str(home),
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "PATH": "/usr/bin:/bin",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONNOUSERSITE": "1",
        "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
        "TMPDIR": str(home),
    }


def source_manifest(verifier: Path, release: Path, commit: str) -> bytes:
    try:
        visible = verifier.lstat()
    except OSError as exc:
        fail(f"cannot inspect source verifier: {exc}")
    if verifier.is_symlink() or not stat.S_ISREG(visible.st_mode):
        fail("source verifier is not one regular file")
    result = subprocess.run(
        [
            "/usr/bin/python3",
            "-I",
            str(verifier),
            str(release),
            commit,
            "--allow-generated",
            ".venv",
            "--allow-generated",
            ".hub-deployment",
        ],
        cwd="/",
        env={"HOME": "/nonexistent", "LANG": "C.UTF-8", "PATH": "/usr/bin:/bin"},
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        sys.stderr.buffer.write(result.stderr)
        fail("candidate source tree verification failed")
    try:
        parsed = json.loads(result.stdout)
    except (UnicodeDecodeError, json.JSONDecodeError):
        fail("source verifier returned invalid evidence")
    expected = (json.dumps(parsed, sort_keys=True, separators=(",", ":")) + "\n").encode("ascii")
    if result.stdout != expected:
        fail("source verifier evidence is not canonical")
    if parsed.get("commit") != commit or not isinstance(
        parsed.get("source_tree_sha256"),
        str,
    ):
        fail("source verifier evidence is incomplete")
    return result.stdout


def worker_identity(release: Path, venv: Path) -> tuple[int, int]:
    if os.geteuid() != 0:
        return os.getegid(), os.geteuid()
    try:
        account = pwd.getpwnam("nobody")
    except KeyError:
        fail("the nobody validation account is unavailable")
    if account.pw_uid == 0:
        fail("the nobody validation account unexpectedly resolves to root")
    for candidate in (release, venv):
        info = candidate.stat(follow_symlinks=False)
        if info.st_uid == account.pw_uid and stat.S_IMODE(info.st_mode) & 0o200:
            fail(f"validation worker can write candidate path: {candidate}")
    return account.pw_gid, account.pw_uid


def make_preexec(gid: int, uid: int):
    def prepare() -> None:
        if os.geteuid() == 0:
            os.setgroups([])
            os.setgid(gid)
            os.setuid(uid)
        no_new_privileges()

    return prepare


def marker(evidence: dict[str, object]) -> str:
    order = (
        "collected",
        "terminal",
        "passed",
        "skipped",
        "failed",
        "pytest_exit_code",
        "nodeids_sha256",
        "descendants",
        "source_tree_sha256",
        "venv_tree_sha256",
        "worker_uid",
        "result",
    )
    return "HUB_OPTIMUS_VALIDATION_V1 " + " ".join(
        f"{name}={evidence[name]}" for name in order
    )


def run_validation(
    release: Path,
    commit: str,
    verifier: Path,
    timeout: int,
) -> int:
    venv = canonical_directory(str(release / ".venv"), "candidate venv")
    venv_python = venv / "bin" / "python"
    if not venv_python.is_file() or not os.access(venv_python, os.X_OK):
        fail("candidate venv Python is not executable")
    gid, uid = worker_identity(release, venv)
    source_before = source_manifest(verifier, release, commit)
    venv_before = venv_manifest(venv, uid if uid != os.geteuid() else None)

    set_subreaper()
    temporary = Path(tempfile.mkdtemp(prefix="hub-optimus-validation-", dir="/tmp"))
    worker_descriptor = -1
    process: subprocess.Popen[bytes] | None = None
    observed_descendants: set[int] = set()
    try:
        if os.geteuid() == 0:
            try:
                os.chown(temporary, uid, gid)
            except OSError as exc:
                fail(f"cannot assign validation workspace to worker UID {uid}: {exc}")
        temporary.chmod(0o700)
        result_path = temporary / "evidence.json"
        log_path = temporary / "pytest.log"
        worker_descriptor = sealed_worker()
        with log_path.open("wb") as log_stream:
            process = subprocess.Popen(
                [
                    str(venv_python),
                    "-I",
                    "-B",
                    f"/proc/self/fd/{worker_descriptor}",
                    str(release),
                    str(result_path),
                ],
                cwd=release,
                env=clean_worker_environment(temporary),
                pass_fds=(worker_descriptor,),
                stdout=log_stream,
                stderr=subprocess.STDOUT,
                start_new_session=True,
                preexec_fn=make_preexec(gid, uid),
            )
            try:
                process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                process.wait(timeout=10)
        # Give orphans one scheduler turn to reparent to this subreaper.
        time.sleep(0.05)
        observed_descendants = kill_and_reap_descendants()
        raw_log = log_path.read_bytes()
        sys.stdout.buffer.write(raw_log)
        if raw_log and not raw_log.endswith(b"\n"):
            sys.stdout.buffer.write(b"\n")
        try:
            raw_evidence = result_path.read_bytes()
            evidence = json.loads(raw_evidence)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            fail("validation worker did not return canonical evidence")
        canonical = (json.dumps(evidence, sort_keys=True, separators=(",", ":")) + "\n").encode("ascii")
        if raw_evidence != canonical:
            fail("validation worker evidence is not canonical")
    finally:
        if process is not None and process.poll() is None:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait(timeout=10)
        try:
            observed_descendants.update(kill_and_reap_descendants())
        finally:
            if worker_descriptor >= 0:
                os.close(worker_descriptor)
            shutil.rmtree(temporary, ignore_errors=True)

    source_after = source_manifest(verifier, release, commit)
    venv_after = venv_manifest(venv, uid if uid != os.geteuid() else None)
    if source_after != source_before:
        fail("candidate source tree changed during validation")
    if venv_after != venv_before:
        fail("candidate venv changed during validation")

    evidence["descendants"] = len(observed_descendants)
    evidence["source_tree_sha256"] = json.loads(source_before)["source_tree_sha256"]
    evidence["venv_tree_sha256"] = venv_before
    evidence["worker_uid"] = uid
    success = (
        process is not None
        and process.returncode == 0
        and evidence.get("collected", 0) > 0
        and evidence.get("terminal") == evidence.get("collected")
        and evidence.get("failed") == 0
        and evidence.get("passed", 0) + evidence.get("skipped", 0)
        == evidence.get("terminal")
        and evidence["descendants"] == 0
    )
    evidence["result"] = "passed" if success else "failed"
    print(marker(evidence), flush=True)
    return 0 if success else 1


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    if len(sys.argv) == 3 and sys.argv[1] == "manifest-venv":
        return argparse.Namespace(
            operation="manifest-venv",
            release=sys.argv[2],
            commit=None,
            source_verifier=None,
            timeout=900,
        )
    parser.add_argument("release")
    parser.add_argument("commit")
    parser.add_argument("source_verifier")
    parser.add_argument("--timeout", type=int, default=900)
    arguments = parser.parse_args()
    if not 1 <= arguments.timeout <= 3600:
        parser.error("--timeout must be between 1 and 3600 seconds")
    arguments.operation = "run"
    return arguments


def main() -> None:
    arguments = parse_arguments()
    release = canonical_directory(arguments.release, "candidate release")
    if arguments.operation == "manifest-venv":
        venv = canonical_directory(str(release / ".venv"), "candidate venv")
        _gid, uid = worker_identity(release, venv)
        print(venv_manifest(venv, uid if uid != os.geteuid() else None))
        return
    if len(arguments.commit) != 40 or any(
        character not in "0123456789abcdef" for character in arguments.commit
    ):
        fail("candidate commit must be one full lowercase SHA")
    verifier = Path(arguments.source_verifier)
    raise SystemExit(
        run_validation(release, arguments.commit, verifier, arguments.timeout)
    )


if __name__ == "__main__":
    try:
        main()
    except ValidationError as exc:
        print(f"[validation-boundary:error] {exc}", file=sys.stderr)
        raise SystemExit(1)
