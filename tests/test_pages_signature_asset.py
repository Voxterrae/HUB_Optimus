from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ASSET = REPO_ROOT / "assets" / "huboptimus_signature_mark.png"
PAGES_ASSET = REPO_ROOT / "site" / "assets" / "huboptimus_signature_mark.png"
PAGES_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "pages.yml"


def test_signature_asset_is_packaged_byte_for_byte_for_pages() -> None:
    source = SOURCE_ASSET.read_bytes()
    deployed = PAGES_ASSET.read_bytes()

    assert source.startswith(b"\x89PNG\r\n\x1a\n")
    assert deployed == source


def test_pages_workflow_uploads_the_site_directory() -> None:
    workflow = PAGES_WORKFLOW.read_text(encoding="utf-8")

    assert '      - "site/**"' in workflow
    assert "          path: site" in workflow
