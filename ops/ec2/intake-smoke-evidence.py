#!/usr/bin/env python3
"""Render only the reviewed allowlist from one localhost intake response."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import urlparse


FULL_COMMIT_RE = re.compile(r"[0-9a-f]{40}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("response", type=Path)
    parser.add_argument("http_status")
    parser.add_argument("curl_exit_code", type=int)
    parser.add_argument("target_commit")
    return parser.parse_args()


def controlled_string(payload: dict, key: str) -> str | None:
    value = payload.get(key)
    return value if isinstance(value, str) else None


def reject_non_standard_constant(value: str) -> None:
    raise ValueError(f"non-standard JSON constant: {value}")


def main() -> int:
    args = parse_args()
    if not FULL_COMMIT_RE.fullmatch(args.target_commit):
        raise SystemExit("target_commit must be one full lowercase commit SHA")
    if not re.fullmatch(r"[0-9]{3}", args.http_status):
        raise SystemExit("http_status must be a three-digit value")

    try:
        raw = args.response.read_text(encoding="utf-8")
        payload = json.loads(raw, parse_constant=reject_non_standard_constant)
    except (OSError, UnicodeError, ValueError) as exc:
        raise SystemExit("controlled intake returned unreadable JSON") from exc
    if not isinstance(payload, dict):
        raise SystemExit("controlled intake response must be a JSON object")

    text = payload.get("text", "")
    if not isinstance(text, str):
        raise SystemExit("controlled intake text field must be a string")

    final_url = controlled_string(payload, "final_url")
    final_domain = urlparse(final_url).hostname if final_url else None
    source_domain = controlled_string(payload, "source_domain")
    if final_domain is not None:
        final_domain = final_domain.lower()

    evidence = {
        "target_commit": args.target_commit,
        "curl_exit_code": args.curl_exit_code,
        "http_status": int(args.http_status),
        "response_status": controlled_string(payload, "status"),
        "error_code": controlled_string(payload, "error"),
        "source_domain": source_domain,
        "final_domain": final_domain,
        "final_url": final_url,
        "content_type": controlled_string(payload, "content_type"),
        "retrieved_at_utc": controlled_string(payload, "retrieved_at_utc"),
        "bytes_read": (
            payload.get("bytes_read")
            if isinstance(payload.get("bytes_read"), int)
            and not isinstance(payload.get("bytes_read"), bool)
            else None
        ),
        "truncated": (
            payload.get("truncated")
            if isinstance(payload.get("truncated"), bool)
            else None
        ),
        "verification_status": controlled_string(
            payload,
            "verification_status",
        ),
        "text_present": bool(text.strip()),
        "text_characters": len(text),
        "text_sha256": (
            hashlib.sha256(text.encode("utf-8")).hexdigest() if text else None
        ),
    }
    print(json.dumps(evidence, indent=2, sort_keys=True, ensure_ascii=False))

    if args.http_status != "200":
        raise SystemExit("controlled intake did not return required HTTP 200")
    if args.curl_exit_code != 0:
        raise SystemExit("controlled intake transport failed")
    if evidence["response_status"] != "ok":
        raise SystemExit("controlled intake returned an application failure")
    if evidence["verification_status"] != "unreviewed":
        raise SystemExit("verification boundary changed unexpectedly")
    if not evidence["text_present"]:
        raise SystemExit("controlled intake returned empty extracted text")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
