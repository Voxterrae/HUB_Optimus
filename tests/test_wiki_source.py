from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
WIKI = REPO_ROOT / "docs" / "wiki"


def test_reviewed_wiki_source_has_the_required_navigation_pages():
    expected = {
        "README.md",
        "Home.md",
        "Operator-User-Guide.md",
        "Operator-Troubleshooting.md",
        "Architecture.md",
        "Hosting-and-Deployment.md",
        "Roadmap-and-Live-Status.md",
        "_Sidebar.md",
        "_Footer.md",
    }
    assert {path.name for path in WIKI.glob("*.md")} == expected

    sidebar = (WIKI / "_Sidebar.md").read_text(encoding="utf-8")
    for page in expected - {"README.md", "_Sidebar.md", "_Footer.md"}:
        assert page.removesuffix(".md") in sidebar


def test_wiki_declares_its_audited_boundary_and_live_state_authorities():
    home = (WIKI / "Home.md").read_text(encoding="utf-8")
    roadmap = (WIKI / "Roadmap-and-Live-Status.md").read_text(encoding="utf-8")
    publishing = (WIKI / "README.md").read_text(encoding="utf-8")

    assert "4400b0d778dc64779f9db9bd4cdb398a7d46a69b" in home
    assert "main" in publishing
    assert "independent source of truth" in publishing
    assert "https://github.com/Voxterrae/HUB_Optimus/issues" in roadmap
    assert "https://github.com/Voxterrae/HUB_Optimus/pulls" in roadmap
    assert "https://github.com/Voxterrae/HUB_Optimus/actions" in roadmap


def test_wiki_contains_no_secret_material_or_live_secret_placeholders():
    text = "\n".join(
        path.read_text(encoding="utf-8") for path in sorted(WIKI.glob("*.md"))
    ).lower()
    forbidden = (
        "-----begin private key-----",
        "aws_access_key_id=",
        "aws_secret_access_key=",
        "client_secret=",
        "cookie_secret=",
        "hub_operator_intake_capability=",
    )
    for marker in forbidden:
        assert marker not in text
