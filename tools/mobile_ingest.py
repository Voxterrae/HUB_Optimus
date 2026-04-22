from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


OUTPUT_PATH = Path(__file__).resolve().parent.parent / "mobile_ingest.jsonl"
ERROR_EXIT_CODE = 1


def _read_claim(argv_claim: list[str]) -> str:
    if argv_claim:
        return " ".join(argv_claim).strip()
    if not sys.stdin.isatty():
        return sys.stdin.read().strip()
    return ""


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Append a raw mobile claim to mobile_ingest.jsonl."
    )
    parser.add_argument("claim", nargs="*", help="Claim text to ingest.")
    args = parser.parse_args()

    claim = _read_claim(args.claim)
    if not claim:
        print("[mobile_ingest:error] no input provided", file=sys.stderr)
        return ERROR_EXIT_CODE

    record = {
        "claim": claim,
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": "mobile_termux",
        "status": "raw",
    }

    try:
        with OUTPUT_PATH.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    except OSError as exc:
        print(f"[mobile_ingest:error] {exc}", file=sys.stderr)
        return ERROR_EXIT_CODE

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
