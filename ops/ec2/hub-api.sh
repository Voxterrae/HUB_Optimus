#!/usr/bin/env bash
set -euo pipefail

export PYTHONDONTWRITEBYTECODE=1

APP_ROOT="${HUB_OPTIMUS_APP_ROOT:-/opt/hub-optimus}"
API_DIR="$APP_ROOT/shared/api"
API_FILE="$API_DIR/hub_api.py"

case "$APP_ROOT" in
  /*) ;;
  *)
    echo "[hub-api:error] HUB_OPTIMUS_APP_ROOT must be an absolute path." >&2
    exit 1
    ;;
esac

RUNNING_RELEASE="$(readlink -f "$APP_ROOT/current")"
case "$RUNNING_RELEASE" in
  "$APP_ROOT/releases/"*) ;;
  *)
    echo "[hub-api:error] current is outside the managed releases directory." >&2
    exit 1
    ;;
esac
[ -d "$RUNNING_RELEASE" ] || {
  echo "[hub-api:error] running release directory does not exist." >&2
  exit 1
}

RUNNING_COMMIT="$(git -C "$RUNNING_RELEASE" rev-parse --verify HEAD)"
[[ "$RUNNING_COMMIT" =~ ^[0-9a-f]{40}$ ]] || {
  echo "[hub-api:error] running release has no full commit identity." >&2
  exit 1
}

RUNNING_LAUNCHER_SHA256="$(sha256sum -- "$0" | awk '{print $1}')"
[[ "$RUNNING_LAUNCHER_SHA256" =~ ^[0-9a-f]{64}$ ]] || {
  echo "[hub-api:error] launcher SHA-256 could not be captured." >&2
  exit 1
}

export HUB_OPTIMUS_API_APP_ROOT="$APP_ROOT"
export HUB_OPTIMUS_API_RUNNING_RELEASE="$RUNNING_RELEASE"
export HUB_OPTIMUS_API_RUNNING_COMMIT="$RUNNING_COMMIT"
export HUB_OPTIMUS_API_RUNNING_LAUNCHER_SHA256="$RUNNING_LAUNCHER_SHA256"

mkdir -p "$API_DIR"

cat > "$API_FILE" <<'PY'
#!/usr/bin/env python3
from __future__ import annotations

import datetime as dt
import codecs
import ipaddress
import json
import os
import re
import signal
import socket
import subprocess
import tempfile
import threading
import time
from contextlib import contextmanager
from email.message import Message
from html.parser import HTMLParser
from http.client import (
    HTTPConnection,
    HTTPException,
    HTTPSConnection,
    InvalidURL,
)
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import NamedTuple
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

APP_ROOT = Path(os.environ.get("HUB_OPTIMUS_API_APP_ROOT", "/opt/hub-optimus"))
CURRENT = APP_ROOT / "current"
SHARED = APP_ROOT / "shared"
RUNNING_RELEASE = os.environ.get("HUB_OPTIMUS_API_RUNNING_RELEASE", "")
RUNNING_COMMIT = os.environ.get("HUB_OPTIMUS_API_RUNNING_COMMIT", "")
RUNNING_LAUNCHER_SHA256 = os.environ.get(
    "HUB_OPTIMUS_API_RUNNING_LAUNCHER_SHA256",
    "",
)

MAX_URL_LENGTH = 2048
MAX_URL_BODY_LENGTH = 4096
MAX_ANALYZE_BODY_LENGTH = 64_000
MAX_URL_BYTES = 1_000_000
MAX_EXTRACTED_TEXT_CHARS = 24_000
MAX_HTML_DEPTH = 256
MAX_PRIMARY_REGIONS = 64
MAX_REDIRECTS = 3
URL_TIMEOUT_SECONDS = 8
USER_AGENT = "HUB_Optimus-Operator-URL-Intake/0.1 (+https://huboptimus.dev/operator/)"
CORE_RUN_ID_PREFIX = "[hub-core:run-id] "
CORE_RUN_ID_PATTERN = re.compile(r"\A\d{8}T\d{6}Z\.[A-Za-z0-9]{6}\Z")

IPV4_COMPATIBLE_NETWORK = ipaddress.IPv6Network("::/96")
IPV4_TRANSLATED_NETWORK = ipaddress.IPv6Network("0:0:0:0:ffff:0::/96")
NAT64_WELL_KNOWN_NETWORK = ipaddress.IPv6Network("64:ff9b::/96")


class IntakeError(Exception):
    def __init__(self, status: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message


def reject_non_standard_json_constant(value: str) -> None:
    """Reject Python's non-standard JSON numeric constants."""

    raise ValueError(f"non-standard numeric constant {value} is not valid JSON")


def require_scalar_unicode(value, max_depth: int = 64, max_nodes: int = 100_000) -> None:
    stack = [(value, "$", 0)]
    seen_containers = set()
    visited = 0

    while stack:
        current, path, depth = stack.pop()
        visited += 1
        if visited > max_nodes:
            raise ValueError("JSON structure exceeds maximum node count")
        if depth > max_depth:
            raise ValueError("JSON structure exceeds maximum depth")
        if isinstance(current, str):
            try:
                current.encode("utf-8")
            except UnicodeEncodeError as exc:
                raise ValueError(f"{path} contains non-scalar Unicode") from exc
            continue
        if isinstance(current, (list, dict)):
            identity = id(current)
            if identity in seen_containers:
                raise ValueError("JSON structure contains a repeated or circular container")
            seen_containers.add(identity)
        if isinstance(current, list):
            stack.extend(
                (item, f"{path}[{index}]", depth + 1)
                for index, item in reversed(list(enumerate(current)))
            )
        elif isinstance(current, dict):
            for key, item in current.items():
                if isinstance(key, str):
                    stack.append((key, f"{path}.<key>", depth + 1))
                stack.append((item, f"{path}.<value>", depth + 1))


def load_strict_json(raw: str):
    try:
        payload = json.loads(
            raw,
            parse_constant=reject_non_standard_json_constant,
        )
    except RecursionError as exc:
        raise ValueError("JSON structure exceeds parser depth") from exc
    require_scalar_unicode(payload)
    return payload


def dump_strict_json(payload) -> str:
    require_scalar_unicode(payload)
    return json.dumps(
        payload,
        allow_nan=False,
        indent=2,
        sort_keys=True,
        ensure_ascii=False,
    ) + "\n"


class FetchDeadlineExceeded(IntakeError):
    def __init__(self) -> None:
        super().__init__(
            504,
            "url_fetch_timeout",
            "URL fetch exceeded the total time limit.",
        )


class FetchDeadline(NamedTuple):
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


class ValidatedIntakeUrl(NamedTuple):
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
    candidate_ips = tuple(pinned_ips)

    for index, ip_text in enumerate(candidate_ips):
        try:
            ipaddress.ip_address(ip_text)
            remaining = deadline.remaining_seconds()
            candidates_left = len(candidate_ips) - index
            candidate_budget = remaining / candidates_left
            attempt_timeout = (
                min(float(timeout), candidate_budget)
                if isinstance(timeout, (int, float))
                else candidate_budget
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
        "article", "aside", "blockquote", "br", "button", "dd", "div", "dl", "dt", "figcaption",
        "footer", "h1", "h2", "h3", "h4", "h5", "h6", "header", "li", "main", "nav",
        "ol", "p", "pre", "section", "table", "td", "th", "tr", "ul"
    }

    skipped_tags = {
        "aside", "canvas", "dialog", "footer", "form", "iframe", "nav",
        "noscript", "script", "style", "svg", "template"
    }

    primary_tags = {"article", "main"}

    void_tags = {
        "area", "base", "br", "col", "embed", "hr", "img", "input", "link",
        "meta", "param", "source", "track", "wbr"
    }

    boilerplate_tokens = {
        "advert", "advertisement", "cookiebot", "footer", "modal",
        "navbar", "navigation", "newsletter", "onetrust", "promo", "sidebar"
    }

    boilerplate_phrases = {
        "consent banner", "consent modal", "cookie banner", "cookie consent",
        "cookie notice", "cookie settings", "main menu", "nav menu",
        "cky consent", "osano cm",
        "related articles", "related content", "related posts", "related stories",
        "share bar", "share buttons",
        "share tools", "site menu", "social buttons", "social links",
        "social share"
    }

    paragraph_closing_tags = {
        "address", "article", "aside", "blockquote", "div", "dl", "fieldset",
        "footer", "form", "h1", "h2", "h3", "h4", "h5", "h6", "header",
        "hr", "main", "nav", "ol", "p", "pre", "section", "table", "ul"
    }

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.outside_primary_parts: list[str] = []
        self.primary_regions: list[dict] = []
        self.title_parts: list[str] = []
        self.open_elements: list[dict] = []
        self.skip_depth = 0
        self.active_primary_index: int | None = None
        self.limit_exceeded = False
        self.in_title = False

    @staticmethod
    def _attribute_label(attrs) -> str:
        values = " ".join(
            value
            for key, value in attrs
            if key.lower() in {"aria-label", "class", "id", "role"}
            and isinstance(value, str)
        )
        values = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", values)
        return " ".join(re.findall(r"[a-z0-9]+", values.lower()))

    def _is_boilerplate_container(self, tag: str, attrs, in_primary: bool) -> bool:
        normalized_attrs = {str(key).lower(): value for key, value in attrs}
        if "hidden" in normalized_attrs:
            return True
        if str(normalized_attrs.get("aria-hidden", "")).strip().lower() == "true":
            return True
        inline_style = str(normalized_attrs.get("style", ""))
        if re.search(
            r"(?:^|;)\s*(?:display\s*:\s*none|visibility\s*:\s*hidden)\s*(?:!important\s*)?(?:;|$)",
            inline_style,
            re.I,
        ):
            return True
        if tag in self.skipped_tags:
            return True
        if tag == "header" and not in_primary:
            return True

        label = self._attribute_label(attrs)
        tokens = set(label.split())
        words = label.split()

        def contains_phrase(phrase: str) -> bool:
            phrase_words = phrase.split()
            width = len(phrase_words)
            return any(
                words[index:index + width] == phrase_words
                and (index == 0 or words[index - 1] not in {"not", "unrelated"})
                for index in range(max(0, len(words) - width + 1))
            )

        return bool(
            tokens & self.boilerplate_tokens
            or any(contains_phrase(phrase) for phrase in self.boilerplate_phrases)
        )

    def _active_primary_indexes(self) -> list[int]:
        if self.active_primary_index is None:
            return []
        return [self.active_primary_index]

    def _is_skipping(self) -> bool:
        return self.skip_depth > 0

    @staticmethod
    def _append_text(target: list[str], data: str) -> None:
        # Preserve whether the source contained whitespace at an inline boundary.
        # Adding a separator unconditionally corrupts identifiers such as
        # ``state-<em>owned</em>``, ``can'<em>t</em>`` and ``2<b>0</b>26``.
        cleaned = re.sub(r"\s+", " ", data)
        if not cleaned:
            return
        if not cleaned.strip():
            if target and not target[-1].endswith(("\n", " ")):
                target.append(" ")
            return
        target.append(cleaned)

    def _append_break(self) -> None:
        if self.parts and self.parts[-1] != "\n":
            self.parts.append("\n")
        active_indexes = self._active_primary_indexes()
        if not active_indexes and self.outside_primary_parts and self.outside_primary_parts[-1] != "\n":
            self.outside_primary_parts.append("\n")
        for index in active_indexes:
            parts = self.primary_regions[index]["parts"]
            if parts and parts[-1] != "\n":
                parts.append("\n")

    def handle_starttag(self, tag: str, attrs) -> None:
        normalized = tag.lower()

        if self.limit_exceeded:
            return

        # HTMLParser intentionally does not apply HTML's implied end-tag rules.
        # Close the common optional-end elements so an excluded container cannot
        # swallow later visible siblings that a browser would parse separately.
        if self.open_elements:
            current = self.open_elements[-1]["tag"]
            if (
                normalized in self.paragraph_closing_tags
                and any(frame["tag"] == "p" for frame in self.open_elements)
            ):
                self.handle_endtag("p")
            elif current == "li" and normalized == "li":
                self.handle_endtag(current)
            elif current in {"dt", "dd"} and normalized in {"dt", "dd"}:
                self.handle_endtag(current)
            elif current == "tr" and normalized == "tr":
                self.handle_endtag(current)
            elif current in {"th", "td"} and normalized in {"th", "td"}:
                self.handle_endtag(current)

        if normalized not in self.void_tags and len(self.open_elements) >= MAX_HTML_DEPTH:
            # Fail closed for the remainder. Attempting to recover from arbitrary
            # malformed closing tags can resume at the wrong depth and leak text
            # from an excluded region. The response exposes this as truncation.
            self.limit_exceeded = True
            return

        inherited_skip = self._is_skipping()
        active_primary = self._active_primary_indexes()
        container_skip = self._is_boilerplate_container(
            normalized,
            attrs,
            bool(active_primary),
        )
        skipped = inherited_skip or container_skip

        if normalized == "title":
            self.in_title = True

        if not skipped and normalized in self.block_tags:
            self._append_break()

        primary_index = None
        if (
            not skipped
            and normalized in self.primary_tags
            and self.active_primary_index is None
        ):
            primary_limit = (
                MAX_PRIMARY_REGIONS
                if normalized == "main"
                or any(region["tag"] == "main" for region in self.primary_regions)
                else MAX_PRIMARY_REGIONS - 1
            )
            if len(self.primary_regions) < primary_limit:
                primary_index = len(self.primary_regions)
                self.primary_regions.append({"tag": normalized, "parts": []})
                self.active_primary_index = primary_index

        if normalized not in self.void_tags:
            self.open_elements.append(
                {
                    "tag": normalized,
                    "starts_skip": container_skip,
                    "primary_index": primary_index,
                }
            )
            if container_skip:
                self.skip_depth += 1

    def handle_endtag(self, tag: str) -> None:
        normalized = tag.lower()

        if self.limit_exceeded:
            return

        matching_index = next(
            (
                index
                for index in range(len(self.open_elements) - 1, -1, -1)
                if self.open_elements[index]["tag"] == normalized
            ),
            None,
        )
        if matching_index is None:
            return

        if not self._is_skipping() and normalized in self.block_tags:
            self._append_break()

        closed = self.open_elements[matching_index:]
        del self.open_elements[matching_index:]
        self.skip_depth = max(
            0,
            self.skip_depth - sum(1 for frame in closed if frame["starts_skip"]),
        )
        if any(
            frame["primary_index"] == self.active_primary_index
            for frame in closed
        ):
            self.active_primary_index = None
        if any(frame["tag"] == "title" for frame in closed):
            self.in_title = False

    def handle_data(self, data: str) -> None:
        if self.limit_exceeded:
            return
        if self._is_skipping():
            return

        if self.in_title:
            self._append_text(self.title_parts, data)
            return

        self._append_text(self.parts, data)
        active_indexes = self._active_primary_indexes()
        if not active_indexes:
            self._append_text(self.outside_primary_parts, data)
        for index in active_indexes:
            self._append_text(self.primary_regions[index]["parts"], data)


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
    configured_current_release = ""
    configured_current_commit = ""
    if CURRENT.is_symlink():
        configured_current_release = str(CURRENT.resolve())
        code, stdout, _ = run_command(
            [
                "git",
                "-C",
                configured_current_release,
                "rev-parse",
                "--verify",
                "HEAD",
            ]
        )
        if code == 0:
            candidate = stdout.strip()
            if re.fullmatch(r"[0-9a-f]{40}", candidate):
                configured_current_commit = candidate

    release_state = read_text(SHARED / "RELEASE_STATE")

    return {
        "product": "HUB_Optimus backend v0.1",
        "current": RUNNING_RELEASE,
        "commit": RUNNING_COMMIT,
        "running_release": RUNNING_RELEASE,
        "running_commit": RUNNING_COMMIT,
        "running_launcher_sha256": RUNNING_LAUNCHER_SHA256,
        "configured_current_release": configured_current_release,
        "configured_current_commit": configured_current_commit,
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


def core_run_id(stdout: str) -> str | None:
    candidates = [
        line.removeprefix(CORE_RUN_ID_PREFIX)
        for line in stdout.splitlines()
        if line.startswith(CORE_RUN_ID_PREFIX)
    ]
    if len(candidates) != 1:
        return None
    run_id = candidates[0]
    return run_id if CORE_RUN_ID_PATTERN.fullmatch(run_id) else None


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


def parse_content_type(content_type: str) -> tuple[str, str]:
    raw = content_type or ""
    if any(ord(character) < 0x20 or ord(character) == 0x7F for character in raw):
        return "", "utf-8"
    media_type = raw.split(";", 1)[0].strip().lower()
    token = r"[!#$%&'*+.^_`|~0-9A-Za-z-]+"
    if not re.fullmatch(rf"{token}/{token}", media_type):
        return "", "utf-8"

    message = Message()
    message["content-type"] = raw
    parameters = message.get_params(header="content-type", unquote=True) or []
    charset_values = [
        value
        for key, value in parameters[1:]
        if isinstance(key, str) and key.casefold() == "charset"
    ]
    if (
        len(charset_values) > 1
        or (
            len(charset_values) == 1
            and (
                not isinstance(charset_values[0], str)
                or not charset_values[0].strip()
            )
        )
    ):
        raise IntakeError(
            415,
            "unsupported_content_type",
            "Source Content-Type must declare at most one non-empty charset.",
        )
    charset = charset_values[0].strip() if charset_values else "utf-8"
    return media_type, charset


def response_header_values(headers, name: str) -> list[str]:
    get_all = getattr(headers, "get_all", None)
    if callable(get_all):
        values = get_all(name, []) or []
    else:
        values = [
            value
            for key, value in headers.items()
            if str(key).lower() == name.lower()
        ]
    return [str(value) for value in values if value is not None]


def source_text_charset(declared_charset: str) -> str:
    try:
        canonical = codecs.lookup(declared_charset).name.lower()
    except LookupError as exc:
        raise IntakeError(
            415,
            "unsupported_content_type",
            "Source charset is unknown or unsupported.",
        ) from exc

    safe_names = {
        "ascii", "big5", "big5hkscs", "euc_jp", "euc_kr", "gb18030",
        "gb2312", "gbk", "hz", "johab", "koi8-r", "koi8-u", "latin-1",
        "mac-roman", "ptcp154", "shift_jis", "tis-620", "utf-8",
        "utf-8-sig", "utf-16", "utf-16-be", "utf-16-le", "utf-32",
        "utf-32-be", "utf-32-le",
    }
    if (
        canonical in safe_names
        or re.fullmatch(r"cp[0-9]+", canonical)
        or re.fullmatch(r"iso8859-[0-9]+", canonical)
    ):
        return canonical
    raise IntakeError(
        415,
        "unsupported_content_type",
        "Source charset is not a supported text encoding.",
    )


def clean_extracted_text(raw: str) -> tuple[str, bool]:
    # HTMLParser already resolves character references exactly once. Plain text
    # is not HTML, so entity-looking strings there must remain literal.
    normalized = raw.replace("\u00a0", " ")
    normalized = re.sub(r"[ \t\r\f\v]+", " ", normalized)

    lines = []
    seen = set()

    for line in normalized.splitlines():
        item = line.strip()
        if not item:
            continue

        key = item.lower()
        if key in seen:
            continue

        seen.add(key)
        lines.append(item)

    full_text = "\n".join(lines)
    truncated = len(full_text) > MAX_EXTRACTED_TEXT_CHARS
    text = full_text
    if truncated:
        text = full_text[:MAX_EXTRACTED_TEXT_CHARS].rstrip() + "…"

    return text, truncated


def extract_text_document(body: bytes, content_type: str) -> tuple[str, str | None, bool]:
    media_type, charset = parse_content_type(content_type)
    if media_type not in {"text/html", "text/plain", "application/xhtml+xml"}:
        raise IntakeError(
            415,
            "unsupported_content_type",
            "Source Content-Type is malformed or unsupported.",
        )
    charset = source_text_charset(charset)

    try:
        decoded = body.decode(charset, errors="strict")
    except (LookupError, UnicodeDecodeError, ValueError) as exc:
        raise IntakeError(
            415,
            "unsupported_content_type",
            "Source bytes are not valid for the declared text encoding.",
        ) from exc
    try:
        decoded.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise IntakeError(
            415,
            "unsupported_content_type",
            "Decoded source text contains unsupported non-scalar Unicode.",
        ) from exc

    if media_type == "text/plain":
        text, truncated = clean_extracted_text(decoded)
        return text, None, truncated

    parser = TextExtractor()
    parser.feed(decoded)
    parser.close()

    title, title_truncated = clean_extracted_text("".join(parser.title_parts))
    fallback_text, fallback_truncated = clean_extracted_text("".join(parser.parts))
    outside_text, outside_truncated = clean_extracted_text(
        "".join(parser.outside_primary_parts)
    )

    cleaned_regions = []
    for region in parser.primary_regions:
        region_text, region_truncated = clean_extracted_text("".join(region["parts"]))
        if region_text:
            cleaned_regions.append(
                (region["tag"], region_text, region_truncated)
            )

    main_region = max(
        (item for item in cleaned_regions if item[0] == "main"),
        key=lambda item: len(item[1]),
        default=None,
    )
    article_region = max(
        (item for item in cleaned_regions if item[0] == "article"),
        key=lambda item: len(item[1]),
        default=None,
    )

    placeholder_text = (
        " ".join(main_region[1].casefold().split()).strip(" .…!?。！？؟")
        if main_region
        else ""
    )
    placeholder_prefixes = {
        "loading", "please wait", "redirecting", "just a moment",
        "welcome", "bienvenido", "willkommen",
        "cargando", "espere", "bitte warten", "wird geladen",
        "загрузка", "пожалуйста подождите", "טוען", "נא להמתין",
        "加载中", "请稍候",
    }
    placeholder_main = bool(
        main_region
        and len(main_region[1]) < 80
        and any(
            placeholder_text == prefix or placeholder_text.startswith(prefix + " ")
            for prefix in placeholder_prefixes
        )
    )
    if main_region and not placeholder_main:
        _, text, text_truncated = main_region
    elif (
        article_region
        and len(article_region[1]) >= 40
        and len(article_region[1]) >= max(1, len(outside_text)) * 2
    ):
        _, text, text_truncated = article_region
    elif (
        article_region
        and outside_text
        and len(outside_text) >= len(article_region[1]) * 1.5
    ):
        text, text_truncated = outside_text, outside_truncated
    elif main_region and outside_text:
        text, text_truncated = outside_text, outside_truncated
    else:
        text, text_truncated = fallback_text, fallback_truncated

    return (
        text,
        title or None,
        text_truncated or title_truncated or parser.limit_exceeded,
    )


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
                    "Accept-Encoding": "identity",
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
                status_code = response.getcode()
                content_range_values = response_header_values(
                    response.headers,
                    "Content-Range",
                )
                if status_code != 200 or content_range_values:
                    raise IntakeError(
                        502,
                        "url_fetch_failed",
                        "URL fetch returned a partial or unsupported success status.",
                    )
                content_encoding_values = response_header_values(
                    response.headers,
                    "Content-Encoding",
                )
                if len(content_encoding_values) > 1:
                    raise IntakeError(
                        415,
                        "unsupported_content_encoding",
                        "Multiple content encodings are not supported.",
                    )
                content_encoding = (
                    content_encoding_values[0].strip().lower()
                    if content_encoding_values
                    else ""
                )
                if content_encoding not in {"", "identity"}:
                    raise IntakeError(
                        415,
                        "unsupported_content_encoding",
                        f"Unsupported content encoding: {content_encoding}.",
                    )
                content_type_values = response_header_values(
                    response.headers,
                    "Content-Type",
                )
                if len(content_type_values) != 1:
                    raise IntakeError(
                        415,
                        "unsupported_content_type",
                        "Exactly one Content-Type header is required.",
                    )
                content_type = content_type_values[0]
                content_length_values = response_header_values(
                    response.headers,
                    "Content-Length",
                )
                transfer_encoding_values = response_header_values(
                    response.headers,
                    "Transfer-Encoding",
                )
                if len(content_length_values) > 1 or len(transfer_encoding_values) > 1:
                    raise IntakeError(
                        502,
                        "url_fetch_failed",
                        "URL response framing headers are ambiguous.",
                    )
                declared_length = None
                if content_length_values:
                    raw_length = content_length_values[0].strip()
                    if len(raw_length) > 20 or not re.fullmatch(r"[0-9]+", raw_length):
                        raise IntakeError(
                            502,
                            "url_fetch_failed",
                            "URL response Content-Length is invalid.",
                        )
                    declared_length = int(raw_length)
                if transfer_encoding_values:
                    transfer_encoding = transfer_encoding_values[0].strip().lower()
                    if transfer_encoding != "chunked" or declared_length is not None:
                        raise IntakeError(
                            502,
                            "url_fetch_failed",
                            "URL response transfer framing is unsupported.",
                        )
                media_type, _ = parse_content_type(content_type)
                if media_type not in {
                    "text/html",
                    "text/plain",
                    "application/xhtml+xml",
                }:
                    raise IntakeError(
                        415,
                        "unsupported_content_type",
                        f"Unsupported content type: {content_type or 'unknown'}",
                    )

                body = response.read(MAX_URL_BYTES + 1)
                expected_read = (
                    min(declared_length, MAX_URL_BYTES + 1)
                    if declared_length is not None
                    else None
                )
                if expected_read is not None and len(body) != expected_read:
                    raise IntakeError(
                        502,
                        "url_fetch_failed",
                        "URL response ended before its declared Content-Length.",
                    )
                truncated = len(body) > MAX_URL_BYTES
                if truncated:
                    body = body[:MAX_URL_BYTES]

                text, title, text_truncated = extract_text_document(body, content_type)
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
                    "truncated": truncated or text_truncated,
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
                location_values = response_header_values(exc.headers, "Location")
                if len(location_values) != 1 or not location_values[0].strip():
                    raise IntakeError(
                        502,
                        "redirect_without_location",
                        "URL redirect must include exactly one non-empty Location header.",
                    )
                location = location_values[0].strip()

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
        try:
            encoded = dump_strict_json(payload).encode("utf-8")
        except (TypeError, ValueError, UnicodeEncodeError):
            status = 500
            encoded = dump_strict_json(
                {"error": "response payload is not valid strict JSON"}
            ).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def read_json_body(self, max_body_length: int) -> dict | None:
        content_length_values = response_header_values(
            self.headers,
            "Content-Length",
        )
        transfer_encoding_values = response_header_values(
            self.headers,
            "Transfer-Encoding",
        )

        if transfer_encoding_values:
            self.send_json(
                400,
                {"error": "Transfer-Encoding request bodies are not supported"},
            )
            return None

        if not content_length_values:
            self.send_json(411, {"error": "Content-Length header is required"})
            return None

        if len(content_length_values) != 1:
            self.send_json(
                400,
                {"error": "exactly one Content-Length header is required"},
            )
            return None

        content_length = content_length_values[0].strip()

        if len(content_length) > 20 or not re.fullmatch(r"[0-9]+", content_length):
            self.send_json(400, {"error": "Content-Length header must be an integer"})
            return None

        length = int(content_length)

        if length > max_body_length:
            self.send_json(
                413,
                {
                    "error": "request body too large",
                    "limit_bytes": max_body_length,
                },
            )
            return None

        try:
            raw_bytes = self.rfile.read(length)
        except (OSError, ValueError):
            self.send_json(400, {"error": "request body could not be read"})
            return None

        if len(raw_bytes) != length:
            self.send_json(
                400,
                {"error": "request body ended before its declared Content-Length"},
            )
            return None

        try:
            raw = raw_bytes.decode("utf-8")
        except UnicodeDecodeError:
            self.send_json(400, {"error": "request body must be valid UTF-8"})
            return None

        try:
            payload = load_strict_json(raw)
        except json.JSONDecodeError as exc:
            self.send_json(400, {"error": f"invalid JSON: {exc.msg}"})
            return None
        except ValueError as exc:
            self.send_json(400, {"error": f"invalid JSON: {exc}"})
            return None

        if not isinstance(payload, dict):
            self.send_json(400, {"error": "JSON body must be an object"})
            return None

        return payload

    def handle_url_intake(self) -> None:
        payload = self.read_json_body(MAX_URL_BODY_LENGTH)
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
        payload = self.read_json_body(MAX_ANALYZE_BODY_LENGTH)
        if payload is None:
            return

        try:
            serialized_payload = dump_strict_json(payload)
        except (TypeError, ValueError):
            self.send_json(
                500,
                {"error": "cannot serialize case input as strict JSON"},
            )
            return

        case_dir = SHARED / "api" / "cases"
        case_path: Path | None = None
        try:
            case_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
            case_dir.chmod(0o700)
            descriptor, raw_case_path = tempfile.mkstemp(
                prefix="case-",
                suffix=".json",
                dir=case_dir,
            )
            case_path = Path(raw_case_path)
            with os.fdopen(
                descriptor,
                "w",
                encoding="utf-8",
                newline="\n",
            ) as case_file:
                case_file.write(serialized_payload)
        except OSError as exc:
            if case_path is not None:
                try:
                    case_path.unlink(missing_ok=True)
                except OSError:
                    pass
            self.send_json(500, {"error": f"cannot create temporary case input: {exc}"})
            return

        cleanup_error: OSError | None = None
        try:
            code, stdout, stderr = run_command([
                "/opt/hub-optimus/shared/bin/hub-core",
                "analyze",
                str(case_path),
            ])
        except OSError as exc:
            code, stdout, stderr = 1, "", str(exc)
        finally:
            try:
                case_path.unlink()
            except OSError as exc:
                cleanup_error = exc

        if cleanup_error is not None:
            self.send_json(500, {"error": "cannot remove temporary case input"})
            return

        run_id = core_run_id(stdout)
        if code != 0:
            failure = {
                "error": "analysis failed",
                "stderr": stderr,
                "stdout": stdout,
            }
            if run_id is not None:
                failure["run_id"] = run_id
                failure["run_path"] = str(
                    SHARED / "runs" / "analyze" / run_id
                )
            self.send_json(
                500,
                failure,
            )
            return

        if run_id is None:
            self.send_json(
                500,
                {
                    "error": "analysis completed without one valid run identity",
                    "stdout": stdout,
                },
            )
            return

        run_path = SHARED / "runs" / "analyze" / run_id
        result_path = run_path / "analysis_result.json"

        try:
            analysis_result = load_strict_json(
                result_path.read_text(encoding="utf-8")
            )
        except OSError as exc:
            self.send_json(500, {"error": f"cannot read analysis result: {exc}"})
            return
        except json.JSONDecodeError as exc:
            self.send_json(500, {"error": f"analysis result is invalid JSON: {exc.msg}"})
            return
        except ValueError as exc:
            self.send_json(500, {"error": f"analysis result is invalid JSON: {exc}"})
            return

        self.send_json(
            200,
            {
                "status": "ok",
                "run_id": run_id,
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
