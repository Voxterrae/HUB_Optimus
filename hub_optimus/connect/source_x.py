"""Read-only X public-signal records for HUB_Optimus Connect.

The phase-one adapter accepts an observation from a caller-injected transport
and immediately derives a compact record.  The derived record retains stable
IDs, observed/reference URLs, timestamps, provenance, edit history, and a text
digest, but never contains a serializable raw-post body.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Protocol

from .contracts import (
    BridgeContractError,
    BridgeDisabledError,
    canonical_payload_hash,
    normalize_text,
    normalize_utc_timestamp,
    require_plain_bool,
    require_plain_string,
    require_sha256_ref,
    require_string_tuple,
    sha256_text,
)


X_SIGNAL_SCHEMA_VERSION = "optimus-x-signal.v1"
X_ID_PATTERN = re.compile(r"[0-9]{1,20}")
X_USERNAME_PATTERN = re.compile(r"[A-Za-z0-9_]{1,15}")
MAX_X_ID = (1 << 64) - 1
DEFAULT_X_PROVENANCE_REF = sha256_text("x-observation")


class XRetrievalMethod(str, Enum):
    """Allowlisted origins for one hydrated public X observation."""

    X_API = "x_api"
    XAI_X_SEARCH = "xai_x_search"
    OPERATOR_REFERENCE = "operator_reference"


def require_x_id(value: Any, field_name: str) -> str:
    """Keep X Snowflake-style identifiers as decimal strings."""

    value = require_plain_string(value, field_name)
    if X_ID_PATTERN.fullmatch(value) is None:
        raise BridgeContractError(f"{field_name} must be a decimal string")
    if value.startswith("0") or int(value) > MAX_X_ID:
        raise BridgeContractError(f"{field_name} is outside the X ID range")
    return value


def require_x_username(value: Any, field_name: str) -> str:
    """Validate an observed X username without treating it as stable identity."""

    value = require_plain_string(value, field_name)
    if X_USERNAME_PATTERN.fullmatch(value) is None:
        raise BridgeContractError(f"{field_name} is not a valid X username")
    return value


def require_derived_evidence_refs(
    values: Any,
    field_name: str = "derived_evidence_refs",
) -> tuple[str, ...]:
    """Require content-addressed references rather than persistable free text."""

    references = require_string_tuple(values, field_name)
    for index, reference in enumerate(references):
        require_sha256_ref(reference, f"{field_name}[{index}]")
    return references


def x_post_id_reference_url(post_id: str) -> str:
    """Return the ID-based URL form observed in xAI citation output."""

    require_x_id(post_id, "post_id")
    return f"https://x.com/i/status/{post_id}"


def display_x_post_url(username: str, post_id: str) -> str:
    """Return the username-at-observation permalink for human display."""

    require_x_username(username, "username")
    require_x_id(post_id, "post_id")
    return f"https://x.com/{username}/status/{post_id}"


@dataclass(frozen=True)
class XSourceConfig:
    """External-read gate; disabled unless a caller opts in explicitly."""

    enabled: bool = False

    def __post_init__(self) -> None:
        require_plain_bool(self.enabled, "enabled")


@dataclass(frozen=True)
class XPostObservation:
    """Ephemeral hydrated X post returned by an injected read transport."""

    post_id: str
    author_id: str
    username_at_observation: str
    created_at_utc: str
    observed_at_utc: str
    text: str = field(repr=False)
    retrieval_method: XRetrievalMethod = XRetrievalMethod.X_API
    provenance_ref: str = DEFAULT_X_PROVENANCE_REF
    edit_history_ids: tuple[str, ...] = ()
    derived_evidence_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        require_x_id(self.post_id, "post_id")
        require_x_id(self.author_id, "author_id")
        require_x_username(self.username_at_observation, "username_at_observation")
        object.__setattr__(
            self,
            "created_at_utc",
            normalize_utc_timestamp(self.created_at_utc, "created_at_utc"),
        )
        object.__setattr__(
            self,
            "observed_at_utc",
            normalize_utc_timestamp(self.observed_at_utc, "observed_at_utc"),
        )
        object.__setattr__(self, "text", normalize_text(self.text, "text"))
        created_at = datetime.fromisoformat(
            self.created_at_utc.replace("Z", "+00:00")
        )
        observed_at = datetime.fromisoformat(
            self.observed_at_utc.replace("Z", "+00:00")
        )
        if observed_at < created_at:
            raise BridgeContractError(
                "observed_at_utc must not precede created_at_utc"
            )
        if type(self.retrieval_method) is not XRetrievalMethod:
            raise BridgeContractError(
                "retrieval_method must be an XRetrievalMethod"
            )
        require_sha256_ref(self.provenance_ref, "provenance_ref")
        edit_history = require_string_tuple(
            self.edit_history_ids,
            "edit_history_ids",
        )
        for index, edit_id in enumerate(edit_history):
            require_x_id(edit_id, f"edit_history_ids[{index}]")
        if not edit_history or self.post_id not in edit_history:
            raise BridgeContractError(
                "edit_history_ids must contain the observed post_id"
            )
        evidence_references = require_derived_evidence_refs(
            self.derived_evidence_refs,
            "derived_evidence_refs",
        )
        if self.provenance_ref == self.text or self.text in evidence_references:
            raise BridgeContractError(
                "persistable references must not equal raw X post text"
            )


@dataclass(frozen=True)
class XSignalRecord:
    """Persistable public-signal derivative with no raw-post body."""

    post_id: str
    author_id: str
    username_at_observation: str
    id_reference_url: str
    display_url: str
    created_at_utc: str
    last_hydrated_at_utc: str
    retrieval_method: XRetrievalMethod
    provenance_ref: str
    edit_history_ids: tuple[str, ...]
    derived_evidence_refs: tuple[str, ...]
    text_sha256: str
    text_characters: int
    record_sha256: str
    raw_text_retained: bool = False

    def __post_init__(self) -> None:
        require_x_id(self.post_id, "post_id")
        require_x_id(self.author_id, "author_id")
        require_x_username(self.username_at_observation, "username_at_observation")
        if self.id_reference_url != x_post_id_reference_url(self.post_id):
            raise BridgeContractError("id_reference_url does not match post_id")
        if self.display_url != display_x_post_url(
            self.username_at_observation,
            self.post_id,
        ):
            raise BridgeContractError("display_url does not match the observation")
        if self.created_at_utc != normalize_utc_timestamp(
            self.created_at_utc,
            "created_at_utc",
        ):
            raise BridgeContractError("created_at_utc is not canonical UTC")
        if self.last_hydrated_at_utc != normalize_utc_timestamp(
            self.last_hydrated_at_utc,
            "last_hydrated_at_utc",
        ):
            raise BridgeContractError("last_hydrated_at_utc is not canonical UTC")
        created_at = datetime.fromisoformat(
            self.created_at_utc.replace("Z", "+00:00")
        )
        last_hydrated_at = datetime.fromisoformat(
            self.last_hydrated_at_utc.replace("Z", "+00:00")
        )
        if last_hydrated_at < created_at:
            raise BridgeContractError(
                "last_hydrated_at_utc must not precede created_at_utc"
            )
        if type(self.retrieval_method) is not XRetrievalMethod:
            raise BridgeContractError(
                "retrieval_method must be an XRetrievalMethod"
            )
        require_sha256_ref(self.provenance_ref, "provenance_ref")
        edit_history = require_string_tuple(
            self.edit_history_ids,
            "edit_history_ids",
        )
        for index, edit_id in enumerate(edit_history):
            require_x_id(edit_id, f"edit_history_ids[{index}]")
        if not edit_history or self.post_id not in edit_history:
            raise BridgeContractError(
                "edit_history_ids must contain the observed post_id"
            )
        require_derived_evidence_refs(
            self.derived_evidence_refs,
            "derived_evidence_refs",
        )
        require_sha256_ref(self.text_sha256, "text_sha256")
        if type(self.text_characters) is not int or self.text_characters < 1:
            raise BridgeContractError("text_characters must be a positive integer")
        require_sha256_ref(self.record_sha256, "record_sha256")
        require_plain_bool(self.raw_text_retained, "raw_text_retained")
        if self.raw_text_retained:
            raise BridgeContractError("phase one must not retain raw X post text")
        if self.record_sha256 != canonical_payload_hash(self._descriptor()):
            raise BridgeContractError("record_sha256 does not match the X signal")

    def _descriptor(self) -> dict[str, Any]:
        return {
            "schema_version": X_SIGNAL_SCHEMA_VERSION,
            "source_type": "x_public_post",
            "post_id": self.post_id,
            "author_id": self.author_id,
            "username_at_observation": self.username_at_observation,
            "id_reference_url": self.id_reference_url,
            "display_url": self.display_url,
            "created_at_utc": self.created_at_utc,
            "last_hydrated_at_utc": self.last_hydrated_at_utc,
            "retrieval_method": self.retrieval_method.value,
            "provenance_ref": self.provenance_ref,
            "edit_history_ids": list(self.edit_history_ids),
            "derived_evidence_refs": list(self.derived_evidence_refs),
            "text_sha256": self.text_sha256,
            "text_characters": self.text_characters,
            "raw_text_retained": False,
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self._descriptor(), "record_sha256": self.record_sha256}

    def to_audit_dict(self) -> dict[str, Any]:
        return {
            "schema_version": X_SIGNAL_SCHEMA_VERSION,
            "source_type": "x_public_post",
            "post_id": self.post_id,
            "author_id": self.author_id,
            "id_reference_url_sha256": sha256_text(self.id_reference_url),
            "display_url_sha256": sha256_text(self.display_url),
            "created_at_utc": self.created_at_utc,
            "last_hydrated_at_utc": self.last_hydrated_at_utc,
            "retrieval_method": self.retrieval_method.value,
            "provenance_ref": self.provenance_ref,
            "edit_history_count": len(self.edit_history_ids),
            "derived_evidence_count": len(self.derived_evidence_refs),
            "text_sha256": self.text_sha256,
            "text_characters": self.text_characters,
            "record_sha256": self.record_sha256,
            "raw_text_retained": False,
        }


def derive_x_signal_record(observation: XPostObservation) -> XSignalRecord:
    """Derive a bounded record without copying the observation body into it."""

    if type(observation) is not XPostObservation:
        raise BridgeContractError("observation must be an XPostObservation")
    descriptor = {
        "schema_version": X_SIGNAL_SCHEMA_VERSION,
        "source_type": "x_public_post",
        "post_id": observation.post_id,
        "author_id": observation.author_id,
        "username_at_observation": observation.username_at_observation,
        "id_reference_url": x_post_id_reference_url(observation.post_id),
        "display_url": display_x_post_url(
            observation.username_at_observation,
            observation.post_id,
        ),
        "created_at_utc": observation.created_at_utc,
        "last_hydrated_at_utc": observation.observed_at_utc,
        "retrieval_method": observation.retrieval_method.value,
        "provenance_ref": observation.provenance_ref,
        "edit_history_ids": list(observation.edit_history_ids),
        "derived_evidence_refs": list(observation.derived_evidence_refs),
        "text_sha256": sha256_text(observation.text),
        "text_characters": len(observation.text),
        "raw_text_retained": False,
    }
    return XSignalRecord(
        post_id=observation.post_id,
        author_id=observation.author_id,
        username_at_observation=observation.username_at_observation,
        id_reference_url=descriptor["id_reference_url"],
        display_url=descriptor["display_url"],
        created_at_utc=observation.created_at_utc,
        last_hydrated_at_utc=observation.observed_at_utc,
        retrieval_method=observation.retrieval_method,
        provenance_ref=observation.provenance_ref,
        edit_history_ids=observation.edit_history_ids,
        derived_evidence_refs=observation.derived_evidence_refs,
        text_sha256=descriptor["text_sha256"],
        text_characters=descriptor["text_characters"],
        record_sha256=canonical_payload_hash(descriptor),
    )


class XSourceTransport(Protocol):
    """Injected read transport; phase one supplies no implementation."""

    def fetch_public_post(self, post_id: str) -> XPostObservation:
        """Return one hydrated public post observation."""


class XSourceAdapter:
    """Read one public post only when explicitly enabled and injected."""

    def __init__(
        self,
        config: XSourceConfig | None = None,
        transport: XSourceTransport | None = None,
    ) -> None:
        self._config = XSourceConfig() if config is None else config
        if type(self._config) is not XSourceConfig:
            raise BridgeContractError("config must be an XSourceConfig")
        self._transport = transport

    def read_public_post(self, post_id: str) -> XSignalRecord:
        """Hydrate through the injected transport and return a compact record."""

        if not self._config.enabled:
            raise BridgeDisabledError("X public-source adapter is disabled")
        if self._transport is None:
            raise BridgeDisabledError("X public-source transport is not configured")
        post_id = require_x_id(post_id, "post_id")
        observation = self._transport.fetch_public_post(post_id)
        if type(observation) is not XPostObservation:
            raise BridgeContractError("X source transport returned an invalid type")
        if observation.post_id != post_id:
            raise BridgeContractError("X source transport returned the wrong post_id")
        return derive_x_signal_record(observation)

    def read(self, source_ref: str) -> XSignalRecord:
        """Provider-neutral read alias for the X post-ID source."""

        return self.read_public_post(source_ref)
