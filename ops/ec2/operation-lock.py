#!/usr/bin/env python3
from __future__ import annotations

import errno
import fcntl
import os
import stat
import sys
from dataclasses import dataclass


LOCK_ENVIRONMENT = "HUB_OPTIMUS_OPERATION_LOCK_FD"
LOCK_NAME = "deploy.lock"
MINIMUM_LOCK_FD = 100
DIRECTORY_IDENTITY_FIELDS = (
    "st_dev",
    "st_ino",
    "st_mode",
    "st_nlink",
    "st_uid",
    "st_gid",
)
LOCK_IDENTITY_FIELDS = DIRECTORY_IDENTITY_FIELDS + (
    "st_size",
    "st_mtime_ns",
    "st_ctime_ns",
)


class OperationLockError(RuntimeError):
    pass


@dataclass(frozen=True)
class OpenDirectories:
    app_root_fd: int
    shared_fd: int
    app_root_stat: os.stat_result
    shared_stat: os.stat_result


def fail(message: str) -> None:
    raise OperationLockError(message)


def same_identity(
    left: os.stat_result,
    right: os.stat_result,
    fields: tuple[str, ...],
) -> bool:
    return all(getattr(left, field) == getattr(right, field) for field in fields)


def validate_directory(info: os.stat_result, label: str, euid: int) -> None:
    if not stat.S_ISDIR(info.st_mode):
        fail(f"{label} is not a directory")
    if info.st_uid != euid:
        fail(f"{label} is not owned by the effective user")
    if stat.S_IMODE(info.st_mode) & 0o022:
        fail(f"{label} is group- or world-writable")


def validate_lock(info: os.stat_result, euid: int) -> None:
    if not stat.S_ISREG(info.st_mode):
        fail("deploy.lock is not one regular file")
    if info.st_uid != euid:
        fail("deploy.lock is not owned by the effective user")
    if stat.S_IMODE(info.st_mode) != 0o600:
        fail("deploy.lock does not have mode 0600")
    if info.st_nlink != 1:
        fail("deploy.lock does not have exactly one link")


def directory_flags() -> int:
    required = ("O_DIRECTORY", "O_NOFOLLOW", "O_NONBLOCK")
    if any(not hasattr(os, name) for name in required):
        fail("required no-follow directory flags are unavailable")
    return (
        os.O_RDONLY
        | os.O_DIRECTORY
        | os.O_NOFOLLOW
        | os.O_NONBLOCK
        | os.O_CLOEXEC
    )


def lock_flags() -> int:
    if not hasattr(os, "O_NOFOLLOW") or not hasattr(os, "O_NONBLOCK"):
        fail("required no-follow lock flags are unavailable")
    return os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC


def require_canonical_app_root(app_root: str) -> None:
    if not os.path.isabs(app_root) or os.path.abspath(app_root) != app_root:
        fail("APP_ROOT must be one canonical absolute path")


def open_directories(app_root: str) -> OpenDirectories:
    require_canonical_app_root(app_root)
    flags = directory_flags()
    euid = os.geteuid()
    try:
        app_root_fd = os.open(app_root, flags)
    except OSError as exc:
        fail(f"cannot safely open APP_ROOT: {exc}")
    try:
        app_root_stat = os.fstat(app_root_fd)
        validate_directory(app_root_stat, "APP_ROOT", euid)
        visible_app_root = os.stat(app_root, follow_symlinks=False)
        if not same_identity(
            app_root_stat,
            visible_app_root,
            DIRECTORY_IDENTITY_FIELDS,
        ):
            fail("APP_ROOT changed while it was opened")
        try:
            shared_fd = os.open("shared", flags, dir_fd=app_root_fd)
        except OSError as exc:
            fail(f"cannot safely open APP_ROOT/shared: {exc}")
        try:
            shared_stat = os.fstat(shared_fd)
            validate_directory(shared_stat, "APP_ROOT/shared", euid)
            visible_shared = os.stat(
                "shared",
                dir_fd=app_root_fd,
                follow_symlinks=False,
            )
            if not same_identity(
                shared_stat,
                visible_shared,
                DIRECTORY_IDENTITY_FIELDS,
            ):
                fail("APP_ROOT/shared changed while it was opened")
        except BaseException:
            os.close(shared_fd)
            raise
    except BaseException:
        os.close(app_root_fd)
        raise
    return OpenDirectories(
        app_root_fd=app_root_fd,
        shared_fd=shared_fd,
        app_root_stat=app_root_stat,
        shared_stat=shared_stat,
    )


def close_directories(directories: OpenDirectories) -> None:
    os.close(directories.shared_fd)
    os.close(directories.app_root_fd)


def require_visible_directories(
    app_root: str,
    directories: OpenDirectories,
) -> None:
    visible_app_root = os.stat(app_root, follow_symlinks=False)
    visible_shared = os.stat(
        "shared",
        dir_fd=directories.app_root_fd,
        follow_symlinks=False,
    )
    if not same_identity(
        directories.app_root_stat,
        visible_app_root,
        DIRECTORY_IDENTITY_FIELDS,
    ):
        fail("APP_ROOT changed during operation-lock acquisition")
    if not same_identity(
        directories.shared_stat,
        visible_shared,
        DIRECTORY_IDENTITY_FIELDS,
    ):
        fail("APP_ROOT/shared changed during operation-lock acquisition")


def open_existing_lock(shared_fd: int) -> int:
    try:
        return os.open(LOCK_NAME, lock_flags(), dir_fd=shared_fd)
    except OSError as exc:
        fail(f"cannot safely open deploy.lock: {exc}")


def open_or_create_lock(shared_fd: int) -> int:
    flags = lock_flags()
    try:
        return os.open(LOCK_NAME, flags, dir_fd=shared_fd)
    except FileNotFoundError:
        pass
    except OSError as exc:
        fail(f"cannot safely open deploy.lock: {exc}")

    try:
        descriptor = os.open(
            LOCK_NAME,
            flags | os.O_CREAT | os.O_EXCL,
            0o600,
            dir_fd=shared_fd,
        )
    except FileExistsError:
        return open_existing_lock(shared_fd)
    except OSError as exc:
        fail(f"cannot safely create deploy.lock: {exc}")
    try:
        os.fchmod(descriptor, 0o600)
    except BaseException:
        os.close(descriptor)
        raise
    return descriptor


def visible_lock_stat(shared_fd: int) -> os.stat_result:
    try:
        return os.stat(
            LOCK_NAME,
            dir_fd=shared_fd,
            follow_symlinks=False,
        )
    except OSError as exc:
        fail(f"cannot safely stat deploy.lock: {exc}")


def require_visible_lock(
    descriptor_stat: os.stat_result,
    shared_fd: int,
) -> None:
    visible = visible_lock_stat(shared_fd)
    if not same_identity(descriptor_stat, visible, LOCK_IDENTITY_FIELDS):
        fail("deploy.lock path does not match the opened lock descriptor")


def acquire_flock(descriptor: int) -> None:
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        fail("another deploy, rollback, or adoption operation is active")
    except OSError as exc:
        if exc.errno in (errno.EACCES, errno.EAGAIN):
            fail("another deploy, rollback, or adoption operation is active")
        fail(f"cannot acquire deploy.lock: {exc}")


def acquire(app_root: str) -> int:
    directories = open_directories(app_root)
    descriptor = -1
    try:
        descriptor = open_or_create_lock(directories.shared_fd)
        opened = os.fstat(descriptor)
        validate_lock(opened, os.geteuid())
        require_visible_lock(opened, directories.shared_fd)
        acquire_flock(descriptor)
        locked = os.fstat(descriptor)
        validate_lock(locked, os.geteuid())
        require_visible_lock(locked, directories.shared_fd)
        require_visible_directories(app_root, directories)
        inherited = fcntl.fcntl(
            descriptor,
            fcntl.F_DUPFD_CLOEXEC,
            MINIMUM_LOCK_FD,
        )
        os.close(descriptor)
        descriptor = inherited
        os.set_inheritable(descriptor, True)
        return descriptor
    except BaseException:
        if descriptor >= 0:
            os.close(descriptor)
        raise
    finally:
        close_directories(directories)


def parse_inherited_descriptor(raw: str) -> int:
    if not raw.isascii() or not raw.isdecimal():
        fail("inherited operation-lock FD is invalid")
    descriptor = int(raw)
    if descriptor < MINIMUM_LOCK_FD:
        fail("inherited operation-lock FD is outside the reserved range")
    return descriptor


def verify(app_root: str, raw_descriptor: str) -> None:
    descriptor = parse_inherited_descriptor(raw_descriptor)
    try:
        inherited = os.fstat(descriptor)
    except OSError as exc:
        fail(f"inherited operation-lock FD is not open: {exc}")
    if not os.get_inheritable(descriptor):
        fail("inherited operation-lock FD is not inheritable")
    validate_lock(inherited, os.geteuid())

    directories = open_directories(app_root)
    visible_descriptor = -1
    try:
        visible_descriptor = open_existing_lock(directories.shared_fd)
        visible = os.fstat(visible_descriptor)
        validate_lock(visible, os.geteuid())
        require_visible_lock(visible, directories.shared_fd)
        if not same_identity(inherited, visible, LOCK_IDENTITY_FIELDS):
            fail("inherited operation-lock FD does not match APP_ROOT/shared/deploy.lock")
        try:
            fcntl.flock(
                visible_descriptor,
                fcntl.LOCK_EX | fcntl.LOCK_NB,
            )
        except BlockingIOError:
            pass
        except OSError as exc:
            if exc.errno not in (errno.EACCES, errno.EAGAIN):
                fail(f"cannot verify the retained deploy.lock: {exc}")
        else:
            fcntl.flock(visible_descriptor, fcntl.LOCK_UN)
            fail("inherited operation-lock FD does not retain the exclusive flock")
        try:
            # A separately opened descriptor blocking above proves only that
            # some open-file-description owns the flock. Re-locking the
            # inherited descriptor is a no-op only for the exact retained
            # open-file-description; an unlocked FD to the same inode still
            # conflicts and must not authenticate the re-exec.
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            fail("inherited operation-lock FD is not the exclusive lock owner")
        except OSError as exc:
            if exc.errno in (errno.EACCES, errno.EAGAIN):
                fail("inherited operation-lock FD is not the exclusive lock owner")
            fail(f"cannot confirm the inherited deploy.lock owner: {exc}")
        locked = os.fstat(descriptor)
        validate_lock(locked, os.geteuid())
        require_visible_lock(locked, directories.shared_fd)
        require_visible_directories(app_root, directories)
    finally:
        if visible_descriptor >= 0:
            os.close(visible_descriptor)
        close_directories(directories)


def execute(app_root: str, entrypoint: str, arguments: list[str]) -> None:
    if not os.path.isabs(entrypoint):
        fail("operation entrypoint must be an absolute path")
    descriptor = acquire(app_root)
    environment = os.environ.copy()
    environment[LOCK_ENVIRONMENT] = str(descriptor)
    try:
        os.execve(entrypoint, [entrypoint, *arguments], environment)
    except BaseException:
        os.close(descriptor)
        raise


def usage() -> None:
    fail(
        "Usage: operation-lock.py exec <app-root> <entrypoint> [args ...] | "
        "verify <app-root> <inherited-fd>"
    )


def main() -> None:
    if len(sys.argv) >= 4 and sys.argv[1] == "exec":
        execute(sys.argv[2], sys.argv[3], sys.argv[4:])
    elif len(sys.argv) == 4 and sys.argv[1] == "verify":
        verify(sys.argv[2], sys.argv[3])
    else:
        usage()


if __name__ == "__main__":
    try:
        main()
    except OperationLockError as exc:
        print(f"[operation-lock:error] {exc}", file=sys.stderr)
        raise SystemExit(1)
    except OSError as exc:
        print(f"[operation-lock:error] operating-system failure: {exc}", file=sys.stderr)
        raise SystemExit(1)
