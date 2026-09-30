import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "site" / "operator" / "index.html"
PUBLIC_SCHEMA = ROOT / "ops" / "ec2" / "operator_public_intake.v1.schema.json"
GATEWAY = ROOT / "ops" / "ec2" / "operator-intake-gateway.py"
NGINX = ROOT / "ops" / "ec2" / "nginx" / "operator-api.conf"
RUNBOOK = ROOT / "docs" / "maintenance" / "operator_oidc_owner_team.md"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _javascript_array(source: str, name: str) -> list[str]:
    match = re.search(
        rf"const {name} = Object\.freeze\((\[.*?\])\);",
        source,
        re.DOTALL,
    )
    assert match is not None
    return json.loads(match.group(1))


def _javascript_status_map(source: str, name: str) -> dict[str, int]:
    match = re.search(
        rf"const {name} = Object\.freeze\(\{{(.*?)\}}\);",
        source,
        re.DOTALL,
    )
    assert match is not None
    return {
        code: int(status)
        for code, status in re.findall(
            r'^\s+"([a-z][a-z0-9_]+)":\s+(\d+),?$',
            match.group(1),
            re.MULTILINE,
        )
    }


def test_browser_public_envelope_exactly_matches_versioned_schema():
    html = _read(INDEX)
    schema = json.loads(_read(PUBLIC_SCHEMA))
    success = schema["$defs"]["success_response"]["allOf"][1]
    error = schema["$defs"]["error_response"]["allOf"][1]

    assert f'const PUBLIC_INTAKE_SCHEMA_VERSION = "{schema["$defs"]["response_identity"]["properties"]["schema_version"]["const"]}";' in html
    assert set(_javascript_array(html, "PUBLIC_INTAKE_SUCCESS_FIELDS")) == set(
        success["required"]
    )
    assert set(_javascript_array(html, "PUBLIC_INTAKE_ERROR_FIELDS")) == set(
        error["required"]
    )
    assert set(_javascript_array(html, "PUBLIC_INTAKE_ERROR_DETAIL_FIELDS")) == set(
        schema["$defs"]["error"]["required"]
    )
    gateway_errors = _javascript_status_map(
        html, "PUBLIC_INTAKE_GATEWAY_ERROR_HTTP_STATUS"
    )
    assert gateway_errors == schema["x-hub-optimus-gateway-error-http-status"]
    edge_errors = _javascript_status_map(
        html, "PUBLIC_INTAKE_NGINX_ERROR_HTTP_STATUS"
    )
    assert edge_errors == schema["x-hub-optimus-edge-error-http-status"]
    edge_schema = schema["$defs"]["edge_error_response"]
    assert set(edge_schema["required"]) == {"error", "request_id"}
    assert set(edge_schema["properties"]["error"]["enum"]) == set(edge_errors)
    assert set(schema["$defs"]["error"]["properties"]["code"]["enum"]) == (
        set(schema["x-hub-optimus-gateway-error-http-status"])
        | set(schema["x-hub-optimus-upstream-error-http-status"])
    )


def test_public_operator_cannot_send_a_url_and_private_fetch_is_same_origin():
    html = _read(INDEX)
    controlled_contract = html[
        html.index("// OPERATOR_CONTROLLED_INTAKE_CONTRACT_START"):
        html.index("// OPERATOR_CONTROLLED_INTAKE_CONTRACT_END")
    ]

    assert 'const PRIVATE_OPERATOR_ORIGIN = "https://api.huboptimus.dev";' in html
    assert 'const CONTROLLED_URL_INTAKE_ENDPOINT = "/api/intake";' in html
    assert html.count("function controlledUrlIntakeAvailable()") == 1
    assert "window.location?.origin === PRIVATE_OPERATOR_ORIGIN" in html
    assert (
        controlled_contract.index("if (!controlledUrlIntakeAvailable())")
        < controlled_contract.index("fetch(CONTROLLED_URL_INTAKE_ENDPOINT")
    )
    assert 'throw new ControlledIntakeError("private_intake_required");' in controlled_contract
    assert "sourceUrl && !useControlledUrlIntake && !raw" in html
    assert "if (useControlledUrlIntake)" in html
    assert 'credentials: "include"' in html
    assert 'redirect: "error"' in html
    assert "fetch(sourceUrl" not in html
    assert "https://api.huboptimus.dev/intake/url" not in html
    assert (
        'href="https://api.huboptimus.dev/oauth2/start?rd='
        "https%3A%2F%2Fapi.huboptimus.dev%2Foperator%2F\"" in html
    )
    assert "localStorage.setItem" not in controlled_contract


def test_nginx_and_gateway_use_one_sanitized_internal_contract():
    nginx = _read(NGINX)
    gateway = _read(GATEWAY)

    assert "location = /api/intake" in nginx
    assert "proxy_pass http://127.0.0.1:8081/intake/url;" in nginx
    assert "proxy_pass http://127.0.0.1:8080" not in nginx
    assert "proxy_pass_request_headers off;" in nginx
    for header in (
        "X-Hub-Internal-Capability",
        "X-Hub-Authenticated-Subject",
        "X-Hub-Authenticated-Roles",
        "X-Hub-Client-IP",
    ):
        assert f"proxy_set_header {header} " in nginx
        assert f'"{header}"' in gateway
    assert 'EXPECTED_ORIGIN = "https://api.huboptimus.dev"' in gateway
    assert 'PUBLIC_PATH = "/intake/url"' in gateway
    assert 'UPSTREAM_PATH = "/intake/url"' in gateway
    assert 'UPSTREAM_HOST = "127.0.0.1"' in gateway
    assert 'UPSTREAM_PORT = 8080' in gateway


def test_runbook_keeps_activation_and_external_evidence_gates_open():
    runbook = _read(RUNBOOK)

    assert "repository deployment candidate" in runbook
    assert "not evidence of a live identity or\nEC2 deployment" in runbook
    assert "`#1832` has been reviewed and merged" in runbook
    assert "`#1831` has deployed the reviewed full commit SHA" in runbook
    for gate in (
        "DNS",
        "TLS",
        "Redis",
        "MFA",
        "Conditional Access",
        "Safari/iOS",
    ):
        assert gate in runbook
    assert "must remain open until their evidence is\nrecorded" in runbook
