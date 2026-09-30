"""Provider-neutral contracts for the isolated HUB_Optimus Connect prototype.

The records in this module are stdlib-only, immutable at their public
boundaries, and deterministic to serialize.  They do not provide networking,
authentication, provider SDKs, durable storage, or governance authority.
"""

from __future__ import annotations

import hashlib
import ipaddress
import json
import math
import re
import unicodedata
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from types import MappingProxyType
from typing import Any, Protocol, TypeVar
from urllib.parse import parse_qsl, urlsplit


SHA256_REF_PATTERN = re.compile(r"sha256:[0-9a-f]{64}")
IDENTIFIER_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}")
DNS_LABEL_PATTERN = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?")
SENSITIVE_URL_QUERY_KEYS = {
    "accesstoken",
    "apikey",
    "authorization",
    "clientsecret",
    "code",
    "credential",
    "idtoken",
    "jwt",
    "key",
    "otp",
    "password",
    "redirect",
    "redirecturi",
    "returnurl",
    "samlresponse",
    "secret",
    "sig",
    "signature",
    "ticket",
    "token",
}
SENSITIVE_URL_QUERY_SUFFIXES = {
    "accesstoken",
    "apikey",
    "authorization",
    "clientsecret",
    "credential",
    "idtoken",
    "jwt",
    "otp",
    "password",
    "secret",
    "securitytoken",
    "signature",
    "token",
}
_MAPPING_PROXY_TYPE = type(MappingProxyType({}))

PlanT_contra = TypeVar("PlanT_contra", contravariant=True)
PlanT_co = TypeVar("PlanT_co", covariant=True)
SignalT_co = TypeVar("SignalT_co", covariant=True)
IntentT_contra = TypeVar("IntentT_contra", contravariant=True)


class SignalBridgeError(RuntimeError):
    """Base error for the phase-one signal bridge."""


class BridgeContractError(ValueError, SignalBridgeError):
    """A typed bridge record violated its local contract."""


class BridgePolicyError(PermissionError, SignalBridgeError):
    """A request was validly shaped but outside the allowed policy."""


class BridgeDisabledError(BridgePolicyError):
    """An adapter was invoked while its external boundary was disabled."""


class DataClassification(str, Enum):
    """Data classifications understood by the phase-one provider boundary."""

    PUBLIC = "public"
    INTERNAL = "internal"
    CLIENT = "client"


class CitationScope(str, Enum):
    """Whether a provider encountered a URL or cited it inline."""

    ENCOUNTERED = "encountered"
    INLINE_CITED = "inline_cited"


def _validate_unicode_scalars(value: str, field_name: str) -> None:
    for character in value:
        codepoint = ord(character)
        if 0xD800 <= codepoint <= 0xDFFF:
            raise BridgeContractError(
                f"{field_name} contains an unpaired Unicode surrogate"
            )


def require_plain_bool(value: Any, field_name: str) -> bool:
    """Require an exact bool rather than an integer-compatible value."""

    if type(value) is not bool:
        raise BridgeContractError(f"{field_name} must be a bool")
    return value


def require_plain_string(
    value: Any,
    field_name: str,
    *,
    allow_empty: bool = False,
    allow_line_breaks: bool = False,
) -> str:
    """Validate a plain string without retaining subclass-defined behavior."""

    if type(value) is not str:
        raise BridgeContractError(f"{field_name} must be a plain string")
    _validate_unicode_scalars(value, field_name)
    if not allow_empty and not value.strip():
        raise BridgeContractError(f"{field_name} must not be empty")
    for character in value:
        codepoint = ord(character)
        if codepoint == 0 or (
            codepoint < 32
            and not (allow_line_breaks and character in {"\n", "\r", "\t"})
        ):
            raise BridgeContractError(f"{field_name} contains a control character")
    return value


def require_identifier(value: Any, field_name: str) -> str:
    """Require a bounded opaque identifier suitable for deterministic records."""

    value = require_plain_string(value, field_name)
    if IDENTIFIER_PATTERN.fullmatch(value) is None:
        raise BridgeContractError(f"{field_name} is not a valid opaque identifier")
    return value


def require_sha256_ref(value: Any, field_name: str) -> str:
    """Require the repository's prefixed lowercase SHA-256 representation."""

    value = require_plain_string(value, field_name)
    if SHA256_REF_PATTERN.fullmatch(value) is None:
        raise BridgeContractError(f"{field_name} must use sha256:<64 lowercase hex>")
    return value


def require_string_tuple(values: Any, field_name: str) -> tuple[str, ...]:
    """Require an immutable tuple of non-empty plain strings."""

    if type(values) is not tuple:
        raise BridgeContractError(f"{field_name} must be a tuple")
    checked = tuple(
        require_plain_string(value, f"{field_name}[{index}]")
        for index, value in enumerate(values)
    )
    if len(set(checked)) != len(checked):
        raise BridgeContractError(f"{field_name} must not contain duplicates")
    return checked


def normalize_text(value: Any, field_name: str) -> str:
    """Normalize approval-relevant text to NFC with LF line endings."""

    value = require_plain_string(
        value,
        field_name,
        allow_line_breaks=True,
    )
    return unicodedata.normalize("NFC", value.replace("\r\n", "\n").replace("\r", "\n"))


def normalize_utc_timestamp(value: Any, field_name: str) -> str:
    """Return one timezone-aware ISO-8601 timestamp in canonical UTC form."""

    value = require_plain_string(value, field_name)
    candidate = f"{value[:-1]}+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError as error:
        raise BridgeContractError(f"{field_name} must be an ISO-8601 timestamp") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise BridgeContractError(f"{field_name} must include a timezone")
    parsed = parsed.astimezone(timezone.utc)
    timespec = "microseconds" if parsed.microsecond else "seconds"
    return parsed.isoformat(timespec=timespec).replace("+00:00", "Z")


def snapshot_json(value: Any, path: str = "$") -> Any:
    """Copy a strict JSON value without invoking user-defined mapping hooks."""

    value_type = type(value)
    if value is None or value_type in {bool, int}:
        return value
    if value_type is str:
        _validate_unicode_scalars(value, path)
        return value
    if value_type is float:
        if not math.isfinite(value):
            raise BridgeContractError(f"{path} contains a non-finite number")
        return value
    if value_type in {list, tuple}:
        return [
            snapshot_json(item, f"{path}[{index}]")
            for index, item in enumerate(value)
        ]
    if value_type is dict:
        snapshot: dict[str, Any] = {}
        for key, item in value.items():
            if type(key) is not str:
                raise BridgeContractError(f"{path} contains a non-string key")
            _validate_unicode_scalars(key, f"{path} key")
            snapshot[key] = snapshot_json(item, f"{path}.{key}")
        return snapshot
    raise BridgeContractError(f"{path} contains a non-JSON value")


def freeze_json(value: Any) -> Any:
    """Return a recursively immutable copy of one strict JSON value."""

    def freeze_snapshot(item: Any) -> Any:
        if type(item) is dict:
            return MappingProxyType(
                {key: freeze_snapshot(child) for key, child in item.items()}
            )
        if type(item) is list:
            return tuple(freeze_snapshot(child) for child in item)
        return item

    return freeze_snapshot(snapshot_json(value))


def thaw_json(value: Any, path: str = "$") -> Any:
    """Return a fresh mutable JSON copy of a value produced by ``freeze_json``."""

    value_type = type(value)
    if value is None or value_type in {bool, int, float, str}:
        return snapshot_json(value, path)
    if value_type is tuple:
        return [thaw_json(item, f"{path}[{index}]") for index, item in enumerate(value)]
    if value_type is _MAPPING_PROXY_TYPE:
        return {
            key: thaw_json(item, f"{path}.{key}")
            for key, item in value.items()
        }
    raise BridgeContractError(f"{path} is not a frozen JSON value")


def canonical_json_bytes(value: Any) -> bytes:
    """Serialize a strict JSON value deterministically as UTF-8."""

    return json.dumps(
        snapshot_json(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    """Return one prefixed lowercase SHA-256 digest."""

    return f"sha256:{hashlib.sha256(value).hexdigest()}"


def sha256_text(value: str) -> str:
    """Hash one plain Unicode string as UTF-8 without logging it."""

    require_plain_string(value, "hash input", allow_empty=True, allow_line_breaks=True)
    return sha256_bytes(value.encode("utf-8"))


def canonical_payload_hash(value: Any) -> str:
    """Hash one explicit deterministic JSON descriptor."""

    return sha256_bytes(canonical_json_bytes(value))


def validate_public_https_url(value: Any, field_name: str = "url") -> str:
    """Reject credential-bearing, local, fragmented, or malformed HTTPS URLs."""

    value = require_plain_string(value, field_name)
    if "\\" in value or any(
        character.isspace() or ord(character) == 127 for character in value
    ):
        raise BridgeContractError(
            f"{field_name} contains browser-ambiguous characters"
        )
    try:
        parsed = urlsplit(value)
        parsed_port = parsed.port
    except ValueError as error:
        raise BridgeContractError(f"{field_name} has an invalid host or port") from error
    if parsed.scheme.lower() != "https" or not parsed.hostname:
        raise BridgeContractError(f"{field_name} must be an absolute HTTPS URL")
    if parsed.username is not None or parsed.password is not None:
        raise BridgeContractError(f"{field_name} must not contain user information")
    if parsed.fragment:
        raise BridgeContractError(f"{field_name} must not contain a fragment")
    if parsed_port is not None and not 1 <= parsed_port <= 65535:
        raise BridgeContractError(f"{field_name} has an invalid port")

    hostname = parsed.hostname.rstrip(".").lower()
    try:
        ascii_hostname = hostname.encode("idna").decode("ascii")
    except UnicodeError as error:
        raise BridgeContractError(f"{field_name} has an invalid hostname") from error
    if not ascii_hostname or any(not label for label in ascii_hostname.split(".")):
        raise BridgeContractError(f"{field_name} has an invalid hostname")
    if ascii_hostname in {"localhost", "localhost.localdomain"} or ascii_hostname.endswith(
        (".local", ".internal", ".localhost")
    ):
        raise BridgeContractError(f"{field_name} must not target a local host")
    try:
        address = ipaddress.ip_address(ascii_hostname)
    except ValueError:
        address = None
    if address is not None and (not address.is_global or address.is_multicast):
        raise BridgeContractError(
            f"{field_name} must target a public unicast IP"
        )
    if address is None:
        labels = ascii_hostname.split(".")
        if (
            len(labels) < 2
            or not labels[-1][0].isalpha()
            or any(DNS_LABEL_PATTERN.fullmatch(label) is None for label in labels)
        ):
            raise BridgeContractError(
                f"{field_name} must use a canonical public hostname"
            )

    for key, query_value in parse_qsl(parsed.query, keep_blank_values=True):
        normalized_key = re.sub(r"[^a-z0-9]", "", key.lower())
        if normalized_key in SENSITIVE_URL_QUERY_KEYS or any(
            normalized_key.endswith(suffix)
            for suffix in SENSITIVE_URL_QUERY_SUFFIXES
        ):
            raise BridgeContractError(
                f"{field_name} contains a sensitive query parameter"
            )
        lowered_value = query_value.lower()
        if any(
            marker in lowered_value
            for marker in ("token=", "password=", "secret=", "otp=", "signature=")
        ):
            raise BridgeContractError(
                f"{field_name} contains nested sensitive material"
            )
    return value


@dataclass(frozen=True)
class SourceCitation:
    """Provider-returned URL provenance with explicit citation scope."""

    url: str = field(repr=False)
    scope: CitationScope
    label: str | None = None
    start_index: int | None = None
    end_index: int | None = None

    def __post_init__(self) -> None:
        validate_public_https_url(self.url, "url")
        if type(self.scope) is not CitationScope:
            raise BridgeContractError("scope must be a CitationScope")
        if self.label is not None:
            require_plain_string(self.label, "label")
        positions = (self.start_index, self.end_index)
        if self.scope is CitationScope.INLINE_CITED and not all(
            type(position) is int for position in positions
        ):
            raise BridgeContractError(
                "inline citations require start_index and end_index"
            )
        if self.scope is CitationScope.ENCOUNTERED and any(
            position is not None for position in positions
        ):
            raise BridgeContractError(
                "encountered citations must not claim inline indexes"
            )
        if any(position is not None for position in positions):
            if not all(type(position) is int for position in positions):
                raise BridgeContractError(
                    "start_index and end_index must be provided together"
                )
            if self.start_index < 0 or self.end_index < self.start_index:
                raise BridgeContractError("citation indexes are invalid")

    def to_dict(self) -> dict[str, Any]:
        return {
            "url": self.url,
            "scope": self.scope.value,
            "label": self.label,
            "start_index": self.start_index,
            "end_index": self.end_index,
        }


@dataclass(frozen=True)
class UsageMetric:
    """One non-negative provider usage counter."""

    name: str
    value: int

    def __post_init__(self) -> None:
        require_identifier(self.name, "name")
        if type(self.value) is not int or self.value < 0:
            raise BridgeContractError("value must be a non-negative integer")

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "value": self.value}


@dataclass(frozen=True)
class AnalysisRequest:
    """Provider-neutral analytical request with an explicit data boundary."""

    request_id: str
    case_id: str
    task: str
    input_text: str = field(repr=False)
    output_schema: Mapping[str, Any] = field(repr=False)
    source_refs: tuple[str, ...] = ()
    output_contract: str = "optimus-analysis.v1"
    output_schema_name: str = "optimus_analysis_v1"
    data_classification: DataClassification = DataClassification.PUBLIC

    def __post_init__(self) -> None:
        require_identifier(self.request_id, "request_id")
        require_identifier(self.case_id, "case_id")
        object.__setattr__(self, "task", normalize_text(self.task, "task"))
        object.__setattr__(
            self,
            "input_text",
            normalize_text(self.input_text, "input_text"),
        )
        if type(self.output_schema) is not dict:
            raise BridgeContractError("output_schema must be a plain dict")
        output_schema = snapshot_json(self.output_schema)
        if output_schema.get("type") != "object":
            raise BridgeContractError("output_schema must describe an object")
        if output_schema.get("additionalProperties") is not False:
            raise BridgeContractError(
                "output_schema must set additionalProperties to false"
            )
        object.__setattr__(self, "output_schema", freeze_json(output_schema))
        require_string_tuple(self.source_refs, "source_refs")
        require_identifier(self.output_contract, "output_contract")
        schema_name = require_plain_string(
            self.output_schema_name,
            "output_schema_name",
        )
        if re.fullmatch(r"[A-Za-z0-9_-]{1,64}", schema_name) is None:
            raise BridgeContractError("output_schema_name is invalid")
        if type(self.data_classification) is not DataClassification:
            raise BridgeContractError(
                "data_classification must be a DataClassification"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "case_id": self.case_id,
            "task": self.task,
            "input_text": self.input_text,
            "output_schema": thaw_json(self.output_schema),
            "source_refs": list(self.source_refs),
            "output_contract": self.output_contract,
            "output_schema_name": self.output_schema_name,
            "data_classification": self.data_classification.value,
        }

    def to_audit_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "case_id": self.case_id,
            "task_sha256": sha256_text(self.task),
            "input_text_sha256": sha256_text(self.input_text),
            "input_characters": len(self.input_text),
            "source_ref_sha256": [sha256_text(ref) for ref in self.source_refs],
            "source_ref_count": len(self.source_refs),
            "output_contract": self.output_contract,
            "output_schema_name": self.output_schema_name,
            "output_schema_sha256": canonical_payload_hash(
                thaw_json(self.output_schema)
            ),
            "data_classification": self.data_classification.value,
        }


@dataclass(frozen=True)
class AnalysisResult:
    """Structured provider result separated from its raw response envelope."""

    request_id: str
    provider: str
    response_id: str
    model_resolved: str
    status: str
    output_json: Mapping[str, Any] = field(repr=False)
    plan_sha256: str
    raw_response_sha256: str
    zdr_attested: bool | None = None
    citations: tuple[SourceCitation, ...] = ()
    usage: tuple[UsageMetric, ...] = ()

    def __post_init__(self) -> None:
        require_identifier(self.request_id, "request_id")
        require_identifier(self.provider, "provider")
        require_identifier(self.response_id, "response_id")
        require_plain_string(self.model_resolved, "model_resolved")
        if self.status not in {"completed", "incomplete", "failed"}:
            raise BridgeContractError("status is not recognized")
        if type(self.output_json) is not dict:
            raise BridgeContractError("output_json must be a plain dict")
        object.__setattr__(self, "output_json", freeze_json(self.output_json))
        require_sha256_ref(self.plan_sha256, "plan_sha256")
        require_sha256_ref(self.raw_response_sha256, "raw_response_sha256")
        if self.zdr_attested is not None:
            require_plain_bool(self.zdr_attested, "zdr_attested")
        if type(self.citations) is not tuple or not all(
            type(citation) is SourceCitation for citation in self.citations
        ):
            raise BridgeContractError("citations must be a tuple of SourceCitation")
        if type(self.usage) is not tuple or not all(
            type(metric) is UsageMetric for metric in self.usage
        ):
            raise BridgeContractError("usage must be a tuple of UsageMetric")

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "provider": self.provider,
            "response_id": self.response_id,
            "model_resolved": self.model_resolved,
            "status": self.status,
            "output_json": thaw_json(self.output_json),
            "citations": [citation.to_dict() for citation in self.citations],
            "usage": [metric.to_dict() for metric in self.usage],
            "plan_sha256": self.plan_sha256,
            "raw_response_sha256": self.raw_response_sha256,
            "zdr_attested": self.zdr_attested,
        }

    def to_audit_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "provider": self.provider,
            "response_id": self.response_id,
            "model_resolved_sha256": sha256_text(self.model_resolved),
            "status": self.status,
            "output_json_sha256": canonical_payload_hash(thaw_json(self.output_json)),
            "citation_url_sha256": [
                sha256_text(citation.url) for citation in self.citations
            ],
            "citation_scopes": [
                citation.scope.value for citation in self.citations
            ],
            "citation_count": len(self.citations),
            "usage": [metric.to_dict() for metric in self.usage],
            "plan_sha256": self.plan_sha256,
            "raw_response_sha256": self.raw_response_sha256,
            "zdr_attested": self.zdr_attested,
        }


class AnalysisTransport(Protocol[PlanT_contra]):
    """Injected provider transport; no implementation ships in phase one."""

    def execute(self, plan: PlanT_contra) -> AnalysisResult:
        """Execute one already validated provider call plan."""


class AnalyticalProvider(Protocol[PlanT_co]):
    """Provider-neutral analytical planning and execution surface."""

    def plan(self, request: AnalysisRequest) -> PlanT_co:
        """Build one deterministic provider call plan."""

    def analyze(self, request: AnalysisRequest) -> AnalysisResult:
        """Return one provider result under the adapter's explicit policy."""


class SignalSource(Protocol[SignalT_co]):
    """Provider-neutral read-only signal source."""

    def read(self, source_ref: str) -> SignalT_co:
        """Read one source reference and return a bounded derivative."""


class PublicationPlanner(Protocol[IntentT_contra, PlanT_co]):
    """Provider-neutral local publication planning surface."""

    def plan(self, intent: IntentT_contra) -> PlanT_co:
        """Return a deterministic plan without publishing it."""
