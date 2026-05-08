from __future__ import annotations

import json
from pathlib import Path

import jsonschema


REPO_ROOT = Path(__file__).resolve().parents[1]
DATASET_DIR = REPO_ROOT / "datasets" / "geopolitical_claim_packs"
SCHEMA_PATH = DATASET_DIR / "claim_pack.schema.json"
NORTHSTONE_PACK = DATASET_DIR / "northstone_putin_security_2026_pack_001.json"


def _load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def test_geopolitical_claim_packs_validate_against_schema() -> None:
    schema = _load_json(SCHEMA_PATH)
    validator = jsonschema.Draft202012Validator(schema)

    pack_files = sorted(
        path for path in DATASET_DIR.glob("*.json") if path.name != "claim_pack.schema.json"
    )
    assert pack_files

    for pack_file in pack_files:
        payload = _load_json(pack_file)
        errors = sorted(validator.iter_errors(payload), key=lambda e: list(e.path))
        assert errors == [], [error.message for error in errors]


def test_northstone_pack_keeps_screenshot_claims_unverified() -> None:
    pack = _load_json(NORTHSTONE_PACK)
    assert isinstance(pack, dict)

    assert pack["source_type"] == "social_media_screenshot"
    assert pack["verification_status"] == "unverified"
    assert pack["evidence_tier"] == "low"
    assert pack["overall_risk"] == "high"
    assert len(pack["claims"]) >= 5

    for claim in pack["claims"]:
        assert claim["source_type"] == "social_media_screenshot"
        assert claim["verification_status"] == "unverified"
        assert claim["evidence_tier"] in {"low", "very_low"}
        assert claim["risk_level"] in {"medium_high", "high", "very_high"}
        assert claim["claim_text"].startswith("A social media post claims")
        assert claim["primary_evidence_needed"]
        assert "truth_status" not in claim
        assert "true" not in claim
        assert "false" not in claim


def test_northstone_pack_marks_high_burden_inference_claims() -> None:
    pack = _load_json(NORTHSTONE_PACK)
    assert isinstance(pack, dict)
    claims = {claim["claim_id"]: claim for claim in pack["claims"]}

    location_claim = claims["ns_putin_location_2026_002"]
    assert location_claim["evidence_tier"] == "very_low"
    assert location_claim["risk_level"] == "very_high"
    assert location_claim["inference_chain"] == [
        "convoy movement",
        "presumed protected-person movement",
        "bunker location",
        "absence from Moscow",
    ]

    classified_report_claim = claims["ns_eu_intel_assassination_fear_2026_005"]
    assert classified_report_claim["evidence_tier"] == "very_low"
    assert classified_report_claim["risk_level"] == "very_high"
    assert {
        "European intelligence agency",
        "classified report",
        "not meant to be public",
        "specifically by drone",
    }.issubset(set(classified_report_claim["red_flags"]))


def test_northstone_benchmark_expected_behavior_preserves_epistemic_restraint() -> None:
    pack = _load_json(NORTHSTONE_PACK)
    assert isinstance(pack, dict)
    benchmark = pack["benchmark"]

    assert benchmark["scenario"] == "social_media_geopolitical_claim_pack"
    assert {
        "does_not_assert_truth",
        "extracts_subclaims",
        "marks_evidence_insufficient",
        "identifies_unsupported_inference_chains",
        "requests_primary_sources",
        "separates_observable_from_intelligence_claims",
        "preserves_social_media_source_context",
        "keeps_absence_claims_scope_limited",
    }.issubset(set(benchmark["expected_behavior"]))
