from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import tomllib
from pathlib import Path


PACKAGE_ROOT = Path(__file__).parents[1]
REPO_ROOT = PACKAGE_ROOT.parents[1]
MANIFEST_PATH = PACKAGE_ROOT / "PACKAGE_MANIFEST.json"
WORKFLOW_PATH = ".github/workflows/optimus-admin-gateway.yml"


def _git_output(*args: str) -> bytes:
    return subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
    ).stdout


def tracked_assets() -> list[tuple[str, str]]:
    result = subprocess.run(
        ["git", "ls-files", "--", "products/admin-gateway/**", WORKFLOW_PATH],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    prefix = "products/admin-gateway/"
    assets: list[tuple[str, str]] = []
    for repo_path in result.stdout.splitlines():
        if repo_path == f"{prefix}PACKAGE_MANIFEST.json":
            continue
        if repo_path.startswith(prefix):
            manifest_path = repo_path.removeprefix(prefix)
        else:
            manifest_path = repo_path
        assets.append((manifest_path, repo_path))
    return sorted(assets)


def require_staged_source_changes() -> None:
    unstaged = _git_output(
        "diff",
        "--name-only",
        "--",
        "products/admin-gateway/**",
        WORKFLOW_PATH,
    ).decode("utf-8").splitlines()
    relevant = [path for path in unstaged if path != "products/admin-gateway/PACKAGE_MANIFEST.json"]
    if relevant:
        raise SystemExit("Stage package source changes before building the manifest: " + ", ".join(relevant))


def render_manifest() -> str:
    require_staged_source_changes()
    project = tomllib.loads((PACKAGE_ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    files = []
    for manifest_path, repo_path in tracked_assets():
        data = _git_output("show", f":{repo_path}")
        files.append(
            {
                "path": manifest_path,
                "sha256": hashlib.sha256(data).hexdigest(),
                "size": len(data),
            }
        )
    manifest = {
        "package": project["name"],
        "version": project["version"],
        "fileCount": len(files),
        "files": files,
    }
    return json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Build or verify the Admin Gateway package manifest.")
    parser.add_argument("--write", action="store_true", help="Replace the manifest with the deterministic output.")
    args = parser.parse_args()
    rendered = render_manifest()
    if args.write:
        MANIFEST_PATH.write_text(rendered, encoding="utf-8", newline="\n")
        return 0
    if not MANIFEST_PATH.exists() or MANIFEST_PATH.read_text(encoding="utf-8") != rendered:
        raise SystemExit("PACKAGE_MANIFEST.json is stale; run build-package-manifest.py --write")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
