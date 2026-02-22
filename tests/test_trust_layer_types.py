from hub_optimus.trust_layer import classify_claim, classify_claim_typed, evidence_required


def test_third_party_audit_is_a():
    level, claim_type = classify_claim_typed(
        "Independent third-party audit with on-site inspections and public reports."
    )
    assert level == "A"
    assert claim_type == "third_party_audit"
    evidence = evidence_required(level, claim_type)
    assert any("audit" in x.lower() or "inspection" in x.lower() for x in evidence)


def test_metrics_reporting_is_b():
    level, claim_type = classify_claim_typed("Weekly KPI reporting with a public dashboard.")
    assert level == "B"
    assert claim_type == "metrics_reporting"
    evidence = evidence_required(level, claim_type)
    assert any("kpi" in x.lower() or "metric" in x.lower() or "dashboard" in x.lower() for x in evidence)


def test_negated_verification_stays_c():
    level, claim_type = classify_claim_typed(
        "Ceasefire announced without independent verification mechanism (evidence gap)."
    )
    assert level == "C"
    assert claim_type == "declarative_only"
    evidence = evidence_required(level, claim_type)
    assert any("verification" in x.lower() or "monitor" in x.lower() for x in evidence)


def test_backward_compatible_classify_claim():
    assert classify_claim("Independent third-party audit with public reporting.") == "A"


def test_backward_compatible_evidence_required_level_only():
    evidence = evidence_required("B")
    assert any("metric" in x.lower() or "audit trail" in x.lower() for x in evidence)
