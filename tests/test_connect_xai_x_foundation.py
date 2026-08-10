"""Offline contract tests for the issue-#1874 xAI/X bridge foundation."""

from __future__ import annotations

import json
import urllib.request
from dataclasses import replace
from pathlib import Path

import pytest

from hub_optimus.connect.contracts import (
    AnalysisRequest,
    AnalysisResult,
    BridgeContractError,
    BridgeDisabledError,
    BridgePolicyError,
    CitationScope,
    DataClassification,
    SourceCitation,
    UsageMetric,
    sha256_text,
)
from hub_optimus.connect.provider_xai import (
    XaiProviderAdapter,
    XaiProviderConfig,
)
from hub_optimus.connect.publisher_x import (
    OFFICIAL_X_ACCOUNT_HANDLE,
    MediaMetadata,
    MilestoneType,
    PublicationChecks,
    PublicationIntent,
    XDryRunPublisher,
    XInteractionType,
    XPublicationPlan,
    XPublisherConfig,
)
from hub_optimus.connect.source_x import (
    XPostObservation,
    XRetrievalMethod,
    XSourceAdapter,
    XSourceConfig,
    derive_x_signal_record,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_REVISION = "ab62e8ed079f677c91a864475fe3665e634cf1f6"
PUBLIC_LINK = "https://huboptimus.dev/operator/"
PUBLIC_TEXT = f"Verified HUB_Optimus milestone. Evidence: {PUBLIC_LINK}"
RAW_POST_SENTINEL = "raw post body must not be persisted"
PROVIDER_INPUT_SENTINEL = "provider input must not enter the audit record"
PROVIDER_OUTPUT_SENTINEL = "provider output must not enter the audit record"
ALT_TEXT_SENTINEL = "Architecture diagram with the verified milestone"
EVIDENCE_REF_SENTINEL = "evidence-public-release"
X_PROVENANCE_REF = sha256_text("x-read-1874")
X_DERIVED_EVIDENCE_REF = sha256_text("evidence-x-1")
OUTPUT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {"summary": {"type": "string"}},
    "required": ["summary"],
}


class RaisingProviderTransport:
    def __init__(self) -> None:
        self.calls = 0

    def execute(self, _plan):
        self.calls += 1
        raise AssertionError("disabled provider invoked its transport")


class FakeProviderTransport:
    def __init__(
        self,
        *,
        zdr_attested: bool | None = True,
        plan_sha256: str | None = None,
        model_resolved: str = "deployment/current",
        output_json: dict | None = None,
    ) -> None:
        self.plans = []
        self.zdr_attested = zdr_attested
        self.plan_sha256 = plan_sha256
        self.model_resolved = model_resolved
        self.output_json = (
            {"summary": PROVIDER_OUTPUT_SENTINEL}
            if output_json is None
            else output_json
        )

    def execute(self, plan):
        self.plans.append(plan)
        return AnalysisResult(
            request_id=plan.request.request_id,
            provider="xai",
            response_id="response-1",
            model_resolved=self.model_resolved,
            status="completed",
            output_json=self.output_json,
            plan_sha256=self.plan_sha256 or plan.payload_sha256,
            raw_response_sha256=sha256_text("raw provider envelope"),
            zdr_attested=self.zdr_attested,
            citations=(
                SourceCitation(
                    url="https://x.com/i/status/1234567890123456789",
                    scope=CitationScope.ENCOUNTERED,
                ),
                SourceCitation(
                    url="https://huboptimus.dev/",
                    scope=CitationScope.INLINE_CITED,
                    label="HUB_Optimus",
                    start_index=0,
                    end_index=12,
                ),
            ),
            usage=(UsageMetric("input_tokens", 42),),
        )


class RaisingXSourceTransport:
    def __init__(self) -> None:
        self.calls = 0

    def fetch_public_post(self, _post_id):
        self.calls += 1
        raise AssertionError("disabled source invoked its transport")


class FakeXSourceTransport:
    def __init__(self, observation: XPostObservation) -> None:
        self.observation = observation
        self.calls = []

    def fetch_public_post(self, post_id):
        self.calls.append(post_id)
        return self.observation


class FalseyInvalidConfig:
    def __bool__(self) -> bool:
        return False


def valid_analysis_request(
    *,
    classification: DataClassification = DataClassification.PUBLIC,
) -> AnalysisRequest:
    return AnalysisRequest(
        request_id="request-1874",
        case_id="case-public-xai",
        task="Separate claims, evidence, inference, and uncertainty.",
        input_text=PROVIDER_INPUT_SENTINEL,
        output_schema=OUTPUT_SCHEMA,
        source_refs=("source-public-1",),
        output_contract="optimus-analysis.v1",
        data_classification=classification,
    )


def valid_observation() -> XPostObservation:
    return XPostObservation(
        post_id="1234567890123456789",
        author_id="987654321098765432",
        username_at_observation="HubOptimus",
        created_at_utc="2026-08-09T15:00:00Z",
        observed_at_utc="2026-08-09T17:00:00+00:00",
        text=RAW_POST_SENTINEL,
        retrieval_method=XRetrievalMethod.X_API,
        provenance_ref=X_PROVENANCE_REF,
        edit_history_ids=("1234567890123456789",),
        derived_evidence_refs=(X_DERIVED_EVIDENCE_REF,),
    )


def valid_checks(**changes: bool) -> PublicationChecks:
    values = {
        "evidence_verified": True,
        "public_information_only": True,
        "security_cleared": True,
        "rights_cleared": True,
    }
    values.update(changes)
    return PublicationChecks(**values)


def valid_media() -> MediaMetadata:
    return MediaMetadata(
        asset_id="release-diagram",
        sha256=f"sha256:{'a' * 64}",
        media_type="image/png",
        alt_text=ALT_TEXT_SENTINEL,
    )


def valid_intent(**changes) -> PublicationIntent:
    values = {
        "interaction_type": XInteractionType.ORIGINAL_POST,
        "milestone_type": MilestoneType.PUBLIC_FEATURE,
        "text": PUBLIC_TEXT,
        "source_revision": SOURCE_REVISION,
        "evidence_refs": (EVIDENCE_REF_SENTINEL,),
        "checks": valid_checks(),
        "links": (PUBLIC_LINK,),
        "media": (valid_media(),),
    }
    values.update(changes)
    return PublicationIntent(**values)


def enabled_publisher() -> XDryRunPublisher:
    return XDryRunPublisher(XPublisherConfig(enabled=True))


def test_disabled_xai_provider_never_invokes_injected_transport() -> None:
    transport = RaisingProviderTransport()
    adapter = XaiProviderAdapter(transport=transport)

    with pytest.raises(BridgeDisabledError, match="disabled"):
        adapter.analyze(valid_analysis_request())

    assert transport.calls == 0


def test_xai_plan_is_deterministic_public_only_and_store_false() -> None:
    adapter = XaiProviderAdapter(
        XaiProviderConfig(model_ref="deployment-current")
    )
    request = valid_analysis_request()

    first = adapter.plan(request)
    second = adapter.plan(request)

    assert first.payload_sha256 == second.payload_sha256
    assert first.to_dict()["api_surface"] == "responses"
    xai_request = first.to_dict()["xai_request"]
    assert xai_request["store"] is False
    assert xai_request["input"] == [
        {"role": "system", "content": request.task},
        {"role": "user", "content": request.input_text},
    ]
    assert xai_request["text"]["format"] == {
        "type": "json_schema",
        "name": "optimus_analysis_v1",
        "schema": OUTPUT_SCHEMA,
        "strict": True,
    }
    assert first.to_audit_dict()["plan_created_offline"] is True
    assert PROVIDER_INPUT_SENTINEL not in json.dumps(first.to_audit_dict())

    with pytest.raises(BridgePolicyError, match="public project information"):
        adapter.plan(valid_analysis_request(classification=DataClassification.CLIENT))


def test_enabled_xai_adapter_uses_only_the_injected_transport() -> None:
    transport = FakeProviderTransport()
    adapter = XaiProviderAdapter(
        XaiProviderConfig(enabled=True, model_ref="deployment-current"),
        transport,
    )

    result = adapter.analyze(valid_analysis_request())

    assert len(transport.plans) == 1
    assert result.to_dict()["output_json"] == {
        "summary": PROVIDER_OUTPUT_SENTINEL
    }
    audit = json.dumps(result.to_audit_dict(), sort_keys=True)
    assert PROVIDER_OUTPUT_SENTINEL not in audit
    assert "https://x.com/" not in audit
    assert "https://huboptimus.dev/" not in audit
    assert result.to_audit_dict()["citation_scopes"] == [
        "encountered",
        "inline_cited",
    ]


def test_xai_provider_fails_closed_on_state_storage_or_legacy_surface() -> None:
    with pytest.raises(BridgePolicyError, match="server-side state"):
        XaiProviderConfig(model_ref="deployment-current", store=True)
    with pytest.raises(BridgeContractError, match="Responses"):
        XaiProviderConfig(
            model_ref="deployment-current",
            api_surface="chat_completions",
        )


def test_xai_plan_and_result_are_bound_and_deeply_immutable() -> None:
    request = valid_analysis_request()
    schema_copy = request.to_dict()["output_schema"]
    schema_copy["properties"]["summary"]["type"] = "integer"

    adapter = XaiProviderAdapter(
        XaiProviderConfig(model_ref="deployment-current")
    )
    plan = adapter.plan(request)
    with pytest.raises(BridgeContractError, match="does not match"):
        replace(plan, payload_sha256=f"sha256:{'0' * 64}")
    with pytest.raises(BridgePolicyError, match="public project information"):
        replace(
            plan,
            request=valid_analysis_request(
                classification=DataClassification.INTERNAL
            ),
        )

    result = AnalysisResult(
        request_id=request.request_id,
        provider="xai",
        response_id="response-immutable",
        model_resolved="deployment/current",
        status="completed",
        output_json={"nested": ["value"]},
        plan_sha256=plan.payload_sha256,
        raw_response_sha256=sha256_text("raw response"),
    )
    with pytest.raises(TypeError):
        result.output_json["nested"] = ("changed",)
    with pytest.raises(AttributeError):
        result.output_json["nested"].append("changed")
    returned = result.to_dict()
    returned["output_json"]["nested"].append("changed")
    assert result.to_dict()["output_json"] == {"nested": ["value"]}
    assert request.to_dict()["output_schema"] == OUTPUT_SCHEMA


def test_xai_execution_checks_plan_binding_and_optional_zdr_attestation() -> None:
    request = valid_analysis_request()
    wrong_plan_transport = FakeProviderTransport(
        plan_sha256=f"sha256:{'0' * 64}"
    )
    wrong_plan_adapter = XaiProviderAdapter(
        XaiProviderConfig(enabled=True, model_ref="deployment-current"),
        wrong_plan_transport,
    )
    with pytest.raises(BridgeContractError, match="plan_sha256"):
        wrong_plan_adapter.analyze(request)

    no_zdr_transport = FakeProviderTransport(zdr_attested=False)
    no_zdr_adapter = XaiProviderAdapter(
        XaiProviderConfig(
            enabled=True,
            model_ref="deployment-current",
            require_zdr=True,
        ),
        no_zdr_transport,
    )
    with pytest.raises(BridgePolicyError, match="Zero Data Retention"):
        no_zdr_adapter.analyze(request)


def test_non_public_xai_request_never_reaches_enabled_transport() -> None:
    transport = RaisingProviderTransport()
    adapter = XaiProviderAdapter(
        XaiProviderConfig(enabled=True, model_ref="deployment-current"),
        transport,
    )
    with pytest.raises(BridgePolicyError, match="public project information"):
        adapter.analyze(
            valid_analysis_request(classification=DataClassification.CLIENT)
        )
    assert transport.calls == 0


def test_invalid_output_schema_never_reaches_enabled_transport() -> None:
    transport = RaisingProviderTransport()
    adapter = XaiProviderAdapter(
        XaiProviderConfig(enabled=True, model_ref="deployment-current"),
        transport,
    )
    request = replace(
        valid_analysis_request(),
        output_schema={
            "type": "object",
            "additionalProperties": False,
            "properties": {"summary": {"type": "not-a-json-schema-type"}},
        },
    )

    with pytest.raises(BridgeContractError, match="Draft 2020-12"):
        adapter.analyze(request)

    assert transport.calls == 0


def test_xai_result_must_conform_to_the_declared_output_schema() -> None:
    transport = FakeProviderTransport(output_json={"summary": 1874})
    adapter = XaiProviderAdapter(
        XaiProviderConfig(enabled=True, model_ref="deployment-current"),
        transport,
    )

    with pytest.raises(BridgeContractError, match="output_schema"):
        adapter.analyze(valid_analysis_request())

    assert len(transport.plans) == 1


def test_xai_schema_references_cannot_create_a_hidden_network_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    network_calls = []

    def fail_if_called(*args, **kwargs):
        network_calls.append((args, kwargs))
        raise AssertionError("schema validation attempted network access")

    monkeypatch.setattr(urllib.request, "urlopen", fail_if_called)
    transport = RaisingProviderTransport()
    adapter = XaiProviderAdapter(
        XaiProviderConfig(enabled=True, model_ref="deployment-current"),
        transport,
    )
    request = replace(
        valid_analysis_request(),
        output_schema={
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "summary": {"$ref": "https://example.com/schema.json"}
            },
        },
    )

    with pytest.raises(BridgeContractError, match="internal JSON Pointer"):
        adapter.analyze(request)

    assert network_calls == []
    assert transport.calls == 0


def test_unresolved_internal_schema_reference_is_a_controlled_error() -> None:
    transport = FakeProviderTransport()
    adapter = XaiProviderAdapter(
        XaiProviderConfig(enabled=True, model_ref="deployment-current"),
        transport,
    )
    request = replace(
        valid_analysis_request(),
        output_schema={
            "type": "object",
            "additionalProperties": False,
            "properties": {"summary": {"$ref": "#/$defs/missing"}},
        },
    )

    with pytest.raises(BridgeContractError, match="unresolved internal"):
        adapter.analyze(request)

    assert len(transport.plans) == 1


@pytest.mark.parametrize(
    "url",
    [
        "https://127.0.0.1/private",
        "https://224.0.0.1/",
        "https://239.255.255.250/",
        "https://[ff02::1]/",
        "https://[ff0e::1]/",
        "https://2130706433/",
        "https://0x7f000001/",
        "https://0177.0.0.1/",
        "https://127.1/",
        "https://127.0.0.0x1/",
        "https://0x7f.0x0.0x0.0x1/",
        "https://0177.0.0.0x1/",
        "https://0x7f.0x1/",
        "https://127.0.0.0x/",
        "https://%31%32%37.0.0.1/",
        "https://127.0.0.1\\foo/",
        "https://localhost\\foo/",
        "https://169.254.169.254\\x/",
        "https://example.com/a b",
        "https://example.com/?token=TOPSECRET",
        "https://example.com/?X-Amz-Signature=TOPSECRET",
        "https://example.com/?X-Goog-Credential=TOPSECRET",
        "https://example.com/#access_token=TOPSECRET",
    ],
)
def test_provider_citations_must_be_public_and_sanitized(url: str) -> None:
    with pytest.raises(BridgeContractError):
        SourceCitation(url=url, scope=CitationScope.ENCOUNTERED)


def test_result_audit_hashes_resolved_model_instead_of_exposing_it() -> None:
    result = AnalysisResult(
        request_id="request-model-audit",
        provider="xai",
        response_id="response-model-audit",
        model_resolved="client_secret=TOPSECRET",
        status="completed",
        output_json={"summary": "public"},
        plan_sha256=sha256_text("plan"),
        raw_response_sha256=sha256_text("raw response"),
    )
    audit = json.dumps(result.to_audit_dict(), sort_keys=True)
    assert "client_secret" not in audit
    assert "TOPSECRET" not in audit
    assert "model_resolved_sha256" in result.to_audit_dict()


def test_falsey_invalid_configs_are_rejected_instead_of_defaulted() -> None:
    invalid = FalseyInvalidConfig()
    with pytest.raises(BridgeContractError, match="XaiProviderConfig"):
        XaiProviderAdapter(invalid)
    with pytest.raises(BridgeContractError, match="XSourceConfig"):
        XSourceAdapter(invalid)
    with pytest.raises(BridgeContractError, match="XPublisherConfig"):
        XDryRunPublisher(invalid)


def test_disabled_x_source_never_invokes_injected_transport() -> None:
    transport = RaisingXSourceTransport()
    adapter = XSourceAdapter(transport=transport)

    with pytest.raises(BridgeDisabledError, match="disabled"):
        adapter.read_public_post("1234567890123456789")

    assert transport.calls == 0


def test_x_source_derives_provenance_without_a_raw_corpus() -> None:
    observation = valid_observation()

    first = derive_x_signal_record(observation)
    second = derive_x_signal_record(observation)
    payload = first.to_dict()

    assert RAW_POST_SENTINEL not in repr(observation)
    assert first.record_sha256 == second.record_sha256
    assert payload["post_id"] == "1234567890123456789"
    assert payload["author_id"] == "987654321098765432"
    assert payload["id_reference_url"] == (
        "https://x.com/i/status/1234567890123456789"
    )
    assert payload["display_url"] == (
        "https://x.com/HubOptimus/status/1234567890123456789"
    )
    assert payload["created_at_utc"] == "2026-08-09T15:00:00Z"
    assert payload["last_hydrated_at_utc"] == "2026-08-09T17:00:00Z"
    assert payload["provenance_ref"] == X_PROVENANCE_REF
    assert payload["derived_evidence_refs"] == [X_DERIVED_EVIDENCE_REF]
    assert payload["raw_text_retained"] is False
    assert "text" not in payload
    assert RAW_POST_SENTINEL not in json.dumps(payload)

    audit = json.dumps(first.to_audit_dict(), sort_keys=True)
    assert RAW_POST_SENTINEL not in audit
    assert "https://x.com/" not in audit


@pytest.mark.parametrize(
    "changes",
    [
        {"provenance_ref": RAW_POST_SENTINEL},
        {"derived_evidence_refs": (RAW_POST_SENTINEL,)},
        {"provenance_ref": "hello"},
        {"derived_evidence_refs": ("hello",)},
    ],
)
def test_x_observation_rejects_raw_text_in_persistable_reference_fields(
    changes: dict[str, object],
) -> None:
    with pytest.raises(BridgeContractError, match="sha256"):
        replace(valid_observation(), **changes)


@pytest.mark.parametrize(
    "changes",
    [
        {"provenance_ref": "hello"},
        {"derived_evidence_refs": ("hello",)},
    ],
)
def test_x_signal_record_revalidates_content_addressed_refs(
    changes: dict[str, object],
) -> None:
    record = derive_x_signal_record(valid_observation())

    with pytest.raises(BridgeContractError, match="sha256"):
        replace(record, **changes)


@pytest.mark.parametrize(
    "changes",
    [
        {
            "text": X_PROVENANCE_REF,
            "provenance_ref": X_PROVENANCE_REF,
        },
        {
            "text": X_DERIVED_EVIDENCE_REF,
            "derived_evidence_refs": (X_DERIVED_EVIDENCE_REF,),
        },
    ],
)
def test_x_observation_rejects_digest_shaped_raw_text_aliases(
    changes: dict[str, object],
) -> None:
    with pytest.raises(BridgeContractError, match="must not equal raw"):
        replace(valid_observation(), **changes)


def test_enabled_x_source_returns_only_the_derived_record() -> None:
    observation = valid_observation()
    transport = FakeXSourceTransport(observation)
    adapter = XSourceAdapter(XSourceConfig(enabled=True), transport)

    record = adapter.read_public_post(observation.post_id)

    assert transport.calls == [observation.post_id]
    assert record.text_sha256 == sha256_text(RAW_POST_SENTINEL)
    assert not hasattr(record, "text")
    assert adapter.read(observation.post_id).record_sha256 == record.record_sha256


def test_x_signal_record_rejects_hash_tampering_and_invalid_x_ids() -> None:
    record = derive_x_signal_record(valid_observation())
    with pytest.raises(BridgeContractError, match="does not match"):
        replace(record, record_sha256=f"sha256:{'0' * 64}")

    base = valid_observation()
    with pytest.raises(BridgeContractError, match="X ID range"):
        replace(base, post_id="0123", edit_history_ids=("0123",))
    with pytest.raises(BridgeContractError, match="X ID range"):
        replace(
            base,
            post_id=str(1 << 64),
            edit_history_ids=(str(1 << 64),),
        )


def test_x_observation_rejects_time_travel() -> None:
    with pytest.raises(BridgeContractError, match="must not precede"):
        replace(
            valid_observation(),
            observed_at_utc="2026-08-09T14:59:59Z",
        )

    with pytest.raises(BridgeContractError, match="must not precede"):
        replace(
            derive_x_signal_record(valid_observation()),
            last_hydrated_at_utc="2026-08-09T14:59:59Z",
        )


def test_x_publisher_configuration_is_bound_to_huboptimus_and_dry_run() -> None:
    config = XPublisherConfig()
    assert config.account_handle == OFFICIAL_X_ACCOUNT_HANDLE
    assert config.enabled is False
    with pytest.raises(BridgeDisabledError, match="planning is disabled"):
        XDryRunPublisher().plan(valid_intent())
    for wrong_account in ("@WrongAccount", "@GerritHoff80362"):
        with pytest.raises(BridgePolicyError, match="project account"):
            XPublisherConfig(account_handle=wrong_account)
    with pytest.raises(BridgePolicyError, match="not implemented"):
        XPublisherConfig(dry_run=False)


def test_x_publication_plan_is_exact_deterministic_and_audit_sanitized() -> None:
    publisher = enabled_publisher()
    intent = valid_intent()

    first = publisher.plan(intent)
    second = publisher.plan(intent)
    payload = first.to_dict()

    assert first.payload_sha256 == second.payload_sha256
    assert payload["mode"] == "dry-run"
    assert payload["account"] == {
        "display_handle": "@HubOptimus",
        "verified_user_id": None,
        "live_identity_binding": "required_via_oauth_users_me",
    }
    assert payload["x_api_payload"] == {"text": PUBLIC_TEXT}
    assert set(payload["x_api_payload"]) == {"text"}
    assert payload["review_metadata"]["links"] == [PUBLIC_LINK]
    assert payload["review_metadata"]["media"] == [valid_media().to_dict()]
    assert payload["approval"]["exact_human_approval_required"] is True
    assert payload["approval"]["live_write_allowed"] is False

    audit = json.dumps(first.to_audit_dict(), sort_keys=True)
    for secret in (
        PUBLIC_TEXT,
        PUBLIC_LINK,
        ALT_TEXT_SENTINEL,
        EVIDENCE_REF_SENTINEL,
    ):
        assert secret not in audit
    assert first.to_audit_dict()["account_handle"] == "@HubOptimus"
    assert first.to_audit_dict()["policy_decision"] == "allow_dry_run"
    assert first.to_audit_dict()["live_write_allowed"] is False


def test_every_publication_relevant_change_changes_the_plan_hash() -> None:
    publisher = enabled_publisher()
    base = valid_intent()
    baseline_hash = publisher.plan(base).payload_sha256
    alternate_link = "https://huboptimus.dev/"
    variants = (
        replace(base, text=f"{PUBLIC_TEXT} Verified."),
        replace(
            base,
            text=f"Verified HUB_Optimus milestone. Evidence: {alternate_link}",
            links=(alternate_link,),
        ),
        replace(
            base,
            media=(replace(valid_media(), alt_text="Different alt text"),),
        ),
        replace(base, evidence_refs=("evidence-public-release-2",)),
        replace(base, source_revision="b" * 40),
        replace(base, milestone_type=MilestoneType.QA_PASS),
        replace(
            base,
            checks=valid_checks(
                has_commercial_commitment=True,
                commercial_commitment_ratified=True,
            ),
        ),
    )

    variant_hashes = {publisher.plan(variant).payload_sha256 for variant in variants}

    assert baseline_hash not in variant_hashes
    assert len(variant_hashes) == len(variants)


@pytest.mark.parametrize(
    "interaction_type",
    [
        interaction
        for interaction in XInteractionType
        if interaction is not XInteractionType.ORIGINAL_POST
    ],
)
def test_x_publication_rejects_every_non_standalone_interaction(
    interaction_type: XInteractionType,
) -> None:
    with pytest.raises(BridgePolicyError, match="standalone post"):
        enabled_publisher().plan(valid_intent(interaction_type=interaction_type))


@pytest.mark.parametrize(
    "checks",
    [
        valid_checks(evidence_verified=False),
        valid_checks(public_information_only=False),
        valid_checks(security_cleared=False),
        valid_checks(rights_cleared=False),
        valid_checks(is_draft=True),
        valid_checks(contains_client_data=True),
        valid_checks(has_unresolved_vulnerability=True),
        valid_checks(claims_affiliation_or_endorsement=True),
        valid_checks(has_commercial_commitment=True),
        valid_checks(commercial_commitment_ratified=True),
        valid_checks(repetitive_or_trend_driven=True),
    ],
)
def test_x_publication_rejects_unpublishable_gate_facts(
    checks: PublicationChecks,
) -> None:
    with pytest.raises(BridgePolicyError, match="rejected"):
        enabled_publisher().plan(valid_intent(checks=checks))


@pytest.mark.parametrize(
    ("text", "links"),
    [
        ("Automated update for @Someone", ()),
        ("Automated update for @@Someone", ()),
        ("token=must-not-publish", ()),
        ("client_secret=must-not-publish", ()),
        ("Milestone example.com/file?X-Amz-Signature=TOPSECRET", ()),
        ("Milestone example.com/file?X-Goog-Credential=TOPSECRET", ()),
        ("Milestone example.com/file?sig=TOPSECRET&sv=2026-08-09", ()),
        ("xai-abcdefghijklmnopqrstuvwx", ()),
        (
            "Unsafe link https://example.com/path?access_token=value",
            ("https://example.com/path?access_token=value",),
        ),
        (
            "Local link https://127.0.0.1/private",
            ("https://127.0.0.1/private",),
        ),
    ],
)
def test_x_publication_rejects_mentions_credentials_and_private_links(
    text: str,
    links: tuple[str, ...],
) -> None:
    with pytest.raises(BridgePolicyError, match="rejected"):
        enabled_publisher().plan(valid_intent(text=text, links=links, media=()))


def test_x_publication_requires_declared_evidence_and_exact_link_content() -> None:
    publisher = enabled_publisher()
    with pytest.raises(BridgePolicyError, match="evidence reference"):
        publisher.plan(valid_intent(evidence_refs=()))
    with pytest.raises(BridgePolicyError, match="exactly match outbound text"):
        publisher.plan(valid_intent(text="Verified milestone without its link."))


@pytest.mark.parametrize("separator", ["․", "。", "﹒", "．", "｡"])
def test_declared_https_idna_dot_equivalents_are_not_treated_as_bare(
    separator: str,
) -> None:
    link = f"https://example{separator}com/release"

    plan = enabled_publisher().plan(
        valid_intent(
            text=f"Verified milestone {link}",
            links=(link,),
            media=(),
        )
    )

    assert plan.intent.links == (link,)


@pytest.mark.parametrize(
    ("text", "links"),
    [
        ("Milestone http://example.com/plain", ()),
        ("Milestone huboptimus.dev/release", ()),
        ("Milestone www.huboptimus.dev/release", ()),
        ("Milestone example.com/file?%58-Amz-%53ignature=TOPSECRET", ()),
        ("Milestone пример.рф/release", ()),
        ("Milestone пример。рф/release", ()),
        ("Milestone example․com/release", ()),
        ("Milestone example﹒com/release", ()),
        ("Milestone example．com/release", ()),
        ("Milestone example｡com/release", ()),
        ("Milestone https://127.0.0.1/private", ()),
        ("Milestone https://example.com/?token=TOPSECRET", ()),
        (
            "Milestone https://example.com/file?X-Amz-Signature=TOPSECRET",
            ("https://example.com/file?X-Amz-Signature=TOPSECRET",),
        ),
        (
            "Milestone https://example.com/file?X-Goog-Credential=TOPSECRET",
            ("https://example.com/file?X-Goog-Credential=TOPSECRET",),
        ),
        (
            "Milestone https://example.com/file?sig=TOPSECRET&sv=2026-08-09",
            ("https://example.com/file?sig=TOPSECRET&sv=2026-08-09",),
        ),
        ("Milestone https://2130706433/", ("https://2130706433/",)),
        ("Milestone https://224.0.0.1/", ("https://224.0.0.1/",)),
        (
            "Milestone https://239.255.255.250/",
            ("https://239.255.255.250/",),
        ),
        ("Milestone https://[ff02::1]/", ("https://[ff02::1]/",)),
        ("Milestone https://[ff0e::1]/", ("https://[ff0e::1]/",)),
        ("Milestone https://0x7f000001/", ("https://0x7f000001/",)),
        ("Milestone https://0177.0.0.1/", ("https://0177.0.0.1/",)),
        ("Milestone https://127.1/", ("https://127.1/",)),
        (
            "Milestone https://127.0.0.0x1/",
            ("https://127.0.0.0x1/",),
        ),
        (
            "Milestone https://0x7f.0x0.0x0.0x1/",
            ("https://0x7f.0x0.0x0.0x1/",),
        ),
        (
            "Milestone https://0177.0.0.0x1/",
            ("https://0177.0.0.0x1/",),
        ),
        (
            "Milestone https://0x7f.0x1/",
            ("https://0x7f.0x1/",),
        ),
        (
            "Milestone https://127.0.0.0x/",
            ("https://127.0.0.0x/",),
        ),
        (
            "Milestone https://%31%32%37.0.0.1/",
            ("https://%31%32%37.0.0.1/",),
        ),
        (
            "Milestone https://127.0.0.1\\foo/",
            ("https://127.0.0.1\\foo/",),
        ),
        (
            "Milestone https://localhost\\foo/",
            ("https://localhost\\foo/",),
        ),
        (
            "Milestone https://169.254.169.254\\x/",
            ("https://169.254.169.254\\x/",),
        ),
        (
            "Milestone https://example.com.evil/private",
            ("https://example.com",),
        ),
    ],
)
def test_every_outbound_url_must_be_declared_exactly_and_public(
    text: str,
    links: tuple[str, ...],
) -> None:
    with pytest.raises(BridgePolicyError, match="rejected"):
        enabled_publisher().plan(
            valid_intent(text=text, links=links, media=())
        )


def test_media_metadata_rejects_credential_shaped_alt_text() -> None:
    with pytest.raises(BridgeContractError, match="credential material"):
        replace(valid_media(), alt_text="client_secret=TOPSECRET")


def test_direct_publication_plan_construction_cannot_bypass_policy() -> None:
    reply = valid_intent(interaction_type=XInteractionType.REPLY)
    with pytest.raises(BridgePolicyError, match="standalone post"):
        XPublicationPlan(
            account_handle=OFFICIAL_X_ACCOUNT_HANDLE,
            intent=reply,
            payload_sha256=f"sha256:{'0' * 64}",
        )


def test_unpaired_unicode_surrogates_fail_as_contract_errors() -> None:
    with pytest.raises(BridgeContractError, match="Unicode surrogate"):
        valid_intent(text="Milestone \ud800", links=(), media=())
    with pytest.raises(BridgeContractError, match="Unicode surrogate"):
        AnalysisResult(
            request_id="request-surrogate",
            provider="xai",
            response_id="response-surrogate",
            model_resolved="deployment/current",
            status="completed",
            output_json={"summary": "\ud800"},
            plan_sha256=sha256_text("plan"),
            raw_response_sha256=sha256_text("raw"),
        )


def test_connect_package_has_no_bundled_network_or_live_publish_surface() -> None:
    package = REPO_ROOT / "hub_optimus" / "connect"
    source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted(package.glob("*.py"))
    )

    for forbidden in (
        "import requests",
        "import httpx",
        "import socket",
        "from urllib.request",
        "os.environ",
        "getenv(",
        "def publish(",
    ):
        assert forbidden not in source
    assert "@HubOptimus" in source
    assert "@WrongAccount" not in source


def test_connect_package_is_not_wired_into_existing_executable_surfaces() -> None:
    checked_paths = [
        REPO_ROOT / "run_scenario.py",
        REPO_ROOT / "hub_optimus_simulator.py",
        *sorted((REPO_ROOT / "semantic_engine").rglob("*.py")),
        *sorted((REPO_ROOT / "site" / "operator").rglob("*")),
    ]
    for path in checked_paths:
        if path.is_file():
            assert "hub_optimus.connect" not in path.read_text(
                encoding="utf-8",
                errors="replace",
            )
