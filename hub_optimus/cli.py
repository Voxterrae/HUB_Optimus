import argparse
import json
import sys
from pathlib import Path

from .evaluate import evaluate_scenario


def _has_critical_flags(payload: dict) -> bool:
    schema = payload.get("schema", {})
    if schema.get("critical_missing"):
        return True
    return any(str(flag).startswith("CRITICAL") for flag in payload.get("flags", []))


def main():
    p = argparse.ArgumentParser(prog="hub_optimus")
    sub = p.add_subparsers(dest="cmd", required=True)

    ev = sub.add_parser("evaluate", help="Evaluate a scenario markdown file")
    ev.add_argument("path", help="Path to scenario .md")
    ev.add_argument("--out", default="out", help="Output folder")
    ev.add_argument("--write", action="store_true", help="Write report to file")
    ev.add_argument(
        "--format",
        choices=["md", "json", "both"],
        default=None,
        help="Output format. Defaults to 'md' (or 'both' when --write is used).",
    )
    ev.add_argument(
        "--fail-on-critical",
        action="store_true",
        help="Return a non-zero exit code when critical flags are detected.",
    )

    args = p.parse_args()
    fmt = args.format or ("both" if args.write else "md")

    report_md, payload = evaluate_scenario(Path(args.path))
    payload_json = json.dumps(payload, ensure_ascii=False, indent=2)

    if fmt == "md":
        print(report_md)
    elif fmt == "json":
        print(payload_json)
    else:
        print(f"{report_md}\n\n--- JSON ---\n\n{payload_json}")

    if args.write:
        out_dir = Path(args.out)
        out_dir.mkdir(parents=True, exist_ok=True)

        base_name = Path(args.path).stem + "_report"

        if fmt in ("md", "both"):
            out_md = out_dir / f"{base_name}.md"
            out_md.write_text(report_md, encoding="utf-8")
            print(f"\n[written] {out_md}")

        if fmt in ("json", "both"):
            out_json = out_dir / f"{base_name}.json"
            out_json.write_text(payload_json, encoding="utf-8")
            print(f"[written] {out_json}")

    if args.fail_on_critical and _has_critical_flags(payload):
        print("[critical] Critical flags detected in evaluation output.", file=sys.stderr)
        raise SystemExit(2)


if __name__ == "__main__":
    main()
