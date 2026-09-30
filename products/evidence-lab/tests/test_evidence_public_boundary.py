from __future__ import annotations

from pathlib import Path
import re
import unittest

ROOT = Path(__file__).parents[1]

EMAIL_PATTERN = re.compile(
    r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}",
    re.IGNORECASE,
)
DATAVERSE_HOST_PATTERN = re.compile(
    r"https?://[a-z0-9-]+\.crm[0-9]+\.dynamics\.com",
    re.IGNORECASE,
)
GUID_PATTERN = re.compile(
    r"\b[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}\b",
    re.IGNORECASE,
)

SYNTHETIC_GUIDS = {
    f"00000000-0000-4000-8000-{value:012d}"
    for value in range(0, 400)
}
ALLOWED_PUBLIC_HOSTS = {"example.crm4.dynamics.com"}


class PublicBoundaryTests(unittest.TestCase):
    def test_package_contains_no_private_tenant_identifiers(self):
        for path in ROOT.rglob("*"):
            if (
                not path.is_file()
                or path.name == "PACKAGE_MANIFEST.json"
                or "__pycache__" in path.parts
                or path.suffix == ".pyc"
            ):
                continue

            text = path.read_text(encoding="utf-8")
            emails = set(EMAIL_PATTERN.findall(text))
            self.assertTrue(
                emails <= {"GlobalOptionSet@odata.bind"},
                path.relative_to(ROOT),
            )
            hosts = {
                match.split("//", 1)[1].lower()
                for match in DATAVERSE_HOST_PATTERN.findall(text)
            }
            self.assertTrue(hosts <= ALLOWED_PUBLIC_HOSTS, path.relative_to(ROOT))
            guids = {value.lower() for value in GUID_PATTERN.findall(text)}
            self.assertTrue(guids <= SYNTHETIC_GUIDS, path.relative_to(ROOT))


if __name__ == "__main__":
    unittest.main()
