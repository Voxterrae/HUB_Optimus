"""Check one proposed product release before publishing it on GitHub.

Example: python tools/check_release_identity.py --version v3.1 --tag v3.1 \
    --title 'HUB_Optimus v3.1 — Kernel updates'

Pass the intended product version from the release decision. The first standalone
version identifier in the title names the release; later identifiers may describe
comparisons or dependencies. The command does not read tags or contact GitHub.
"""

import argparse
import re
import sys


VERSION = r"v[0-9]+(?:\.[0-9]+)+(?:-[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*)?(?:\+[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*)?"
TITLE_VERSION = re.compile(rf"(?<![\w./\\+-]){VERSION}(?![\w/\\+-]|\.[\w])")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", required=True, help="intended product version, e.g. v1.1")
    parser.add_argument("--tag", required=True, help="exact proposed GitHub release tag")
    parser.add_argument("--title", required=True, help="complete proposed GitHub release title")
    args = parser.parse_args()

    if not re.fullmatch(VERSION, args.version):
        parser.error("--version requires a product version such as v1.1 or v1.0.0-alpha")
    title_version = TITLE_VERSION.search(args.title)
    if args.tag != args.version or not title_version or title_version.group() != args.version:
        observed = title_version.group() if title_version else "(missing)"
        print(f"Release identity mismatch: intended={args.version}, tag={args.tag}, "
              f"title version={observed}", file=sys.stderr)
        return 1
    print(f"Release tag and title match {args.version}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
