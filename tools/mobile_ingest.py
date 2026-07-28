from __future__ import annotations

import argparse
import json
import os
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


def _append_record(
    output_path: Path,
    record: dict[str, object],
    *,
    protect_default_directory: bool,
) -> None:
    if protect_default_directory:
        resolved_parent = output_path.parent.resolve(strict=False)
        if not resolved_parent.is_relative_to(REPO_ROOT.resolve()):
            raise OSError("default private intake directory resolves outside the repository")

    output_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)

    if protect_default_directory:
        resolved_parent = output_path.parent.resolve()
        if not resolved_parent.is_relative_to(REPO_ROOT.resolve()):
            raise OSError("default private intake directory resolves outside the repository")
        if os.name == "posix":
            os.chmod(output_path.parent, 0o700)

    flags = os.O_APPEND | os.O_CREAT | os.O_WRONLY
    flags |= getattr(os, "O_CLOEXEC", 0)
    flags |= getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(output_path, flags, 0o600)
    try:
        if os.name == "posix":
            os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "a", encoding="utf-8", newline="\n") as handle:
            descriptor = -1
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Append an unverified raw mobile claim to a private local JSONL file."
        )
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
    args = parser.parse_args(argv)

    print(SENSITIVE_CONTENT_WARNING, file=sys.stderr)
    claim, input_method = _read_claim(args.claim)
    if not claim:
        print("[mobile_ingest:error] no input provided", file=sys.stderr)
        return ERROR_EXIT_CODE

    output_path = (
        args.output.expanduser() if args.output is not None else DEFAULT_OUTPUT_PATH
    )
    if args.output is not None:
        print(
            "[mobile_ingest:warning] --output paths are operator-managed and may "
            "not be covered by repository ignore rules.",
            file=sys.stderr,
        )

    try:
        _append_record(
            output_path,
            _build_record(claim, input_method),
            protect_default_directory=args.output is None,
        )
    except OSError as exc:
        print(f"[mobile_ingest:error] {exc}", file=sys.stderr)
        return ERROR_EXIT_CODE

    print(f"[mobile_ingest:ok] stored local raw intake at {output_path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
