"""Deterministic DryRun-only publication planning for ``@HubOptimus``.

The module has no live publish method and no X transport.  It can only build a
human-reviewable plan whose exact content is bound to a SHA-256 digest.  A
future live phase must separately bind OAuth ``GET /2/users/me`` identity,
human approval, and an immutable HUB Gateway receipt to that exact digest.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Any
from urllib.parse import urlsplit

from .contracts import (
    BridgeContractError,
    BridgeDisabledError,
    BridgePolicyError,
    canonical_payload_hash,
    normalize_text,
    require_identifier,
    require_plain_bool,
    require_plain_string,
    require_sha256_ref,
    require_string_tuple,
    sha256_text,
    validate_public_https_url,
)


OFFICIAL_X_ACCOUNT_HANDLE = "@HubOptimus"
X_PUBLICATION_SCHEMA_VERSION = "optimus-x-publication-plan.v1"
FULL_COMMIT_SHA_PATTERN = re.compile(r"[0-9a-f]{40}")
X_HANDLE_PATTERN = re.compile(r"@[A-Za-z0-9_]{1,15}")
MENTION_PATTERN = re.compile(r"(?<![A-Za-z0-9_])@[A-Za-z0-9_]{1,64}\b")
TEXT_URL_PATTERN = re.compile(r"(?i)\bhttps?://[^\s<>\"']+")
BARE_AUTOLINK_DOMAIN_PATTERN = re.compile(
    r"(?iu)(?<![@\w.-])"
    r"(?:www\.)?"
    r"(?:[^\W_](?:[\w-]{0,61}[^\W_])?\.)+"
    r"(?:xn--[a-z0-9-]{2,59}|[^\W\d_]{2,63})"
    r"(?::[0-9]{1,5})?"
    r"(?:/[^\s<>\"']*)?"
)
IDNA_DOT_TRANSLATION = str.maketrans(
    {
        "․": ".",  # U+2024 ONE DOT LEADER
        "。": ".",  # U+3002 IDEOGRAPHIC FULL STOP
        "﹒": ".",  # U+FE52 SMALL FULL STOP
        "．": ".",  # U+FF0E FULLWIDTH FULL STOP
        "｡": ".",  # U+FF61 HALFWIDTH IDEOGRAPHIC FULL STOP
    }
)
SECRET_TEXT_PATTERNS = (
    re.compile(
        r"(?i)(?:access[_-]?token|api[_-]?key|authorization|client[_-]?secret|"
        r"credential|password|passwd|private[_-]?key|secret|signature|sig|token)"
        r"\s*[:=]\s*\S+"
    ),
    re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~-]{12,}"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{12,}"),
    re.compile(r"\bxai-[A-Za-z0-9_-]{12,}", re.IGNORECASE),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}"),
    re.compile(r"\bAKIA[A-Z0-9]{16}\b"),
    re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]+"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
)


def _contains_credential_shape(value: str) -> bool:
    return any(pattern.search(value) for pattern in SECRET_TEXT_PATTERNS)


def _extract_text_urls(text: str) -> tuple[str, ...]:
    urls: list[str] = []
    for match in TEXT_URL_PATTERN.finditer(text):
        url = match.group(0).rstrip(".,;:!?")
        for opening, closing in (("(", ")"), ("[", "]"), ("{", "}")):
            while url.endswith(closing) and url.count(closing) > url.count(opening):
                url = url[:-1]
        urls.append(url)
    return tuple(urls)


def _contains_bare_autolink_domain(text: str) -> bool:
    """Detect domain-shaped text that X may link outside the declared URLs."""

    link_view = text.translate(IDNA_DOT_TRANSLATION)
    scrubbed = list(link_view)
    for match in TEXT_URL_PATTERN.finditer(link_view):
        scrubbed[match.start() : match.end()] = " " * (
            match.end() - match.start()
        )
    return BARE_AUTOLINK_DOMAIN_PATTERN.search("".join(scrubbed)) is not None


class XInteractionType(str, Enum):
    """Known interaction types; phase one allows only a standalone post."""

    ORIGINAL_POST = "original_post"
    REPLY = "reply"
    QUOTE = "quote"
    DIRECT_MESSAGE = "direct_message"
    LIKE = "like"
    FOLLOW = "follow"
    REPOST = "repost"


class MilestoneType(str, Enum):
    """Evidence-bearing project events that may enter a publication DryRun."""

    RELEASE = "release"
    QA_PASS = "qa_pass"
    BENCHMARK = "benchmark"
    PUBLIC_FEATURE = "public_feature"
    UPSTREAM_CONTRIBUTION = "upstream_contribution"
    PUBLIC_CASE_STUDY = "public_case_study"


@dataclass(frozen=True)
class XPublisherConfig:
    """Fail-closed account and mode configuration for phase one."""

    enabled: bool = False
    account_handle: str = OFFICIAL_X_ACCOUNT_HANDLE
    dry_run: bool = True

    def __post_init__(self) -> None:
        require_plain_bool(self.enabled, "enabled")
        require_plain_string(self.account_handle, "account_handle")
        if X_HANDLE_PATTERN.fullmatch(self.account_handle) is None:
            raise BridgeContractError("account_handle is not a valid X handle")
        require_plain_bool(self.dry_run, "dry_run")
        if self.account_handle != OFFICIAL_X_ACCOUNT_HANDLE:
            raise BridgePolicyError("X publication target is not the project account")
        if not self.dry_run:
            raise BridgePolicyError("live X publication is not implemented")


@dataclass(frozen=True)
class MediaMetadata:
    """Review-only media metadata; no bytes or X media IDs are accepted."""

    asset_id: str
    sha256: str
    media_type: str
    alt_text: str

    def __post_init__(self) -> None:
        require_identifier(self.asset_id, "asset_id")
        require_sha256_ref(self.sha256, "sha256")
        media_type = require_plain_string(self.media_type, "media_type")
        if re.fullmatch(r"[a-z0-9.+-]+/[a-z0-9.+-]+", media_type) is None:
            raise BridgeContractError("media_type must be a lowercase MIME type")
        object.__setattr__(self, "alt_text", normalize_text(self.alt_text, "alt_text"))
        if _contains_credential_shape(self.asset_id) or _contains_credential_shape(
            self.alt_text
        ):
            raise BridgeContractError("media metadata resembles credential material")

    def to_dict(self) -> dict[str, Any]:
        return {
            "asset_id": self.asset_id,
            "sha256": self.sha256,
            "media_type": self.media_type,
            "alt_text": self.alt_text,
        }

    def to_audit_dict(self) -> dict[str, Any]:
        return {
            "asset_id_sha256": sha256_text(self.asset_id),
            "sha256": self.sha256,
            "media_type": self.media_type,
            "alt_text_sha256": sha256_text(self.alt_text),
            "alt_text_characters": len(self.alt_text),
        }


@dataclass(frozen=True)
class PublicationChecks:
    """Human-supplied gate facts; these flags do not verify themselves."""

    evidence_verified: bool
    public_information_only: bool
    security_cleared: bool
    rights_cleared: bool
    is_draft: bool = False
    contains_client_data: bool = False
    has_unresolved_vulnerability: bool = False
    claims_affiliation_or_endorsement: bool = False
    has_commercial_commitment: bool = False
    commercial_commitment_ratified: bool = False
    repetitive_or_trend_driven: bool = False

    def __post_init__(self) -> None:
        for field_name, value in self.to_dict().items():
            require_plain_bool(value, field_name)

    def to_dict(self) -> dict[str, bool]:
        return {
            "evidence_verified": self.evidence_verified,
            "public_information_only": self.public_information_only,
            "security_cleared": self.security_cleared,
            "rights_cleared": self.rights_cleared,
            "is_draft": self.is_draft,
            "contains_client_data": self.contains_client_data,
            "has_unresolved_vulnerability": self.has_unresolved_vulnerability,
            "claims_affiliation_or_endorsement": (
                self.claims_affiliation_or_endorsement
            ),
            "has_commercial_commitment": self.has_commercial_commitment,
            "commercial_commitment_ratified": (
                self.commercial_commitment_ratified
            ),
            "repetitive_or_trend_driven": self.repetitive_or_trend_driven,
        }


@dataclass(frozen=True)
class PublicationIntent:
    """Exact proposed content plus the evidence and policy facts behind it."""

    interaction_type: XInteractionType
    milestone_type: MilestoneType
    text: str
    source_revision: str
    evidence_refs: tuple[str, ...]
    checks: PublicationChecks
    links: tuple[str, ...] = ()
    media: tuple[MediaMetadata, ...] = ()

    def __post_init__(self) -> None:
        if type(self.interaction_type) is not XInteractionType:
            raise BridgeContractError(
                "interaction_type must be an XInteractionType"
            )
        if type(self.milestone_type) is not MilestoneType:
            raise BridgeContractError("milestone_type must be a MilestoneType")
        object.__setattr__(self, "text", normalize_text(self.text, "text"))
        source_revision = require_plain_string(
            self.source_revision,
            "source_revision",
        )
        if FULL_COMMIT_SHA_PATTERN.fullmatch(source_revision) is None:
            raise BridgeContractError(
                "source_revision must be a full lowercase Git commit SHA"
            )
        require_string_tuple(self.evidence_refs, "evidence_refs")
        if type(self.checks) is not PublicationChecks:
            raise BridgeContractError("checks must be PublicationChecks")
        require_string_tuple(self.links, "links")
        if type(self.media) is not tuple or not all(
            type(item) is MediaMetadata for item in self.media
        ):
            raise BridgeContractError("media must be a tuple of MediaMetadata")
        asset_ids = [item.asset_id for item in self.media]
        if len(set(asset_ids)) != len(asset_ids):
            raise BridgeContractError("media asset_id values must be unique")


def _policy_violations(intent: PublicationIntent) -> list[str]:
    violations: list[str] = []
    checks = intent.checks
    if intent.interaction_type is not XInteractionType.ORIGINAL_POST:
        violations.append("interaction type is not a standalone post")
    if MENTION_PATTERN.search(intent.text):
        violations.append("automated mentions are not allowed")
    if _contains_credential_shape(intent.text):
        violations.append("content resembles credential material")
    if _contains_bare_autolink_domain(intent.text):
        violations.append(
            "bare autolinkable domains are not allowed; use a declared https URL"
        )
    if not intent.evidence_refs:
        violations.append("at least one evidence reference is required")
    if not checks.evidence_verified:
        violations.append("evidence is not verified")
    if not checks.public_information_only:
        violations.append("information is not public-only")
    if not checks.security_cleared:
        violations.append("security review is not clear")
    if not checks.rights_cleared:
        violations.append("rights review is not clear")
    if checks.is_draft:
        violations.append("draft work is not publishable")
    if checks.contains_client_data:
        violations.append("client data is not publishable")
    if checks.has_unresolved_vulnerability:
        violations.append("unresolved vulnerabilities are not publishable")
    if checks.claims_affiliation_or_endorsement:
        violations.append("affiliation or endorsement claims are not allowed")
    if (
        checks.has_commercial_commitment
        and not checks.commercial_commitment_ratified
    ):
        violations.append("commercial commitment is not ratified")
    if (
        checks.commercial_commitment_ratified
        and not checks.has_commercial_commitment
    ):
        violations.append("commercial commitment flags are inconsistent")
    if checks.repetitive_or_trend_driven:
        violations.append("repetitive or trend-driven automation is not allowed")
    extracted_links = _extract_text_urls(intent.text)
    if extracted_links != intent.links:
        violations.append("declared links do not exactly match outbound text")
    for link in extracted_links:
        try:
            validate_public_https_url(link, "publication link")
            if urlsplit(link).query:
                raise BridgeContractError(
                    "publication link must not contain a query string"
                )
        except BridgeContractError as error:
            violations.append(str(error))
    review_strings = (
        *intent.links,
        *intent.evidence_refs,
        *(item.asset_id for item in intent.media),
        *(item.alt_text for item in intent.media),
    )
    if any(_contains_credential_shape(value) for value in review_strings):
        violations.append("review metadata resembles credential material")
    return violations


def _publication_descriptor(
    account_handle: str,
    intent: PublicationIntent,
) -> dict[str, Any]:
    return {
        "schema_version": X_PUBLICATION_SCHEMA_VERSION,
        "mode": "dry-run",
        "account": {
            "display_handle": account_handle,
            "verified_user_id": None,
            "live_identity_binding": "required_via_oauth_users_me",
        },
        "action": "post.create",
        "interaction_type": intent.interaction_type.value,
        "x_api_payload": {"text": intent.text},
        "review_metadata": {
            "milestone_type": intent.milestone_type.value,
            "links": list(intent.links),
            "media": [item.to_dict() for item in intent.media],
            "source_revision": intent.source_revision,
            "evidence_refs": list(intent.evidence_refs),
            "checks": intent.checks.to_dict(),
        },
        "approval": {
            "exact_human_approval_required": True,
            "gateway_receipt_required_for_live_write": True,
            "live_write_allowed": False,
        },
    }


@dataclass(frozen=True)
class XPublicationPlan:
    """Human-reviewable DryRun bound to the exact publication descriptor."""

    account_handle: str
    intent: PublicationIntent
    payload_sha256: str

    def __post_init__(self) -> None:
        if self.account_handle != OFFICIAL_X_ACCOUNT_HANDLE:
            raise BridgePolicyError("X publication target is not the project account")
        if type(self.intent) is not PublicationIntent:
            raise BridgeContractError("intent must be a PublicationIntent")
        violations = _policy_violations(self.intent)
        if violations:
            raise BridgePolicyError(
                "X publication intent rejected: " + "; ".join(violations)
            )
        require_sha256_ref(self.payload_sha256, "payload_sha256")
        expected = canonical_payload_hash(
            _publication_descriptor(self.account_handle, self.intent)
        )
        if self.payload_sha256 != expected:
            raise BridgeContractError("payload_sha256 does not match the plan")

    def to_dict(self) -> dict[str, Any]:
        return {
            **_publication_descriptor(self.account_handle, self.intent),
            "payload_sha256": self.payload_sha256,
        }

    def to_audit_dict(self) -> dict[str, Any]:
        return {
            "schema_version": X_PUBLICATION_SCHEMA_VERSION,
            "mode": "dry-run",
            "account_handle": self.account_handle,
            "verified_user_id": None,
            "action": "post.create",
            "interaction_type": self.intent.interaction_type.value,
            "milestone_type": self.intent.milestone_type.value,
            "source_revision": self.intent.source_revision,
            "payload_sha256": self.payload_sha256,
            "policy_decision": "allow_dry_run",
            "live_write_allowed": False,
            "text_sha256": sha256_text(self.intent.text),
            "text_characters": len(self.intent.text),
            "link_sha256": [sha256_text(link) for link in self.intent.links],
            "link_count": len(self.intent.links),
            "media": [item.to_audit_dict() for item in self.intent.media],
            "media_count": len(self.intent.media),
            "evidence_ref_sha256": [
                sha256_text(ref) for ref in self.intent.evidence_refs
            ],
            "evidence_ref_count": len(self.intent.evidence_refs),
        }


class XDryRunPublisher:
    """Pure local planner with no live execution surface."""

    def __init__(self, config: XPublisherConfig | None = None) -> None:
        self._config = XPublisherConfig() if config is None else config
        if type(self._config) is not XPublisherConfig:
            raise BridgeContractError("config must be an XPublisherConfig")

    def plan(self, intent: PublicationIntent) -> XPublicationPlan:
        """Validate one intent and bind the exact DryRun descriptor."""

        if type(intent) is not PublicationIntent:
            raise BridgeContractError("intent must be a PublicationIntent")
        if not self._config.enabled:
            raise BridgeDisabledError("X publication planning is disabled")
        violations = _policy_violations(intent)
        if violations:
            raise BridgePolicyError(
                "X publication intent rejected: " + "; ".join(violations)
            )
        descriptor = _publication_descriptor(self._config.account_handle, intent)
        return XPublicationPlan(
            account_handle=self._config.account_handle,
            intent=intent,
            payload_sha256=canonical_payload_hash(descriptor),
        )
