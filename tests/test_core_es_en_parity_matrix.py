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
    "translation equivalent": 1,
    "ES-only": 11,
    "EN-only": 14,
    "semantic conflict": 22,
    "editorial/order difference": 2,
    "unknown": 1,
}
EXPECTED_PAIR_CLASSIFICATION_COUNTS = {
    "declaration": {
        "translation equivalent": 0,
        "ES-only": 4,
        "EN-only": 6,
        "semantic conflict": 6,
        "editorial/order difference": 0,
        "unknown": 0,
    },
    "architecture": {
        "translation equivalent": 1,
        "ES-only": 2,
        "EN-only": 2,
        "semantic conflict": 9,
        "editorial/order difference": 1,
        "unknown": 1,
    },
    "operational_flow": {
        "translation equivalent": 0,
        "ES-only": 5,
        "EN-only": 6,
        "semantic conflict": 7,
        "editorial/order difference": 1,
        "unknown": 0,
    },
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

    assert data["schema_version"] == 2
    assert data["baseline_commit"] == BASELINE_COMMIT
    assert data["baseline_date"] == BASELINE_DATE
    assert data["review_correction_date"] == "2026-07-30"
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
    entries_by_id = {entry["id"]: entry for entry in data["entries"]}
    owned_citations: dict[tuple[str, str, str], str] = {}

    for entry in data["entries"]:
        assert entry["es"] or entry["en"]
        for language in ("es", "en"):
            for citation in entry[language]:
                path = citation["path"]
                assert path in EXPECTED_FILES
                assert f"/{language}/" in path
                citations_by_path[path].append(citation["heading"])
                citation_key = (language, path, citation["heading"])
                assert citation_key not in owned_citations
                owned_citations[citation_key] = entry["id"]

    for relative_path, cited_headings in citations_by_path.items():
        source_headings = _headings(REPO_ROOT / relative_path)
        assert Counter(cited_headings) == Counter(source_headings), relative_path
        assert len(cited_headings) == len(set(cited_headings)), relative_path

    assert sum(len(items) for items in citations_by_path.values()) == 85

    for entry in data["entries"]:
        seen_cross_references: set[tuple[str, str, str]] = set()
        for reference in entry.get("cross_references", []):
            assert set(reference) == {
                "owner_entry_id",
                "language",
                "path",
                "heading",
                "scope",
            }
            owner_entry_id = reference["owner_entry_id"]
            assert owner_entry_id in entries_by_id
            assert owner_entry_id != entry["id"]
            assert entries_by_id[owner_entry_id]["pair_id"] == entry["pair_id"]
            assert isinstance(reference["scope"], str) and reference["scope"].strip()

            citation_key = (
                reference["language"],
                reference["path"],
                reference["heading"],
            )
            assert citation_key not in seen_cross_references
            seen_cross_references.add(citation_key)
            assert owned_citations[citation_key] == owner_entry_id


def test_entries_use_only_evidence_classes_and_match_the_written_summary() -> None:
    data = _matrix_data()
    entries = data["entries"]

    assert len(entries) == 51
    assert len({entry["id"] for entry in entries}) == len(entries)
    assert Counter(entry["pair_id"] for entry in entries) == Counter(EXPECTED_PAIR_COUNTS)
    assert Counter(entry["classification"] for entry in entries) == Counter(
        EXPECTED_CLASSIFICATION_COUNTS
    )
    for pair_id, expected_counts in EXPECTED_PAIR_CLASSIFICATION_COUNTS.items():
        assert Counter(
            entry["classification"] for entry in entries if entry["pair_id"] == pair_id
        ) == Counter(expected_counts)

    for entry in entries:
        assert entry["classification"] in ALLOWED_CLASSIFICATIONS
        assert entry["pair_id"] in EXPECTED_PAIR_COUNTS
        assert isinstance(entry["evidence"], str) and entry["evidence"].strip()
        represented_languages = {
            language
            for language in ("es", "en")
            if entry[language]
            or any(
                reference["language"] == language
                for reference in entry.get("cross_references", [])
            )
        }
        if entry["classification"] == "ES-only":
            assert represented_languages == {"es"}
        elif entry["classification"] == "EN-only":
            assert represented_languages == {"en"}
        else:
            assert represented_languages == {"es", "en"}

    text = _matrix_text()
    assert "| Declaration | 16 | 0 | 4 | 6 | 6 | 0 | 0 |" in text
    assert "| Architecture | 16 | 1 | 2 | 2 | 9 | 1 | 1 |" in text
    assert "| Operational flow | 19 | 0 | 5 | 6 | 7 | 1 | 0 |" in text
    assert "| **Total** | **51** | **1** | **11** | **14** | **22** | **2** | **1** |" in text


def test_review_corrections_preserve_the_six_unresolved_differences() -> None:
    entries = {entry["id"]: entry for entry in _matrix_data()["entries"]}

    assert entries["declaration-06"]["classification"] == "semantic conflict"
    assert "verification and coherence" in entries["declaration-06"]["evidence"]

    assert entries["architecture-01"]["classification"] == "semantic conflict"
    assert (
        "transforms results into system improvements"
        in entries["architecture-01"]["evidence"]
    )

    assert entries["architecture-07"]["classification"] == "semantic conflict"
    assert "four fixed questions" in entries["architecture-07"]["evidence"]
    assert "main decision engine" in entries["architecture-07"]["evidence"]

    architecture_io = entries["architecture-10"]
    assert architecture_io["classification"] == "semantic conflict"
    assert {
        reference["owner_entry_id"] for reference in architecture_io["cross_references"]
    } == {f"architecture-{number:02d}" for number in range(4, 10)}
    assert {reference["language"] for reference in architecture_io["cross_references"]} == {
        "en"
    }

    assert entries["operational-flow-12"]["classification"] == "semantic conflict"
    assert "scenario or template" in entries["operational-flow-12"]["evidence"]
    assert "Active Memory" in entries["operational-flow-12"]["evidence"]

    preventive = entries["operational-flow-13"]
    assert preventive["classification"] == "semantic conflict"
    assert preventive["cross_references"] == [
        {
            "owner_entry_id": "operational-flow-11",
            "language": "es",
            "path": "v1_core/languages/es/03_flujo_operativo.md",
            "heading": "## 5) Aplicación de capas (cómo usar la arquitectura en la práctica)",
            "scope": "Layer 4 checkpoint asking which minimal intervention avoids the failure mode",
        }
    ]


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
