from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
API_SCRIPT = ROOT / "ops" / "ec2" / "hub-api.sh"


def test_hub_api_controlled_url_intake_endpoint_present():
    text = API_SCRIPT.read_text(encoding="utf-8")

    assert "/intake/url" in text
    assert "def validate_intake_url" in text
    assert "def fetch_url_text" in text
    assert "controlled_url_intake" in text
    assert "MAX_URL_BYTES = 1_000_000" in text
    assert "MAX_REDIRECTS = 3" in text
    assert "URL_TIMEOUT_SECONDS = 8" in text
    assert "HUB_Optimus-Operator-URL-Intake/0.1" in text


def test_hub_api_controlled_url_intake_security_boundary_present():
    text = API_SCRIPT.read_text(encoding="utf-8")

    assert "ipaddress.ip_address" in text
    assert "socket.getaddrinfo" in text
    assert "if ip.is_global" in text
    assert "unsupported_url_scheme" in text
    assert "unsupported_url_credentials" in text
    assert "unsupported_url_port" in text
    assert "blocked_url_host" in text
    assert "NoRedirectHandler" in text


def test_hub_api_controlled_url_intake_output_contract_present():
    text = API_SCRIPT.read_text(encoding="utf-8")

    assert '"intake_type": "controlled_url"' in text
    assert '"verification_status": "unreviewed"' in text
    assert '"learning_status": "candidate-source-not-verified"' in text
    assert "No cookies, authentication, browser automation, or paywall bypass were used." in text
    assert "Text extraction is source-bound and does not verify truth." in text
