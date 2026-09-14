#!/usr/bin/env python3
"""Verify release source bytes directly against one immutable Git commit."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
from dataclasses import dataclass
from typing import Any


GIT = "/usr/bin/git"
ALLOWED_GENERATED = frozenset({b".venv", b".hub-deployment"})
GIT_MODE_PERMISSIONS = {b"100644": 0o644, b"100755": 0o755}
GIT_TREE_MODE = b"40000"
FULL_SHA_RE = re.compile(rb"[0-9a-f]{40}")
IDENTITY_FIELDS = (
    "st_dev",
    "st_ino",
    "st_mode",
    "st_nlink",
    "st_size",
    "st_mtime_ns",
    "st_ctime_ns",
)
READ_FLAGS = os.O_RDONLY | os.O_CLOEXEC | os.O_NONBLOCK
DIRECTORY_FLAGS = os.O_RDONLY | os.O_CLOEXEC | os.O_DIRECTORY
GIT_ENVIRONMENT = {
    "GIT_CONFIG_GLOBAL": "/dev/null",
    "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_NO_LAZY_FETCH": "1",
    "GIT_NO_REPLACE_OBJECTS": "1",
    "GIT_OPTIONAL_LOCKS": "0",
    "GIT_TERMINAL_PROMPT": "0",
    "HOME": "/nonexistent",
    "LANG": "C",
    "LC_ALL": "C",
    "PATH": "/usr/bin:/bin",
    "XDG_CONFIG_HOME": "/nonexistent",
}


@dataclass(frozen=True)
class ExpectedFile:
    git_mode: bytes
    object_id: bytes
    content: bytes


@dataclass(frozen=True)
class ActualFile:
    permissions: int
    content: bytes


@dataclass(frozen=True)
class WorktreeSnapshot:
    root_permissions: int
    directories: dict[bytes, int]
    files: dict[bytes, ActualFile]


def fail(message: str) -> None:
    print(f"[release-worktree:error] {message}", file=sys.stderr)
    raise SystemExit(1)


def display_path(path: bytes) -> str:
    return ascii(os.fsdecode(path))


def same_identity(left: os.stat_result, right: os.stat_result) -> bool:
    return all(
        getattr(left, field) == getattr(right, field)
        for field in IDENTITY_FIELDS
    )


def require_safe_directory(info: os.stat_result, label: str) -> None:
    if not stat.S_ISDIR(info.st_mode):
        fail(f"{label} is not one real directory")
    if stat.S_IMODE(info.st_mode) & 0o022:
        fail(f"{label} is group- or world-writable")


def open_directory_at(
    parent_descriptor: int,
    name: bytes,
    label: str,
) -> tuple[int, os.stat_result]:
    try:
        visible = os.stat(
            name,
            dir_fd=parent_descriptor,
            follow_symlinks=False,
        )
    except OSError as exc:
        fail(f"cannot inspect {label}: {exc.strerror or 'operating-system error'}")
    require_safe_directory(visible, label)
    try:
        descriptor = os.open(
            name,
            DIRECTORY_FLAGS | os.O_NOFOLLOW,
            dir_fd=parent_descriptor,
        )
    except OSError as exc:
        fail(
            f"cannot open {label} without following links: "
            f"{exc.strerror or 'operating-system error'}"
        )
    opened = os.fstat(descriptor)
    if not same_identity(visible, opened):
        os.close(descriptor)
        fail(f"{label} changed while it was opened")
    require_safe_directory(opened, label)
    return descriptor, opened


def require_visible_identity(
    parent_descriptor: int,
    name: bytes,
    original: os.stat_result,
    label: str,
) -> None:
    try:
        visible = os.stat(
            name,
            dir_fd=parent_descriptor,
            follow_symlinks=False,
        )
    except OSError as exc:
        fail(f"{label} changed during inspection: {exc.strerror or 'missing'}")
    if not same_identity(original, visible):
        fail(f"{label} changed during inspection")


def open_release(raw_release: str) -> tuple[bytes, int, os.stat_result]:
    release = os.fsencode(raw_release)
    if (
        not os.path.isabs(release)
        or os.path.abspath(release) != release
        or os.path.realpath(release) != release
        or b"\n" in release
        or b"\r" in release
    ):
        fail("release must be one canonical absolute physical path")
    try:
        visible = os.stat(release, follow_symlinks=False)
    except OSError as exc:
        fail(f"cannot inspect release directory: {exc.strerror or 'missing'}")
    require_safe_directory(visible, "release directory")
    try:
        descriptor = os.open(
            release,
            DIRECTORY_FLAGS | os.O_NOFOLLOW,
        )
    except OSError as exc:
        fail(
            "cannot open release directory without following links: "
            f"{exc.strerror or 'operating-system error'}"
        )
    opened = os.fstat(descriptor)
    if not same_identity(visible, opened):
        os.close(descriptor)
        fail("release directory changed while it was opened")
    require_safe_directory(opened, "release directory")
    return release, descriptor, opened


def git_command(
    root_descriptor: int,
    git_descriptor: int,
    arguments: list[str],
    label: str,
    *,
    input_bytes: bytes | None = None,
) -> bytes:
    command = [
        GIT,
        "--no-replace-objects",
        f"--git-dir=/proc/self/fd/{git_descriptor}",
        f"--work-tree=/proc/self/fd/{root_descriptor}",
        *arguments,
    ]
    try:
        completed = subprocess.run(
            command,
            cwd=f"/proc/self/fd/{root_descriptor}",
            input=input_bytes,
            stdin=subprocess.DEVNULL if input_bytes is None else None,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=GIT_ENVIRONMENT,
            pass_fds=(root_descriptor, git_descriptor),
            check=False,
        )
    except OSError as exc:
        fail(f"cannot execute reviewed Git for {label}: {exc.strerror or 'error'}")
    if completed.returncode != 0:
        fail(f"reviewed Git {label} failed")
    return completed.stdout


def resolve_commit(
    root_descriptor: int,
    git_descriptor: int,
    requested: str,
) -> bytes:
    requested_bytes = requested.encode("ascii", errors="strict")
    if requested_bytes != b"HEAD" and FULL_SHA_RE.fullmatch(requested_bytes) is None:
        fail("commit must be HEAD or one full lowercase SHA-1")
    resolved = git_command(
        root_descriptor,
        git_descriptor,
        ["rev-parse", "--verify", "--end-of-options", requested],
        "commit resolution",
    ).strip()
    if FULL_SHA_RE.fullmatch(resolved) is None:
        fail("reviewed Git did not resolve one full commit SHA")
    if requested_bytes != b"HEAD" and resolved != requested_bytes:
        fail("explicit commit does not identify that commit directly")
    return resolved


def validate_git_worktree(
    release: bytes,
    root_descriptor: int,
    git_descriptor: int,
) -> None:
    inside = git_command(
        root_descriptor,
        git_descriptor,
        ["rev-parse", "--is-inside-work-tree"],
        "worktree inspection",
    )
    if inside != b"true\n":
        fail("release is not one Git worktree")
    top_level = git_command(
        root_descriptor,
        git_descriptor,
        ["rev-parse", "--show-toplevel"],
        "worktree-root inspection",
    )
    if top_level != release + b"\n":
        fail("release is not the Git worktree root")


def path_is_reserved(path: bytes) -> bool:
    first = path.split(b"/", 1)[0]
    return first == b".git" or first in ALLOWED_GENERATED


def read_verified_git_object(
    root_descriptor: int,
    git_descriptor: int,
    object_id: bytes,
    expected_type: bytes,
) -> bytes:
    """Read one object, then independently authenticate its canonical Git OID."""

    if FULL_SHA_RE.fullmatch(object_id) is None:
        fail("reviewed commit references an invalid object identity")
    output = git_command(
        root_descriptor,
        git_descriptor,
        ["cat-file", "--batch"],
        f"{expected_type.decode('ascii')} object read",
        input_bytes=object_id + b"\n",
    )
    newline = output.find(b"\n")
    if newline < 0:
        fail("reviewed Git returned a truncated object header")
    header = output[:newline].split(b" ")
    if len(header) != 3 or header[0] != object_id or header[1] != expected_type:
        fail("reviewed Git returned a mismatched object header")
    size_bytes = header[2]
    if not size_bytes.isdigit():
        fail("reviewed Git returned an invalid object size")
    size = int(size_bytes)
    if str(size).encode("ascii") != size_bytes:
        fail("reviewed Git returned a non-canonical object size")
    start = newline + 1
    end = start + size
    if end + 1 != len(output) or output[end:] != b"\n":
        fail("reviewed Git returned truncated or trailing object bytes")
    payload = output[start:end]
    canonical = expected_type + b" " + size_bytes + b"\0" + payload
    actual_id = hashlib.sha1(canonical).hexdigest().encode("ascii")
    if actual_id != object_id:
        fail(
            "reviewed Git object bytes do not match their cryptographic identity"
        )
    return payload


def commit_tree_identity(commit_payload: bytes) -> bytes:
    """Extract exactly one canonical leading tree header from a commit object."""

    header_end = commit_payload.find(b"\n\n")
    if header_end < 0:
        fail("reviewed commit object has no canonical header terminator")
    header_lines = commit_payload[:header_end].split(b"\n")
    if not header_lines or not header_lines[0].startswith(b"tree "):
        fail("reviewed commit object has no leading tree identity")
    first = header_lines[0]
    if len(first) != 45 or FULL_SHA_RE.fullmatch(first[5:]) is None:
        fail("reviewed commit object has an invalid tree identity")
    if any(line.startswith(b"tree ") for line in header_lines[1:]):
        fail("reviewed commit object has duplicate tree identities")
    return first[5:]


@dataclass(frozen=True)
class TreeEntry:
    git_mode: bytes
    name: bytes
    object_id: bytes


def tree_entry_sort_key(entry: TreeEntry) -> bytes:
    suffix = b"/" if entry.git_mode == GIT_TREE_MODE else b"\0"
    return entry.name + suffix


def parse_binary_tree(tree_payload: bytes) -> list[TreeEntry]:
    """Parse Git's binary tree format without trusting porcelain output."""

    entries: list[TreeEntry] = []
    offset = 0
    prior_key: bytes | None = None
    while offset < len(tree_payload):
        mode_end = tree_payload.find(b" ", offset)
        if mode_end < 0:
            fail("reviewed tree object has a truncated mode")
        git_mode = tree_payload[offset:mode_end]
        name_end = tree_payload.find(b"\0", mode_end + 1)
        if name_end < 0:
            fail("reviewed tree object has a truncated path")
        name = tree_payload[mode_end + 1 : name_end]
        identity_end = name_end + 21
        if identity_end > len(tree_payload):
            fail("reviewed tree object has a truncated object identity")
        object_id = tree_payload[name_end + 1 : identity_end].hex().encode("ascii")
        offset = identity_end
        if (
            not name
            or name in {b".", b".."}
            or b"/" in name
            or b"\n" in name
            or b"\r" in name
        ):
            fail("reviewed commit contains an unsafe tree path")
        if git_mode not in {*GIT_MODE_PERMISSIONS, GIT_TREE_MODE}:
            fail(
                "reviewed commit contains a non-regular source entry at "
                f"{display_path(name)}"
            )
        entry = TreeEntry(git_mode, name, object_id)
        sort_key = tree_entry_sort_key(entry)
        if prior_key is not None and sort_key <= prior_key:
            fail("reviewed tree object entries are duplicate or non-canonical")
        prior_key = sort_key
        entries.append(entry)
    return entries


def load_expected_tree(
    root_descriptor: int,
    git_descriptor: int,
    commit: bytes,
) -> tuple[dict[bytes, ExpectedFile], set[bytes]]:
    commit_payload = read_verified_git_object(
        root_descriptor,
        git_descriptor,
        commit,
        b"commit",
    )
    root_tree = commit_tree_identity(commit_payload)
    files: dict[bytes, ExpectedFile] = {}
    directories: set[bytes] = set()
    active_trees: set[bytes] = set()

    def visit(tree_id: bytes, prefix: bytes) -> None:
        if tree_id in active_trees:
            fail("reviewed commit contains a recursive tree graph")
        active_trees.add(tree_id)
        try:
            payload = read_verified_git_object(
                root_descriptor,
                git_descriptor,
                tree_id,
                b"tree",
            )
            for entry in parse_binary_tree(payload):
                path = entry.name if not prefix else prefix + b"/" + entry.name
                if entry.git_mode == GIT_TREE_MODE:
                    if path in directories:
                        fail(
                            "reviewed commit contains duplicate directory "
                            f"{display_path(path)}"
                        )
                    directories.add(path)
                    visit(entry.object_id, path)
                    if path_is_reserved(path):
                        fail(
                            "reviewed commit tracks reserved local path "
                            f"{display_path(path)}"
                        )
                    continue
                if path_is_reserved(path):
                    fail(
                        "reviewed commit tracks reserved local path "
                        f"{display_path(path)}"
                    )
                if path in files:
                    fail(
                        "reviewed commit contains duplicate path "
                        f"{display_path(path)}"
                    )
                content = read_verified_git_object(
                    root_descriptor,
                    git_descriptor,
                    entry.object_id,
                    b"blob",
                )
                files[path] = ExpectedFile(
                    entry.git_mode,
                    entry.object_id,
                    content,
                )
        finally:
            active_trees.remove(tree_id)

    visit(root_tree, b"")
    return files, directories


def read_expected_file(
    parent_descriptor: int,
    name: bytes,
    path: bytes,
    expected: ExpectedFile,
) -> ActualFile:
    label = f"source file {display_path(path)}"
    try:
        visible = os.stat(
            name,
            dir_fd=parent_descriptor,
            follow_symlinks=False,
        )
    except OSError as exc:
        fail(f"cannot inspect {label}: {exc.strerror or 'missing'}")
    if not stat.S_ISREG(visible.st_mode):
        fail(f"{label} is not one regular file")
    if visible.st_nlink != 1:
        fail(f"{label} is not one single-link file")
    permissions = stat.S_IMODE(visible.st_mode)
    if permissions & 0o022:
        fail(f"{label} is group- or world-writable")
    expected_permissions = GIT_MODE_PERMISSIONS[expected.git_mode]
    if permissions != expected_permissions:
        fail(
            f"{label} mode differs from Git "
            f"({permissions:04o} != {expected_permissions:04o})"
        )
    try:
        descriptor = os.open(
            name,
            READ_FLAGS | os.O_NOFOLLOW,
            dir_fd=parent_descriptor,
        )
    except OSError as exc:
        fail(
            f"cannot open {label} without following links: "
            f"{exc.strerror or 'operating-system error'}"
        )
    try:
        opened = os.fstat(descriptor)
        if not same_identity(visible, opened):
            fail(f"{label} changed while it was opened")
        if not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1:
            fail(f"{label} is not one regular single-link file")
        chunks: list[bytes] = []
        total = 0
        expected_size = len(expected.content)
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
            if total > expected_size:
                break
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    if not same_identity(opened, after):
        fail(f"{label} changed while it was read")
    require_visible_identity(parent_descriptor, name, after, label)
    content = b"".join(chunks)
    if content != expected.content:
        fail(f"{label} bytes differ from the reviewed commit")
    return ActualFile(permissions, content)


def list_directory(descriptor: int, label: str) -> list[bytes]:
    try:
        return sorted(os.fsencode(name) for name in os.listdir(descriptor))
    except OSError as exc:
        fail(f"cannot list {label}: {exc.strerror or 'operating-system error'}")


def walk_source_directory(
    descriptor: int,
    relative: bytes,
    opened_identity: os.stat_result,
    expected_files: dict[bytes, ExpectedFile],
    expected_dirs: set[bytes],
    actual_files: dict[bytes, ActualFile],
    actual_dirs: dict[bytes, int],
) -> None:
    label = (
        "release directory"
        if not relative
        else f"source directory {display_path(relative)}"
    )
    initial_names = list_directory(descriptor, label)
    for name in initial_names:
        path = name if not relative else relative + b"/" + name
        try:
            visible = os.stat(
                name,
                dir_fd=descriptor,
                follow_symlinks=False,
            )
        except OSError as exc:
            fail(f"cannot inspect {display_path(path)}: {exc.strerror or 'missing'}")
        if stat.S_ISDIR(visible.st_mode):
            if path not in expected_dirs:
                fail(f"unexpected source directory {display_path(path)}")
            child, child_identity = open_directory_at(
                descriptor,
                name,
                f"source directory {display_path(path)}",
            )
            actual_dirs[path] = stat.S_IMODE(child_identity.st_mode)
            try:
                walk_source_directory(
                    child,
                    path,
                    child_identity,
                    expected_files,
                    expected_dirs,
                    actual_files,
                    actual_dirs,
                )
                require_visible_identity(
                    descriptor,
                    name,
                    child_identity,
                    f"source directory {display_path(path)}",
                )
            finally:
                os.close(child)
        elif stat.S_ISREG(visible.st_mode):
            expected = expected_files.get(path)
            if expected is None:
                fail(f"unexpected source file {display_path(path)}")
            actual_files[path] = read_expected_file(
                descriptor,
                name,
                path,
                expected,
            )
        else:
            fail(f"unexpected non-regular source entry {display_path(path)}")
    if list_directory(descriptor, label) != initial_names:
        fail(f"{label} entries changed during inspection")
    after = os.fstat(descriptor)
    if not same_identity(opened_identity, after):
        fail(f"{label} changed during inspection")


def snapshot_worktree(
    root_descriptor: int,
    root_identity: os.stat_result,
    git_descriptor: int,
    git_identity: os.stat_result,
    expected_files: dict[bytes, ExpectedFile],
    expected_dirs: set[bytes],
    allowed_generated: set[bytes],
) -> WorktreeSnapshot:
    actual_files: dict[bytes, ActualFile] = {}
    actual_dirs: dict[bytes, int] = {}
    generated: list[tuple[bytes, int, os.stat_result]] = []
    initial_names = list_directory(root_descriptor, "release directory")
    try:
        if b".git" not in initial_names:
            fail("release has no root .git directory")
        for name in initial_names:
            if name == b".git":
                require_visible_identity(
                    root_descriptor,
                    name,
                    git_identity,
                    "root .git directory",
                )
                continue
            if name in ALLOWED_GENERATED:
                if name not in allowed_generated:
                    fail(
                        "generated directory requires an explicit allowlist flag: "
                        f"{display_path(name)}"
                    )
                child, child_identity = open_directory_at(
                    root_descriptor,
                    name,
                    f"generated directory {display_path(name)}",
                )
                generated.append((name, child, child_identity))
                continue
            path = name
            try:
                visible = os.stat(
                    name,
                    dir_fd=root_descriptor,
                    follow_symlinks=False,
                )
            except OSError as exc:
                fail(
                    f"cannot inspect {display_path(path)}: "
                    f"{exc.strerror or 'missing'}"
                )
            if stat.S_ISDIR(visible.st_mode):
                if path not in expected_dirs:
                    fail(f"unexpected source directory {display_path(path)}")
                child, child_identity = open_directory_at(
                    root_descriptor,
                    name,
                    f"source directory {display_path(path)}",
                )
                actual_dirs[path] = stat.S_IMODE(child_identity.st_mode)
                try:
                    walk_source_directory(
                        child,
                        path,
                        child_identity,
                        expected_files,
                        expected_dirs,
                        actual_files,
                        actual_dirs,
                    )
                    require_visible_identity(
                        root_descriptor,
                        name,
                        child_identity,
                        f"source directory {display_path(path)}",
                    )
                finally:
                    os.close(child)
            elif stat.S_ISREG(visible.st_mode):
                expected = expected_files.get(path)
                if expected is None:
                    fail(f"unexpected source file {display_path(path)}")
                actual_files[path] = read_expected_file(
                    root_descriptor,
                    name,
                    path,
                    expected,
                )
            else:
                fail(f"unexpected non-regular source entry {display_path(path)}")

        missing_files = sorted(set(expected_files) - set(actual_files))
        if missing_files:
            fail(f"missing source file {display_path(missing_files[0])}")
        missing_dirs = sorted(expected_dirs - set(actual_dirs))
        if missing_dirs:
            fail(f"missing source directory {display_path(missing_dirs[0])}")
        for name, child, identity in generated:
            if not same_identity(identity, os.fstat(child)):
                fail(
                    f"generated directory {display_path(name)} "
                    "changed during inspection"
                )
            require_visible_identity(
                root_descriptor,
                name,
                identity,
                f"generated directory {display_path(name)}",
            )
        require_visible_identity(
            root_descriptor,
            b".git",
            git_identity,
            "root .git directory",
        )
        if list_directory(root_descriptor, "release directory") != initial_names:
            fail("release directory entries changed during inspection")
        if not same_identity(root_identity, os.fstat(root_descriptor)):
            fail("release directory changed during inspection")
    finally:
        for _, descriptor, _ in generated:
            os.close(descriptor)
    return WorktreeSnapshot(
        root_permissions=stat.S_IMODE(root_identity.st_mode),
        directories=actual_dirs,
        files=actual_files,
    )


def update_field(digest: Any, value: bytes) -> None:
    digest.update(len(value).to_bytes(8, "big"))
    digest.update(value)


def source_tree_digest(commit: bytes, snapshot: WorktreeSnapshot) -> str:
    digest = hashlib.sha256()
    digest.update(b"hub-optimus-release-source-tree-v1\0")
    update_field(digest, commit)
    digest.update(snapshot.root_permissions.to_bytes(4, "big"))
    for path in sorted(snapshot.directories):
        digest.update(b"D")
        update_field(digest, path)
        digest.update(snapshot.directories[path].to_bytes(4, "big"))
    for path in sorted(snapshot.files):
        actual = snapshot.files[path]
        digest.update(b"F")
        update_field(digest, path)
        digest.update(actual.permissions.to_bytes(4, "big"))
        update_field(digest, actual.content)
    return digest.hexdigest()


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify direct release source bytes against one Git commit",
    )
    parser.add_argument("release")
    parser.add_argument("commit")
    parser.add_argument(
        "--allow-generated",
        action="append",
        default=[],
        choices=sorted(os.fsdecode(path) for path in ALLOWED_GENERATED),
        metavar="DIRECTORY",
    )
    return parser.parse_args()


def main() -> None:
    if not hasattr(os, "O_NOFOLLOW") or not os.path.isdir("/proc/self/fd"):
        fail("Linux no-follow descriptor traversal is unavailable")
    arguments = parse_arguments()
    allowed_list = [os.fsencode(item) for item in arguments.allow_generated]
    if len(allowed_list) != len(set(allowed_list)):
        fail("generated-directory allowlist contains a duplicate")
    release, root_descriptor, root_identity = open_release(arguments.release)
    git_descriptor = -1
    try:
        git_descriptor, git_identity = open_directory_at(
            root_descriptor,
            b".git",
            "root .git directory",
        )
        validate_git_worktree(
            release,
            root_descriptor,
            git_descriptor,
        )
        commit = resolve_commit(
            root_descriptor,
            git_descriptor,
            arguments.commit,
        )
        expected, expected_dirs = load_expected_tree(
            root_descriptor,
            git_descriptor,
            commit,
        )
        snapshot = snapshot_worktree(
            root_descriptor,
            root_identity,
            git_descriptor,
            git_identity,
            expected,
            expected_dirs,
            set(allowed_list),
        )
        try:
            visible_root = os.stat(release, follow_symlinks=False)
        except OSError as exc:
            fail(
                "release path changed during inspection: "
                f"{exc.strerror or 'missing'}"
            )
        if not same_identity(root_identity, visible_root):
            fail("release path changed during inspection")
        result = {
            "commit": commit.decode("ascii"),
            "source_file_count": len(expected),
            "source_tree_sha256": source_tree_digest(commit, snapshot),
        }
        print(
            json.dumps(
                result,
                ensure_ascii=True,
                separators=(",", ":"),
                sort_keys=True,
            )
        )
    finally:
        if git_descriptor >= 0:
            os.close(git_descriptor)
        os.close(root_descriptor)


if __name__ == "__main__":
    try:
        main()
    except UnicodeEncodeError:
        fail("commit must be HEAD or one full lowercase SHA-1")
    except OSError as exc:
        fail(f"worktree inspection failed: {exc.strerror or 'operating-system error'}")
