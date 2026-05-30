from semantic_engine.contracts import (
    AnalysisResult,
    AuditLogEntry,
    ClaimRecord,
    DecisionTrace,
    EvidenceRecord,
)


def test_analysis_result_preserves_core_decomposition_fields():
    claim = ClaimRecord(
        claim_id="claim-1",
        text="HUB_Optimus separates evidence from inference.",
        source_ref="README.md",
    )
    evidence = EvidenceRecord(
        evidence_id="evidence-1",
        text="The core map requires separate claim, evidence, inference, uncertainty, narrative, and signal fields.",
        source_ref="docs/architecture/core_to_engine_translation_map.md",
        supports_claim_ids=("claim-1",),
    )
    trace = DecisionTrace(
        step="contract_shape",
        rule_applied="core_decomposition",
        input_ref="claim-1",
        output_ref="analysis-1",
        reason="Keep core decomposition explicit in the result contract.",
    )
    audit = AuditLogEntry(
        event_id="audit-1",
        action="created",
        object_type="analysis_result",
        object_id="analysis-1",
        reason="Minimal contract fixture.",
        timestamp="2026-05-30T00:00:00+00:00",
    )

    result = AnalysisResult(
        case_id="case-1",
        core_version_ref="main@core-to-engine-map",
        input_summary="Minimal contract test case.",
        claims=(claim,),
        evidence=(evidence,),
        inferences=("Inference remains separated.",),
        uncertainties=("No evaluator has run yet.",),
        narrative_amplification=("No amplification assessed yet.",),
        operational_signal="none",
        status="draft",
        decision_trace=(trace,),
        audit_log=(audit,),
    )

    payload = result.to_dict()

    assert payload["case_id"] == "case-1"
    assert payload["claims"][0]["claim_id"] == "claim-1"
    assert payload["evidence"][0]["supports_claim_ids"] == ["claim-1"]
    assert payload["inferences"] == ["Inference remains separated."]
    assert payload["uncertainties"] == ["No evaluator has run yet."]
    assert payload["narrative_amplification"] == ["No amplification assessed yet."]
    assert payload["decision_trace"][0]["rule_applied"] == "core_decomposition"
    assert payload["audit_log"][0]["object_type"] == "analysis_result"


def test_contracts_are_stdlib_serializable_shapes():
    result = AnalysisResult(
        case_id="case-2",
        core_version_ref="main@contracts",
        input_summary="Empty draft result.",
    )

    payload = result.to_dict()

    assert payload["claims"] == []
    assert payload["evidence"] == []
    assert payload["decision_trace"] == []
    assert payload["audit_log"] == []
    assert payload["status"] == "draft"
