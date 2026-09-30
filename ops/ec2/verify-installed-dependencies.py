#!/usr/bin/env python3
from __future__ import annotations

import fcntl
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
import ctypes
from dataclasses import dataclass
from importlib.metadata import distributions
from pathlib import Path


INDEX_URL = "https://pypi.org/simple"
LOCK_SPECS = (
    (
        "ops/ec2/requirements-runtime.lock",
        {
            "attrs",
            "jsonschema",
            "jsonschema-specifications",
            "referencing",
            "rpds-py",
            "typing-extensions",
        },
        False,
    ),
    (
        "ops/ec2/requirements-validation.lock",
        {"iniconfig", "packaging", "pluggy", "pygments", "pytest", "pyyaml"},
        True,
    ),
)
HASH_RE = re.compile(r"--hash=sha256:([0-9a-f]{64})")
PIN_RE = re.compile(
    r"([A-Za-z0-9][A-Za-z0-9._-]*)==([A-Za-z0-9][A-Za-z0-9.!+_-]*)"
)
IDENTITY_FIELDS = (
    "st_dev",
    "st_ino",
    "st_mode",
    "st_nlink",
    "st_size",
    "st_mtime_ns",
    "st_ctime_ns",
)


@dataclass(frozen=True)
class LockSnapshot:
    release: Path
    digest: str
    expected: dict[str, str]
    combined_requirements: bytes
    identities: dict[Path, os.stat_result]


def fail(message: str) -> None:
    print(f"[dependency-lock:error] {message}", file=sys.stderr)
    raise SystemExit(1)


def normalize_name(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def logical_entries(text: str) -> list[str]:
    entries: list[str] = []
    pending = ""
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.endswith("\\"):
            pending += line[:-1].rstrip() + " "
            continue
        entries.append((pending + line).strip())
        pending = ""
    if pending:
        fail("lock ends in an incomplete continuation")
    return entries


def read_regular(path: Path) -> tuple[bytes, os.stat_result]:
    flags = os.O_RDONLY | os.O_CLOEXEC
    if not hasattr(os, "O_NOFOLLOW"):
        fail("O_NOFOLLOW is unavailable")
    flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        fail(f"cannot open lock without following links: {path}: {exc}")
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
            fail(f"lock is not one regular single-link file: {path}")
        if stat.S_IMODE(before.st_mode) != 0o644:
            fail(f"lock has an unexpected mode: {path}")
        chunks: list[bytes] = []
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    if any(getattr(before, field) != getattr(after, field) for field in IDENTITY_FIELDS):
        fail(f"lock changed while it was read: {path}")
    visible = os.stat(path, follow_symlinks=False)
    if any(getattr(after, field) != getattr(visible, field) for field in IDENTITY_FIELDS):
        fail(f"lock path changed while it was read: {path}")
    return b"".join(chunks), after


def validate_lock(
    raw: bytes,
    path: Path,
    expected_names: set[str],
    include_runtime: bool,
) -> tuple[list[str], dict[str, str]]:
    if not raw or not raw.endswith(b"\n") or b"\r" in raw or b"\x00" in raw:
        fail(f"lock is not canonical LF text: {path}")
    try:
        text = raw.decode("ascii")
    except UnicodeDecodeError:
        fail(f"lock is not canonical ASCII: {path}")
    entries = logical_entries(text)
    include = "-r requirements-runtime.lock"
    if include_runtime:
        if entries.count(include) != 1:
            fail(f"validation lock must include the runtime lock exactly once: {path}")
        entries.remove(include)
    elif any(entry.startswith(("-r ", "--requirement ")) for entry in entries):
        fail(f"runtime lock must not include another requirements file: {path}")

    pins: dict[str, str] = {}
    for entry in entries:
        if entry.startswith("-"):
            fail(f"lock contains an unsupported option: {entry}")
        pin = PIN_RE.fullmatch(entry.split()[0])
        if pin is None:
            fail(f"dependency is not one exact version pin: {entry}")
        name = normalize_name(pin.group(1))
        if name in pins:
            fail(f"lock contains a duplicate dependency: {name}")
        pins[name] = pin.group(2)
        hashes = HASH_RE.findall(entry)
        remainder = HASH_RE.sub("", entry[len(pin.group(0)) :]).strip()
        if not hashes or remainder:
            fail(f"dependency does not contain only reviewed SHA-256 hashes: {name}")
        if len(hashes) != len(set(hashes)):
            fail(f"dependency contains a duplicate SHA-256 hash: {name}")
    if set(pins) != expected_names:
        missing = ",".join(sorted(expected_names - set(pins))) or "none"
        unexpected = ",".join(sorted(set(pins) - expected_names)) or "none"
        fail(f"lock dependency set differs; missing={missing}; unexpected={unexpected}")
    return entries, pins


def load_snapshot(release: Path) -> LockSnapshot:
    if not release.is_absolute() or str(release) != os.path.abspath(release):
        fail("release path must be one canonical absolute path")
    if release.is_symlink() or not release.is_dir():
        fail("release path is not one real directory")

    digest = hashlib.sha256()
    expected: dict[str, str] = {}
    combined_entries: list[str] = []
    identities: dict[Path, os.stat_result] = {}
    for relative, expected_names, include_runtime in LOCK_SPECS:
        path = release / relative
        raw, identity = read_regular(path)
        entries, pins = validate_lock(raw, path, expected_names, include_runtime)
        overlap = set(expected) & set(pins)
        if overlap:
            fail(f"dependency appears in more than one tier: {sorted(overlap)[0]}")
        expected.update(pins)
        combined_entries.extend(entries)
        identities[path] = identity
        relative_raw = relative.encode("ascii")
        digest.update(len(relative_raw).to_bytes(4, "big"))
        digest.update(relative_raw)
        digest.update(len(raw).to_bytes(8, "big"))
        digest.update(raw)
    combined = ("\n".join(combined_entries) + "\n").encode("ascii")
    return LockSnapshot(
        release=release,
        digest=digest.hexdigest(),
        expected=expected,
        combined_requirements=combined,
        identities=identities,
    )


def require_digest(snapshot: LockSnapshot, expected_digest: str) -> None:
    if not re.fullmatch(r"[0-9a-f]{64}", expected_digest):
        fail("expected dependency-lock digest is invalid")
    if snapshot.digest != expected_digest:
        fail("dependency locks differ from the reviewed input digest")


def require_unchanged_paths(snapshot: LockSnapshot) -> None:
    for path, original in snapshot.identities.items():
        try:
            visible = os.stat(path, follow_symlinks=False)
        except OSError as exc:
            fail(f"lock path changed after capture: {path}: {exc}")
        if any(
            getattr(original, field) != getattr(visible, field)
            for field in IDENTITY_FIELDS
        ):
            fail(f"lock path changed after capture: {path}")


def snapshot_token(snapshot: LockSnapshot) -> str:
    token = hashlib.sha256()
    token.update(snapshot.digest.encode("ascii"))
    for path in sorted(snapshot.identities, key=lambda item: str(item)):
        relative = str(path.relative_to(snapshot.release)).encode("ascii")
        identity = snapshot.identities[path]
        token.update(len(relative).to_bytes(4, "big"))
        token.update(relative)
        for field in IDENTITY_FIELDS:
            value = getattr(identity, field)
            token.update(value.to_bytes(16, "big", signed=False))
    return token.hexdigest()


def require_snapshot_token(snapshot: LockSnapshot, expected_token: str) -> None:
    if not re.fullmatch(r"[0-9a-f]{64}", expected_token):
        fail("expected dependency-lock snapshot token is invalid")
    if snapshot_token(snapshot) != expected_token:
        fail("dependency-lock paths changed since the sealed install snapshot")


def canonical_inventory(inventory: dict[str, str]) -> str:
    return json.dumps(
        [{"name": name, "version": inventory[name]} for name in sorted(inventory)],
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )


def installed_inventory() -> dict[str, str]:
    installed: dict[str, str] = {}
    for distribution in distributions():
        raw_name = distribution.metadata.get("Name")
        if not raw_name:
            fail("installed distribution has no package name")
        name = normalize_name(raw_name)
        if name in installed:
            fail(f"installed inventory contains a duplicate dependency: {name}")
        installed[name] = distribution.version
    return installed


def verify_python_identity(release: Path, system_python: Path) -> None:
    expected_python = release / ".venv" / "bin" / "python"
    if Path(sys.executable) != expected_python:
        fail("inventory is not running from the candidate virtual environment")
    try:
        if not os.path.samefile(sys._base_executable, system_python):
            fail("virtual environment was not created by the reviewed system Python")
    except OSError as exc:
        fail(f"could not attest the virtual-environment base interpreter: {exc}")


def verify_inventory(
    snapshot: LockSnapshot,
    system_python: Path,
) -> str:
    verify_python_identity(snapshot.release, system_python)
    installed = installed_inventory()
    if installed != snapshot.expected:
        missing = sorted(set(snapshot.expected) - set(installed))
        unexpected = sorted(set(installed) - set(snapshot.expected))
        wrong = sorted(
            name
            for name in set(snapshot.expected) & set(installed)
            if snapshot.expected[name] != installed[name]
        )
        fail(
            "installed dependency inventory differs; "
            f"missing={','.join(missing) or 'none'}; "
            f"unexpected={','.join(unexpected) or 'none'}; "
            f"wrong_version={','.join(wrong) or 'none'}"
        )
    require_unchanged_paths(snapshot)
    return canonical_inventory(installed)


def sealed_requirements(raw: bytes) -> int:
    mfd_cloexec = getattr(os, "MFD_CLOEXEC", 0x0001)
    mfd_allow_sealing = getattr(os, "MFD_ALLOW_SEALING", 0x0002)
    flags = mfd_cloexec | mfd_allow_sealing
    if hasattr(os, "memfd_create"):
        descriptor = os.memfd_create("hub-optimus-dependency-lock", flags)
    else:
        # Linux x86_64 syscall number; deploy-current attests that exact ABI.
        libc = ctypes.CDLL(None, use_errno=True)
        descriptor = libc.syscall(
            319,
            b"hub-optimus-dependency-lock",
            flags,
        )
        if descriptor < 0:
            error = ctypes.get_errno()
            fail(f"could not create dependency memfd: {os.strerror(error)}")
    f_add_seals = getattr(fcntl, "F_ADD_SEALS", 1033)
    f_get_seals = getattr(fcntl, "F_GET_SEALS", 1034)
    f_seal_seal = getattr(fcntl, "F_SEAL_SEAL", 0x0001)
    f_seal_shrink = getattr(fcntl, "F_SEAL_SHRINK", 0x0002)
    f_seal_grow = getattr(fcntl, "F_SEAL_GROW", 0x0004)
    f_seal_write = getattr(fcntl, "F_SEAL_WRITE", 0x0008)
    try:
        view = memoryview(raw)
        written = 0
        while written < len(view):
            written += os.write(descriptor, view[written:])
        os.lseek(descriptor, 0, os.SEEK_SET)
        os.fchmod(descriptor, 0o400)
        seals = (
            f_seal_grow
            | f_seal_seal
            | f_seal_shrink
            | f_seal_write
        )
        fcntl.fcntl(descriptor, f_add_seals, seals)
        if fcntl.fcntl(descriptor, f_get_seals) != seals:
            fail("dependency requirements memfd is not fully sealed")
    except BaseException:
        os.close(descriptor)
        raise
    return descriptor


def clean_environment(release: Path) -> dict[str, str]:
    return {
        "HOME": str(release),
        "LANG": "C.UTF-8",
        "PATH": "/usr/bin:/bin",
        "PIP_CONFIG_FILE": "/dev/null",
        "PIP_DISABLE_PIP_VERSION_CHECK": "1",
        "PIP_NO_CACHE_DIR": "1",
        "PIP_NO_INPUT": "1",
        "PYTHONNOUSERSITE": "1",
    }


def run_checked(
    command: list[str],
    *,
    release: Path,
    environment: dict[str, str],
    pass_fds=(),
) -> None:
    result = subprocess.run(
        command,
        cwd=release,
        env=environment,
        pass_fds=pass_fds,
        stdout=sys.stderr,
        check=False,
    )
    if result.returncode != 0:
        raise SystemExit(result.returncode)


def install(
    snapshot: LockSnapshot,
    system_python: Path,
    *,
    wheelhouse: Path | None = None,
) -> str:
    venv_python = snapshot.release / ".venv" / "bin" / "python"
    if not venv_python.is_file() or not os.access(venv_python, os.X_OK):
        fail("virtual-environment Python is not executable")
    environment = clean_environment(snapshot.release)
    location_arguments = ["--index-url", INDEX_URL]
    if wheelhouse is not None:
        if (
            not wheelhouse.is_absolute()
            or str(wheelhouse) != os.path.abspath(wheelhouse)
            or wheelhouse.is_symlink()
            or not wheelhouse.is_dir()
        ):
            fail("offline wheelhouse is not one canonical real directory")
        location_arguments = ["--no-index", "--find-links", str(wheelhouse)]
    descriptor = sealed_requirements(snapshot.combined_requirements)
    try:
        requirement_path = f"/proc/self/fd/{descriptor}"
        run_checked(
            [
                str(venv_python),
                "-I",
                "-m",
                "pip",
                "install",
                "--disable-pip-version-check",
                "--isolated",
                "--no-cache-dir",
                "--no-deps",
                "--no-input",
                "--only-binary=:all:",
                "--require-hashes",
                *location_arguments,
                "--requirement",
                requirement_path,
            ],
            release=snapshot.release,
            environment=environment,
            pass_fds=(descriptor,),
        )
    finally:
        os.close(descriptor)
    require_unchanged_paths(snapshot)
    run_checked(
        [str(venv_python), "-I", "-m", "pip", "check"],
        release=snapshot.release,
        environment=environment,
    )
    run_checked(
        [str(venv_python), "-I", "-m", "pip", "uninstall", "--yes", "pip"],
        release=snapshot.release,
        environment=environment,
    )
    verifier = Path(__file__).resolve()
    result = subprocess.run(
        [
            str(venv_python),
            "-I",
            str(verifier),
            "verify",
            str(snapshot.release),
            str(system_python),
            snapshot.digest,
            snapshot_token(snapshot),
        ],
        cwd=snapshot.release,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        sys.stderr.write(result.stderr)
        raise SystemExit(result.returncode)
    expected_output = canonical_inventory(snapshot.expected) + "\n"
    if result.stdout != expected_output:
        fail("dependency-inventory verifier returned unexpected evidence")
    require_unchanged_paths(snapshot)
    return snapshot_token(snapshot)


def usage() -> None:
    fail(
        "Usage: verify-installed-dependencies "
        "digest <release> | capture <release> <digest> | "
        "install <release> <system-python> <digest> | "
        "install-offline <release> <system-python> <digest> <wheelhouse> | "
        "verify <release> <system-python> <digest> <snapshot-token>"
    )


if len(sys.argv) < 3:
    usage()
operation = sys.argv[1]
release_path = Path(sys.argv[2])
snapshot = load_snapshot(release_path)
if operation == "digest" and len(sys.argv) == 3:
    print(snapshot.digest)
elif operation == "capture" and len(sys.argv) == 4:
    require_digest(snapshot, sys.argv[3])
    print(snapshot_token(snapshot))
elif operation == "install" and len(sys.argv) == 5:
    reviewed_python = Path(sys.argv[3])
    require_digest(snapshot, sys.argv[4])
    print(install(snapshot, reviewed_python))
elif operation == "install-offline" and len(sys.argv) == 6:
    reviewed_python = Path(sys.argv[3])
    require_digest(snapshot, sys.argv[4])
    print(
        install(
            snapshot,
            reviewed_python,
            wheelhouse=Path(sys.argv[5]),
        )
    )
elif operation == "verify" and len(sys.argv) == 6:
    reviewed_python = Path(sys.argv[3])
    require_digest(snapshot, sys.argv[4])
    require_snapshot_token(snapshot, sys.argv[5])
    print(verify_inventory(snapshot, reviewed_python))
else:
    usage()
