from __future__ import annotations

import hashlib
import json
import subprocess
import tomllib
from pathlib import Path


PACKAGE_ROOT = Path(__file__).parents[1]
REPO_ROOT = PACKAGE_ROOT.parents[1]
MANIFEST_PATH = PACKAGE_ROOT / "PACKAGE_MANIFEST.json"
WORKFLOW_PATH = ".github/workflows/optimus-admin-gateway.yml"


def _tracked_package_paths() -> dict[str, str]:
    result = subprocess.run(
        ["git", "ls-files", "--", "products/admin-gateway", WORKFLOW_PATH],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    paths: dict[str, str] = {}
    prefix = "products/admin-gateway/"
    for repo_path in result.stdout.splitlines():
        if repo_path == f"{prefix}PACKAGE_MANIFEST.json":
            continue
        manifest_path = repo_path.removeprefix(prefix) if repo_path.startswith(prefix) else repo_path
        paths[manifest_path] = repo_path
    return paths


def test_package_manifest_covers_every_tracked_asset_with_current_hashes() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    entries = manifest["files"]
    entry_paths = [entry["path"] for entry in entries]
    project = tomllib.loads((PACKAGE_ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]

    assert manifest["package"] == project["name"]
    assert manifest["version"] == project["version"]
    assert manifest["fileCount"] == len(entries)
    assert len(entry_paths) == len(set(entry_paths))
    tracked = _tracked_package_paths()
    assert set(entry_paths) == set(tracked)
    assert WORKFLOW_PATH in tracked
    assert {"README.md", "pyproject.toml", "scripts/build-package-manifest.py"} <= set(tracked)
    assert any(path.startswith("src/") for path in tracked)
    assert any(path.startswith("tests/") for path in tracked)

    for entry in entries:
        relative = Path(entry["path"])
        assert not relative.is_absolute()
        assert ".." not in relative.parts
        asset = REPO_ROOT / tracked[entry["path"]]
        assert asset.is_file()
        data = subprocess.run(
            ["git", "show", f":{tracked[entry['path']]}"],
            cwd=REPO_ROOT,
            check=True,
            capture_output=True,
        ).stdout
        assert entry["size"] == len(data)
        assert entry["sha256"] == hashlib.sha256(data).hexdigest()
