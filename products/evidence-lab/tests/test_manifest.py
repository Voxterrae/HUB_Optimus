from __future__ import annotations
from pathlib import Path
import hashlib
import json
import unittest

ROOT = Path(__file__).parents[1]
MANIFEST = ROOT / "PACKAGE_MANIFEST.json"


class ManifestTests(unittest.TestCase):
    def test_manifest_matches_package(self):
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        actual = {}
        for path in sorted(ROOT.rglob("*")):
            if (
                not path.is_file()
                or path == MANIFEST
                or "__pycache__" in path.parts
                or path.suffix == ".pyc"
            ):
                continue
            actual[path.relative_to(ROOT).as_posix()] = {
                "bytes": path.stat().st_size,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
        expected = {
            item["path"]: {
                "bytes": item["bytes"],
                "sha256": item["sha256"],
            }
            for item in manifest["files"]
        }
        self.assertEqual(expected, actual)
        self.assertEqual(manifest["fileCount"], len(actual))


if __name__ == "__main__":
    unittest.main()
