import socket
import sys
import threading
import time
import types
from http.client import BadStatusLine, IncompleteRead, LineTooLong
from pathlib import Path
from urllib.error import URLError

import pytest

ROOT = Path(__file__).resolve().parents[1]
API_SCRIPT = ROOT / "ops" / "ec2" / "hub-api.sh"


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
            self.headers = {"Content-Type": "text/html; charset=utf-8"}

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
            requests.append((request.full_url, timeout))
            return FakeResponse()

    monkeypatch.setattr(hub_api.socket, "getaddrinfo", fake_getaddrinfo)
    monkeypatch.setattr(
        hub_api,
        "build_pinned_opener",
        lambda pinned_ips, deadline: FakeOpener(),
    )

    result = hub_api.fetch_url_text("https://public.example/article")

    assert len(requests) == 1
    assert requests[0][0] == "https://public.example/article"
    assert 0 < requests[0][1] <= hub_api.URL_TIMEOUT_SECONDS
    assert result["url"] == "https://public.example/article"
    assert result["final_url"] == "https://public.example/article"
    assert result["redirects"] == []
    assert result["verification_status"] == "unreviewed"
    assert result["learning_status"] == "candidate-source-not-verified"
    assert "linked.example" not in result["text"]


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

        def read_json_body(self):
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
            clock[0] += 3
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
    assert [attempt[1] for attempt in attempts] == [8, 5, 2]


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
