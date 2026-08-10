"""Disabled-by-default xAI analytical-provider boundary.

This module builds deterministic plans for an injected xAI Responses
transport.  It ships no HTTP client, SDK, credential loading, model choice,
retry loop, or provider-side authority.  Provider output remains advisory.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError
from referencing import Registry
from referencing.exceptions import Unresolvable

from .contracts import (
    AnalysisRequest,
    AnalysisResult,
    AnalysisTransport,
    BridgeContractError,
    BridgeDisabledError,
    BridgePolicyError,
    DataClassification,
    canonical_payload_hash,
    require_plain_bool,
    require_plain_string,
    require_sha256_ref,
    sha256_text,
    thaw_json,
)


XAI_PROVIDER = "xai"
XAI_API_SURFACE = "responses"
XAI_PLAN_SCHEMA_VERSION = "optimus-xai-call-plan.v1"
_OFFLINE_SCHEMA_REGISTRY = Registry()


def _reject_external_schema_references(value: Any, path: str = "$") -> None:
    if type(value) is dict:
        for key, item in value.items():
            child_path = f"{path}.{key}"
            if key in {"$ref", "$dynamicRef"} and (
                type(item) is not str or not item.startswith("#")
            ):
                raise BridgeContractError(
                    f"{child_path} must be an internal JSON Pointer reference"
                )
            _reject_external_schema_references(item, child_path)
    elif type(value) is list:
        for index, item in enumerate(value):
            _reject_external_schema_references(item, f"{path}[{index}]")


def _validate_output_schema(request: AnalysisRequest) -> None:
    schema = thaw_json(request.output_schema)
    _reject_external_schema_references(schema)
    try:
        Draft202012Validator.check_schema(schema)
    except SchemaError as error:
        raise BridgeContractError("output_schema is not valid Draft 2020-12") from error


def _xai_request_body(
    request: AnalysisRequest,
    model_ref: str,
) -> dict[str, Any]:
    request_payload = request.to_dict()
    return {
        "model": model_ref,
        "input": [
            {"role": "system", "content": request.task},
            {"role": "user", "content": request.input_text},
        ],
        "store": False,
        "text": {
            "format": {
                "type": "json_schema",
                "name": request.output_schema_name,
                "schema": request_payload["output_schema"],
                "strict": True,
            }
        },
    }


def _xai_descriptor(
    request: AnalysisRequest,
    model_ref: str,
    require_zdr: bool,
) -> dict[str, Any]:
    return {
        "schema_version": XAI_PLAN_SCHEMA_VERSION,
        "provider": XAI_PROVIDER,
        "api_surface": XAI_API_SURFACE,
        "xai_request": _xai_request_body(request, model_ref),
        "request_binding": {
            "request_id": request.request_id,
            "case_id": request.case_id,
            "source_refs": list(request.source_refs),
            "output_contract": request.output_contract,
            "data_classification": request.data_classification.value,
        },
        "retention_policy": {
            "responses_store": False,
            "zdr_attestation_required": require_zdr,
        },
    }


@dataclass(frozen=True)
class XaiProviderConfig:
    """Local configuration gate for a separately supplied xAI transport."""

    enabled: bool = False
    model_ref: str | None = None
    api_surface: str = XAI_API_SURFACE
    store: bool = False
    require_zdr: bool = False

    def __post_init__(self) -> None:
        require_plain_bool(self.enabled, "enabled")
        require_plain_bool(self.store, "store")
        require_plain_bool(self.require_zdr, "require_zdr")
        if self.api_surface != XAI_API_SURFACE:
            raise BridgeContractError("xAI phase one supports only Responses plans")
        if self.store:
            raise BridgePolicyError(
                "xAI Responses server-side state must remain disabled"
            )
        if self.model_ref is not None:
            require_plain_string(self.model_ref, "model_ref")
        if self.enabled and self.model_ref is None:
            raise BridgeContractError("enabled xAI configuration requires model_ref")


@dataclass(frozen=True)
class XaiCallPlan:
    """Deterministic, provider-specific plan presented to an injected transport."""

    request: AnalysisRequest
    model_ref: str
    require_zdr: bool
    payload_sha256: str

    def __post_init__(self) -> None:
        if type(self.request) is not AnalysisRequest:
            raise BridgeContractError("request must be an AnalysisRequest")
        require_plain_string(self.model_ref, "model_ref")
        require_plain_bool(self.require_zdr, "require_zdr")
        if self.request.data_classification is not DataClassification.PUBLIC:
            raise BridgePolicyError(
                "xAI phase one accepts public project information only"
            )
        _validate_output_schema(self.request)
        require_sha256_ref(self.payload_sha256, "payload_sha256")
        if self.payload_sha256 != canonical_payload_hash(self._descriptor()):
            raise BridgeContractError("payload_sha256 does not match the xAI plan")

    def _xai_request(self) -> dict[str, Any]:
        return _xai_request_body(self.request, self.model_ref)

    def _descriptor(self) -> dict[str, Any]:
        return _xai_descriptor(self.request, self.model_ref, self.require_zdr)

    def to_dict(self) -> dict[str, Any]:
        return {**self._descriptor(), "payload_sha256": self.payload_sha256}

    def to_audit_dict(self) -> dict[str, Any]:
        return {
            "schema_version": XAI_PLAN_SCHEMA_VERSION,
            "provider": XAI_PROVIDER,
            "api_surface": XAI_API_SURFACE,
            "responses_store": False,
            "zdr_attestation_required": self.require_zdr,
            "model_ref_sha256": sha256_text(self.model_ref),
            "request": self.request.to_audit_dict(),
            "payload_sha256": self.payload_sha256,
            "plan_created_offline": True,
        }


class XaiProviderAdapter:
    """Plan xAI work locally and execute only through an injected transport."""

    def __init__(
        self,
        config: XaiProviderConfig | None = None,
        transport: AnalysisTransport[XaiCallPlan] | None = None,
    ) -> None:
        self._config = XaiProviderConfig() if config is None else config
        if type(self._config) is not XaiProviderConfig:
            raise BridgeContractError("config must be an XaiProviderConfig")
        self._transport = transport

    def plan(self, request: AnalysisRequest) -> XaiCallPlan:
        """Build a deterministic offline plan without invoking a transport."""

        if type(request) is not AnalysisRequest:
            raise BridgeContractError("request must be an AnalysisRequest")
        if request.data_classification is not DataClassification.PUBLIC:
            raise BridgePolicyError(
                "xAI phase one accepts public project information only"
            )
        if self._config.model_ref is None:
            raise BridgeContractError("xAI planning requires model_ref")
        descriptor = _xai_descriptor(
            request,
            self._config.model_ref,
            self._config.require_zdr,
        )
        return XaiCallPlan(
            request=request,
            model_ref=self._config.model_ref,
            require_zdr=self._config.require_zdr,
            payload_sha256=canonical_payload_hash(descriptor),
        )

    def analyze(self, request: AnalysisRequest) -> AnalysisResult:
        """Invoke only an explicitly enabled, caller-injected transport."""

        if not self._config.enabled:
            raise BridgeDisabledError("xAI provider adapter is disabled")
        if self._transport is None:
            raise BridgeDisabledError("xAI provider transport is not configured")

        plan = self.plan(request)
        result = self._transport.execute(plan)
        if type(result) is not AnalysisResult:
            raise BridgeContractError("xAI transport returned an invalid result type")
        if result.provider != XAI_PROVIDER:
            raise BridgeContractError("xAI transport returned the wrong provider")
        if result.request_id != request.request_id:
            raise BridgeContractError("xAI transport returned the wrong request_id")
        if result.plan_sha256 != plan.payload_sha256:
            raise BridgeContractError("xAI transport returned the wrong plan_sha256")
        if self._config.require_zdr and result.zdr_attested is not True:
            raise BridgePolicyError("xAI transport did not attest Zero Data Retention")
        try:
            validation_errors = list(
                Draft202012Validator(
                    thaw_json(request.output_schema),
                    registry=_OFFLINE_SCHEMA_REGISTRY,
                ).iter_errors(result.to_dict()["output_json"])
            )
        except Unresolvable as error:
            raise BridgeContractError(
                "output_schema contains an unresolved internal reference"
            ) from error
        if validation_errors:
            raise BridgeContractError(
                "xAI result does not conform to output_schema"
            )
        return result
