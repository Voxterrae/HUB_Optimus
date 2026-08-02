import ast
import io
import json
import re
import socket
import sys
import threading
import time
import types
from email.message import Message
from http.client import BadStatusLine, HTTPResponse, IncompleteRead, LineTooLong
from pathlib import Path
from urllib.error import URLError

import jsonschema
import pytest

ROOT = Path(__file__).resolve().parents[1]
API_SCRIPT = ROOT / "ops" / "ec2" / "hub-api.sh"
CONTRACT_SCHEMA = ROOT / "ops" / "ec2" / "controlled_url_intake.v1.schema.json"
RFC = ROOT / "docs" / "rfc" / "operator_controlled_url_intake.md"


def load_contract_schema() -> dict:
    return json.loads(CONTRACT_SCHEMA.read_text(encoding="utf-8"))


def validate_contract_payload(payload: dict) -> None:
    schema = load_contract_schema()
    jsonschema.Draft202012Validator(
        schema,
        format_checker=jsonschema.FormatChecker(),
    ).validate(payload)


def embedded_api_source() -> str:
    source = API_SCRIPT.read_text(encoding="utf-8")
    return source.split('cat > "$API_FILE" <<\'PY\'\n', 1)[1].split(
        "\nPY\n",
        1,
    )[0]


def static_intake_error_statuses() -> dict[str, int]:
    tree = ast.parse(embedded_api_source())
    statuses: dict[str, int] = {}

    def record(call: ast.Call) -> None:
        if len(call.args) < 2:
            return
        status_node, code_node = call.args[:2]
        if not (
            isinstance(status_node, ast.Constant)
            and isinstance(status_node.value, int)
            and isinstance(code_node, ast.Constant)
            and isinstance(code_node.value, str)
        ):
            return
        previous = statuses.setdefault(code_node.value, status_node.value)
        assert previous == status_node.value

    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "IntakeError"
        ):
            record(node)

    deadline_error = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "FetchDeadlineExceeded"
    )
    for node in ast.walk(deadline_error):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "__init__"
        ):
            record(node)

    return statuses


def make_body_reader(
    namespace: dict,
    content_length: str | None,
    body: bytes,
    extra_headers: tuple[tuple[str, str], ...] = (),
):
    handler = object.__new__(namespace["Handler"])
    handler.headers = Message()
    if content_length is not None:
        handler.headers.add_header("Content-Length", content_length)
    for name, value in extra_headers:
        handler.headers.add_header(name, value)
    handler.rfile = io.BytesIO(body)
    responses = []
    handler.send_json = lambda status, payload: responses.append((status, payload))
    return handler, responses


@pytest.fixture()
def hub_api():
    source = API_SCRIPT.read_text(encoding="utf-8")
    embedded = source.split('cat > "$API_FILE" <<\'PY\'\n', 1)[1].split(
        "\nPY\n",
        1,
    )[0]
    module = types.ModuleType("hub_api_test")
    module.__file__ = str(API_SCRIPT)
    sys.modules[module.__name__] = module
    exec(  # noqa: S102 - exercise the launcher-generated Python module.
        compile(embedded, str(API_SCRIPT), "exec"),
        module.__dict__,
    )
    yield module
    sys.modules.pop(module.__name__, None)


def address_info(ip_text, port):
    family = socket.AF_INET6 if ":" in ip_text else socket.AF_INET
    socket_address = (
        (ip_text, port, 0, 0)
        if family == socket.AF_INET6
        else (ip_text, port)
    )
    return (family, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", socket_address)


def test_controlled_url_intake_schema_and_examples_are_valid():
    schema = load_contract_schema()
    jsonschema.Draft202012Validator.check_schema(schema)

    examples = [
        schema["$defs"][name]["examples"][0]
        for name in ("request", "success_response", "error_response")
    ]
    for example in examples:
        validate_contract_payload(example)

    assert schema["$id"].endswith("/controlled-url-intake-v1.schema.json")


def test_rfc_examples_are_the_canonical_schema_examples():
    schema = load_contract_schema()
    rfc = RFC.read_text(encoding="utf-8")
    documented_examples = [
        json.loads(block)
        for block in re.findall(r"```json\n(.*?)\n```", rfc, re.DOTALL)
    ]
    canonical_examples = [
        schema["$defs"][name]["examples"][0]
        for name in ("request", "success_response", "error_response")
    ]

    assert documented_examples == canonical_examples
    assert '"intake": {' not in rfc
    assert '"resolved_url":' not in rfc
    assert '"error_code":' not in rfc
    assert "max 40,000 characters" not in rfc
    assert "HUB_Optimus-Operator-Intake/0.1" not in rfc


def test_runtime_limits_user_agent_and_error_codes_match_schema(hub_api):
    schema = load_contract_schema()
    limits = schema["x-hub-optimus-runtime-limits"]

    assert limits["request_body_bytes"] == hub_api.MAX_URL_BODY_LENGTH
    assert limits["url_characters"] == hub_api.MAX_URL_LENGTH
    assert limits["raw_response_bytes"] == hub_api.MAX_URL_BYTES
    assert limits["extracted_text_characters"] == hub_api.MAX_EXTRACTED_TEXT_CHARS
    assert (
        limits["maximum_returned_text_characters"]
        == hub_api.MAX_EXTRACTED_TEXT_CHARS + 1
    )
    assert limits["html_element_depth"] == hub_api.MAX_HTML_DEPTH
    assert limits["html_primary_regions"] == hub_api.MAX_PRIMARY_REGIONS
    assert limits["redirects"] == hub_api.MAX_REDIRECTS
    assert limits["timeout_seconds"] == hub_api.URL_TIMEOUT_SECONDS
    assert limits["user_agent"] == hub_api.USER_AGENT
    assert limits["endpoint"] == "/intake/url"
    assert limits["remote_request_method"] == "GET"
    assert limits["accepted_schemes"] == ["http", "https"]

    schema_statuses = schema["x-hub-optimus-error-http-status"]
    error_enum = set(
        schema["$defs"]["error_response"]["properties"]["error"]["enum"]
    )
    assert set(schema_statuses) == error_enum
    assert static_intake_error_statuses() == schema_statuses


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


def test_analysis_limit_accepts_representative_operator_payload(hub_api):
    namespace = hub_api.__dict__
    body = ('{"case_id":"operator-case","raw_text":"' + ("evidence " * 700) + '"}').encode()
    assert len(body) > namespace["MAX_URL_BODY_LENGTH"]
    assert len(body) < namespace["MAX_ANALYZE_BODY_LENGTH"]

    handler, responses = make_body_reader(namespace, str(len(body)), body)

    payload = handler.read_json_body(namespace["MAX_ANALYZE_BODY_LENGTH"])

    assert payload is not None
    assert payload["case_id"] == "operator-case"
    assert responses == []


def test_url_limit_rejects_same_representative_operator_payload(hub_api):
    namespace = hub_api.__dict__
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


def test_json_body_reader_rejects_missing_invalid_and_negative_lengths(hub_api):
    namespace = hub_api.__dict__

    for content_length, expected_status in ((None, 411), ("invalid", 400), ("-1", 400)):
        handler, responses = make_body_reader(namespace, content_length, b"{}")

        assert handler.read_json_body(namespace["MAX_URL_BODY_LENGTH"]) is None
        assert responses[0][0] == expected_status


@pytest.mark.parametrize(
    ("content_length", "body", "extra_headers", "expected_error"),
    [
        (
            "100",
            b"{}",
            (),
            "request body ended before its declared Content-Length",
        ),
        (
            "2",
            b"{}",
            (("Content-Length", "100"),),
            "exactly one Content-Length header is required",
        ),
        (
            "2",
            b"{}",
            (("Transfer-Encoding", "chunked"),),
            "Transfer-Encoding request bodies are not supported",
        ),
    ],
    ids=["short-body", "duplicate-content-length", "content-length-plus-chunked"],
)
def test_json_body_reader_rejects_ambiguous_or_incomplete_framing(
    hub_api,
    content_length,
    body,
    extra_headers,
    expected_error,
):
    namespace = hub_api.__dict__
    handler, responses = make_body_reader(
        namespace,
        content_length,
        body,
        extra_headers,
    )

    assert handler.read_json_body(namespace["MAX_URL_BODY_LENGTH"]) is None
    assert responses == [(400, {"error": expected_error})]


def test_json_body_reader_rejects_invalid_utf8_without_traceback(hub_api):
    namespace = hub_api.__dict__
    handler, responses = make_body_reader(namespace, "2", b"\xff\xfe")

    assert handler.read_json_body(namespace["MAX_URL_BODY_LENGTH"]) is None
    assert responses == [(400, {"error": "request body must be valid UTF-8"})]


def test_json_body_reader_rejects_escaped_non_scalar_unicode_without_echoing_it(
    hub_api,
):
    namespace = hub_api.__dict__
    body = b'{"url":"\\ud800"}'
    handler, responses = make_body_reader(namespace, str(len(body)), body)

    assert handler.read_json_body(namespace["MAX_URL_BODY_LENGTH"]) is None
    assert responses == [
        (400, {"error": "invalid JSON: $.<value> contains non-scalar Unicode"})
    ]


def test_json_body_reader_rejects_deep_nesting_without_recursion_failure(hub_api):
    namespace = hub_api.__dict__
    raw = (
        '{"url":"https://example.com","x":'
        + ("[" * 1000)
        + "0"
        + ("]" * 1000)
        + "}"
    )
    body = raw.encode("utf-8")
    assert len(body) < namespace["MAX_URL_BODY_LENGTH"]
    handler, responses = make_body_reader(namespace, str(len(body)), body)

    assert handler.read_json_body(namespace["MAX_URL_BODY_LENGTH"]) is None
    assert responses[0][0] == 400
    assert responses[0][1]["error"].startswith(
        "invalid JSON: JSON structure exceeds"
    )


@pytest.mark.parametrize(
    "limit_name",
    ["MAX_URL_BODY_LENGTH", "MAX_ANALYZE_BODY_LENGTH"],
    ids=["url-intake", "analyze"],
)
@pytest.mark.parametrize("constant", ["NaN", "Infinity", "-Infinity"])
def test_json_body_reader_rejects_non_standard_numeric_constants(
    hub_api,
    limit_name,
    constant,
):
    namespace = hub_api.__dict__
    body = (
        '{"metadata":{"nested":{"value":' + constant + "}}}"
    ).encode("utf-8")
    handler, responses = make_body_reader(
        namespace,
        str(len(body)),
        body,
    )

    payload = handler.read_json_body(namespace[limit_name])

    assert payload is None
    assert responses == [
        (
            400,
            {
                "error": (
                    "invalid JSON: non-standard numeric constant "
                    f"{constant} is not valid JSON"
                )
            },
        )
    ]


def test_json_body_reader_preserves_finite_nested_numeric_metadata(hub_api):
    namespace = hub_api.__dict__
    body = (
        b'{"metadata":{"nested":{"negative":-12.5,"zero":0,'
        b'"positive":6.25e18}}}'
    )
    handler, responses = make_body_reader(
        namespace,
        str(len(body)),
        body,
    )

    payload = handler.read_json_body(namespace["MAX_ANALYZE_BODY_LENGTH"])

    assert payload == {
        "metadata": {
            "nested": {
                "negative": -12.5,
                "zero": 0,
                "positive": 6.25e18,
            }
        }
    }
    assert responses == []


def test_response_serializer_fails_closed_before_writing_non_finite_json(
    hub_api,
):
    handler = object.__new__(hub_api.Handler)
    statuses = []
    headers = []
    handler.send_response = statuses.append
    handler.send_header = lambda name, value: headers.append((name, value))
    handler.end_headers = lambda: None
    handler.wfile = io.BytesIO()

    handler.send_json(
        200,
        {"metadata": {"nested": {"value": float("nan")}}},
    )

    body = handler.wfile.getvalue().decode("utf-8")
    assert statuses == [500]
    assert json.loads(body) == {
        "error": "response payload is not valid strict JSON"
    }
    assert "NaN" not in body
    assert headers[0] == (
        "Content-Type",
        "application/json; charset=utf-8",
    )


def test_response_serializer_fails_closed_before_utf8_encoding_a_surrogate(
    hub_api,
):
    handler = object.__new__(hub_api.Handler)
    statuses = []
    handler.send_response = statuses.append
    handler.send_header = lambda name, value: None
    handler.end_headers = lambda: None
    handler.wfile = io.BytesIO()

    handler.send_json(200, {"url": "\ud800"})

    body = handler.wfile.getvalue().decode("utf-8")
    assert statuses == [500]
    assert json.loads(body) == {
        "error": "response payload is not valid strict JSON"
    }


def test_response_serializer_fails_closed_on_deep_or_circular_structure(hub_api):
    deeply_nested = 0
    for _ in range(80):
        deeply_nested = [deeply_nested]
    circular = {}
    circular["self"] = circular

    for payload in ({"nested": deeply_nested}, circular):
        handler = object.__new__(hub_api.Handler)
        statuses = []
        handler.send_response = statuses.append
        handler.send_header = lambda name, value: None
        handler.end_headers = lambda: None
        handler.wfile = io.BytesIO()

        handler.send_json(200, payload)

        assert statuses == [500]
        assert json.loads(handler.wfile.getvalue().decode("utf-8")) == {
            "error": "response payload is not valid strict JSON"
        }


def test_analyze_serializer_fails_closed_before_creating_case_file(
    hub_api,
    tmp_path,
):
    hub_api.SHARED = tmp_path / "shared"
    handler = object.__new__(hub_api.Handler)
    handler.read_json_body = lambda limit: {
        "metadata": {"nested": {"value": float("inf")}}
    }
    responses = []
    handler.send_json = lambda status, payload: responses.append(
        (status, payload)
    )
    hub_api.run_command = lambda *args, **kwargs: pytest.fail(
        "invalid payload must not reach hub-core"
    )

    handler.handle_analyze()

    assert responses == [
        (
            500,
            {"error": "cannot serialize case input as strict JSON"},
        )
    ]
    assert not (hub_api.SHARED / "api" / "cases").exists()


def test_analyze_rejects_non_standard_numeric_constant_in_result_file(
    hub_api,
    tmp_path,
):
    hub_api.SHARED = tmp_path / "shared"
    run_id = "20260729T120000Z.Ab12Cd"

    def fake_run_command(args, input_text=None):
        assert input_text is None
        result_path = (
            hub_api.SHARED
            / "runs"
            / "analyze"
            / run_id
            / "analysis_result.json"
        )
        result_path.parent.mkdir(parents=True)
        result_path.write_text(
            '{"metadata":{"nested":{"value":NaN}}}\n',
            encoding="utf-8",
        )
        return 0, f"[hub-core:run-id] {run_id}\n", ""

    hub_api.run_command = fake_run_command
    handler = object.__new__(hub_api.Handler)
    handler.read_json_body = lambda limit: {
        "case_id": "strict-result",
        "core_version_ref": "main",
        "input_summary": "Strict result regression fixture.",
    }
    responses = []
    handler.send_json = lambda status, payload: responses.append(
        (status, payload)
    )

    handler.handle_analyze()

    assert responses == [
        (
            500,
            {
                "error": (
                    "analysis result is invalid JSON: non-standard numeric "
                    "constant NaN is not valid JSON"
                )
            },
        )
    ]


def test_hub_api_controlled_url_intake_security_boundary_present():
    text = API_SCRIPT.read_text(encoding="utf-8")

    assert "ipaddress.ip_address" in text
    assert "socket.getaddrinfo" in text
    assert "ip.is_global" in text
    assert "invalid_url_port" in text
    assert "unsupported_url_scheme" in text
    assert "unsupported_url_credentials" in text
    assert "unsupported_url_port" in text
    assert "blocked_url_host" in text
    assert "socket.create_connection" not in text
    assert "connection.getpeername()" in text
    assert "PinnedHTTPSConnection" in text
    assert "ProxyHandler({})" in text
    assert "NoRedirectHandler" in text


def test_hub_api_controlled_url_intake_output_contract_present():
    text = API_SCRIPT.read_text(encoding="utf-8")

    assert '"intake_type": "controlled_url"' in text
    assert '"url": raw_url' in text
    assert '"url": url' in text
    assert '"verification_status": "unreviewed"' in text
    assert '"learning_status": "candidate-source-not-verified"' in text
    assert "No cookies, authentication, browser automation, or paywall bypass were used." in text
    assert "Text extraction is source-bound and does not verify truth." in text


@pytest.mark.parametrize(
    "url",
    [
        "https://example.com:bad/article",
        "https://example.com:99999/article",
    ],
)
def test_malformed_and_out_of_range_ports_fail_cleanly(hub_api, url):
    with pytest.raises(hub_api.IntakeError) as caught:
        hub_api.validate_intake_url(url)

    assert caught.value.status == 400
    assert caught.value.code == "invalid_url_port"
    assert "port" in caught.value.message.lower()


def test_malformed_ipv6_url_fails_cleanly(hub_api):
    with pytest.raises(hub_api.IntakeError) as caught:
        hub_api.validate_intake_url("https://[::1/article")

    assert caught.value.status == 400
    assert caught.value.code == "invalid_url"


@pytest.mark.parametrize(
    "url",
    [
        "http://@example.com/article",
        "https://:@example.com/article",
        "https://user@example.com/article",
        "https://user:password@example.com/article",
    ],
)
def test_any_userinfo_syntax_is_rejected_before_dns(hub_api, monkeypatch, url):
    def unexpected_dns(*args, **kwargs):
        raise AssertionError("userinfo must be rejected before DNS")

    monkeypatch.setattr(hub_api.socket, "getaddrinfo", unexpected_dns)

    with pytest.raises(hub_api.IntakeError) as caught:
        hub_api.validate_intake_url(url)

    assert caught.value.status == 400
    assert caught.value.code == "unsupported_url_credentials"


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1/",
        "http://10.0.0.1/",
        "http://169.254.169.254/latest/meta-data/",
        "http://0.0.0.0/",
        "http://224.0.0.1/",
        "http://[::1]/",
        "http://[fc00::1]/",
        "http://[fe80::1]/",
        "http://[fec0::1]/",
        "http://[feff::1]/",
        "http://[::]/",
        "http://[ff02::1]/",
    ],
)
def test_direct_local_private_and_non_global_addresses_are_blocked(hub_api, url):
    with pytest.raises(hub_api.IntakeError) as caught:
        hub_api.validate_intake_url(url)

    assert caught.value.status == 400
    assert caught.value.code == "blocked_url_host"


@pytest.mark.parametrize(
    ("url", "resolved_ip", "port"),
    [
        ("http://8.8.8.8/article", "8.8.8.8", 80),
        (
            "https://[2001:4860:4860::8888]/article",
            "2001:4860:4860::8888",
            443,
        ),
    ],
)
def test_public_ip_literals_are_pinned_without_dns(hub_api, url, resolved_ip, port):
    validated = hub_api.validate_intake_url(url)

    assert validated.resolved_ips == (resolved_ip,)
    assert validated.port == port


@pytest.mark.parametrize(
    "url",
    [
        "http://8.8.8.8:443/",
        "https://8.8.8.8:80/",
    ],
)
def test_cross_scheme_ports_are_not_treated_as_defaults(hub_api, url):
    with pytest.raises(hub_api.IntakeError) as caught:
        hub_api.validate_intake_url(url)

    assert caught.value.status == 400
    assert caught.value.code == "unsupported_url_port"


@pytest.mark.parametrize(
    "blocked_ip",
    ["10.0.0.7", "fe80::7", "fec0::7", "feff::7", "::1"],
)
def test_dns_answer_with_any_non_global_address_is_rejected(
    hub_api,
    monkeypatch,
    blocked_ip,
):
    def fake_getaddrinfo(host, port, type):
        assert host == "mixed.example"
        assert type == socket.SOCK_STREAM
        return [
            address_info("8.8.8.8", port),
            address_info(blocked_ip, port),
        ]

    monkeypatch.setattr(hub_api.socket, "getaddrinfo", fake_getaddrinfo)

    with pytest.raises(hub_api.IntakeError) as caught:
        hub_api.validate_intake_url("https://mixed.example/article")

    assert caught.value.status == 400
    assert caught.value.code == "blocked_url_host"


def test_connection_uses_only_validated_numeric_ips_and_preserves_tls_name(
    hub_api,
    monkeypatch,
):
    dns_queries = []
    connections = []
    tls_names = []

    def fake_getaddrinfo(host, port, type):
        dns_queries.append((host, port, type))
        return [
            address_info("8.8.8.8", port),
            address_info("2001:4860:4860::8888", port),
        ]

    class FakeSocket:
        def __init__(self, family, socket_type, protocol):
            self.family = family
            self.socket_type = socket_type
            self.protocol = protocol
            self.address = None
            self.timeout = None

        def settimeout(self, timeout):
            self.timeout = timeout

        def bind(self, source_address):
            raise AssertionError(f"unexpected source bind: {source_address}")

        def connect(self, address):
            self.address = address
            connections.append((address, self.timeout, None))

        def getpeername(self):
            return self.address

        def setsockopt(self, *args):
            return None

        def close(self):
            return None

    class FakeTlsContext:
        def wrap_socket(self, sock, server_hostname):
            tls_names.append(server_hostname)
            return sock

    monkeypatch.setattr(hub_api.socket, "getaddrinfo", fake_getaddrinfo)
    monkeypatch.setattr(
        hub_api.socket,
        "socket",
        FakeSocket,
    )

    validated = hub_api.validate_intake_url("https://public.example/article")
    deadline = hub_api.FetchDeadline.start(3)
    connection = hub_api.PinnedHTTPSConnection(
        validated.hostname,
        timeout=3,
        context=FakeTlsContext(),
        pinned_ips=validated.resolved_ips,
        deadline=deadline,
    )
    connection.connect()

    assert dns_queries == [
        ("public.example", 443, socket.SOCK_STREAM),
    ]
    assert connections[0][0][0] in validated.resolved_ips
    assert connections[0][0][0] != validated.hostname
    assert connection.host == "public.example"
    assert tls_names == ["public.example"]


def test_numeric_socket_rejects_a_peer_that_differs_from_validated_ip(
    hub_api,
    monkeypatch,
):
    closed = []

    class WrongPeerSocket:
        def __init__(self, family, socket_type, protocol):
            self.address = None

        def settimeout(self, timeout):
            return None

        def connect(self, address):
            self.address = address

        def getpeername(self):
            return ("127.0.0.1", self.address[1])

        def close(self):
            closed.append(True)

    monkeypatch.setattr(hub_api.socket, "socket", WrongPeerSocket)

    deadline = hub_api.FetchDeadline.start(3)
    with pytest.raises(OSError, match="does not match"):
        hub_api.create_pinned_connection(
            ("public.example", 443),
            3,
            None,
            ("8.8.8.8",),
            deadline,
        )

    assert closed == [True]


def test_numeric_ipv6_socket_uses_ipv6_family_and_sockaddr(hub_api, monkeypatch):
    created = []

    class RecordingSocket:
        def __init__(self, family, socket_type, protocol):
            self.family = family
            self.address = None
            created.append(self)

        def settimeout(self, timeout):
            self.timeout = timeout

        def connect(self, address):
            self.address = address

        def getpeername(self):
            return self.address

        def close(self):
            return None

    monkeypatch.setattr(hub_api.socket, "socket", RecordingSocket)

    connection = hub_api.connect_validated_ip(
        "2001:4860:4860::8888",
        443,
        3,
        None,
    )

    assert connection is created[0]
    assert created[0].family == socket.AF_INET6
    assert created[0].address == ("2001:4860:4860::8888", 443, 0, 0)
    assert created[0].timeout == 3


def test_pinned_opener_disables_environment_proxies(hub_api):
    deadline = hub_api.FetchDeadline.start(3)
    opener = hub_api.build_pinned_opener(("8.8.8.8",), deadline)
    proxy_handlers = [
        handler
        for handler in opener.handlers
        if isinstance(handler, hub_api.ProxyHandler)
    ]

    assert proxy_handlers == []


@pytest.mark.parametrize(
    "redirect_target",
    [
        "http://127.0.0.1/private",
        "http://[::1]/private",
        "http://[fec0::1]/private",
        "http://[feff::1]/private",
        "http://private.example/private",
    ],
)
def test_redirects_to_local_or_private_destinations_are_rejected(
    hub_api,
    monkeypatch,
    redirect_target,
):
    requests = []

    def fake_getaddrinfo(host, port, type):
        if host == "public.example":
            return [address_info("8.8.8.8", port)]
        if host == "private.example":
            return [address_info("10.0.0.9", port)]
        raise AssertionError(f"unexpected DNS query: {host}")

    class RedirectOpener:
        def open(self, request, timeout):
            requests.append((request.full_url, timeout))
            raise hub_api.HTTPError(
                request.full_url,
                302,
                "Found",
                {"Location": redirect_target},
                None,
            )

    monkeypatch.setattr(hub_api.socket, "getaddrinfo", fake_getaddrinfo)
    monkeypatch.setattr(
        hub_api,
        "build_pinned_opener",
        lambda pinned_ips, deadline: RedirectOpener(),
    )

    with pytest.raises(hub_api.IntakeError) as caught:
        hub_api.fetch_url_text("https://public.example/article")

    assert caught.value.status == 400
    assert caught.value.code == "blocked_url_host"
    assert len(requests) == 1
    assert requests[0][0] == "https://public.example/article"
    assert 0 < requests[0][1] <= hub_api.URL_TIMEOUT_SECONDS


def test_redirect_with_duplicate_location_headers_is_rejected(
    hub_api,
    monkeypatch,
):
    headers = Message()
    headers.add_header("Location", "https://first.example/article")
    headers.add_header("Location", "http://127.0.0.1/private")

    def fake_getaddrinfo(host, port, type):
        assert host == "public.example"
        return [address_info("8.8.8.8", port)]

    class RedirectOpener:
        def open(self, request, timeout):
            raise hub_api.HTTPError(
                request.full_url,
                302,
                "Found",
                headers,
                None,
            )

    monkeypatch.setattr(hub_api.socket, "getaddrinfo", fake_getaddrinfo)
    monkeypatch.setattr(
        hub_api,
        "build_pinned_opener",
        lambda pinned_ips, deadline: RedirectOpener(),
    )

    with pytest.raises(hub_api.IntakeError) as caught:
        hub_api.fetch_url_text("https://public.example/article")

    assert caught.value.status == 502
    assert caught.value.code == "redirect_without_location"


def test_success_fetches_one_url_without_crawling_and_marks_provenance(
    hub_api,
    monkeypatch,
):
    requests = []
    body = b"""
        <html>
          <head><title>Public source article title.</title></head>
          <body>
            <p>This submitted public source contains enough text for extraction.</p>
            <a href="https://linked.example/should-not-be-fetched">Related link</a>
          </body>
        </html>
    """

    def fake_getaddrinfo(host, port, type):
        assert host == "public.example"
        return [address_info("8.8.8.8", port)]

    class FakeResponse:
        def __init__(self):
            self.headers = {
                "Content-Type": "text/html; charset=utf-8",
                "Content-Length": str(len(body)),
            }

        def getcode(self):
            return 200

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

        def read(self, limit):
            assert limit == hub_api.MAX_URL_BYTES + 1
            return body

        def geturl(self):
            return "https://public.example/article"

    class FakeOpener:
        def open(self, request, timeout):
            requests.append((
                request.full_url,
                timeout,
                {key.lower(): value for key, value in request.header_items()},
            ))
            return FakeResponse()

    monkeypatch.setattr(hub_api.socket, "getaddrinfo", fake_getaddrinfo)
    monkeypatch.setattr(
        hub_api,
        "build_pinned_opener",
        lambda pinned_ips, deadline: FakeOpener(),
    )

    result = hub_api.fetch_url_text("https://public.example/article")

    validate_contract_payload(result)
    assert len(requests) == 1
    assert requests[0][0] == "https://public.example/article"
    assert 0 < requests[0][1] <= hub_api.URL_TIMEOUT_SECONDS
    assert requests[0][2]["accept-encoding"] == "identity"
    assert result["url"] == "https://public.example/article"
    assert result["final_url"] == "https://public.example/article"
    assert result["redirects"] == []
    assert result["verification_status"] == "unreviewed"
    assert result["learning_status"] == "candidate-source-not-verified"
    assert "linked.example" not in result["text"]


@pytest.mark.parametrize(
    ("status_code", "extra_headers", "expected_status", "expected_code"),
    [
        (206, {"Content-Range": "bytes 0-31/10000"}, 502, "url_fetch_failed"),
        (200, {"Content-Range": "bytes 0-31/10000"}, 502, "url_fetch_failed"),
        (200, {"Content-Encoding": "gzip"}, 415, "unsupported_content_encoding"),
    ],
    ids=["partial-206", "content-range-on-200", "encoded-gzip"],
)
def test_partial_or_encoded_success_is_never_presented_as_complete_source_text(
    hub_api,
    monkeypatch,
    status_code,
    extra_headers,
    expected_status,
    expected_code,
):
    request_headers = {}
    read_called = False

    def fake_getaddrinfo(host, port, type):
        assert host == "public.example"
        return [address_info("8.8.8.8", port)]

    class PartialOrEncodedResponse:
        headers = {"Content-Type": "text/plain", **extra_headers}

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

        def getcode(self):
            return status_code

        def read(self, limit):
            nonlocal read_called
            read_called = True
            return b"partial or compressed bytes"

        def geturl(self):
            return "https://public.example/article"

    class PartialOrEncodedOpener:
        def open(self, request, timeout):
            request_headers.update(
                {key.lower(): value for key, value in request.header_items()}
            )
            return PartialOrEncodedResponse()

    monkeypatch.setattr(hub_api.socket, "getaddrinfo", fake_getaddrinfo)
    monkeypatch.setattr(
        hub_api,
        "build_pinned_opener",
        lambda pinned_ips, deadline: PartialOrEncodedOpener(),
    )

    with pytest.raises(hub_api.IntakeError) as caught:
        hub_api.fetch_url_text("https://public.example/article")

    assert caught.value.status == expected_status
    assert caught.value.code == expected_code
    assert request_headers["accept-encoding"] == "identity"
    assert read_called is False


@pytest.mark.parametrize(
    ("header_pairs", "expected_status", "expected_code"),
    [
        (
            [
                ("Content-Type", "text/plain"),
                ("Content-Encoding", "identity"),
                ("Content-Encoding", "gzip"),
            ],
            415,
            "unsupported_content_encoding",
        ),
        (
            [
                ("Content-Type", "text/plain"),
                ("Content-Range", ""),
                ("Content-Range", "bytes 0-31/10000"),
            ],
            502,
            "url_fetch_failed",
        ),
        (
            [
                ("Content-Type", "text/plain"),
                ("Content-Type", "text/html"),
            ],
            415,
            "unsupported_content_type",
        ),
    ],
    ids=["duplicate-encoding", "duplicate-content-range", "duplicate-content-type"],
)
def test_repeated_representation_headers_cannot_hide_an_unsupported_value(
    hub_api,
    monkeypatch,
    header_pairs,
    expected_status,
    expected_code,
):
    read_called = False
    headers = hub_api.Message()
    for name, value in header_pairs:
        headers[name] = value

    def fake_getaddrinfo(host, port, type):
        return [address_info("8.8.8.8", port)]

    class RepeatedHeaderResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

        def getcode(self):
            return 200

        def read(self, limit):
            nonlocal read_called
            read_called = True
            return b"must not be read"

    response = RepeatedHeaderResponse()
    response.headers = headers

    class RepeatedHeaderOpener:
        def open(self, request, timeout):
            return response

    monkeypatch.setattr(hub_api.socket, "getaddrinfo", fake_getaddrinfo)
    monkeypatch.setattr(
        hub_api,
        "build_pinned_opener",
        lambda pinned_ips, deadline: RepeatedHeaderOpener(),
    )

    with pytest.raises(hub_api.IntakeError) as caught:
        hub_api.fetch_url_text("https://public.example/article")

    assert caught.value.status == expected_status
    assert caught.value.code == expected_code
    assert read_called is False


@pytest.mark.parametrize(
    ("header_pairs", "body", "expect_read"),
    [
        (
            [("Content-Type", "text/plain"), ("Content-Length", "100")],
            b"only ten!",
            True,
        ),
        (
            [
                ("Content-Type", "text/plain"),
                ("Content-Length", "10"),
                ("Content-Length", "100"),
            ],
            b"0123456789",
            False,
        ),
        (
            [("Content-Type", "text/plain"), ("Content-Length", "10, 100")],
            b"0123456789",
            False,
        ),
        (
            [("Content-Type", "text/plain"), ("Content-Length", "9" * 5000)],
            b"0123456789",
            False,
        ),
        (
            [
                ("Content-Type", "text/plain"),
                ("Content-Length", "10"),
                ("Transfer-Encoding", "chunked"),
            ],
            b"0123456789",
            False,
        ),
        (
            [("Content-Type", "text/plain"), ("Transfer-Encoding", "gzip")],
            b"encoded",
            False,
        ),
    ],
    ids=["short-eof", "duplicate-content-length", "combined-content-length", "oversized-content-length", "cl-and-te", "unsupported-te"],
)
def test_response_framing_ambiguity_or_early_eof_fails_closed(
    hub_api,
    monkeypatch,
    header_pairs,
    body,
    expect_read,
):
    read_called = False
    headers = hub_api.Message()
    for name, value in header_pairs:
        headers[name] = value

    def fake_getaddrinfo(host, port, type):
        return [address_info("8.8.8.8", port)]

    class FramingResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

        def getcode(self):
            return 200

        def read(self, limit):
            nonlocal read_called
            read_called = True
            return body

    response = FramingResponse()
    response.headers = headers

    class FramingOpener:
        def open(self, request, timeout):
            return response

    monkeypatch.setattr(hub_api.socket, "getaddrinfo", fake_getaddrinfo)
    monkeypatch.setattr(
        hub_api,
        "build_pinned_opener",
        lambda pinned_ips, deadline: FramingOpener(),
    )

    with pytest.raises(hub_api.IntakeError) as caught:
        hub_api.fetch_url_text("https://public.example/article")

    assert caught.value.status == 502
    assert caught.value.code == "url_fetch_failed"
    assert read_called is expect_read


@pytest.mark.parametrize(
    "raw_response",
    [
        (
            b"HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\n"
            b"Content-Length: 100\r\n\r\nonly ten!"
        ),
        (
            b"HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\n"
            b"Transfer-Encoding: chunked\r\n\r\nA\r\nshort"
        ),
    ],
    ids=["real-short-content-length", "real-incomplete-chunk"],
)
def test_real_http_response_incomplete_framing_is_rejected(
    hub_api,
    monkeypatch,
    raw_response,
):
    class FakeSocket:
        def makefile(self, mode):
            return io.BytesIO(raw_response)

    response = HTTPResponse(FakeSocket())
    response.begin()

    def fake_getaddrinfo(host, port, type):
        return [address_info("8.8.8.8", port)]

    class RealResponseOpener:
        def open(self, request, timeout):
            return response

    monkeypatch.setattr(hub_api.socket, "getaddrinfo", fake_getaddrinfo)
    monkeypatch.setattr(
        hub_api,
        "build_pinned_opener",
        lambda pinned_ips, deadline: RealResponseOpener(),
    )

    with pytest.raises(hub_api.IntakeError) as caught:
        hub_api.fetch_url_text("https://public.example/article")

    assert caught.value.status == 502
    assert caught.value.code == "url_fetch_failed"


def test_html_extraction_preserves_inline_text_and_short_title(hub_api):
    body = b"""
        <html>
          <head><title>Short headline</title></head>
          <body>
            <main>
              <p>Important policy <strong>changed</strong> on Friday after the public review.</p>
            </main>
          </body>
        </html>
    """

    text, title, truncated = hub_api.extract_text_document(
        body,
        "text/html; charset=utf-8",
    )

    assert title == "Short headline"
    assert text == "Important policy changed on Friday after the public review."
    assert truncated is False


def test_html_extraction_preserves_exact_inline_boundaries(hub_api):
    body = b"""
        <main><p>state-<em>owned</em> can'<em>t</em> cost
        $<b>10</b>/<span>month</span> (<b>A</b>) in
        2<strong>0</strong>26.</p></main>
    """

    text, _, truncated = hub_api.extract_text_document(body, "text/html")

    assert text == "state-owned can't cost $10/month (A) in 2026."
    assert truncated is False


def test_html_extraction_prefers_primary_content_and_drops_boilerplate(hub_api):
    body = b"""
        <html>
          <body>
            <nav>Navigation links should never become extracted source material.</nav>
            <div class="cookie-consent">Cookie controls should never become extracted source material.</div>
            <main>
              <article>
                <h1>Institutional update</h1>
                <p>The institution published a revised procedure after the documented review.</p>
                <p>The notice says the new procedure enters into force next month.</p>
              </article>
              <aside class="related-stories">Related stories should not displace the primary article.</aside>
            </main>
            <footer>Footer terms should never become extracted source material.</footer>
          </body>
        </html>
    """

    text, _, truncated = hub_api.extract_text_document(
        body,
        "text/html; charset=utf-8",
    )

    assert text == (
        "Institutional update\n"
        "The institution published a revised procedure after the documented review.\n"
        "The notice says the new procedure enters into force next month."
    )
    assert truncated is False


def test_nested_boilerplate_container_cannot_leak_after_inner_close(hub_api):
    body = b"""
      <main>
        <div class="cookieConsent">
          <div>Cookie preferences</div>
          <p>ACCEPT ALL COOKIES NOW</p>
        </div>
        <p>Real source statement.</p>
      </main>
    """

    text, _, _ = hub_api.extract_text_document(body, "text/html")

    assert text == "Real source statement."


def test_unrelated_article_card_does_not_replace_longer_document_content(hub_api):
    body = b"""
      <article>Unrelated promotional article teaser containing more than forty characters.</article>
      <div>The actual source report contains a substantially longer account of the
      documented event, including the affected programme, the published date, the
      responsible institution, the cited notice, and the next review step.</div>
    """

    text, _, _ = hub_api.extract_text_document(body, "text/html")

    assert text == (
        "The actual source report contains a substantially longer account of the "
        "documented event, including the affected programme, the published date, the "
        "responsible institution, the cited notice, and the next review step."
    )


def test_main_region_is_not_discarded_by_long_outside_comments(hub_api):
    body = b"""
      <div>Reader comments contain a much longer discussion that repeats unrelated
      opinions, navigation prompts, reaction counts, and subscription requests. This
      material is outside the source document and must not replace its main region.</div>
      <main><h1>Binding decision</h1><p>The operative measure takes effect today.</p></main>
    """

    text, _, _ = hub_api.extract_text_document(body, "text/html")

    assert text == "Binding decision\nThe operative measure takes effect today."


def test_article_card_near_outside_length_cannot_hijack_fallback(hub_api):
    body = b"""
      <article>An unrelated card contains enough characters to look substantial but
      does not contain the submitted source document.</article>
      <div>The actual outside source is similar in length and records the operative
      decision, its publication date, and the responsible body.</div>
    """

    text, _, _ = hub_api.extract_text_document(body, "text/html")

    assert "An unrelated card" in text
    assert "The actual outside source" in text


def test_implied_paragraph_close_ends_skipped_container(hub_api):
    body = b"""
      <main><p class="promo">Subscribe now
      <p>The legitimate source statement remains readable after the implied close.</main>
    """

    text, _, _ = hub_api.extract_text_document(body, "text/html")

    assert text == (
        "The legitimate source statement remains readable after the implied close."
    )


def test_implied_paragraph_close_pops_nested_inline_markup(hub_api):
    body = b"""
      <main><p class="promo"><strong>Subscribe now
      <p>The legitimate statement remains readable after nested malformed markup.</main>
    """

    text, _, _ = hub_api.extract_text_document(body, "text/html")

    assert text == (
        "The legitimate statement remains readable after nested malformed markup."
    )


def test_entities_are_decoded_exactly_once_and_plain_text_stays_literal(hub_api):
    html_text, _, _ = hub_api.extract_text_document(
        b"<main><p>A &amp;amp; B / &amp;lt;draft&amp;gt;</p></main>",
        "text/html",
    )
    plain_text, _, _ = hub_api.extract_text_document(
        b"A &amp; B / &lt;draft&gt;",
        "text/plain",
    )

    assert html_text == "A &amp; B / &lt;draft&gt;"
    assert plain_text == "A &amp; B / &lt;draft&gt;"


def test_boilerplate_phrases_require_real_token_boundaries(hub_api):
    body = b"""
      <main>
        <div class="unrelatedContent">Legitimate unrelated content remains.</div>
        <div class="notRelatedContent">This section explicitly is not related content.</div>
        <div aria-label="Cookie consent">Accept all cookies</div>
      </main>
    """

    text, _, _ = hub_api.extract_text_document(body, "text/html")

    assert text == (
        "Legitimate unrelated content remains.\n"
        "This section explicitly is not related content."
    )


def test_hidden_primary_and_common_auxiliary_labels_are_excluded(hub_api):
    body = b"""
      <main hidden>Stale hidden template text is deliberately much longer than the
      visible notice and must never become the selected source region.</main>
      <main aria-hidden="true">Another inaccessible archived source record.</main>
      <div class="cookieNotice">Accept cookies and manage preferences.</div>
      <article class="relatedArticles">A long recommendation card must not replace
      the actual visible source merely because it uses an article element.</article>
      <main><h1>Visible notice</h1><p>The operative measure applies today.</p></main>
    """

    text, _, _ = hub_api.extract_text_document(body, "text/html")

    assert text == "Visible notice\nThe operative measure applies today."


def test_inline_hidden_style_cannot_win_primary_selection(hub_api):
    body = b"""
      <main style="display: none !important">A stale invisible main region is much
      longer than the visible notice and must not be selected as source text.</main>
      <main style="visibility:hidden">Another hidden archived record.</main>
      <main><h1>Visible notice</h1><p>The operative measure applies today.</p></main>
    """

    text, _, _ = hub_api.extract_text_document(body, "text/html")

    assert text == "Visible notice\nThe operative measure applies today."


def test_hidden_word_in_class_does_not_hide_visible_analysis(hub_api):
    body = b"""
      <main class="not-hidden hidden-costs-analysis">
        <h1>Visible cost analysis</h1>
        <p>The source documents hidden costs but the element itself is visible.</p>
      </main>
    """

    text, _, _ = hub_api.extract_text_document(body, "text/html")

    assert text == (
        "Visible cost analysis\n"
        "The source documents hidden costs but the element itself is visible."
    )


def test_common_cmp_identifiers_are_excluded_and_buttons_stay_separate(hub_api):
    body = b"""
      <main>
        <div id="onetrust-banner-sdk"><p>Consent preferences</p><button>Accept all</button><button>Reject all</button></div>
        <div id="CybotCookiebotDialog">Cookiebot controls</div>
        <div class="cky-consent-container">Managed cookie notice</div>
        <div class="osano-cm-window">Consent management window</div>
        <p>The visible source statement remains after consent controls.</p>
      </main>
    """

    text, _, _ = hub_api.extract_text_document(body, "text/html")

    assert text == "The visible source statement remains after consent controls."


def test_placeholder_main_does_not_replace_substantive_visible_source(hub_api):
    outside = b"""
      <section>The institution published a complete decision with its operative
      measure, effective date, responsible body, scope, and review route.</section>
    """
    text, _, _ = hub_api.extract_text_document(
        b"<main>Loading...</main>" + outside,
        "text/html",
    )
    article_text, _, _ = hub_api.extract_text_document(
        b"<main>Please wait</main><article>The institution published a complete "
        b"decision with its operative measure, effective date, responsible body, "
        b"scope, and review route.</article>",
        "text/html",
    )

    assert text == (
        "The institution published a complete decision with its operative measure, "
        "effective date, responsible body, scope, and review route."
    )
    assert article_text == (
        "The institution published a complete decision with its operative measure, "
        "effective date, responsible body, scope, and review route."
    )

    prefixed_text, _, _ = hub_api.extract_text_document(
        b"<main>Loading content...</main>" + outside,
        "text/html",
    )
    welcome_text, _, _ = hub_api.extract_text_document(
        b"<main>Welcome</main>" + outside,
        "text/html",
    )
    assert prefixed_text == text
    assert welcome_text == text


def test_short_structured_main_dominates_print_controls(hub_api):
    body = b"""
      <main><h1>Recall 24-17</h1><p>Stop use now.</p><p>Fire risk.</p></main>
      <div>Print</div>
    """

    text, _, truncated = hub_api.extract_text_document(body, "text/html")

    assert text == "Recall 24-17\nStop use now.\nFire risk."
    assert truncated is False


def test_html_parser_has_deterministic_depth_and_primary_region_bounds(hub_api):
    parser = hub_api.TextExtractor()
    parser.feed(
        ("<div>" * (hub_api.MAX_HTML_DEPTH + 100))
        + "ignored deep text"
        + "</wrong>text that must not leak after a mismatched close"
        + ("</div>" * (hub_api.MAX_HTML_DEPTH + 100))
        + "<main>Visible tail must remain unavailable after the hard bound.</main>"
    )
    parser.close()

    assert parser.limit_exceeded is True
    assert "ignored deep text" not in "".join(parser.parts)
    assert "must not leak" not in "".join(parser.parts)
    assert "Visible tail" not in "".join(parser.parts)

    text, _, truncated = hub_api.extract_text_document(
        (
            ("<div>" * (hub_api.MAX_HTML_DEPTH + 1))
            + "substantive section beyond the supported depth"
            + ("</div>" * (hub_api.MAX_HTML_DEPTH + 1))
        ).encode(),
        "text/html",
    )
    assert text == ""
    assert truncated is True

    siblings = hub_api.TextExtractor()
    siblings.feed(
        "<article>A bounded sibling article with enough source text.</article>" * 200
    )
    siblings.close()

    assert siblings.limit_exceeded is False
    assert len(parser.primary_regions) <= hub_api.MAX_PRIMARY_REGIONS
    assert len(siblings.primary_regions) <= hub_api.MAX_PRIMARY_REGIONS
    assert "bounded sibling article" in "".join(siblings.parts)


def test_article_candidate_cap_reserves_a_main_region(hub_api):
    cards = "".join(
        f"<article>Recommendation card {index} contains unrelated auxiliary text.</article>"
        for index in range(hub_api.MAX_PRIMARY_REGIONS)
    )
    body = (
        cards
        + "<main>Actual decision applies today.</main>"
    ).encode()

    text, _, _ = hub_api.extract_text_document(body, "text/html")

    assert text == "Actual decision applies today."


def test_truncated_title_sets_the_shared_truncation_flag(hub_api):
    oversized_title = "T" * (hub_api.MAX_EXTRACTED_TEXT_CHARS + 20)
    body = f"<title>{oversized_title}</title><main>Short body.</main>".encode()

    text, title, truncated = hub_api.extract_text_document(body, "text/html")

    assert text == "Short body."
    assert title == "T" * hub_api.MAX_EXTRACTED_TEXT_CHARS + "…"
    assert truncated is True


def test_article_header_and_legitimate_social_topic_are_retained(hub_api):
    body = b"""
      <main class="social">
        <article>
          <header><h1>Social policy update</h1><p>By Ana. 2 August.</p></header>
          <p>The legitimate social-policy article remains available.</p>
        </article>
      </main>
    """

    text, _, _ = hub_api.extract_text_document(body, "text/html")

    assert text == (
        "Social policy update\n"
        "By Ana. 2 August.\n"
        "The legitimate social-policy article remains available."
    )


def test_short_structured_source_facts_are_not_discarded(hub_api):
    body = b"""
      <main>
        <h1>Recall 24-17</h1>
        <ul><li>Model AX9</li><li>Stop use now</li><li>Fire risk</li></ul>
        <p>See notice.</p>
      </main>
    """

    text, _, _ = hub_api.extract_text_document(body, "text/html")

    assert text == "Recall 24-17\nModel AX9\nStop use now\nFire risk\nSee notice."


@pytest.mark.parametrize(
    "content_type",
    [
        'text/html; charset="windows-1252"',
        "text/html; charset = windows-1252",
    ],
)
def test_declared_quoted_or_spaced_charset_is_used(hub_api, content_type):
    text, _, _ = hub_api.extract_text_document(
        "Café e institución".encode("windows-1252"),
        content_type,
    )

    assert text == "Café e institución"


@pytest.mark.parametrize(
    "content_type",
    [
        "text/plain; charset=iso-8859-1; charset=utf-8",
        "text/plain; charset=utf-8; charset=iso-8859-1",
        "text/plain; CHARSET=utf-8; charset=utf-8",
        "text/plain; charset=",
    ],
    ids=["latin-first", "utf8-first", "case-insensitive-duplicate", "empty"],
)
def test_ambiguous_or_empty_charset_parameters_are_rejected(
    hub_api,
    content_type,
):
    with pytest.raises(hub_api.IntakeError) as caught:
        hub_api.extract_text_document("Café".encode("utf-8"), content_type)

    assert caught.value.status == 415
    assert caught.value.code == "unsupported_content_type"


@pytest.mark.parametrize(
    "content_type",
    [
        "text/plain; charset=iso-8859-1; charset=utf-8",
        "text/plain; charset=utf-8; charset=iso-8859-1",
    ],
    ids=["fetch-latin-first", "fetch-utf8-first"],
)
def test_fetch_rejects_conflicting_charset_parameters(
    hub_api,
    monkeypatch,
    content_type,
):
    body = "Café".encode("utf-8")

    def fake_getaddrinfo(host, port, type):
        assert host == "public.example"
        return [address_info("8.8.8.8", port)]

    class AmbiguousCharsetResponse:
        headers = {
            "Content-Type": content_type,
            "Content-Length": str(len(body)),
        }

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

        def getcode(self):
            return 200

        def read(self, limit):
            return body

        def geturl(self):
            return "https://public.example/article"

    class AmbiguousCharsetOpener:
        def open(self, request, timeout):
            return AmbiguousCharsetResponse()

    monkeypatch.setattr(hub_api.socket, "getaddrinfo", fake_getaddrinfo)
    monkeypatch.setattr(
        hub_api,
        "build_pinned_opener",
        lambda pinned_ips, deadline: AmbiguousCharsetOpener(),
    )

    with pytest.raises(hub_api.IntakeError) as caught:
        hub_api.fetch_url_text("https://public.example/article")

    assert caught.value.status == 415
    assert caught.value.code == "unsupported_content_type"


@pytest.mark.parametrize(
    ("body", "content_type"),
    [
        (
            b"Claim: \xff evidence",
            "text/plain; charset=definitely-not-a-codec",
        ),
        (
            b"Claim: incomplete UTF-8 \xe2\x82",
            "text/plain; charset=utf-8",
        ),
    ],
    ids=["unknown-explicit-charset", "incomplete-declared-utf8"],
)
def test_source_bytes_that_cannot_be_decoded_exactly_are_rejected(
    hub_api,
    body,
    content_type,
):
    with pytest.raises(hub_api.IntakeError) as caught:
        hub_api.extract_text_document(body, content_type)

    assert caught.value.status == 415
    assert caught.value.code == "unsupported_content_type"
    assert "\ufffd" not in caught.value.message


@pytest.mark.parametrize(
    ("body", "content_type"),
    [
        (
            b"Claim: \xff evidence",
            "text/plain; charset=definitely-not-a-codec",
        ),
        (
            b"Claim: incomplete UTF-8 \xe2\x82",
            "text/plain; charset=utf-8",
        ),
    ],
    ids=["fetch-unknown-explicit-charset", "fetch-incomplete-declared-utf8"],
)
def test_fetch_rejects_undecodable_source_without_replacement_text(
    hub_api,
    monkeypatch,
    body,
    content_type,
):
    def fake_getaddrinfo(host, port, type):
        assert host == "public.example"
        return [address_info("8.8.8.8", port)]

    class UndecodableResponse:
        headers = {
            "Content-Type": content_type,
            "Content-Length": str(len(body)),
        }

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

        def getcode(self):
            return 200

        def read(self, limit):
            return body

        def geturl(self):
            return "https://public.example/article"

    class UndecodableOpener:
        def open(self, request, timeout):
            return UndecodableResponse()

    monkeypatch.setattr(hub_api.socket, "getaddrinfo", fake_getaddrinfo)
    monkeypatch.setattr(
        hub_api,
        "build_pinned_opener",
        lambda pinned_ips, deadline: UndecodableOpener(),
    )

    with pytest.raises(hub_api.IntakeError) as caught:
        hub_api.fetch_url_text("https://public.example/article")

    assert caught.value.status == 415
    assert caught.value.code == "unsupported_content_type"


@pytest.mark.parametrize("charset", ["unicode_escape", "raw_unicode_escape"])
def test_remote_charset_cannot_introduce_non_scalar_unicode(hub_api, charset):
    with pytest.raises(hub_api.IntakeError) as caught:
        hub_api.extract_text_document(
            b"Visible source text: \\ud800",
            f"text/plain; charset={charset}",
        )

    assert caught.value.status == 415
    assert caught.value.code == "unsupported_content_type"
    assert "supported text encoding" in caught.value.message


@pytest.mark.parametrize("charset", ["unicode_escape", "raw_unicode_escape", "utf-7", "punycode"])
def test_transformation_codecs_cannot_rewrite_literal_source_text(hub_api, charset):
    with pytest.raises(hub_api.IntakeError) as caught:
        hub_api.extract_text_document(
            b"Literal source characters: \\n and \\x41",
            f"text/plain; charset={charset}",
        )

    assert caught.value.status == 415
    assert caught.value.code == "unsupported_content_type"


@pytest.mark.parametrize(
    "content_type",
    [
        "application/x-text/html-garbage",
        "text/htmlx",
        "text/plain-javascript",
    ],
)
def test_lookalike_content_types_are_not_accepted(hub_api, content_type):
    media_type, _ = hub_api.parse_content_type(content_type)

    assert media_type not in {"text/html", "text/plain", "application/xhtml+xml"}


def test_charset_parser_ignores_non_charset_parameters(hub_api):
    assert hub_api.parse_content_type("text/html; xcharset=utf-16") == (
        "text/html",
        "utf-8",
    )
    assert hub_api.parse_content_type('text/html; foo="charset=utf-16"') == (
        "text/html",
        "utf-8",
    )


@pytest.mark.parametrize(
    "content_type",
    [
        'text/plain; charset="utf-8\x00"',
        "text/plain; charset=utf-8\r\n x-folded: value",
        "text/plain; charset=utf-8\x7f",
    ],
    ids=["nul", "obs-fold", "delete"],
)
def test_content_type_controls_cannot_escape_as_codec_or_contract_errors(
    hub_api,
    content_type,
):
    assert hub_api.parse_content_type(content_type) == ("", "utf-8")
    with pytest.raises(hub_api.IntakeError) as caught:
        hub_api.extract_text_document(b"Visible source text", content_type)

    assert caught.value.status == 415
    assert caught.value.code == "unsupported_content_type"


def test_extracted_text_cap_sets_truncated_even_below_raw_byte_cap(hub_api):
    body = ("A" * (hub_api.MAX_EXTRACTED_TEXT_CHARS + 100)).encode("utf-8")

    text, _, truncated = hub_api.extract_text_document(body, "text/plain")

    assert len(body) < hub_api.MAX_URL_BYTES
    assert text == "A" * hub_api.MAX_EXTRACTED_TEXT_CHARS + "…"
    assert truncated is True


def test_parser_close_flushes_text_before_an_incomplete_entity(hub_api):
    body = b"<main><p>" + (b"A" * 100) + b" &amp"

    text, _, truncated = hub_api.extract_text_document(body, "text/html")

    assert text == "A" * 100 + " &"
    assert truncated is False


@pytest.mark.parametrize(
    "error_factory",
    [
        lambda: BadStatusLine("NOT-HTTP"),
        lambda: LineTooLong("header line"),
        lambda: IncompleteRead(b"", 32),
    ],
    ids=["bad-status", "long-header", "incomplete-chunk"],
)
def test_malformed_http_responses_fail_with_controlled_intake_error(
    hub_api,
    monkeypatch,
    error_factory,
):
    def fake_getaddrinfo(host, port, type):
        return [address_info("8.8.8.8", port)]

    class MalformedResponseOpener:
        def open(self, request, timeout):
            raise error_factory()

    monkeypatch.setattr(hub_api.socket, "getaddrinfo", fake_getaddrinfo)
    monkeypatch.setattr(
        hub_api,
        "build_pinned_opener",
        lambda pinned_ips, deadline: MalformedResponseOpener(),
    )

    with pytest.raises(hub_api.IntakeError) as caught:
        hub_api.fetch_url_text("https://public.example/article")

    assert caught.value.status == 502
    assert caught.value.code == "url_fetch_failed"
    assert "malformed" in caught.value.message


@pytest.mark.parametrize(
    ("read_error", "expected_status", "expected_code"),
    [
        (OSError("connection reset"), 502, "url_fetch_failed"),
        (TimeoutError("response stalled"), 504, "url_fetch_timeout"),
    ],
)
def test_response_read_errors_fail_cleanly(
    hub_api,
    monkeypatch,
    read_error,
    expected_status,
    expected_code,
):
    def fake_getaddrinfo(host, port, type):
        return [address_info("8.8.8.8", port)]

    class BrokenResponse:
        headers = {"Content-Type": "text/plain"}

        def getcode(self):
            return 200

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

        def read(self, limit):
            raise read_error

    class BrokenResponseOpener:
        def open(self, request, timeout):
            return BrokenResponse()

    monkeypatch.setattr(hub_api.socket, "getaddrinfo", fake_getaddrinfo)
    monkeypatch.setattr(
        hub_api,
        "build_pinned_opener",
        lambda pinned_ips, deadline: BrokenResponseOpener(),
    )

    with pytest.raises(hub_api.IntakeError) as caught:
        hub_api.fetch_url_text("https://public.example/article")

    assert caught.value.status == expected_status
    assert caught.value.code == expected_code


def test_wrapped_url_timeout_remains_a_504(hub_api, monkeypatch):
    def fake_getaddrinfo(host, port, type):
        return [address_info("8.8.8.8", port)]

    class TimeoutOpener:
        def open(self, request, timeout):
            raise URLError(TimeoutError("connect stalled"))

    monkeypatch.setattr(hub_api.socket, "getaddrinfo", fake_getaddrinfo)
    monkeypatch.setattr(
        hub_api,
        "build_pinned_opener",
        lambda pinned_ips, deadline: TimeoutOpener(),
    )

    with pytest.raises(hub_api.IntakeError) as caught:
        hub_api.fetch_url_text("https://public.example/article")

    assert caught.value.status == 504
    assert caught.value.code == "url_fetch_timeout"


def test_handler_preserves_unreviewed_provenance_for_malformed_http(
    hub_api,
    monkeypatch,
):
    url = "https://public.example/article"

    def fake_getaddrinfo(host, port, type):
        return [address_info("8.8.8.8", port)]

    class MalformedResponseOpener:
        def open(self, request, timeout):
            raise BadStatusLine("NOT-HTTP")

    class RecordingHandler:
        response = None

        def read_json_body(self, max_body_length):
            return {"url": url}

        def send_json(self, status, payload):
            self.response = (status, payload)

    monkeypatch.setattr(hub_api.socket, "getaddrinfo", fake_getaddrinfo)
    monkeypatch.setattr(
        hub_api,
        "build_pinned_opener",
        lambda pinned_ips, deadline: MalformedResponseOpener(),
    )

    handler = RecordingHandler()
    hub_api.Handler.handle_url_intake(handler)

    status, payload = handler.response
    validate_contract_payload(payload)
    assert status == 502
    assert payload["status"] == "error"
    assert payload["error"] == "url_fetch_failed"
    assert payload["url"] == url
    assert payload["verification_status"] == "unreviewed"


@pytest.mark.parametrize(
    "url",
    [
        "https://example.com/a\x00b",
        "https://example.com/a\rb",
        "https://example.com/a\nb",
        "https://example.com/a\tb",
        "https://example.com/a b",
        "https://example.com/a\x7fb",
        " https://example.com/article",
        "https://example.com/article ",
    ],
)
def test_raw_spaces_and_control_characters_fail_before_dns(
    hub_api,
    monkeypatch,
    url,
):
    def unexpected_dns(*args, **kwargs):
        raise AssertionError("malformed URI must be rejected before DNS")

    monkeypatch.setattr(hub_api.socket, "getaddrinfo", unexpected_dns)

    with pytest.raises(hub_api.IntakeError) as caught:
        hub_api.validate_intake_url(url)

    assert caught.value.status == 400
    assert caught.value.code == "invalid_url"


def test_unicode_iri_requires_explicit_percent_encoded_uri(
    hub_api,
    monkeypatch,
):
    dns_queries = []

    def fake_getaddrinfo(host, port, type):
        dns_queries.append((host, port, type))
        return [address_info("8.8.8.8", port)]

    monkeypatch.setattr(hub_api.socket, "getaddrinfo", fake_getaddrinfo)

    with pytest.raises(hub_api.IntakeError) as caught:
        hub_api.validate_intake_url("https://example.com/café")

    assert caught.value.status == 400
    assert caught.value.code == "unsupported_url_iri"
    assert dns_queries == []

    validated = hub_api.validate_intake_url(
        "https://example.com/caf%C3%A9",
    )
    assert validated.url == "https://example.com/caf%C3%A9"
    assert dns_queries == [
        ("example.com", 443, socket.SOCK_STREAM),
    ]


def test_international_hostname_requires_idna_a_label(
    hub_api,
    monkeypatch,
):
    dns_queries = []

    def fake_getaddrinfo(host, port, type):
        dns_queries.append((host, port, type))
        return [address_info("8.8.8.8", port)]

    monkeypatch.setattr(hub_api.socket, "getaddrinfo", fake_getaddrinfo)

    with pytest.raises(hub_api.IntakeError) as caught:
        hub_api.validate_intake_url("https://%65xample.com/article")

    assert caught.value.status == 400
    assert caught.value.code == "invalid_url_host"
    assert dns_queries == []

    validated = hub_api.validate_intake_url(
        "https://xn--caf-dma.example/article",
    )
    assert validated.hostname == "xn--caf-dma.example"
    assert dns_queries == [
        ("xn--caf-dma.example", 443, socket.SOCK_STREAM),
    ]


@pytest.mark.parametrize(
    ("location", "error_code"),
    [
        ("https://public.example/a\x00b", "invalid_url"),
        ("https://public.example/café", "unsupported_url_iri"),
        ("https://@public.example/article", "unsupported_url_credentials"),
        ("https://[2001:db8::1", "invalid_url"),
    ],
)
def test_redirect_location_uses_same_ascii_uri_policy(
    hub_api,
    monkeypatch,
    location,
    error_code,
):
    def fake_getaddrinfo(host, port, type):
        assert host == "public.example"
        return [address_info("8.8.8.8", port)]

    class RedirectOpener:
        def open(self, request, timeout):
            raise hub_api.HTTPError(
                request.full_url,
                302,
                "Found",
                {"Location": location},
                None,
            )

    monkeypatch.setattr(hub_api.socket, "getaddrinfo", fake_getaddrinfo)
    monkeypatch.setattr(
        hub_api,
        "build_pinned_opener",
        lambda pinned_ips, deadline: RedirectOpener(),
    )

    with pytest.raises(hub_api.IntakeError) as caught:
        hub_api.fetch_url_text("https://public.example/article")

    assert caught.value.status == 400
    assert caught.value.code == error_code


@pytest.mark.parametrize(
    "url",
    [
        "http://[64:ff9b::10.0.0.1]/",
        "http://[64:ff9b::127.0.0.1]/",
        "http://[64:ff9b::169.254.169.254]/",
        "http://[::ffff:10.0.0.1]/",
        "http://[::10.0.0.1]/",
        "http://[::ffff:0:10.0.0.1]/",
        "http://[2002:0a00:0001::]/",
        "http://[2001:4860::0200:5efe:0a00:0001]/",
    ],
)
def test_ipv6_transition_addresses_cannot_hide_non_global_ipv4(
    hub_api,
    url,
):
    with pytest.raises(hub_api.IntakeError) as caught:
        hub_api.validate_intake_url(url)

    assert caught.value.status == 400
    assert caught.value.code == "blocked_url_host"


@pytest.mark.parametrize(
    "url",
    [
        "http://[64:ff9b::8.8.8.8]/",
        "http://[::8.8.8.8]/",
        "http://[::ffff:8.8.8.8]/",
        "http://[::ffff:0:8.8.8.8]/",
    ],
)
def test_ipv6_transition_addresses_with_public_embedded_ipv4_remain_public(
    hub_api,
    url,
):
    validated = hub_api.validate_intake_url(url)

    assert len(validated.resolved_ips) == 1


def test_pinned_ip_fallbacks_share_one_total_deadline(
    hub_api,
    monkeypatch,
):
    clock = [100.0]
    attempts = []

    monkeypatch.setattr(hub_api.time, "monotonic", lambda: clock[0])

    class TimedOutSocket:
        def __init__(self, family, socket_type, protocol):
            self.timeout = None

        def settimeout(self, timeout):
            self.timeout = timeout

        def bind(self, source_address):
            raise AssertionError(f"unexpected source bind: {source_address}")

        def connect(self, address):
            attempts.append((address, self.timeout, None))
            clock[0] += self.timeout
            raise TimeoutError("simulated connection timeout")

        def close(self):
            return None

    monkeypatch.setattr(hub_api.socket, "socket", TimedOutSocket)

    deadline = hub_api.FetchDeadline.start(8)
    with pytest.raises(hub_api.FetchDeadlineExceeded):
        hub_api.create_pinned_connection(
            ("public.example", 443),
            8,
            None,
            ("8.8.8.8", "9.9.9.9", "1.1.1.1"),
            deadline,
        )

    assert [attempt[0] for attempt in attempts] == [
        ("8.8.8.8", 443),
        ("9.9.9.9", 443),
        ("1.1.1.1", 443),
    ]
    assert [attempt[1] for attempt in attempts] == pytest.approx(
        [8 / 3, 8 / 3, 8 / 3]
    )


def test_stalled_first_ip_preserves_time_for_working_later_ip(
    hub_api,
    monkeypatch,
):
    clock = [100.0]
    attempts = []

    monkeypatch.setattr(hub_api.time, "monotonic", lambda: clock[0])

    class FirstAddressStalls:
        def __init__(self, family, socket_type, protocol):
            self.family = family
            self.timeout = None
            self.peer = None

        def settimeout(self, timeout):
            self.timeout = timeout

        def bind(self, source_address):
            raise AssertionError(f"unexpected source bind: {source_address}")

        def connect(self, address):
            attempts.append((address, self.timeout))
            if self.family == socket.AF_INET:
                clock[0] += self.timeout
                raise TimeoutError("simulated IPv4 black hole")
            self.peer = address

        def getpeername(self):
            return self.peer

        def close(self):
            return None

    monkeypatch.setattr(hub_api.socket, "socket", FirstAddressStalls)

    deadline = hub_api.FetchDeadline.start(8)
    connection = hub_api.create_pinned_connection(
        ("public.example", 443),
        8,
        None,
        ("8.8.8.8", "2001:4860:4860::8888"),
        deadline,
    )

    assert isinstance(connection, FirstAddressStalls)
    assert [attempt[0] for attempt in attempts] == [
        ("8.8.8.8", 443),
        ("2001:4860:4860::8888", 443, 0, 0),
    ]
    assert [attempt[1] for attempt in attempts] == pytest.approx([4, 4])


def test_redirect_hops_share_one_total_deadline(
    hub_api,
    monkeypatch,
):
    clock = [100.0]
    request_timeouts = []

    monkeypatch.setattr(hub_api.time, "monotonic", lambda: clock[0])

    def fake_getaddrinfo(host, port, type):
        assert host == "public.example"
        return [address_info("8.8.8.8", port)]

    class SlowRedirectOpener:
        def open(self, request, timeout):
            request_timeouts.append(timeout)
            clock[0] += 3
            raise hub_api.HTTPError(
                request.full_url,
                302,
                "Found",
                {"Location": request.full_url},
                None,
            )

    monkeypatch.setattr(hub_api.socket, "getaddrinfo", fake_getaddrinfo)
    monkeypatch.setattr(
        hub_api,
        "build_pinned_opener",
        lambda pinned_ips, deadline: SlowRedirectOpener(),
    )

    with pytest.raises(hub_api.FetchDeadlineExceeded):
        hub_api.fetch_url_text("https://public.example/article")

    assert request_timeouts == [8, 5, 2]


def test_main_thread_alarm_interrupts_python_level_blocking_dns_probe(
    hub_api,
    monkeypatch,
):
    previous_handler = hub_api.signal.getsignal(hub_api.signal.SIGALRM)
    previous_timer = hub_api.signal.getitimer(hub_api.signal.ITIMER_REAL)
    monkeypatch.setattr(hub_api, "URL_TIMEOUT_SECONDS", 0.02)

    def blocking_getaddrinfo(host, port, type):
        time.sleep(1)
        raise AssertionError("SIGALRM should interrupt this Python-level probe")

    monkeypatch.setattr(
        hub_api.socket,
        "getaddrinfo",
        blocking_getaddrinfo,
    )

    started_at = time.monotonic()
    with pytest.raises(hub_api.FetchDeadlineExceeded):
        hub_api.fetch_url_text("https://public.example/article")
    elapsed = time.monotonic() - started_at

    assert elapsed < 0.5
    assert hub_api.signal.getsignal(hub_api.signal.SIGALRM) == previous_handler
    assert hub_api.signal.getitimer(hub_api.signal.ITIMER_REAL) == previous_timer


def test_deadline_enforcement_off_main_thread_fails_cleanly(hub_api):
    failures = []

    def run_fetch():
        try:
            hub_api.fetch_url_text("https://public.example/article")
        except Exception as exc:
            failures.append(exc)

    worker = threading.Thread(target=run_fetch)
    worker.start()
    worker.join(timeout=2)

    assert not worker.is_alive()
    assert len(failures) == 1
    assert isinstance(failures[0], hub_api.IntakeError)
    assert failures[0].status == 503
    assert failures[0].code == "url_fetch_unavailable"


def test_total_deadline_closes_a_slow_response(
    hub_api,
    monkeypatch,
):
    response_exit_types = []
    monkeypatch.setattr(hub_api, "URL_TIMEOUT_SECONDS", 0.02)

    def fake_getaddrinfo(host, port, type):
        return [address_info("8.8.8.8", port)]

    class SlowResponse:
        headers = {"Content-Type": "text/plain"}

        def getcode(self):
            return 200

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            response_exit_types.append(exc_type)
            return False

        def read(self, limit):
            time.sleep(1)
            raise AssertionError("SIGALRM should interrupt response reading")

    class SlowOpener:
        def open(self, request, timeout):
            return SlowResponse()

    monkeypatch.setattr(hub_api.socket, "getaddrinfo", fake_getaddrinfo)
    monkeypatch.setattr(
        hub_api,
        "build_pinned_opener",
        lambda pinned_ips, deadline: SlowOpener(),
    )

    with pytest.raises(hub_api.FetchDeadlineExceeded):
        hub_api.fetch_url_text("https://public.example/article")

    assert response_exit_types == [hub_api.FetchDeadlineExceeded]
