from __future__ import annotations

import argparse
import json
import os
import stat
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DATA_DIR = REPO_ROOT / ".local" / "intake"
DEFAULT_OUTPUT_PATH = DEFAULT_DATA_DIR / "mobile_ingest.jsonl"
SCHEMA_VERSION = 1
ERROR_EXIT_CODE = 1
SENSITIVE_CONTENT_WARNING = (
    "[mobile_ingest:warning] Raw intake is unverified, local-only material. "
    "Do not enter credentials or secrets; use an approved private process for "
    "regulated, client-confidential, or otherwise sensitive data."
)


def _read_claim(argv_claim: list[str]) -> tuple[str, str]:
    if argv_claim:
        return " ".join(argv_claim).strip(), "argv"
    if not sys.stdin.isatty():
        return sys.stdin.read().strip(), "stdin"
    return "", "none"


def _build_record(claim: str, input_method: str) -> dict[str, object]:
    return {
        "schema_version": SCHEMA_VERSION,
        "intake_id": f"mobile-{uuid.uuid4()}",
        "captured_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": {
            "channel": "mobile_termux",
            "input_method": input_method,
            "tool": "tools/mobile_ingest.py",
        },
        "classification": "private_raw_intake",
        "verification_status": "unverified",
        "publication_status": "local_only",
        "claim": claim,
    }


def _supports_secure_default_writer() -> bool:
    supports_dir_fd = getattr(os, "supports_dir_fd", set())
    return all(
        (
            os.name == "posix",
            os.open in supports_dir_fd,
            os.mkdir in supports_dir_fd,
            hasattr(os, "O_DIRECTORY"),
            hasattr(os, "O_NOFOLLOW"),
            hasattr(os, "fchmod"),
        )
    )


def _directory_open_flags() -> int:
    return (
        os.O_RDONLY
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_DIRECTORY", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )


def _protected_relative_parts(output_path: Path) -> tuple[tuple[str, ...], str]:
    repo_root = Path(os.path.abspath(REPO_ROOT))
    candidate = output_path if output_path.is_absolute() else repo_root / output_path
    absolute_output = Path(os.path.abspath(candidate))
    try:
        relative_output = absolute_output.relative_to(repo_root)
    except ValueError as exc:
        raise OSError(
            "default private intake path must remain inside the repository"
        ) from exc

    parts = relative_output.parts
    if len(parts) < 2 or any(part in {"", ".", ".."} for part in parts):
        raise OSError("default private intake path is not a safe repository path")
    return tuple(parts[:-1]), parts[-1]


def _open_protected_parent(output_path: Path) -> tuple[int, str]:
    if not _supports_secure_default_writer():
        raise OSError(
            "secure default intake requires POSIX no-follow directory descriptors; "
            "this platform must use an explicit operator-managed --output path"
        )

    parent_parts, file_name = _protected_relative_parts(output_path)
    current_descriptor = os.open(REPO_ROOT, _directory_open_flags())
    try:
        for part in parent_parts:
            try:
                os.mkdir(part, mode=0o700, dir_fd=current_descriptor)
            except FileExistsError:
                pass

            next_descriptor = os.open(
                part,
                _directory_open_flags(),
                dir_fd=current_descriptor,
            )
            if not stat.S_ISDIR(os.fstat(next_descriptor).st_mode):
                os.close(next_descriptor)
                raise OSError("default private intake path contains a non-directory")
            os.close(current_descriptor)
            current_descriptor = next_descriptor

        os.fchmod(current_descriptor, 0o700)
        return current_descriptor, file_name
    except BaseException:
        os.close(current_descriptor)
        raise


def _file_open_flags() -> int:
    return (
        os.O_APPEND
        | os.O_RDWR
        | getattr(os, "O_BINARY", 0)
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOINHERIT", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )


def _open_output_descriptor(
    target: str | Path,
    *,
    directory_descriptor: int | None,
    force_private_permissions: bool,
) -> int:
    flags = _file_open_flags()
    open_kwargs = (
        {"dir_fd": directory_descriptor}
        if directory_descriptor is not None
        else {}
    )

    try:
        descriptor = os.open(
            target,
            flags | os.O_CREAT | os.O_EXCL,
            0o600,
            **open_kwargs,
        )
        created = True
    except FileExistsError:
        descriptor = os.open(target, flags, 0o600, **open_kwargs)
        created = False

    try:
        output_status = os.fstat(descriptor)
        if not stat.S_ISREG(output_status.st_mode):
            raise OSError("mobile intake output must be a regular file")
        if force_private_permissions and output_status.st_nlink != 1:
            raise OSError(
                "default private intake file must not be hard-linked"
            )
        if os.name == "posix" and (force_private_permissions or created):
            os.fchmod(descriptor, 0o600)
    except BaseException:
        os.close(descriptor)
        raise
    return descriptor


def _write_jsonl_record(descriptor: int, record: dict[str, object]) -> None:
    needs_separator = False
    if os.fstat(descriptor).st_size:
        os.lseek(descriptor, -1, os.SEEK_END)
        needs_separator = os.read(descriptor, 1) != b"\n"

    serialized = json.dumps(record, ensure_ascii=False).encode("utf-8") + b"\n"
    payload = (b"\n" if needs_separator else b"") + serialized
    remaining = memoryview(payload)
    while remaining:
        written = os.write(descriptor, remaining)
        if written <= 0:
            raise OSError("mobile intake append made no forward progress")
        remaining = remaining[written:]


def _append_record(
    output_path: Path,
    record: dict[str, object],
    *,
    protect_default_directory: bool,
) -> None:
    if protect_default_directory:
        parent_descriptor, file_name = _open_protected_parent(output_path)
        try:
            descriptor = _open_output_descriptor(
                file_name,
                directory_descriptor=parent_descriptor,
                force_private_permissions=True,
            )
        finally:
            os.close(parent_descriptor)
    else:
        output_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        descriptor = _open_output_descriptor(
            output_path,
            directory_descriptor=None,
            force_private_permissions=False,
        )

    try:
        _write_jsonl_record(descriptor, record)
    finally:
        os.close(descriptor)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Append an unverified raw mobile claim to a private local JSONL file."
        ),
        epilog=(
            "Option-like claim text is accepted. Use -- before a claim that is "
            "exactly --output, -h, or --help."
        ),
    )
    parser.add_argument("claim", nargs="*", help="Claim text to ingest.")
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help=(
            "Explicit operator-managed JSONL path. The default is "
            ".local/intake/mobile_ingest.jsonl and is git-ignored."
        ),
    )
    return parser


def _parse_arguments(
    argv: list[str] | None,
) -> tuple[Path | None, list[str], bool]:
    tokens = list(sys.argv[1:] if argv is None else argv)
    output_path: Path | None = None
    claim: list[str] = []
    index = 0
    parse_options = True

    while index < len(tokens):
        token = tokens[index]
        if parse_options and token == "--":
            parse_options = False
            index += 1
            continue
        if parse_options and token in {"-h", "--help"}:
            return None, [], True
        if parse_options and token == "--output":
            if output_path is not None:
                raise ValueError("--output may be specified only once")
            if index + 1 >= len(tokens):
                raise ValueError("--output requires a path")
            output_path = Path(tokens[index + 1])
            index += 2
            continue
        if parse_options and token.startswith("--output="):
            if output_path is not None:
                raise ValueError("--output may be specified only once")
            raw_path = token.partition("=")[2]
            if not raw_path:
                raise ValueError("--output requires a path")
            output_path = Path(raw_path)
            index += 1
            continue

        claim.append(token)
        index += 1

    return output_path, claim, False


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    try:
        explicit_output, argv_claim, help_requested = _parse_arguments(argv)
    except ValueError as exc:
        print(f"[mobile_ingest:error] {exc}", file=sys.stderr)
        return ERROR_EXIT_CODE
    if help_requested:
        parser.print_help()
        return 0

    print(SENSITIVE_CONTENT_WARNING, file=sys.stderr)
    claim, input_method = _read_claim(argv_claim)
    if not claim:
        print("[mobile_ingest:error] no input provided", file=sys.stderr)
        return ERROR_EXIT_CODE

    output_path = (
        explicit_output.expanduser()
        if explicit_output is not None
        else DEFAULT_OUTPUT_PATH
    )
    if explicit_output is not None:
        print(
            "[mobile_ingest:warning] --output paths are operator-managed and may "
            "not be covered by repository ignore rules.",
            file=sys.stderr,
        )

    try:
        _append_record(
            output_path,
            _build_record(claim, input_method),
            protect_default_directory=explicit_output is None,
        )
    except (OSError, RuntimeError) as exc:
        print(f"[mobile_ingest:error] {exc}", file=sys.stderr)
        return ERROR_EXIT_CODE

    print(
        f"[mobile_ingest:ok] stored local raw intake at {output_path}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
