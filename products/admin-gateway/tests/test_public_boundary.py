import json
import re
import subprocess
from pathlib import Path
from urllib.parse import urlsplit

from jsonschema import Draft202012Validator, FormatChecker


PACKAGE_ROOT = Path(__file__).parents[1]
REPO_ROOT = PACKAGE_ROOT.parents[1]
SYNTHETIC_EMAILS = {"approver@example.com", "owner@example.com", "pilot@example.com"}
SYNTHETIC_GUIDS = {
    "11111111-1111-4111-8111-111111111111",
    "22222222-2222-4222-8222-222222222222",
    "33333333-3333-4333-8333-333333333333",
    "44444444-4444-4444-8444-444444444444",
}
ALLOWED_PUBLIC_HOSTS = {
    "example.com",
    "example.crm4.dynamics.com",
    "huboptimus.example",
    "json-schema.org",
    "login.microsoftonline.com",
    "schemas.microsoft.com",
    "schemas.xmlsoap.org",
    "www.w3.org",
}


def test_public_overlay_example_contains_only_synthetic_values() -> None:
    content = (PACKAGE_ROOT / "deployment" / "sharepoint" / "client-overlay.example.json").read_text(encoding="utf-8").lower()
    assert "lacasa-dashaus" not in content
    assert "t.hoff" not in content
    assert "bgh@" not in content
    assert "owner@example.com" in content


def test_custom_connector_contains_placeholders_not_secrets() -> None:
    content = (PACKAGE_ROOT / "power-platform" / "custom-connector" / "apiProperties.template.json").read_text(encoding="utf-8")
    assert "REPLACE_WITH_CLIENT_ID" in content
    assert "REPLACE_IN_CONNECTION_ONLY" in content
    assert "REPLACE_WITH_TENANT_ID" in content


def test_custom_connector_is_tenant_bound_and_role_aware() -> None:
    connector = json.loads(
        (PACKAGE_ROOT / "power-platform" / "custom-connector" / "apiDefinition.swagger.json").read_text(
            encoding="utf-8"
        )
    )
    oauth = connector["securityDefinitions"]["oauth2"]
    assert "/common/" not in oauth["authorizationUrl"].lower()
    assert "/common/" not in oauth["tokenUrl"].lower()
    assert "REPLACE_WITH_TENANT_ID" in oauth["authorizationUrl"]
    assert "REPLACE_WITH_TENANT_ID" in oauth["tokenUrl"]

    paths = connector["paths"]
    assert paths["/operations"]["get"]["responses"]["403"]["description"] == "Optimus.Reader role required"
    execute_forbidden = paths["/operations/{operation_id}:execute"]["post"]["responses"]["403"]["description"]
    assert execute_forbidden == (
        "Optimus.Reader is required; live mutations additionally require "
        "Optimus.Mutator and a valid approval"
    )


def test_overlay_and_azure_templates_require_fail_closed_identity_binding() -> None:
    schema = json.loads(
        (PACKAGE_ROOT / "deployment" / "sharepoint" / "tenant-overlay.schema.json").read_text(encoding="utf-8")
    )
    example = json.loads(
        (PACKAGE_ROOT / "deployment" / "sharepoint" / "client-overlay.example.json").read_text(encoding="utf-8")
    )
    azure = json.loads(
        (PACKAGE_ROOT / "deployment" / "azure" / "parameters.template.json").read_text(encoding="utf-8")
    )

    required = set(schema["properties"]["identity"]["required"])
    assert {"entraTenantId", "allowedTokenAudiences", "readerRole", "mutatorRole"} <= required
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(example)
    assert example["identity"]["readerRole"] == "Optimus.Reader"
    assert example["identity"]["mutatorRole"] == "Optimus.Mutator"
    assert azure["requireAuthentication"] is True
    assert azure["unauthenticatedClientAction"] == "Return401"
    assert "REPLACE_WITH_TENANT_ID" in azure["easyAuthIssuer"]
    assert azure["excludedPaths"] == ["/healthz"]
    assert azure["applicationSettings"] == {
        "OPTIMUS_ENTRA_TENANT_ID": "REPLACE_WITH_TENANT_ID",
        "OPTIMUS_READER_ROLE": "Optimus.Reader",
        "OPTIMUS_MUTATOR_ROLE": "Optimus.Mutator",
    }


def test_public_package_uses_only_allowlisted_synthetic_identifiers() -> None:
    tracked = subprocess.run(
        ["git", "ls-files", "--", "products/admin-gateway/**"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    email_pattern = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.IGNORECASE)
    guid_pattern = re.compile(r"\b[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}\b", re.IGNORECASE)
    url_pattern = re.compile(r"https?://[^\s\"'<>`)]+", re.IGNORECASE)

    for repo_path in tracked:
        content = (REPO_ROOT / repo_path).read_text(encoding="utf-8")
        assert set(email_pattern.findall(content)) <= SYNTHETIC_EMAILS, repo_path
        assert {value.lower() for value in guid_pattern.findall(content)} <= SYNTHETIC_GUIDS, repo_path
        for url in url_pattern.findall(content):
            assert (urlsplit(url).hostname or "").lower() in ALLOWED_PUBLIC_HOSTS, (repo_path, url)
