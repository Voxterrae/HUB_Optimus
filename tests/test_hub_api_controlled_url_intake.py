import io
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
API_SCRIPT = ROOT / "ops" / "ec2" / "hub-api.sh"


def load_embedded_api_namespace() -> dict:
    script = API_SCRIPT.read_text(encoding="utf-8")
    embedded = script.split("<<'PY'\n", 1)[1].split("\nPY\n", 1)[0]
    namespace = {"__name__": "hub_api_contract_test"}
    exec(compile(embedded, str(API_SCRIPT), "exec"), namespace)
    return namespace


def make_body_reader(namespace: dict, content_length: str | None, body: bytes):
    handler = object.__new__(namespace["Handler"])
    handler.headers = {}
    if content_length is not None:
        handler.headers["Content-Length"] = content_length
    handler.rfile = io.BytesIO(body)
    responses = []
    handler.send_json = lambda status, payload: responses.append((status, payload))
    return handler, responses


def test_hub_api_controlled_url_intake_endpoint_present():
    text = API_SCRIPT.read_text(encoding="utf-8")

    assert "/intake/url" in text
    assert "def validate_intake_url" in text
    assert "def fetch_url_text" in text
    assert "controlled_url_intake" in text
    assert "MAX_URL_BYTES = 1_000_000" in text
    assert "MAX_URL_BODY_LENGTH = 4096" in text
    assert "MAX_ANALYZE_BODY_LENGTH = 64_000" in text
    assert "MAX_REDIRECTS = 3" in text
    assert "URL_TIMEOUT_SECONDS = 8" in text
    assert "HUB_Optimus-Operator-URL-Intake/0.1" in text


def test_url_and_analyze_handlers_use_separate_bounded_body_limits():
    text = API_SCRIPT.read_text(encoding="utf-8")

    assert "self.read_json_body(MAX_URL_BODY_LENGTH)" in text
    assert "self.read_json_body(MAX_ANALYZE_BODY_LENGTH)" in text


def test_analysis_limit_accepts_representative_operator_payload():
    namespace = load_embedded_api_namespace()
    body = ('{"case_id":"operator-case","raw_text":"' + ("evidence " * 700) + '"}').encode()
    assert len(body) > namespace["MAX_URL_BODY_LENGTH"]
    assert len(body) < namespace["MAX_ANALYZE_BODY_LENGTH"]

    handler, responses = make_body_reader(namespace, str(len(body)), body)

    payload = handler.read_json_body(namespace["MAX_ANALYZE_BODY_LENGTH"])

    assert payload is not None
    assert payload["case_id"] == "operator-case"
    assert responses == []


def test_url_limit_rejects_same_representative_operator_payload():
    namespace = load_embedded_api_namespace()
    body = ('{"raw_text":"' + ("evidence " * 700) + '"}').encode()
    handler, responses = make_body_reader(namespace, str(len(body)), body)

    payload = handler.read_json_body(namespace["MAX_URL_BODY_LENGTH"])

    assert payload is None
    assert responses == [
        (
            413,
            {
                "error": "request body too large",
                "limit_bytes": namespace["MAX_URL_BODY_LENGTH"],
            },
        )
    ]


def test_json_body_reader_rejects_missing_invalid_and_negative_lengths():
    namespace = load_embedded_api_namespace()

    for content_length, expected_status in ((None, 411), ("invalid", 400), ("-1", 400)):
        handler, responses = make_body_reader(namespace, content_length, b"{}")

        assert handler.read_json_body(namespace["MAX_URL_BODY_LENGTH"]) is None
        assert responses[0][0] == expected_status


def test_json_body_reader_rejects_invalid_utf8_without_traceback():
    namespace = load_embedded_api_namespace()
    handler, responses = make_body_reader(namespace, "2", b"\xff\xfe")

    assert handler.read_json_body(namespace["MAX_URL_BODY_LENGTH"]) is None
    assert responses == [(400, {"error": "request body must be valid UTF-8"})]


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
