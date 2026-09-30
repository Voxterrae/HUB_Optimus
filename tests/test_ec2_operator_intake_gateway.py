import importlib.util
import io
import json
import socket
import sys
import threading
from email.message import Message
from pathlib import Path

import jsonschema
import pytest


ROOT = Path(__file__).resolve().parents[1]
GATEWAY_PATH = ROOT / "ops" / "ec2" / "operator-intake-gateway.py"
SERVICE_PATH = ROOT / "ops" / "ec2" / "operator-intake-gateway.service"
SCHEMA_PATH = ROOT / "ops" / "ec2" / "operator_public_intake.v1.schema.json"
TEST_CAPABILITY = "A" * 43
OTHER_CAPABILITY = "B" * 43
TEST_NGINX_REQUEST_ID = "0123456789abcdef0123456789abcdef"
TEST_REQUEST_ID = f"req_{TEST_NGINX_REQUEST_ID}"


@pytest.fixture(scope="module")
def gateway():
    spec = importlib.util.spec_from_file_location("operator_intake_gateway_test", GATEWAY_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    yield module
    sys.modules.pop(spec.name, None)


def trusted_headers(
    gateway,
    *,
    capability=TEST_CAPABILITY,
    origin="https://api.huboptimus.dev",
    subject="opaque-subject-0001",
    roles="HUB.Operator",
    client_ip="198.51.100.40",
    request_id=TEST_NGINX_REQUEST_ID,
    extras=(),
):
    headers = Message()
    headers.add_header(gateway.CAPABILITY_HEADER, capability)
    headers.add_header("Origin", origin)
    headers.add_header(gateway.SUBJECT_HEADER, subject)
    headers.add_header(gateway.ROLES_HEADER, roles)
    headers.add_header(gateway.CLIENT_IP_HEADER, client_ip)
    if request_id is not None:
        headers.add_header(gateway.CORRELATION_HEADER, request_id)
    headers.add_header("Content-Type", "application/json")
    for name, value in extras:
        headers.add_header(name, value)
    return headers


def valid_intake_payload():
    return {
        "status": "ok",
        "intake_type": "controlled_url",
        "url": "https://example.com/article",
        "final_url": "https://example.com/article",
        "source_domain": "example.com",
        "retrieved_at_utc": "2026-08-02T00:00:00+00:00",
        "title": "Example",
        "text": "Exact source text.",
        "content_type": "text/html; charset=utf-8",
        "bytes_read": 512,
        "truncated": False,
        "redirects": [],
        "verification_status": "unreviewed",
        "learning_status": "candidate-source-not-verified",
        "extraction_notes": ["Fetched by local backend controlled URL intake."],
    }


class FakeResponse:
    def __init__(self, status, payload, *, headers=None, raw=None):
        self.status = status
        self.raw = raw if raw is not None else json.dumps(payload).encode("utf-8")
        self.headers = headers or [
            ("Content-Type", "application/json; charset=utf-8"),
            ("Content-Length", str(len(self.raw))),
        ]

    def getheaders(self):
        return list(self.headers)

    def read(self, length):
        return self.raw[:length]


class FakeConnection:
    def __init__(self, response):
        self.response = response
        self.requests = []
        self.closed = False

    def request(self, method, path, *, body, headers):
        self.requests.append((method, path, body, dict(headers)))

    def getresponse(self):
        if isinstance(self.response, BaseException):
            raise self.response
        return self.response

    def close(self):
        self.closed = True


def make_upstream(gateway, response):
    created = []

    def factory(host, port, *, timeout):
        connection = FakeConnection(response)
        created.append((host, port, timeout, connection))
        return connection

    return gateway.UpstreamClient(factory), created


def assert_gateway_error(gateway, exc_info, status, code):
    assert isinstance(exc_info.value, gateway.GatewayError)
    assert exc_info.value.status == status
    assert exc_info.value.code == code


def test_gateway_has_fixed_loopback_bind_and_upstream(gateway):
    assert (gateway.BIND_HOST, gateway.BIND_PORT) == ("127.0.0.1", 8081)
    assert gateway.GatewayHTTPServer.address_family == socket.AF_INET
    assert gateway.GatewayHTTPServer.allow_reuse_address is False
    assert gateway.PUBLIC_PATH == "/intake/url"
    assert (gateway.UPSTREAM_HOST, gateway.UPSTREAM_PORT, gateway.UPSTREAM_PATH) == (
        "127.0.0.1",
        8080,
        "/intake/url",
    )
    with pytest.raises(gateway.ConfigurationError):
        gateway.GatewayHTTPServer(
            ("0.0.0.0", 8081),
            gateway.Handler,
            gateway.GatewayApplication(TEST_CAPABILITY),
        )


def test_only_exact_post_path_is_routed(gateway):
    assert gateway.Handler.do_DELETE is gateway.Handler._reject_method
    assert gateway.Handler.do_CONNECT is gateway.Handler._reject_method
    assert gateway.Handler.do_GET is gateway.Handler._reject_method
    assert gateway.Handler.do_HEAD is gateway.Handler._reject_method
    assert gateway.Handler.do_OPTIONS is gateway.Handler._reject_method
    assert gateway.Handler.do_PATCH is gateway.Handler._reject_method
    assert gateway.Handler.do_PUT is gateway.Handler._reject_method
    assert gateway.Handler.do_TRACE is gateway.Handler._reject_method

    handler = object.__new__(gateway.Handler)
    handler.path = "/intake/url?url=https://attacker.invalid"
    sent = []
    handler._send_error = lambda request_id, error: sent.append(error)
    handler.do_POST()
    assert [(error.status, error.code) for error in sent] == [(404, "not_found")]


@pytest.mark.parametrize(
    "value",
    [None, "", "   ", "line\nbreak", "A" * 42, "A" * 129, ("A" * 42) + "+"],
)
def test_capability_environment_requires_bounded_base64url(gateway, value):
    env = {} if value is None else {gateway.CAPABILITY_ENV: value}
    with pytest.raises(gateway.ConfigurationError):
        gateway.load_application(env)

    application = gateway.load_application({gateway.CAPABILITY_ENV: TEST_CAPABILITY})
    assert application.capability == TEST_CAPABILITY


def test_capability_is_constant_time_checked_and_never_optional(gateway):
    headers = trusted_headers(gateway, capability=OTHER_CAPABILITY)
    with pytest.raises(gateway.GatewayError) as exc_info:
        gateway.authenticate_request(headers, TEST_CAPABILITY)
    assert_gateway_error(gateway, exc_info, 401, "unauthorized")

    headers.replace_header(gateway.CAPABILITY_HEADER, TEST_CAPABILITY)
    identity = gateway.authenticate_request(headers, TEST_CAPABILITY)
    assert identity.subject == "opaque-subject-0001"


def test_nginx_request_id_is_strictly_correlated_with_public_request_id(gateway):
    headers = trusted_headers(gateway)
    assert gateway.correlated_request_id(headers) == TEST_REQUEST_ID

    malformed_headers = [
        trusted_headers(gateway, request_id=None),
        trusted_headers(gateway, request_id="req_" + TEST_NGINX_REQUEST_ID),
        trusted_headers(gateway, request_id=TEST_NGINX_REQUEST_ID.upper()),
        trusted_headers(
            gateway,
            extras=((gateway.CORRELATION_HEADER, "f" * 32),),
        ),
    ]
    for candidate in malformed_headers:
        with pytest.raises(gateway.GatewayError) as exc_info:
            gateway.correlated_request_id(candidate)
        assert_gateway_error(gateway, exc_info, 400, "invalid_framing")


@pytest.mark.parametrize(
    "origin",
    [
        "https://huboptimus.dev",
        "https://api.huboptimus.dev/",
        "HTTPS://api.huboptimus.dev",
        "https://api.huboptimus.dev.attacker.invalid",
    ],
)
def test_origin_must_match_api_origin_exactly(gateway, origin):
    headers = trusted_headers(gateway, origin=origin)
    with pytest.raises(gateway.GatewayError) as exc_info:
        gateway.authenticate_request(headers, TEST_CAPABILITY)
    assert_gateway_error(gateway, exc_info, 403, "origin_forbidden")


@pytest.mark.parametrize(
    ("subject", "roles", "status", "code"),
    [
        ("person@example.com", "HUB.Operator", 401, "unauthorized"),
        ("short", "HUB.Operator", 401, "unauthorized"),
        ("opaque-subject-0001", "Reader", 403, "forbidden"),
        ("opaque-subject-0001", "HUB.Owner\nReader", 403, "forbidden"),
        ("opaque-subject-0001", "", 403, "forbidden"),
    ],
)
def test_subject_is_opaque_and_owner_operator_roles_are_required(
    gateway,
    subject,
    roles,
    status,
    code,
):
    headers = trusted_headers(gateway, subject=subject, roles=roles)
    with pytest.raises(gateway.GatewayError) as exc_info:
        gateway.authenticate_request(headers, TEST_CAPABILITY)
    assert_gateway_error(gateway, exc_info, status, code)


def test_owner_or_operator_can_coexist_with_other_sanitized_roles(gateway):
    for roles in ("HUB.Owner", "HUB.Operator", "Reader,HUB.Owner"):
        headers = trusted_headers(gateway, roles=roles)
        identity = gateway.authenticate_request(headers, TEST_CAPABILITY)
        assert identity.roles.intersection(gateway.AUTHORIZED_ROLES)


@pytest.mark.parametrize(
    "spoof_header",
    [
        "Authorization",
        "Cookie",
        "Forwarded",
        "Remote-User",
        "X-Auth-Request-User",
        "X-Forwarded-For",
        "X-MS-CLIENT-PRINCIPAL-NAME",
        "X-Real-IP",
    ],
)
def test_untrusted_client_identity_and_forwarding_headers_are_rejected(
    gateway,
    spoof_header,
):
    headers = trusted_headers(gateway, extras=((spoof_header, "spoofed-value"),))
    with pytest.raises(gateway.GatewayError) as exc_info:
        gateway.authenticate_request(headers, TEST_CAPABILITY)
    assert_gateway_error(gateway, exc_info, 400, "untrusted_headers")


def test_duplicate_trusted_headers_and_non_numeric_client_ip_are_rejected(gateway):
    headers = trusted_headers(
        gateway,
        extras=((gateway.SUBJECT_HEADER, "other-opaque-subject"),),
    )
    with pytest.raises(gateway.GatewayError) as exc_info:
        gateway.authenticate_request(headers, TEST_CAPABILITY)
    assert_gateway_error(gateway, exc_info, 401, "unauthorized")

    headers = trusted_headers(gateway, client_ip="198.51.100.10, 203.0.113.5")
    with pytest.raises(gateway.GatewayError) as exc_info:
        gateway.authenticate_request(headers, TEST_CAPABILITY)
    assert_gateway_error(gateway, exc_info, 400, "invalid_client_ip")


def test_ipv4_mapped_client_address_cannot_bypass_ip_rate_key(gateway):
    plain = gateway.authenticate_request(
        trusted_headers(gateway, client_ip="198.51.100.40"),
        TEST_CAPABILITY,
    )
    mapped = gateway.authenticate_request(
        trusted_headers(gateway, client_ip="::ffff:198.51.100.40"),
        TEST_CAPABILITY,
    )
    assert plain.client_ip == mapped.client_ip == "198.51.100.40"


def make_body_handler(gateway, body, *, lengths=None, content_type="application/json", extras=()):
    handler = object.__new__(gateway.Handler)
    handler.headers = Message()
    for length in lengths if lengths is not None else [str(len(body))]:
        handler.headers.add_header("Content-Length", length)
    if content_type is not None:
        handler.headers.add_header("Content-Type", content_type)
    for name, value in extras:
        handler.headers.add_header(name, value)
    handler.rfile = io.BytesIO(body)
    return handler


@pytest.mark.parametrize(
    ("lengths", "extras", "status", "code"),
    [
        ([], (), 411, "length_required"),
        (["2", "2"], (), 400, "invalid_framing"),
        (["+2"], (), 400, "invalid_framing"),
        (["2"], (("Transfer-Encoding", "chunked"),), 400, "invalid_framing"),
        (["2"], (("Content-Encoding", "gzip"),), 400, "invalid_framing"),
        (["2"], (("Expect", "100-continue"),), 400, "invalid_framing"),
        (["4097"], (), 413, "request_too_large"),
    ],
)
def test_request_body_has_exact_bounded_framing(gateway, lengths, extras, status, code):
    handler = make_body_handler(gateway, b"{}", lengths=lengths, extras=extras)
    with pytest.raises(gateway.GatewayError) as exc_info:
        handler._read_request_body()
    assert_gateway_error(gateway, exc_info, status, code)


def test_request_body_rejects_short_body_and_non_json_media_type(gateway):
    handler = make_body_handler(gateway, b"{}", lengths=["3"])
    with pytest.raises(gateway.GatewayError) as exc_info:
        handler._read_request_body()
    assert_gateway_error(gateway, exc_info, 400, "invalid_framing")

    handler = make_body_handler(gateway, b"{}", content_type="text/plain")
    with pytest.raises(gateway.GatewayError) as exc_info:
        handler._read_request_body()
    assert_gateway_error(gateway, exc_info, 415, "unsupported_media_type")


@pytest.mark.parametrize(
    "raw",
    [
        b"[]",
        b'{"url":"https://example.com","extra":true}',
        b'{"url":"https://one.example","url":"https://two.example"}',
        b'{"url":NaN}',
        b'{"url":"\\ud800"}',
        b'{"url":""}',
    ],
)
def test_request_json_is_strict_and_contains_only_url(gateway, raw):
    with pytest.raises(gateway.GatewayError) as exc_info:
        gateway.canonicalize_request_body(raw)
    assert exc_info.value.status in {400, 413}
    assert exc_info.value.code in {"invalid_request", "request_too_large"}


def test_rate_limit_is_atomic_per_subject_and_per_ip(gateway):
    now = [100.0]
    limiter = gateway.SlidingWindowRateLimiter(
        limit=2,
        window_seconds=60,
        clock=lambda: now[0],
    )
    limiter.consume("subject-a", "198.51.100.1")
    limiter.consume("subject-a", "198.51.100.2")
    with pytest.raises(gateway.GatewayError) as exc_info:
        limiter.consume("subject-a", "198.51.100.3")
    assert_gateway_error(gateway, exc_info, 429, "rate_limited")

    limiter.consume("subject-b", "198.51.100.9")
    limiter.consume("subject-c", "198.51.100.9")
    with pytest.raises(gateway.GatewayError) as exc_info:
        limiter.consume("subject-d", "198.51.100.9")
    assert_gateway_error(gateway, exc_info, 429, "rate_limited")

    now[0] = 161.0
    limiter.consume("subject-a", "198.51.100.9")


def test_default_rate_limit_is_exactly_twelve_per_minute(gateway):
    assert gateway.RATE_LIMIT_REQUESTS == 12
    assert gateway.RATE_LIMIT_WINDOW_SECONDS == 60.0
    assert gateway.MAX_RATE_LIMIT_SUBJECT_KEYS == 4096
    assert gateway.MAX_RATE_LIMIT_IP_KEYS == 4096


def test_rate_limit_key_maps_are_bounded_and_expired_keys_are_removed(gateway):
    now = [100.0]
    limiter = gateway.SlidingWindowRateLimiter(
        limit=12,
        window_seconds=60,
        max_subject_keys=2,
        max_ip_keys=2,
        clock=lambda: now[0],
    )
    limiter.consume("subject-a", "198.51.100.1")
    limiter.consume("subject-b", "198.51.100.2")

    for index in range(25):
        with pytest.raises(gateway.GatewayError) as exc_info:
            limiter.consume(f"new-subject-{index}", f"203.0.113.{index + 1}")
        assert_gateway_error(gateway, exc_info, 429, "rate_limited")
    assert len(limiter._subject_events) == 2
    assert len(limiter._ip_events) == 2

    now[0] = 161.0
    limiter.consume("subject-c", "198.51.100.3")
    assert list(limiter._subject_events) == ["subject-c"]
    assert list(limiter._ip_events) == ["198.51.100.3"]


def test_subject_and_global_upstream_concurrency_are_nonblocking(gateway):
    limits = gateway.ConcurrencyLimits()
    limits.acquire_subject("opaque-subject-0001")
    with pytest.raises(gateway.GatewayError) as exc_info:
        limits.acquire_subject("opaque-subject-0001")
    assert_gateway_error(gateway, exc_info, 429, "subject_busy")

    limits.acquire_upstream()
    with pytest.raises(gateway.GatewayError) as exc_info:
        limits.acquire_upstream()
    assert_gateway_error(gateway, exc_info, 503, "upstream_busy")
    limits.release_upstream()
    limits.release_subject("opaque-subject-0001")


def test_app_enforces_subject_and_global_concurrency_while_upstream_blocks(gateway):
    started = threading.Event()
    release = threading.Event()

    class BlockingUpstream:
        def request(self, body, *, request_id):
            assert request_id == TEST_REQUEST_ID
            started.set()
            assert release.wait(timeout=2)
            return gateway.UpstreamResult(200, valid_intake_payload(), True)

    app = gateway.GatewayApplication(
        TEST_CAPABILITY,
        upstream=BlockingUpstream(),
    )
    raw = b'{"url":"https://example.com/article"}'
    result = []
    thread = threading.Thread(
        target=lambda: result.append(app.process(trusted_headers(gateway), raw)),
        daemon=True,
    )
    thread.start()
    assert started.wait(timeout=1)

    with pytest.raises(gateway.GatewayError) as exc_info:
        app.process(trusted_headers(gateway), raw)
    assert_gateway_error(gateway, exc_info, 429, "subject_busy")

    with pytest.raises(gateway.GatewayError) as exc_info:
        app.process(
            trusted_headers(
                gateway,
                subject="opaque-subject-0002",
                client_ip="198.51.100.41",
            ),
            raw,
        )
    assert_gateway_error(gateway, exc_info, 503, "upstream_busy")
    release.set()
    thread.join(timeout=2)
    assert len(result) == 1


def test_upstream_target_method_path_headers_and_body_are_fixed(gateway):
    upstream, created = make_upstream(gateway, FakeResponse(200, valid_intake_payload()))
    supplied = b'{"url": "https://example.com/article"}'
    result = upstream.request(supplied, request_id=TEST_REQUEST_ID)

    assert result.is_success is True
    assert len(created) == 1
    host, port, timeout, connection = created[0]
    assert (host, port, timeout) == ("127.0.0.1", 8080, 12.0)
    assert connection.closed is True
    assert connection.requests == [
        (
            "POST",
            "/intake/url",
            supplied,
            {
                "Accept": "application/json",
                "Connection": "close",
                "Content-Type": "application/json",
                "X-Request-ID": TEST_REQUEST_ID,
            },
        )
    ]


def test_application_propagates_the_trusted_nginx_correlation_id(gateway):
    upstream, created = make_upstream(gateway, FakeResponse(200, valid_intake_payload()))
    application = gateway.GatewayApplication(TEST_CAPABILITY, upstream=upstream)

    result = application.process(
        trusted_headers(gateway),
        b'{"url":"https://example.com/article"}',
    )

    assert result.is_success is True
    assert len(created) == 1
    assert created[0][3].requests[0][3][gateway.CORRELATION_HEADER] == TEST_REQUEST_ID


def test_invalid_internal_correlation_id_never_reaches_upstream(gateway):
    upstream, created = make_upstream(gateway, FakeResponse(200, valid_intake_payload()))
    with pytest.raises(gateway.GatewayError) as exc_info:
        upstream.request(
            b'{"url":"https://example.com/article"}',
            request_id=TEST_NGINX_REQUEST_ID,
        )
    assert_gateway_error(gateway, exc_info, 500, "internal_error")
    assert created == []


@pytest.mark.parametrize(
    "attack",
    [
        "different_original_url",
        "unreported_redirect",
        "redirect_starts_at_other_url",
        "redirect_chain_is_discontinuous",
        "final_url_is_not_redirect_tail",
        "source_domain_is_not_final_hostname",
    ],
)
def test_success_response_is_exactly_bound_to_requested_url_and_provenance(
    gateway,
    attack,
):
    requested_url = "https://example.com/article"
    payload = valid_intake_payload()

    if attack == "different_original_url":
        payload.update(
            {
                "url": "https://other.example/article",
                "final_url": "https://other.example/article",
                "source_domain": "other.example",
                "text": "Content fetched for URL B.",
            }
        )
    elif attack == "unreported_redirect":
        payload.update(
            {
                "final_url": "https://other.example/article",
                "source_domain": "other.example",
                "text": "Content fetched for URL B.",
            }
        )
    elif attack == "redirect_starts_at_other_url":
        payload.update(
            {
                "final_url": "https://final.example/article",
                "source_domain": "final.example",
                "redirects": [
                    {
                        "from": "https://other.example/article",
                        "to": "https://final.example/article",
                        "status": 302,
                    }
                ],
            }
        )
    elif attack == "redirect_chain_is_discontinuous":
        payload.update(
            {
                "final_url": "https://final.example/article",
                "source_domain": "final.example",
                "redirects": [
                    {
                        "from": requested_url,
                        "to": "https://middle.example/article",
                        "status": 301,
                    },
                    {
                        "from": "https://unrelated.example/article",
                        "to": "https://final.example/article",
                        "status": 308,
                    },
                ],
            }
        )
    elif attack == "final_url_is_not_redirect_tail":
        payload.update(
            {
                "final_url": "https://final.example/article",
                "source_domain": "final.example",
                "redirects": [
                    {
                        "from": requested_url,
                        "to": "https://middle.example/article",
                        "status": 307,
                    }
                ],
            }
        )
    elif attack == "source_domain_is_not_final_hostname":
        payload["source_domain"] = "other.example"

    upstream, _ = make_upstream(gateway, FakeResponse(200, payload))
    with pytest.raises(gateway.GatewayError) as exc_info:
        upstream.request(
            json.dumps({"url": requested_url}).encode("utf-8"),
            request_id=TEST_REQUEST_ID,
        )
    assert_gateway_error(gateway, exc_info, 502, "upstream_malformed")


def test_contiguous_redirect_provenance_for_requested_url_is_accepted(gateway):
    requested_url = "https://example.com/article"
    payload = valid_intake_payload()
    payload.update(
        {
            "final_url": "https://final.example/article",
            "source_domain": "final.example",
            "redirects": [
                {
                    "from": requested_url,
                    "to": "https://middle.example/article",
                    "status": 302,
                },
                {
                    "from": "https://middle.example/article",
                    "to": "https://final.example/article",
                    "status": 308,
                },
            ],
        }
    )
    upstream, _ = make_upstream(gateway, FakeResponse(200, payload))

    result = upstream.request(
        json.dumps({"url": requested_url}).encode("utf-8"),
        request_id=TEST_REQUEST_ID,
    )

    assert result == gateway.UpstreamResult(200, payload, True)


@pytest.mark.parametrize(
    "response",
    [
        FakeResponse(200, []),
        FakeResponse(200, {"status": "ok"}),
        FakeResponse(201, valid_intake_payload()),
        FakeResponse(400, {"status": "error", "error": "unknown", "message": "x"}),
        FakeResponse(
            200,
            valid_intake_payload(),
            headers=[
                ("Content-Type", "application/json"),
                ("Content-Length", "2"),
                ("Content-Length", "2"),
            ],
        ),
        FakeResponse(
            200,
            valid_intake_payload(),
            headers=[
                ("Content-Type", "application/json"),
                ("Transfer-Encoding", "chunked"),
            ],
        ),
        FakeResponse(200, None, raw=b"not json"),
    ],
)
def test_malformed_upstream_responses_fail_closed(gateway, response):
    upstream, _ = make_upstream(gateway, response)
    with pytest.raises(gateway.GatewayError) as exc_info:
        upstream.request(
            b'{"url":"https://example.com"}',
            request_id=TEST_REQUEST_ID,
        )
    assert_gateway_error(gateway, exc_info, 502, "upstream_malformed")


def test_malformed_redirect_record_is_rejected(gateway):
    payload = valid_intake_payload()
    payload["redirects"] = [
        {
            "from": "https://example.com/one",
            "to": "https://example.com/two",
            "status": True,
        }
    ]
    upstream, _ = make_upstream(gateway, FakeResponse(200, payload))
    with pytest.raises(gateway.GatewayError) as exc_info:
        upstream.request(
            b'{"url":"https://example.com"}',
            request_id=TEST_REQUEST_ID,
        )
    assert_gateway_error(gateway, exc_info, 502, "upstream_malformed")


def test_invalid_timestamp_and_incomplete_local_error_are_rejected(gateway):
    payload = valid_intake_payload()
    payload["retrieved_at_utc"] = "not-a-date"
    upstream, _ = make_upstream(gateway, FakeResponse(200, payload))
    with pytest.raises(gateway.GatewayError) as exc_info:
        upstream.request(
            b'{"url":"https://example.com"}',
            request_id=TEST_REQUEST_ID,
        )
    assert_gateway_error(gateway, exc_info, 502, "upstream_malformed")

    upstream, _ = make_upstream(
        gateway,
        FakeResponse(
            400,
            {
                "status": "error",
                "error": "invalid_url",
                "message": "URL is required.",
            },
        ),
    )
    with pytest.raises(gateway.GatewayError) as exc_info:
        upstream.request(
            b'{"url":"https://example.com"}',
            request_id=TEST_REQUEST_ID,
        )
    assert_gateway_error(gateway, exc_info, 502, "upstream_malformed")


def test_upstream_response_size_is_bounded_before_read(gateway):
    response = FakeResponse(
        200,
        valid_intake_payload(),
        headers=[
            ("Content-Type", "application/json"),
            ("Content-Length", str(gateway.MAX_UPSTREAM_RESPONSE_BYTES + 1)),
        ],
    )
    upstream, _ = make_upstream(gateway, response)
    with pytest.raises(gateway.GatewayError) as exc_info:
        upstream.request(
            b'{"url":"https://example.com"}',
            request_id=TEST_REQUEST_ID,
        )
    assert_gateway_error(gateway, exc_info, 502, "upstream_response_too_large")


def test_upstream_timeout_and_connection_failures_are_controlled(gateway):
    upstream, _ = make_upstream(gateway, socket.timeout("secret URL must not escape"))
    with pytest.raises(gateway.GatewayError) as exc_info:
        upstream.request(
            b'{"url":"https://secret.example/path"}',
            request_id=TEST_REQUEST_ID,
        )
    assert_gateway_error(gateway, exc_info, 504, "upstream_timeout")
    assert "secret" not in exc_info.value.message

    def failed_factory(host, port, *, timeout):
        raise ConnectionRefusedError("local connection refused")

    upstream = gateway.UpstreamClient(failed_factory)
    with pytest.raises(gateway.GatewayError) as exc_info:
        upstream.request(
            b'{"url":"https://secret.example/path"}',
            request_id=TEST_REQUEST_ID,
        )
    assert_gateway_error(gateway, exc_info, 502, "upstream_unavailable")


def test_valid_upstream_application_error_drops_echoed_url(gateway):
    payload = {
        "status": "error",
        "error": "invalid_url",
        "message": "URL is required.",
        "url": "https://secret.example/private",
        "verification_status": "unreviewed",
    }
    upstream, _ = make_upstream(gateway, FakeResponse(400, payload))
    result = upstream.request(
        b'{"url":"https://secret.example/private"}',
        request_id=TEST_REQUEST_ID,
    )
    assert result == gateway.UpstreamResult(
        status=400,
        payload={"code": "invalid_url", "message": "URL is required."},
        is_success=False,
    )
    assert "secret.example" not in json.dumps(result.payload)


def test_upstream_application_error_for_another_url_is_rejected(gateway):
    payload = {
        "status": "error",
        "error": "invalid_url",
        "message": "URL is required.",
        "url": "https://other.example/private",
        "verification_status": "unreviewed",
    }
    upstream, _ = make_upstream(gateway, FakeResponse(400, payload))

    with pytest.raises(gateway.GatewayError) as exc_info:
        upstream.request(
            b'{"url":"https://secret.example/private"}',
            request_id=TEST_REQUEST_ID,
        )
    assert_gateway_error(gateway, exc_info, 502, "upstream_malformed")


def test_public_schema_envelopes_are_versioned_and_request_id_is_non_sensitive(gateway):
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator.check_schema(schema)
    validator = jsonschema.Draft202012Validator(
        schema,
        format_checker=jsonschema.FormatChecker(),
    )
    request_id = gateway.new_request_id()
    assert gateway.REQUEST_ID_PATTERN.fullmatch(request_id)
    assert "subject" not in request_id
    assert "example" not in request_id

    success = gateway.success_envelope(request_id, valid_intake_payload())
    error = gateway.error_envelope(request_id, "unauthorized", "Authentication is required.")
    validator.validate({"url": "https://example.com/article"})
    validator.validate(success)
    validator.validate(error)
    assert success["schema_version"] == "operator_public_intake.v1"
    assert error["request_id"] == request_id
    assert set(error) == {"schema_version", "request_id", "status", "error"}


def test_schema_runtime_limits_and_error_codes_match_implementation(gateway):
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    boundary = schema["x-hub-optimus-runtime-boundary"]
    assert boundary == {
        "bind_host": gateway.BIND_HOST,
        "bind_port": gateway.BIND_PORT,
        "endpoint": gateway.PUBLIC_PATH,
        "method": "POST",
        "origin": gateway.EXPECTED_ORIGIN,
        "correlation_header": gateway.CORRELATION_HEADER,
        "correlation_input_pattern": "^[0-9a-f]{32}$",
        "public_request_id_prefix": "req_",
        "upstream_correlation_header": gateway.CORRELATION_HEADER,
        "request_body_bytes": gateway.MAX_REQUEST_BODY_BYTES,
        "capability_format": "base64url",
        "capability_min_characters": 43,
        "capability_max_characters": 128,
        "requests_per_minute_per_subject": gateway.RATE_LIMIT_REQUESTS,
        "requests_per_minute_per_ip": gateway.RATE_LIMIT_REQUESTS,
        "maximum_rate_limit_subject_keys": gateway.MAX_RATE_LIMIT_SUBJECT_KEYS,
        "maximum_rate_limit_ip_keys": gateway.MAX_RATE_LIMIT_IP_KEYS,
        "concurrent_requests_per_subject": 1,
        "concurrent_upstream_requests": 1,
        "upstream": "http://127.0.0.1:8080/intake/url",
        "upstream_timeout_seconds": gateway.UPSTREAM_TIMEOUT_SECONDS,
        "upstream_response_bytes": gateway.MAX_UPSTREAM_RESPONSE_BYTES,
        "success_url_binding": (
            "intake.url equals request.url exactly; redirects form one contiguous "
            "chain from request.url to final_url; source_domain equals the final_url hostname"
        ),
        "authorized_roles": ["HUB.Owner", "HUB.Operator"],
    }
    assert schema["x-hub-optimus-upstream-error-http-status"] == gateway.UPSTREAM_ERROR_STATUS
    assert schema["x-hub-optimus-gateway-error-http-status"] == gateway.GATEWAY_ERROR_STATUS
    enum = set(schema["$defs"]["error"]["properties"]["code"]["enum"])
    assert enum == set(schema["x-hub-optimus-gateway-error-http-status"]) | set(
        gateway.UPSTREAM_ERROR_STATUS
    )


def test_no_request_material_is_logged(gateway, capsys):
    handler = object.__new__(gateway.Handler)
    handler.log_message(
        "%s %s %s",
        "https://secret.example/path",
        "secret-token",
        "opaque-subject-0001",
    )
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""


def test_systemd_unit_runs_hardened_gateway_with_private_environment():
    text = SERVICE_PATH.read_text(encoding="utf-8")
    assert "After=network.target hub-api.service" in text
    assert "Requires=hub-api.service" in text
    assert "EnvironmentFile=/etc/hub-optimus/operator-intake-gateway.env" in text
    assert (
        "ExecStart=/usr/bin/python3 "
        "/opt/hub-optimus/current/ops/ec2/operator-intake-gateway.py"
    ) in text
    assert "NoNewPrivileges=true" in text
    assert "User=hub-operator-gateway" in text
    assert "Group=hub-operator-gateway" in text
    assert "DynamicUser=true" in text
    assert "ProtectSystem=strict" in text
    assert "RestrictAddressFamilies=AF_INET" in text
    assert "IPAddressDeny=any" in text
    assert "IPAddressAllow=localhost" in text
    assert "StandardOutput=journal" in text
    assert "StandardError=journal" in text
    assert "HUB_OPERATOR_INTAKE_CAPABILITY=" not in text
