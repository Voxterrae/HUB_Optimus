#!/usr/bin/env bash
set -euo pipefail

APP_ROOT="/opt/hub-optimus"
API_DIR="$APP_ROOT/shared/api"
API_FILE="$API_DIR/hub_api.py"

mkdir -p "$API_DIR"

cat > "$API_FILE" <<'PY'
#!/usr/bin/env python3
from __future__ import annotations

import datetime as dt
import html
import ipaddress
import json
import re
import signal
import socket
import subprocess
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass
from html.parser import HTMLParser
from http.client import (
    HTTPConnection,
    HTTPException,
    HTTPSConnection,
    InvalidURL,
)
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import (
    HTTPHandler,
    HTTPRedirectHandler,
    HTTPSHandler,
    ProxyHandler,
    Request,
    build_opener,
)

APP_ROOT = Path("/opt/hub-optimus")
CURRENT = APP_ROOT / "current"
SHARED = APP_ROOT / "shared"

MAX_URL_LENGTH = 2048
MAX_URL_BODY_LENGTH = 4096
MAX_URL_BYTES = 1_000_000
MAX_EXTRACTED_TEXT_CHARS = 24_000
MAX_REDIRECTS = 3
URL_TIMEOUT_SECONDS = 8
USER_AGENT = "HUB_Optimus-Operator-URL-Intake/0.1 (+https://huboptimus.dev/operator/)"

IPV4_COMPATIBLE_NETWORK = ipaddress.IPv6Network("::/96")
IPV4_TRANSLATED_NETWORK = ipaddress.IPv6Network("0:0:0:0:ffff:0::/96")
NAT64_WELL_KNOWN_NETWORK = ipaddress.IPv6Network("64:ff9b::/96")


class IntakeError(Exception):
    def __init__(self, status: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message


class FetchDeadlineExceeded(IntakeError):
    def __init__(self) -> None:
        super().__init__(
            504,
            "url_fetch_timeout",
            "URL fetch exceeded the total time limit.",
        )


@dataclass(frozen=True)
class FetchDeadline:
    expires_at: float

    @classmethod
    def start(cls, timeout_seconds: float) -> "FetchDeadline":
        return cls(time.monotonic() + timeout_seconds)

    def remaining_seconds(self) -> float:
        remaining = self.expires_at - time.monotonic()
        if remaining <= 0:
            raise FetchDeadlineExceeded()
        return remaining


@contextmanager
def enforce_fetch_deadline(deadline: FetchDeadline):
    """Enforce the synchronous Linux intake budget from the main thread."""

    if threading.current_thread() is not threading.main_thread():
        raise IntakeError(
            503,
            "url_fetch_unavailable",
            "URL fetch deadline enforcement requires the API main thread.",
        )

    timeout_seconds = deadline.remaining_seconds()
    previous_handler = signal.getsignal(signal.SIGALRM)
    previous_timer = signal.getitimer(signal.ITIMER_REAL)
    started_at = time.monotonic()

    def deadline_handler(signum, frame):
        raise FetchDeadlineExceeded()

    signal.signal(signal.SIGALRM, deadline_handler)
    signal.setitimer(signal.ITIMER_REAL, timeout_seconds)

    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous_handler)

        previous_delay, previous_interval = previous_timer
        if previous_delay > 0:
            elapsed = time.monotonic() - started_at
            signal.setitimer(
                signal.ITIMER_REAL,
                max(previous_delay - elapsed, 1e-6),
                previous_interval,
            )


@dataclass(frozen=True)
class ValidatedIntakeUrl:
    url: str
    hostname: str
    port: int
    resolved_ips: tuple[str, ...]


class NoRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def connect_validated_ip(
    ip_text,
    port,
    timeout,
    source_address,
):
    """Open a numeric socket and verify the peer remains the validated IP."""

    ip = ipaddress.ip_address(ip_text)
    family = socket.AF_INET if ip.version == 4 else socket.AF_INET6
    socket_address = (
        (str(ip), port)
        if ip.version == 4
        else (str(ip), port, 0, 0)
    )
    connection = socket.socket(family, socket.SOCK_STREAM, socket.IPPROTO_TCP)

    try:
        connection.settimeout(timeout)
        if source_address:
            connection.bind(source_address)
        connection.connect(socket_address)

        try:
            peer_ip = ipaddress.ip_address(connection.getpeername()[0])
        except ValueError as exc:
            raise OSError(
                "Connected peer did not return a numeric IP address."
            ) from exc

        if peer_ip != ip:
            raise OSError(
                "Connected peer does not match the validated IP address."
            )

        return connection
    except BaseException:
        connection.close()
        raise


def create_pinned_connection(
    address,
    timeout,
    source_address,
    pinned_ips,
    deadline,
):
    """Connect only to numeric IPs validated for the current URL hop."""

    _, port = address
    last_error = None

    for ip_text in pinned_ips:
        try:
            ipaddress.ip_address(ip_text)
            remaining = deadline.remaining_seconds()
            attempt_timeout = (
                min(float(timeout), remaining)
                if isinstance(timeout, (int, float))
                else remaining
            )
            return connect_validated_ip(
                ip_text,
                port,
                attempt_timeout,
                source_address,
            )
        except OSError as exc:
            last_error = exc
            deadline.remaining_seconds()

    if last_error is not None:
        raise last_error
    raise OSError("No validated public IP address is available for connection.")


class PinnedHTTPConnection(HTTPConnection):
    def __init__(self, host, *, pinned_ips, deadline, **kwargs):
        super().__init__(host, **kwargs)
        self._pinned_ips = tuple(pinned_ips)
        self._deadline = deadline
        self._create_connection = self._create_pinned_connection

    def _create_pinned_connection(self, address, timeout, source_address):
        return create_pinned_connection(
            address,
            timeout,
            source_address,
            self._pinned_ips,
            self._deadline,
        )


class PinnedHTTPSConnection(HTTPSConnection):
    def __init__(self, host, *, pinned_ips, deadline, **kwargs):
        super().__init__(host, **kwargs)
        self._pinned_ips = tuple(pinned_ips)
        self._deadline = deadline
        self._create_connection = self._create_pinned_connection

    def _create_pinned_connection(self, address, timeout, source_address):
        return create_pinned_connection(
            address,
            timeout,
            source_address,
            self._pinned_ips,
            self._deadline,
        )


class PinnedHTTPHandler(HTTPHandler):
    def __init__(self, pinned_ips, deadline):
        super().__init__()
        self._pinned_ips = tuple(pinned_ips)
        self._deadline = deadline

    def http_open(self, req):
        return self.do_open(
            PinnedHTTPConnection,
            req,
            pinned_ips=self._pinned_ips,
            deadline=self._deadline,
        )


class PinnedHTTPSHandler(HTTPSHandler):
    def __init__(self, pinned_ips, deadline):
        super().__init__()
        self._pinned_ips = tuple(pinned_ips)
        self._deadline = deadline

    def https_open(self, req):
        return self.do_open(
            PinnedHTTPSConnection,
            req,
            context=self._context,
            pinned_ips=self._pinned_ips,
            deadline=self._deadline,
        )


def build_pinned_opener(pinned_ips, deadline):
    """Build an opener with redirects and environment proxies disabled."""

    return build_opener(
        ProxyHandler({}),
        NoRedirectHandler(),
        PinnedHTTPHandler(pinned_ips, deadline),
        PinnedHTTPSHandler(pinned_ips, deadline),
    )


class TextExtractor(HTMLParser):
    block_tags = {
        "article", "aside", "blockquote", "br", "dd", "div", "dl", "dt", "figcaption",
        "footer", "h1", "h2", "h3", "h4", "h5", "h6", "header", "li", "main", "nav",
        "ol", "p", "pre", "section", "table", "td", "th", "tr", "ul"
    }

    skipped_tags = {
        "canvas", "iframe", "noscript", "script", "style", "svg", "template"
    }

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.title_parts: list[str] = []
        self.skip_stack: list[str] = []
        self.in_title = False

    def handle_starttag(self, tag: str, attrs) -> None:
        normalized = tag.lower()

        if normalized == "title":
            self.in_title = True

        if normalized in self.skipped_tags:
            self.skip_stack.append(normalized)
            return

        if not self.skip_stack and normalized in self.block_tags:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        normalized = tag.lower()

        if normalized == "title":
            self.in_title = False

        if self.skip_stack and self.skip_stack[-1] == normalized:
            self.skip_stack.pop()
            return

        if not self.skip_stack and normalized in self.block_tags:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self.skip_stack:
            return

        cleaned = data.strip()
        if not cleaned:
            return

        if self.in_title:
            self.title_parts.append(cleaned)
            return

        self.parts.append(cleaned)


def read_text(path: Path, default: str = "") -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return default


def run_command(args: list[str], input_text: str | None = None) -> tuple[int, str, str]:
    proc = subprocess.run(
        args,
        input=input_text,
        text=True,
        capture_output=True,
        check=False,
    )
    return proc.returncode, proc.stdout, proc.stderr


def product_status() -> dict:
    current_path = ""
    commit = ""
    if CURRENT.is_symlink():
        current_path = str(CURRENT.resolve())
        code, stdout, _ = run_command(["git", "-C", current_path, "rev-parse", "--short", "HEAD"])
        if code == 0:
            commit = stdout.strip()

    release_state = read_text(SHARED / "RELEASE_STATE")

    return {
        "product": "HUB_Optimus backend v0.1",
        "current": current_path,
        "commit": commit,
        "release_state": release_state,
        "capabilities": {
            "semantic_analyze": True,
            "scenario_runner": True,
            "deploy_rollback": True,
            "runs_registry": True,
            "controlled_url_intake": True,
            "public_api": False,
            "frontend": False,
        },
    }


def latest_run_id(command: str) -> str | None:
    command_dir = SHARED / "runs" / command
    if not command_dir.is_dir():
        return None
    runs = sorted(p.name for p in command_dir.iterdir() if p.is_dir())
    return runs[-1] if runs else None


def embedded_ipv4_addresses(
    ip: ipaddress.IPv4Address | ipaddress.IPv6Address,
) -> tuple[ipaddress.IPv4Address, ...]:
    if not isinstance(ip, ipaddress.IPv6Address):
        return ()

    embedded = []

    if ip.ipv4_mapped is not None:
        embedded.append(ip.ipv4_mapped)

    if (
        ip in IPV4_COMPATIBLE_NETWORK
        or ip in IPV4_TRANSLATED_NETWORK
        or ip in NAT64_WELL_KNOWN_NETWORK
    ):
        embedded.append(ipaddress.IPv4Address(ip.packed[-4:]))

    if ip.sixtofour is not None:
        embedded.append(ip.sixtofour)

    if ip.teredo is not None:
        embedded.extend(ip.teredo)

    interface_prefix = ip.packed[8:12]
    if interface_prefix in {b"\x00\x00\x5e\xfe", b"\x02\x00\x5e\xfe"}:
        embedded.append(ipaddress.IPv4Address(ip.packed[-4:]))

    return tuple(dict.fromkeys(embedded))


def blocked_ip_reason(ip_text: str) -> str | None:
    try:
        ip = ipaddress.ip_address(ip_text)
    except ValueError:
        return "invalid_ip"

    if (
        not ip.is_global
        or ip.is_multicast
        or (
            isinstance(ip, ipaddress.IPv6Address)
            and ip.is_site_local
        )
    ):
        return "non_global_ip"

    for embedded_ip in embedded_ipv4_addresses(ip):
        if not embedded_ip.is_global or embedded_ip.is_multicast:
            return "embedded_non_global_ip"

    return None


def validate_host(
    hostname: str,
    port: int,
    deadline: FetchDeadline | None = None,
) -> tuple[str, ...]:
    host = hostname.strip("[]").rstrip(".").lower()

    if not host:
        raise IntakeError(400, "invalid_url_host", "URL host is empty.")

    if host == "localhost" or host.endswith(".localhost"):
        raise IntakeError(400, "blocked_url_host", "Localhost URLs are not allowed.")

    direct_reason = blocked_ip_reason(host)
    if direct_reason is None:
        return (str(ipaddress.ip_address(host)),)

    if direct_reason != "invalid_ip":
        raise IntakeError(400, "blocked_url_host", "URL resolves to a non-public IP address.")

    try:
        infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except (socket.gaierror, UnicodeError) as exc:
        raise IntakeError(400, "unresolvable_url_host", f"Could not resolve URL host: {exc}") from exc

    if deadline is not None:
        deadline.remaining_seconds()

    resolved_ips = set()
    try:
        for item in infos:
            resolved_ips.add(str(ipaddress.ip_address(item[4][0])))
    except ValueError as exc:
        raise IntakeError(
            400,
            "unresolvable_url_host",
            "URL host resolution returned an invalid address.",
        ) from exc
    if not resolved_ips:
        raise IntakeError(400, "unresolvable_url_host", "URL host did not resolve to any address.")

    for ip_text in resolved_ips:
        reason = blocked_ip_reason(ip_text)
        if reason is not None:
            raise IntakeError(
                400,
                "blocked_url_host",
                "URL host resolves to a non-public IP address.",
            )

    return tuple(
        str(ip)
        for ip in sorted(
            (ipaddress.ip_address(ip_text) for ip_text in resolved_ips),
            key=lambda ip: (ip.version, int(ip)),
        )
    )


def validate_intake_url(
    raw_url: str,
    deadline: FetchDeadline | None = None,
) -> ValidatedIntakeUrl:
    if not isinstance(raw_url, str):
        raise IntakeError(400, "invalid_url", "URL must be a string.")

    url = raw_url
    if not url:
        raise IntakeError(400, "invalid_url", "URL is required.")

    if len(url) > MAX_URL_LENGTH:
        raise IntakeError(414, "url_too_long", "URL exceeds maximum allowed length.")

    if any(ord(character) <= 0x20 or ord(character) == 0x7F for character in url):
        raise IntakeError(
            400,
            "invalid_url",
            "URL must not contain raw spaces or control characters.",
        )

    try:
        url.encode("ascii")
    except UnicodeEncodeError as exc:
        raise IntakeError(
            400,
            "unsupported_url_iri",
            "Unicode IRIs are not supported; use an IDNA A-label hostname and "
            "percent-encode non-ASCII path or query text.",
        ) from exc

    try:
        parsed = urlparse(url)
    except ValueError as exc:
        raise IntakeError(400, "invalid_url", "URL could not be parsed.") from exc

    if parsed.scheme not in {"http", "https"}:
        raise IntakeError(400, "unsupported_url_scheme", "Only http and https URLs are allowed.")

    if parsed.username is not None or parsed.password is not None:
        raise IntakeError(400, "unsupported_url_credentials", "URLs with credentials are not allowed.")

    try:
        hostname = parsed.hostname
    except ValueError as exc:
        raise IntakeError(400, "invalid_url_host", "URL host is malformed.") from exc

    if not hostname:
        raise IntakeError(400, "invalid_url_host", "URL host is required.")

    if "%" in hostname:
        raise IntakeError(
            400,
            "invalid_url_host",
            "Percent-encoded hostnames are not supported; use an IDNA A-label.",
        )

    try:
        explicit_port = parsed.port
    except ValueError as exc:
        raise IntakeError(
            400,
            "invalid_url_port",
            "URL port is malformed or out of range.",
        ) from exc

    default_port = 80 if parsed.scheme == "http" else 443
    if explicit_port not in {None, default_port}:
        raise IntakeError(400, "unsupported_url_port", "Only default HTTP/HTTPS ports are allowed.")

    resolved_ips = validate_host(hostname, default_port, deadline)

    return ValidatedIntakeUrl(
        url=url,
        hostname=hostname,
        port=default_port,
        resolved_ips=resolved_ips,
    )


def response_charset(content_type: str) -> str:
    match = re.search(r"charset=([A-Za-z0-9._-]+)", content_type or "", re.I)
    if match:
        return match.group(1)
    return "utf-8"


def clean_extracted_text(raw: str) -> str:
    normalized = html.unescape(raw)
    normalized = normalized.replace("\u00a0", " ")
    normalized = re.sub(r"[ \t\r\f\v]+", " ", normalized)

    lines = []
    seen = set()

    for line in normalized.splitlines():
        item = line.strip()
        if not item:
            continue

        if len(item) < 28 and not item.endswith((".", ":", "!", "?")):
            continue

        key = item.lower()
        if key in seen:
            continue

        seen.add(key)
        lines.append(item)

    text = "\n".join(lines)
    if len(text) > MAX_EXTRACTED_TEXT_CHARS:
        text = text[:MAX_EXTRACTED_TEXT_CHARS].rstrip() + "…"

    return text


def extract_text_document(body: bytes, content_type: str) -> tuple[str, str | None]:
    charset = response_charset(content_type)

    try:
        decoded = body.decode(charset, errors="replace")
    except LookupError:
        decoded = body.decode("utf-8", errors="replace")

    if "html" not in content_type.lower():
        return clean_extracted_text(decoded), None

    parser = TextExtractor()
    parser.feed(decoded)

    title = clean_extracted_text("\n".join(parser.title_parts))
    text = clean_extracted_text("\n".join(parser.parts))

    return text, title or None


def fetch_url_text_with_deadline(raw_url: str, deadline: FetchDeadline) -> dict:
    current = validate_intake_url(raw_url, deadline)
    redirects = []

    for _ in range(MAX_REDIRECTS + 1):
        deadline.remaining_seconds()
        opener = build_pinned_opener(current.resolved_ips, deadline)

        try:
            request = Request(
                current.url,
                headers={
                    "User-Agent": USER_AGENT,
                    "Accept": "text/html, text/plain, application/xhtml+xml;q=0.9, */*;q=0.4",
                },
                method="GET",
            )
        except (UnicodeError, ValueError) as exc:
            raise IntakeError(
                400,
                "invalid_url",
                "URL could not be encoded as an HTTP request.",
            ) from exc

        try:
            with opener.open(
                request,
                timeout=deadline.remaining_seconds(),
            ) as response:
                content_type = response.headers.get("Content-Type", "")
                if not (
                    "text/html" in content_type.lower()
                    or "text/plain" in content_type.lower()
                    or "application/xhtml+xml" in content_type.lower()
                ):
                    raise IntakeError(
                        415,
                        "unsupported_content_type",
                        f"Unsupported content type: {content_type or 'unknown'}",
                    )

                body = response.read(MAX_URL_BYTES + 1)
                truncated = len(body) > MAX_URL_BYTES
                if truncated:
                    body = body[:MAX_URL_BYTES]

                text, title = extract_text_document(body, content_type)
                if not text:
                    raise IntakeError(422, "empty_extraction", "URL was fetched but no readable text was extracted.")

                final_url = response.geturl()
                parsed = urlparse(final_url)

                return {
                    "status": "ok",
                    "intake_type": "controlled_url",
                    "url": raw_url,
                    "final_url": final_url,
                    "source_domain": parsed.hostname or "",
                    "retrieved_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
                    "title": title,
                    "text": text,
                    "content_type": content_type,
                    "bytes_read": len(body),
                    "truncated": truncated,
                    "redirects": redirects,
                    "verification_status": "unreviewed",
                    "learning_status": "candidate-source-not-verified",
                    "extraction_notes": [
                        "Fetched by local backend controlled URL intake.",
                        "No cookies, authentication, browser automation, or paywall bypass were used.",
                        "Text extraction is source-bound and does not verify truth.",
                    ],
                }

        except HTTPError as exc:
            if exc.code in {301, 302, 303, 307, 308}:
                location = exc.headers.get("Location")
                if not location:
                    raise IntakeError(502, "redirect_without_location", "URL redirect did not include a Location header.")

                try:
                    next_url = urljoin(current.url, location)
                except (UnicodeError, ValueError) as redirect_error:
                    raise IntakeError(
                        400,
                        "invalid_url",
                        "Redirect URL could not be parsed.",
                    ) from redirect_error
                next_hop = validate_intake_url(next_url, deadline)
                redirects.append({"from": current.url, "to": next_hop.url, "status": exc.code})
                current = next_hop
                continue

            raise IntakeError(502, "url_fetch_failed", f"URL fetch failed with HTTP {exc.code}.") from exc
        except (InvalidURL, UnicodeError) as exc:
            raise IntakeError(
                400,
                "invalid_url",
                "URL could not be encoded as an HTTP request.",
            ) from exc
        except URLError as exc:
            if isinstance(exc.reason, TimeoutError):
                raise IntakeError(
                    504,
                    "url_fetch_timeout",
                    "URL fetch timed out.",
                ) from exc
            raise IntakeError(502, "url_fetch_failed", f"URL fetch failed: {exc.reason}") from exc
        except TimeoutError as exc:
            raise IntakeError(504, "url_fetch_timeout", "URL fetch timed out.") from exc
        except HTTPException as exc:
            raise IntakeError(
                502,
                "url_fetch_failed",
                "URL fetch failed because the HTTP response was malformed.",
            ) from exc
        except OSError as exc:
            raise IntakeError(
                502,
                "url_fetch_failed",
                "URL fetch failed while reading the remote response.",
            ) from exc

    raise IntakeError(508, "too_many_redirects", "URL exceeded maximum redirect limit.")


def fetch_url_text(raw_url: str) -> dict:
    deadline = FetchDeadline.start(URL_TIMEOUT_SECONDS)
    with enforce_fetch_deadline(deadline):
        return fetch_url_text_with_deadline(raw_url, deadline)


class Handler(BaseHTTPRequestHandler):
    server_version = "HUBOptimusAPI/0.1"

    def send_json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
        encoded = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def read_json_body(self) -> dict | None:
        length = int(self.headers.get("Content-Length", "0"))

        if length > MAX_URL_BODY_LENGTH:
            self.send_json(413, {"error": "request body too large"})
            return None

        raw = self.rfile.read(length).decode("utf-8")

        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            self.send_json(400, {"error": f"invalid JSON: {exc.msg}"})
            return None

        if not isinstance(payload, dict):
            self.send_json(400, {"error": "JSON body must be an object"})
            return None

        return payload

    def handle_url_intake(self) -> None:
        payload = self.read_json_body()
        if payload is None:
            return

        url = payload.get("url", "")

        try:
            result = fetch_url_text(url)
        except IntakeError as exc:
            self.send_json(
                exc.status,
                {
                    "status": "error",
                    "error": exc.code,
                    "message": exc.message,
                    "url": url,
                    "verification_status": "unreviewed",
                },
            )
            return

        self.send_json(200, result)

    def handle_analyze(self) -> None:
        payload = self.read_json_body()
        if payload is None:
            return

        case_dir = SHARED / "api" / "cases"
        case_dir.mkdir(parents=True, exist_ok=True)
        case_path = case_dir / "api-case.json"
        case_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

        before_latest = latest_run_id("analyze")

        code, stdout, stderr = run_command([
            "/opt/hub-optimus/shared/bin/hub-core",
            "analyze",
            str(case_path),
        ])

        after_latest = latest_run_id("analyze")

        if code != 0:
            self.send_json(
                500,
                {
                    "error": "analysis failed",
                    "stderr": stderr,
                    "stdout": stdout,
                },
            )
            return

        if not after_latest or after_latest == before_latest:
            self.send_json(
                500,
                {
                    "error": "analysis completed but run output was not detected",
                    "stdout": stdout,
                },
            )
            return

        run_path = SHARED / "runs" / "analyze" / after_latest
        result_path = run_path / "analysis_result.json"

        try:
            analysis_result = json.loads(result_path.read_text(encoding="utf-8"))
        except OSError as exc:
            self.send_json(500, {"error": f"cannot read analysis result: {exc}"})
            return
        except json.JSONDecodeError as exc:
            self.send_json(500, {"error": f"analysis result is invalid JSON: {exc.msg}"})
            return

        self.send_json(
            200,
            {
                "status": "ok",
                "run_id": after_latest,
                "run_path": str(run_path),
                "analysis_result": analysis_result,
            },
        )

    def do_GET(self) -> None:
        path = urlparse(self.path).path

        if path == "/status":
            self.send_json(200, product_status())
            return

        if path == "/health":
            self.send_json(200, {"status": "ok"})
            return

        self.send_json(404, {"error": "not found"})

    def do_POST(self) -> None:
        path = urlparse(self.path).path

        if path == "/intake/url":
            self.handle_url_intake()
            return

        if path == "/analyze":
            self.handle_analyze()
            return

        self.send_json(404, {"error": "not found"})


def main() -> int:
    host = "127.0.0.1"
    port = 8080
    httpd = HTTPServer((host, port), Handler)
    print(f"[hub-api] listening on http://{host}:{port}", flush=True)
    httpd.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
PY

chmod +x "$API_FILE"

echo "[hub-api] Starting local API on 127.0.0.1:8080"
exec python3 "$API_FILE"
