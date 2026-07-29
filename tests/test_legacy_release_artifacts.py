import hashlib
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LEGACY_DIR = ROOT / "legacy" / "v0_exploratory"
ARCHIVE = LEGACY_DIR / "HUB_Optimus_GitHub_Release_2025-12-12_LEGACY.zip"
NOTICE = LEGACY_DIR / "HISTORICAL_RELEASE_2025-12-12.md"
ARCHIVE_SHA256 = "ef4d9931449a2b4c46382c7b3b835802ca2e08abe431f3d83eb2bd09a2441b7e"


def test_historical_release_is_not_presented_at_repository_root():
    assert not (ROOT / "HUB_Optimus_GitHub_Release.zip").exists()
    assert ARCHIVE.is_file()


def test_historical_release_bytes_and_inventory_are_preserved():
    assert hashlib.sha256(ARCHIVE.read_bytes()).hexdigest() == ARCHIVE_SHA256

    with zipfile.ZipFile(ARCHIVE) as package:
        assert package.testzip() is None
        assert set(package.namelist()) == {
            "README.md",
            "LICENSE",
            "docs/HUB_Optimus_EN.pdf",
            "docs/HUB_Optimus_ES.pdf",
        }
        assert package.read("docs/HUB_Optimus_EN.pdf") == package.read(
            "docs/HUB_Optimus_ES.pdf"
        )


def test_historical_notice_exposes_status_provenance_and_conflict():
    notice = NOTICE.read_text(encoding="utf-8")
    normalized_notice = " ".join(notice.split())

    assert "Historical / legacy / non-canonical." in notice
    assert ARCHIVE.name in notice
    assert ARCHIVE_SHA256 in notice
    assert "../../IP_NOTICE.md" in notice
    assert "does not rewrite the historical artifact" in normalized_notice
    assert (
        "must not be used to infer the current repository-wide licensing"
        in normalized_notice
    )
