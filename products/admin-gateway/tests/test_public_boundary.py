from pathlib import Path


def test_public_overlay_example_contains_only_synthetic_values() -> None:
    content = (Path(__file__).parents[1] / "deployment" / "sharepoint" / "client-overlay.example.json").read_text(encoding="utf-8").lower()
    assert "lacasa-dashaus" not in content
    assert "t.hoff" not in content
    assert "bgh@" not in content
    assert "owner@example.com" in content


def test_custom_connector_contains_placeholders_not_secrets() -> None:
    content = (Path(__file__).parents[1] / "power-platform" / "custom-connector" / "apiProperties.template.json").read_text(encoding="utf-8")
    assert "REPLACE_WITH_CLIENT_ID" in content
    assert "REPLACE_IN_CONNECTION_ONLY" in content
