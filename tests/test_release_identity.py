import subprocess
import sys
import unittest
from pathlib import Path


CHECK = Path(__file__).resolve().parents[1] / "tools" / "check_release_identity.py"


class ReleaseIdentityTests(unittest.TestCase):
    def check_candidate(self, version, tag, title):
        return subprocess.run(
            [sys.executable, str(CHECK), "--version", version, "--tag", tag, "--title", title],
            capture_output=True, text=True, check=False,
        )

    def test_matching_product_titles(self):
        for version, title in (
            ("v1.1", "Multilingual profiles (v1.1)"),
            ("v1.0.0-alpha", "HUB_Optimus v1.0.0-alpha — Kernel"),
            ("v2.0.0-rc.1+build.4", "v2.0.0-rc.1+build.4 with SDK v10.0"),
        ):
            with self.subTest(title=title):
                result = self.check_candidate(version, version, title)
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_drift_or_missing_identity_is_rejected(self):
        for version, tag, title in (
            ("v1.0.0-alpha", "v2.3.4", "HUB_Optimus v1.0.0-alpha — Kernel"),
            ("v2.3.4", "v2.3.4", "HUB_Optimus v1.0.0-alpha — Kernel"),
            ("v2.3.4", "v2.3.4", "v1.0.0-alpha (compare v2.3.4)"),
            ("v2.3.4", "v2.3.4", "v2.3.40"),
            ("v2.3.4", "v2.3.4", "v2.3.4-rc.1"),
            ("v2.3.4", "v2.3.4", "Milestone complete"),
        ):
            with self.subTest(tag=tag, title=title):
                result = self.check_candidate(version, tag, title)
                self.assertEqual(result.returncode, 1, result.stderr)
