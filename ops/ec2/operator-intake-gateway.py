#!/usr/bin/env python3
"""Authenticated, loopback-only gateway for controlled Operator URL intake.

The public reverse proxy is responsible for OIDC.  It must remove all client
identity headers and add the four ``X-Hub-*`` headers defined below.  A shared
capability is required as a second, local trust boundary.  The capability,
identity, client address, submitted URL, and upstream response are never
logged by this process.
"""

from __future__ import annotations

import hmac
import http.client
import ipaddress
import json
import os
import re
import secrets
import socket
import sys
import threading
import time
import uuid
from collections import OrderedDict, deque
from dataclasses import dataclass
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn
from typing import Callable, Mapping, Protocol
from urllib.parse import urlsplit


BIND_HOST = "127.0.0.1"
BIND_PORT = 8081
UPSTREAM_HOST = "127.0.0.1"
UPSTREAM_PORT = 8080
UPSTREAM_PATH = "/intake/url"
PUBLIC_PATH = "/intake/url"
EXPECTED_ORIGIN = "https://api.huboptimus.dev"

CAPABILITY_ENV = "HUB_OPERATOR_INTAKE_CAPABILITY"
CAPABILITY_HEADER = "X-Hub-Internal-Capability"
SUBJECT_HEADER = "X-Hub-Authenticated-Subject"
ROLES_HEADER = "X-Hub-Authenticated-Roles"
CLIENT_IP_HEADER = "X-Hub-Client-IP"
CORRELATION_HEADER = "X-Request-ID"

SCHEMA_VERSION = "operator_public_intake.v1"
MAX_REQUEST_BODY_BYTES = 4096
MAX_URL_CHARACTERS = 2048
MAX_UPSTREAM_RESPONSE_BYTES = 131_072
UPSTREAM_TIMEOUT_SECONDS = 12.0
CLIENT_IO_TIMEOUT_SECONDS = 10.0
RATE_LIMIT_REQUESTS = 12
RATE_LIMIT_WINDOW_SECONDS = 60.0
MAX_RATE_LIMIT_SUBJECT_KEYS = 4096
MAX_RATE_LIMIT_IP_KEYS = 4096

AUTHORIZED_ROLES = frozenset({"HUB.Owner", "HUB.Operator"})
CAPABILITY_PATTERN = re.compile(r"\A[A-Za-z0-9_-]{43,128}\Z")
OPAQUE_SUBJECT_PATTERN = re.compile(r"\A[A-Za-z0-9._~-]{8,255}\Z")
ROLE_PATTERN = re.compile(r"\A[A-Za-z][A-Za-z0-9._-]{0,63}\Z")
REQUEST_ID_PATTERN = re.compile(r"\Areq_[0-9a-f]{32}\Z")
NGINX_REQUEST_ID_PATTERN = re.compile(r"\A[0-9a-f]{32}\Z")
ERROR_CODE_PATTERN = re.compile(r"\A[a-z][a-z0-9_]{0,63}\Z")

GATEWAY_ERROR_STATUS = {
    "forbidden": 403,
    "internal_error": 500,
    "invalid_client_ip": 400,
    "invalid_framing": 400,
    "invalid_request": 400,
    "length_required": 411,
    "method_not_allowed": 405,
    "not_found": 404,
    "origin_forbidden": 403,
    "rate_limited": 429,
    "request_timeout": 408,
    "request_too_large": 413,
    "subject_busy": 429,
    "unauthorized": 401,
    "unsupported_media_type": 415,
    "untrusted_headers": 400,
    "upstream_busy": 503,
    "upstream_malformed": 502,
    "upstream_response_too_large": 502,
    "upstream_timeout": 504,
    "upstream_unavailable": 502,
}

UPSTREAM_ERROR_STATUS = {
    "blocked_url_host": 400,
    "empty_extraction": 422,
    "invalid_url": 400,
    "invalid_url_host": 400,
    "invalid_url_port": 400,
    "redirect_without_location": 502,
    "too_many_redirects": 508,
    "unresolvable_url_host": 400,
    "unsupported_content_encoding": 415,
    "unsupported_content_type": 415,
    "unsupported_url_credentials": 400,
    "unsupported_url_iri": 400,
    "unsupported_url_port": 400,
    "unsupported_url_scheme": 400,
    "url_fetch_failed": 502,
    "url_fetch_timeout": 504,
    "url_fetch_unavailable": 503,
    "url_too_long": 414,
}

UNTRUSTED_EXACT_HEADERS = frozenset(
    {
        "authorization",
        "cookie",
        "forwarded",
        "proxy-authorization",
        "remote-user",
        "x-real-ip",
    }
)
UNTRUSTED_HEADER_PREFIXES = (
    "x-auth-request-",
    "x-forwarded-",
    "x-ms-client-principal",
)


class ConfigurationError(RuntimeError):
    """The gateway cannot start safely with its current configuration."""


class GatewayError(Exception):
    """A controlled public error."""

    def __init__(
        self,
        status: int,
        code: str,
        message: str,
        *,
        retry_after: int | None = None,
    ) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
        self.retry_after = retry_after


@dataclass(frozen=True)
class Identity:
    subject: str
    roles: frozenset[str]
    client_ip: str


@dataclass(frozen=True)
class UpstreamResult:
    status: int
    payload: dict
    is_success: bool


class HeadersLike(Protocol):
    def get_all(self, name: str, failobj=None): ...

    def keys(self): ...


def _contains_unsafe_header_character(value: str) -> bool:
    return any(ord(character) < 0x20 or ord(character) == 0x7F for character in value)


def _single_header(
    headers: HeadersLike,
    name: str,
    *,
    status: int,
    code: str,
    message: str,
) -> str:
    values = list(headers.get_all(name, []) or [])
    if len(values) != 1:
        raise GatewayError(status, code, message)
    value = values[0]
    if not isinstance(value, str) or not value or _contains_unsafe_header_character(value):
        raise GatewayError(status, code, message)
    return value


def _reject_untrusted_headers(headers: HeadersLike) -> None:
    for raw_name in headers.keys():
        name = str(raw_name).lower()
        if name in UNTRUSTED_EXACT_HEADERS or any(
            name.startswith(prefix) for prefix in UNTRUSTED_HEADER_PREFIXES
        ):
            raise GatewayError(
                400,
                "untrusted_headers",
                "Untrusted client identity or forwarding headers are not accepted.",
            )


def authenticate_request(headers: HeadersLike, configured_capability: str) -> Identity:
    """Authenticate only the sanitized, capability-bound internal headers."""

    _reject_untrusted_headers(headers)

    supplied_capability = _single_header(
        headers,
        CAPABILITY_HEADER,
        status=401,
        code="unauthorized",
        message="Authentication is required.",
    )
    capability_has_valid_shape = bool(CAPABILITY_PATTERN.fullmatch(supplied_capability))
    capability_matches = hmac.compare_digest(
        supplied_capability.encode("utf-8"),
        configured_capability.encode("utf-8"),
    )
    if not capability_has_valid_shape or not capability_matches:
        raise GatewayError(401, "unauthorized", "Authentication is required.")

    origin = _single_header(
        headers,
        "Origin",
        status=403,
        code="origin_forbidden",
        message="The request origin is not allowed.",
    )
    if origin != EXPECTED_ORIGIN:
        raise GatewayError(
            403,
            "origin_forbidden",
            "The request origin is not allowed.",
        )

    subject = _single_header(
        headers,
        SUBJECT_HEADER,
        status=401,
        code="unauthorized",
        message="Authentication is required.",
    )
    if not OPAQUE_SUBJECT_PATTERN.fullmatch(subject) or "@" in subject:
        raise GatewayError(401, "unauthorized", "Authentication is required.")

    roles_value = _single_header(
        headers,
        ROLES_HEADER,
        status=403,
        code="forbidden",
        message="The authenticated identity is not authorized for URL intake.",
    )
    role_items = [item.strip() for item in roles_value.split(",")]
    if (
        not role_items
        or any(not item or not ROLE_PATTERN.fullmatch(item) for item in role_items)
    ):
        raise GatewayError(
            403,
            "forbidden",
            "The authenticated identity is not authorized for URL intake.",
        )
    roles = frozenset(role_items)
    if not roles.intersection(AUTHORIZED_ROLES):
        raise GatewayError(
            403,
            "forbidden",
            "The authenticated identity is not authorized for URL intake.",
        )

    raw_client_ip = _single_header(
        headers,
        CLIENT_IP_HEADER,
        status=400,
        code="invalid_client_ip",
        message="The trusted client IP header is invalid.",
    )
    try:
        parsed_client_ip = ipaddress.ip_address(raw_client_ip)
        if isinstance(parsed_client_ip, ipaddress.IPv6Address):
            parsed_client_ip = parsed_client_ip.ipv4_mapped or parsed_client_ip
        client_ip = parsed_client_ip.compressed
    except ValueError as exc:
        raise GatewayError(
            400,
            "invalid_client_ip",
            "The trusted client IP header is invalid.",
        ) from exc

    return Identity(subject=subject, roles=roles, client_ip=client_ip)


def correlated_request_id(headers: HeadersLike) -> str:
    """Bind the public response to the request ID minted by trusted NGINX."""

    raw_request_id = _single_header(
        headers,
        CORRELATION_HEADER,
        status=400,
        code="invalid_framing",
        message="The request framing is invalid.",
    )
    if not NGINX_REQUEST_ID_PATTERN.fullmatch(raw_request_id):
        raise GatewayError(400, "invalid_framing", "The request framing is invalid.")
    request_id = f"req_{raw_request_id}"
    if not REQUEST_ID_PATTERN.fullmatch(request_id):  # defensive invariant
        raise GatewayError(500, "internal_error", "The request could not be completed.")
    return request_id


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"non-standard numeric constant {value} is not valid JSON")


def _reject_duplicate_object_keys(pairs: list[tuple[str, object]]) -> dict:
    result: dict = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("JSON object contains a duplicate key")
        result[key] = value
    return result


def _require_scalar_unicode(value, *, max_depth: int = 32, max_nodes: int = 4096) -> None:
    stack = [(value, 0)]
    visited = 0
    while stack:
        current, depth = stack.pop()
        visited += 1
        if visited > max_nodes or depth > max_depth:
            raise ValueError("JSON structure exceeds its safety limit")
        if isinstance(current, str):
            try:
                current.encode("utf-8")
            except UnicodeEncodeError as exc:
                raise ValueError("JSON contains non-scalar Unicode") from exc
        elif isinstance(current, list):
            stack.extend((item, depth + 1) for item in current)
        elif isinstance(current, dict):
            for key, item in current.items():
                stack.append((key, depth + 1))
                stack.append((item, depth + 1))


def load_strict_json(raw: bytes):
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise GatewayError(400, "invalid_request", "The request must be valid UTF-8 JSON.") from exc
    try:
        payload = json.loads(
            text,
            object_pairs_hook=_reject_duplicate_object_keys,
            parse_constant=_reject_json_constant,
        )
        _require_scalar_unicode(payload)
    except (json.JSONDecodeError, RecursionError, ValueError) as exc:
        raise GatewayError(400, "invalid_request", "The request must be valid UTF-8 JSON.") from exc
    return payload


def canonicalize_request_body(raw: bytes) -> bytes:
    payload = load_strict_json(raw)
    if not isinstance(payload, dict) or set(payload) != {"url"}:
        raise GatewayError(
            400,
            "invalid_request",
            "The request body must contain exactly one url field.",
        )
    url = payload["url"]
    if not isinstance(url, str) or not url or len(url) > MAX_URL_CHARACTERS:
        raise GatewayError(400, "invalid_request", "The url field is invalid.")
    try:
        canonical = json.dumps(
            {"url": url},
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
        ).encode("utf-8")
    except (TypeError, UnicodeEncodeError, ValueError) as exc:
        raise GatewayError(400, "invalid_request", "The url field is invalid.") from exc
    if len(canonical) > MAX_REQUEST_BODY_BYTES:
        raise GatewayError(413, "request_too_large", "The request body is too large.")
    return canonical


class SlidingWindowRateLimiter:
    """Atomically enforce independent subject and client-IP windows."""

    def __init__(
        self,
        limit: int = RATE_LIMIT_REQUESTS,
        window_seconds: float = RATE_LIMIT_WINDOW_SECONDS,
        max_subject_keys: int = MAX_RATE_LIMIT_SUBJECT_KEYS,
        max_ip_keys: int = MAX_RATE_LIMIT_IP_KEYS,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if limit < 1 or window_seconds <= 0 or max_subject_keys < 1 or max_ip_keys < 1:
            raise ValueError("rate limiter bounds must be positive")
        self.limit = limit
        self.window_seconds = window_seconds
        self.max_subject_keys = max_subject_keys
        self.max_ip_keys = max_ip_keys
        self.clock = clock
        self._subject_events: OrderedDict[str, deque[float]] = OrderedDict()
        self._ip_events: OrderedDict[str, deque[float]] = OrderedDict()
        self._lock = threading.Lock()

    @staticmethod
    def _remove_expired_keys(
        events_by_key: OrderedDict[str, deque[float]],
        cutoff: float,
    ) -> None:
        # OrderedDict order is refreshed only after a successful admission,
        # so the first key always has the oldest last-admitted event.
        while events_by_key:
            _, events = next(iter(events_by_key.items()))
            if events and events[-1] > cutoff:
                break
            events_by_key.popitem(last=False)

    def _require_key_capacity(
        self,
        events_by_key: OrderedDict[str, deque[float]],
        key: str,
        maximum: int,
    ) -> None:
        if key not in events_by_key and len(events_by_key) >= maximum:
            raise GatewayError(
                429,
                "rate_limited",
                "The URL intake rate limit has been reached.",
                retry_after=max(1, int(self.window_seconds)),
            )

    def consume(self, subject: str, client_ip: str) -> None:
        now = self.clock()
        cutoff = now - self.window_seconds
        with self._lock:
            self._remove_expired_keys(self._subject_events, cutoff)
            self._remove_expired_keys(self._ip_events, cutoff)
            self._require_key_capacity(
                self._subject_events,
                subject,
                self.max_subject_keys,
            )
            self._require_key_capacity(
                self._ip_events,
                client_ip,
                self.max_ip_keys,
            )

            subject_events = self._subject_events.get(subject, deque())
            ip_events = self._ip_events.get(client_ip, deque())
            for events in (subject_events, ip_events):
                while events and events[0] <= cutoff:
                    events.popleft()
            if len(subject_events) >= self.limit or len(ip_events) >= self.limit:
                raise GatewayError(
                    429,
                    "rate_limited",
                    "The URL intake rate limit has been reached.",
                    retry_after=max(1, int(self.window_seconds)),
                )
            subject_events.append(now)
            ip_events.append(now)
            self._subject_events[subject] = subject_events
            self._ip_events[client_ip] = ip_events
            self._subject_events.move_to_end(subject)
            self._ip_events.move_to_end(client_ip)


class ConcurrencyLimits:
    """One request per subject and one synchronous hub-api request globally."""

    def __init__(self) -> None:
        self._active_subjects: set[str] = set()
        self._subject_lock = threading.Lock()
        self._upstream = threading.BoundedSemaphore(1)

    def acquire_subject(self, subject: str) -> None:
        with self._subject_lock:
            if subject in self._active_subjects:
                raise GatewayError(
                    429,
                    "subject_busy",
                    "This identity already has an active URL intake request.",
                    retry_after=1,
                )
            self._active_subjects.add(subject)

    def release_subject(self, subject: str) -> None:
        with self._subject_lock:
            self._active_subjects.discard(subject)

    def acquire_upstream(self) -> None:
        if not self._upstream.acquire(blocking=False):
            raise GatewayError(
                503,
                "upstream_busy",
                "The URL intake service is busy. Try again shortly.",
                retry_after=1,
            )

    def release_upstream(self) -> None:
        self._upstream.release()


def _response_header_values(headers: list[tuple[str, str]], name: str) -> list[str]:
    return [value for key, value in headers if key.lower() == name.lower()]


def _requested_url_from_body(body: bytes) -> str:
    """Recover the exact URL sent on the one validated upstream request."""

    try:
        request_payload = load_strict_json(body)
    except GatewayError as exc:
        raise GatewayError(
            500,
            "internal_error",
            "The request could not be completed.",
        ) from exc
    if (
        not isinstance(request_payload, dict)
        or set(request_payload) != {"url"}
        or not isinstance(request_payload.get("url"), str)
        or not request_payload["url"]
    ):
        raise GatewayError(500, "internal_error", "The request could not be completed.")
    return request_payload["url"]


def _validate_success_payload(payload: dict, requested_url: str) -> None:
    required = {
        "status",
        "intake_type",
        "url",
        "final_url",
        "source_domain",
        "retrieved_at_utc",
        "title",
        "text",
        "content_type",
        "bytes_read",
        "truncated",
        "redirects",
        "verification_status",
        "learning_status",
        "extraction_notes",
    }
    if set(payload) != required:
        raise GatewayError(502, "upstream_malformed", "The local intake response was invalid.")
    if payload.get("status") != "ok" or payload.get("intake_type") != "controlled_url":
        raise GatewayError(502, "upstream_malformed", "The local intake response was invalid.")
    if any(
        not isinstance(payload.get(name), str) or not payload[name]
        for name in ("url", "final_url", "source_domain", "retrieved_at_utc", "text", "content_type")
    ):
        raise GatewayError(502, "upstream_malformed", "The local intake response was invalid.")
    try:
        retrieved_at = datetime.fromisoformat(payload["retrieved_at_utc"].replace("Z", "+00:00"))
    except ValueError as exc:
        raise GatewayError(
            502,
            "upstream_malformed",
            "The local intake response was invalid.",
        ) from exc
    if retrieved_at.tzinfo is None or retrieved_at.utcoffset() is None:
        raise GatewayError(502, "upstream_malformed", "The local intake response was invalid.")
    if len(payload["text"]) > 24_001:
        raise GatewayError(502, "upstream_malformed", "The local intake response was invalid.")
    if payload["title"] is not None and not isinstance(payload["title"], str):
        raise GatewayError(502, "upstream_malformed", "The local intake response was invalid.")
    if not isinstance(payload["bytes_read"], int) or isinstance(payload["bytes_read"], bool):
        raise GatewayError(502, "upstream_malformed", "The local intake response was invalid.")
    if not 0 <= payload["bytes_read"] <= 1_000_000:
        raise GatewayError(502, "upstream_malformed", "The local intake response was invalid.")
    if not isinstance(payload["truncated"], bool):
        raise GatewayError(502, "upstream_malformed", "The local intake response was invalid.")
    if not isinstance(payload["redirects"], list) or len(payload["redirects"]) > 3:
        raise GatewayError(502, "upstream_malformed", "The local intake response was invalid.")
    for redirect in payload["redirects"]:
        if not isinstance(redirect, dict) or set(redirect) != {"from", "to", "status"}:
            raise GatewayError(502, "upstream_malformed", "The local intake response was invalid.")
        if any(
            not isinstance(redirect[name], str) or not redirect[name]
            for name in ("from", "to")
        ):
            raise GatewayError(502, "upstream_malformed", "The local intake response was invalid.")
        if type(redirect["status"]) is not int or redirect["status"] not in {
            301,
            302,
            303,
            307,
            308,
        }:
            raise GatewayError(502, "upstream_malformed", "The local intake response was invalid.")
    if payload["url"] != requested_url:
        raise GatewayError(502, "upstream_malformed", "The local intake response was invalid.")
    provenance_cursor = requested_url
    for redirect in payload["redirects"]:
        if redirect["from"] != provenance_cursor:
            raise GatewayError(502, "upstream_malformed", "The local intake response was invalid.")
        provenance_cursor = redirect["to"]
    if payload["final_url"] != provenance_cursor:
        raise GatewayError(502, "upstream_malformed", "The local intake response was invalid.")
    try:
        final_url = urlsplit(payload["final_url"])
        final_hostname = final_url.hostname
    except (UnicodeError, ValueError) as exc:
        raise GatewayError(
            502,
            "upstream_malformed",
            "The local intake response was invalid.",
        ) from exc
    if (
        final_url.scheme not in {"http", "https"}
        or not final_hostname
        or payload["source_domain"] != final_hostname
    ):
        raise GatewayError(502, "upstream_malformed", "The local intake response was invalid.")
    if payload["verification_status"] != "unreviewed":
        raise GatewayError(502, "upstream_malformed", "The local intake response was invalid.")
    if payload["learning_status"] != "candidate-source-not-verified":
        raise GatewayError(502, "upstream_malformed", "The local intake response was invalid.")
    notes = payload["extraction_notes"]
    if not isinstance(notes, list) or not notes or any(
        not isinstance(note, str) or not note for note in notes
    ):
        raise GatewayError(502, "upstream_malformed", "The local intake response was invalid.")
    try:
        _require_scalar_unicode(payload)
    except ValueError as exc:
        raise GatewayError(
            502,
            "upstream_malformed",
            "The local intake response was invalid.",
        ) from exc


class UpstreamClient:
    def __init__(
        self,
        connection_factory: Callable[..., http.client.HTTPConnection] = http.client.HTTPConnection,
    ) -> None:
        self.connection_factory = connection_factory

    def request(self, body: bytes, *, request_id: str) -> UpstreamResult:
        requested_url = _requested_url_from_body(body)
        if not REQUEST_ID_PATTERN.fullmatch(request_id):
            raise GatewayError(500, "internal_error", "The request could not be completed.")
        connection = None
        try:
            connection = self.connection_factory(
                UPSTREAM_HOST,
                UPSTREAM_PORT,
                timeout=UPSTREAM_TIMEOUT_SECONDS,
            )
            connection.request(
                "POST",
                UPSTREAM_PATH,
                body=body,
                headers={
                    "Accept": "application/json",
                    "Connection": "close",
                    "Content-Type": "application/json",
                    CORRELATION_HEADER: request_id,
                },
            )
            response = connection.getresponse()
            status = response.status
            response_headers = list(response.getheaders())

            transfer_encoding = _response_header_values(response_headers, "Transfer-Encoding")
            content_lengths = _response_header_values(response_headers, "Content-Length")
            content_types = _response_header_values(response_headers, "Content-Type")
            if transfer_encoding or len(content_lengths) != 1 or len(content_types) != 1:
                raise GatewayError(502, "upstream_malformed", "The local intake response was invalid.")
            raw_length = content_lengths[0].strip()
            if len(raw_length) > 20 or not re.fullmatch(r"[0-9]+", raw_length):
                raise GatewayError(502, "upstream_malformed", "The local intake response was invalid.")
            length = int(raw_length)
            if length > MAX_UPSTREAM_RESPONSE_BYTES:
                raise GatewayError(
                    502,
                    "upstream_response_too_large",
                    "The local intake response exceeded its size limit.",
                )
            if content_types[0].strip().lower() not in {
                "application/json",
                "application/json; charset=utf-8",
            }:
                raise GatewayError(502, "upstream_malformed", "The local intake response was invalid.")
            raw = response.read(length)
            if len(raw) != length:
                raise GatewayError(502, "upstream_malformed", "The local intake response was invalid.")
        except GatewayError:
            raise
        except (socket.timeout, TimeoutError) as exc:
            raise GatewayError(
                504,
                "upstream_timeout",
                "The local intake service timed out.",
            ) from exc
        except (http.client.HTTPException, OSError) as exc:
            raise GatewayError(
                502,
                "upstream_unavailable",
                "The local intake service is unavailable.",
            ) from exc
        finally:
            if connection is not None:
                try:
                    connection.close()
                except OSError:
                    pass

        try:
            payload = load_strict_json(raw)
        except GatewayError as exc:
            raise GatewayError(502, "upstream_malformed", "The local intake response was invalid.") from exc
        if not isinstance(payload, dict):
            raise GatewayError(502, "upstream_malformed", "The local intake response was invalid.")

        if status == 200:
            _validate_success_payload(payload, requested_url)
            return UpstreamResult(status=200, payload=payload, is_success=True)

        if 400 <= status <= 599:
            code = payload.get("error")
            message = payload.get("message")
            if (
                set(payload)
                != {"status", "error", "message", "url", "verification_status"}
                or payload.get("status") != "error"
                or code not in UPSTREAM_ERROR_STATUS
                or UPSTREAM_ERROR_STATUS[code] != status
                or not isinstance(message, str)
                or not message
                or len(message) > 512
                or _contains_unsafe_header_character(message)
                or payload.get("url") != requested_url
                or payload.get("verification_status") != "unreviewed"
            ):
                raise GatewayError(502, "upstream_malformed", "The local intake response was invalid.")
            return UpstreamResult(
                status=status,
                payload={"code": code, "message": message},
                is_success=False,
            )

        raise GatewayError(502, "upstream_malformed", "The local intake response was invalid.")


class GatewayApplication:
    def __init__(
        self,
        capability: str,
        *,
        upstream: UpstreamClient | None = None,
        rate_limiter: SlidingWindowRateLimiter | None = None,
        concurrency: ConcurrencyLimits | None = None,
    ) -> None:
        if not isinstance(capability, str) or not CAPABILITY_PATTERN.fullmatch(capability):
            raise ConfigurationError(
                f"{CAPABILITY_ENV} must be a 43-128 character base64url value"
            )
        self.capability = capability
        self.upstream = upstream or UpstreamClient()
        self.rate_limiter = rate_limiter or SlidingWindowRateLimiter()
        self.concurrency = concurrency or ConcurrencyLimits()

    def process(self, headers: HeadersLike, raw_body: bytes) -> UpstreamResult:
        request_id = correlated_request_id(headers)
        identity = self.authenticate(headers)
        return self.process_authenticated(identity, raw_body, request_id=request_id)

    def authenticate(self, headers: HeadersLike) -> Identity:
        return authenticate_request(headers, self.capability)

    def process_authenticated(
        self,
        identity: Identity,
        raw_body: bytes,
        *,
        request_id: str,
    ) -> UpstreamResult:
        self.rate_limiter.consume(identity.subject, identity.client_ip)
        body = canonicalize_request_body(raw_body)

        self.concurrency.acquire_subject(identity.subject)
        try:
            self.concurrency.acquire_upstream()
            try:
                return self.upstream.request(body, request_id=request_id)
            finally:
                self.concurrency.release_upstream()
        finally:
            self.concurrency.release_subject(identity.subject)


def new_request_id() -> str:
    request_id = f"req_{uuid.UUID(bytes=secrets.token_bytes(16)).hex}"
    if not REQUEST_ID_PATTERN.fullmatch(request_id):  # defensive invariant
        raise RuntimeError("request ID generator returned an invalid value")
    return request_id


def success_envelope(request_id: str, intake: dict) -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "request_id": request_id,
        "status": "ok",
        "intake": intake,
    }


def error_envelope(request_id: str, code: str, message: str) -> dict:
    public_error_codes = GATEWAY_ERROR_STATUS.keys() | UPSTREAM_ERROR_STATUS.keys()
    if not ERROR_CODE_PATTERN.fullmatch(code) or code not in public_error_codes:
        code = "internal_error"
        message = "The request could not be completed."
    return {
        "schema_version": SCHEMA_VERSION,
        "request_id": request_id,
        "status": "error",
        "error": {"code": code, "message": message},
    }


class GatewayHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True
    block_on_close = True
    allow_reuse_address = False
    address_family = socket.AF_INET

    def __init__(self, server_address, handler_class, application: GatewayApplication):
        if server_address != (BIND_HOST, BIND_PORT):
            raise ConfigurationError("the gateway may bind only to 127.0.0.1:8081")
        self.application = application
        super().__init__(server_address, handler_class, bind_and_activate=True)

    def handle_error(self, request, client_address) -> None:
        # socketserver's default includes the peer address.  Keep operational
        # logging deliberately content- and identity-free.
        print("[operator-intake-gateway] request failed", file=sys.stderr, flush=True)


class Handler(BaseHTTPRequestHandler):
    server_version = "HUBOptimusOperatorIntakeGateway/1"
    sys_version = ""
    protocol_version = "HTTP/1.0"

    @property
    def application(self) -> GatewayApplication:
        return self.server.application  # type: ignore[attr-defined]

    def setup(self) -> None:
        super().setup()
        self.connection.settimeout(CLIENT_IO_TIMEOUT_SECONDS)

    def log_message(self, format: str, *args) -> None:
        # Never let BaseHTTPRequestHandler log a request line or headers.
        return

    def send_error(self, code: int, message=None, explain=None) -> None:
        # Parser failures must not fall back to BaseHTTPRequestHandler's HTML
        # body or interpolate the raw request line into logs or responses.
        self._send_json(
            400,
            error_envelope(
                new_request_id(),
                "invalid_framing",
                "The request framing is invalid.",
            ),
        )

    def _send_json(
        self,
        status: int,
        payload: dict,
        *,
        retry_after: int | None = None,
    ) -> None:
        encoded = json.dumps(
            payload,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8") + b"\n"
        self.close_connection = True
        self.send_response(status)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("X-Content-Type-Options", "nosniff")
        if retry_after is not None:
            self.send_header("Retry-After", str(retry_after))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(encoded)

    def _send_error(self, request_id: str, error: GatewayError) -> None:
        self._send_json(
            error.status,
            error_envelope(request_id, error.code, error.message),
            retry_after=error.retry_after,
        )

    def _read_request_body(self) -> bytes:
        if self.headers.get_all("Expect", []):
            raise GatewayError(400, "invalid_framing", "The request framing is invalid.")
        if self.headers.get_all("Transfer-Encoding", []):
            raise GatewayError(400, "invalid_framing", "The request framing is invalid.")
        if self.headers.get_all("Content-Encoding", []):
            raise GatewayError(400, "invalid_framing", "The request framing is invalid.")

        lengths = list(self.headers.get_all("Content-Length", []) or [])
        if not lengths:
            raise GatewayError(411, "length_required", "Content-Length is required.")
        if len(lengths) != 1:
            raise GatewayError(400, "invalid_framing", "The request framing is invalid.")
        raw_length = lengths[0].strip()
        if len(raw_length) > 20 or not re.fullmatch(r"[0-9]+", raw_length):
            raise GatewayError(400, "invalid_framing", "The request framing is invalid.")
        length = int(raw_length)
        if length > MAX_REQUEST_BODY_BYTES:
            raise GatewayError(413, "request_too_large", "The request body is too large.")

        content_types = list(self.headers.get_all("Content-Type", []) or [])
        if len(content_types) != 1 or content_types[0].strip().lower() not in {
            "application/json",
            "application/json; charset=utf-8",
        }:
            raise GatewayError(
                415,
                "unsupported_media_type",
                "Content-Type must be application/json with UTF-8 encoding.",
            )
        try:
            body = self.rfile.read(length)
        except (socket.timeout, TimeoutError) as exc:
            raise GatewayError(408, "request_timeout", "The request body timed out.") from exc
        except (OSError, ValueError) as exc:
            raise GatewayError(400, "invalid_framing", "The request framing is invalid.") from exc
        if len(body) != length:
            raise GatewayError(400, "invalid_framing", "The request framing is invalid.")
        return body

    def do_POST(self) -> None:
        request_id = new_request_id()
        if self.path != PUBLIC_PATH:
            self._send_error(
                request_id,
                GatewayError(404, "not_found", "The requested endpoint was not found."),
            )
            return
        try:
            request_id = correlated_request_id(self.headers)
            identity = self.application.authenticate(self.headers)
            body = self._read_request_body()
            result = self.application.process_authenticated(
                identity,
                body,
                request_id=request_id,
            )
            if result.is_success:
                self._send_json(200, success_envelope(request_id, result.payload))
            else:
                self._send_json(
                    result.status,
                    error_envelope(
                        request_id,
                        result.payload["code"],
                        result.payload["message"],
                    ),
                )
        except GatewayError as exc:
            self._send_error(request_id, exc)
        except Exception:
            self._send_error(
                request_id,
                GatewayError(500, "internal_error", "The request could not be completed."),
            )

    def _reject_method(self) -> None:
        request_id = new_request_id()
        if self.path != PUBLIC_PATH:
            self._send_error(
                request_id,
                GatewayError(404, "not_found", "The requested endpoint was not found."),
            )
            return
        self.send_response_only(405)
        # Use the common response writer after recording the required Allow header.
        # BaseHTTPRequestHandler cannot add a header before send_response(), so
        # construct the controlled response directly here.
        payload = error_envelope(
            request_id,
            "method_not_allowed",
            "Only POST is allowed for this endpoint.",
        )
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8") + b"\n"
        self.send_header("Allow", "POST")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.close_connection = True
        if self.command != "HEAD":
            self.wfile.write(encoded)

    do_DELETE = _reject_method
    do_CONNECT = _reject_method
    do_GET = _reject_method
    do_HEAD = _reject_method
    do_OPTIONS = _reject_method
    do_PATCH = _reject_method
    do_PUT = _reject_method
    do_TRACE = _reject_method


def load_application(env: Mapping[str, str] = os.environ) -> GatewayApplication:
    capability = env.get(CAPABILITY_ENV, "")
    return GatewayApplication(capability)


def main() -> int:
    try:
        application = load_application()
        server = GatewayHTTPServer((BIND_HOST, BIND_PORT), Handler, application)
    except (ConfigurationError, OSError):
        print("[operator-intake-gateway] startup failed", file=sys.stderr, flush=True)
        return 1

    print(
        f"[operator-intake-gateway] listening on http://{BIND_HOST}:{BIND_PORT}",
        file=sys.stderr,
        flush=True,
    )
    try:
        server.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
