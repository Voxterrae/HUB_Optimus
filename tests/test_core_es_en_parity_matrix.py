from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MATRIX_PATH = REPO_ROOT / "docs" / "i18n" / "core_es_en_parity_matrix.md"
BASELINE_COMMIT = "3ef199305c2d2d114f88aceb97b65a08b9f91b4a"
BASELINE_DATE = "2026-07-28"
ALLOWED_CLASSIFICATIONS = {
    "translation equivalent",
    "ES-only",
    "EN-only",
    "semantic conflict",
    "editorial/order difference",
    "unknown",
}
ALLOWED_DISPOSITIONS = [
    "Spanish canonical wins",
    "separate governance RFC",
    "English explanatory non-canonical",
]
EXPECTED_FILES = {
    "v1_core/languages/es/01_base_declaracion.md",
    "v1_core/languages/en/01_base_declaracion.md",
    "v1_core/languages/es/02_arquitectura_base.md",
    "v1_core/languages/en/02_arquitectura_base.md",
    "v1_core/languages/es/03_flujo_operativo.md",
    "v1_core/languages/en/03_flujo_operativo.md",
}
EXPECTED_PAIR_COUNTS = {
    "declaration": 16,
    "architecture": 16,
    "operational_flow": 19,
}
EXPECTED_CLASSIFICATION_COUNTS = {
    "translation equivalent": 2,
    "ES-only": 12,
    "EN-only": 15,
    "semantic conflict": 16,
    "editorial/order difference": 5,
    "unknown": 1,
}


def _matrix_text() -> str:
    return MATRIX_PATH.read_text(encoding="utf-8")


def _matrix_data() -> dict[str, object]:
    match = re.search(
        r"## Machine-readable section matrix.*?```json\n(?P<payload>.*?)\n```",
        _matrix_text(),
        flags=re.DOTALL,
    )
    assert match is not None, "machine-readable JSON block is missing"
    payload = json.loads(match.group("payload"))
    assert isinstance(payload, dict)
    return payload


def _headings(path: Path) -> list[str]:
    return [
        line
        for line in path.read_text(encoding="utf-8").splitlines()
        if re.match(r"^#{1,6} ", line)
    ]


def test_matrix_is_bound_to_the_requested_baseline_and_all_six_files() -> None:
    data = _matrix_data()

    assert data["schema_version"] == 1
    assert data["baseline_commit"] == BASELINE_COMMIT
    assert data["baseline_date"] == BASELINE_DATE
    assert data["canonical_language"] == "es"
    assert data["parity_target"] == "en"
    assert set(data["allowed_classifications"]) == ALLOWED_CLASSIFICATIONS
    assert data["allowed_human_dispositions"] == ALLOWED_DISPOSITIONS

    source_files = data["source_files"]
    assert isinstance(source_files, list)
    assert {record["path"] for record in source_files} == EXPECTED_FILES
    assert Counter(record["language"] for record in source_files) == Counter({"es": 3, "en": 3})
    assert Counter(record["pair_id"] for record in source_files) == Counter(
        {"declaration": 2, "architecture": 2, "operational_flow": 2}
    )

    for record in source_files:
        source_path = REPO_ROOT / record["path"]
        digest = hashlib.sha256(source_path.read_bytes()).hexdigest()
        assert digest == record["sha256"], f"baseline content changed: {record['path']}"


def test_every_source_heading_is_cited_exactly_once() -> None:
    data = _matrix_data()
    citations_by_path: dict[str, list[str]] = {path: [] for path in EXPECTED_FILES}

    for entry in data["entries"]:
        assert entry["es"] or entry["en"]
        for language in ("es", "en"):
            for citation in entry[language]:
                path = citation["path"]
                assert path in EXPECTED_FILES
                assert f"/{language}/" in path
                citations_by_path[path].append(citation["heading"])

    for relative_path, cited_headings in citations_by_path.items():
        source_headings = _headings(REPO_ROOT / relative_path)
        assert Counter(cited_headings) == Counter(source_headings), relative_path
        assert len(cited_headings) == len(set(cited_headings)), relative_path

    assert sum(len(items) for items in citations_by_path.values()) == 85


def test_entries_use_only_evidence_classes_and_match_the_written_summary() -> None:
    data = _matrix_data()
    entries = data["entries"]

    assert len(entries) == 51
    assert len({entry["id"] for entry in entries}) == len(entries)
    assert Counter(entry["pair_id"] for entry in entries) == Counter(EXPECTED_PAIR_COUNTS)
    assert Counter(entry["classification"] for entry in entries) == Counter(
        EXPECTED_CLASSIFICATION_COUNTS
    )

    for entry in entries:
        assert entry["classification"] in ALLOWED_CLASSIFICATIONS
        assert entry["pair_id"] in EXPECTED_PAIR_COUNTS
        assert isinstance(entry["evidence"], str) and entry["evidence"].strip()
        if entry["classification"] == "ES-only":
            assert entry["es"] and not entry["en"]
        elif entry["classification"] == "EN-only":
            assert entry["en"] and not entry["es"]
        else:
            assert entry["es"] and entry["en"]

    text = _matrix_text()
    assert "| **Total** | **51** | **2** | **12** | **15** | **16** | **5** | **1** |" in text


def test_every_human_disposition_is_explicitly_unresolved_and_unselected() -> None:
    data = _matrix_data()

    for entry in data["entries"]:
        disposition = entry["human_disposition"]
        assert set(disposition) == {"status", "allowed_options"}
        assert disposition["status"] == "UNRESOLVED"
        assert disposition["allowed_options"] == ALLOWED_DISPOSITIONS

    serialized = json.dumps(data, ensure_ascii=False)
    for invented_field in ('"selected"', '"decision"', '"resolved_by"', '"approved_by"'):
        assert invented_field not in serialized


def test_artifact_does_not_claim_english_parity_or_new_kernel_readiness() -> None:
    text = _matrix_text()

    assert "English parity is not established" in text
    assert "no Russian, Hebrew, or Chinese Kernel-readiness claim is valid" in text

    forbidden_affirmations = (
        "English parity is established",
        "English parity is complete",
        "English parity has been achieved",
        "RU/HE/ZH Kernel-ready",
        "Russian Kernel-ready",
        "Hebrew Kernel-ready",
        "Chinese Kernel-ready",
        "Russian Kernel parity",
        "Hebrew Kernel parity",
        "Chinese Kernel parity",
    )
    for affirmation in forbidden_affirmations:
        assert affirmation not in text
