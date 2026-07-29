"""Tests for the versioned translation maturity policy."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from tools.check_mirror import MirrorChecker
from tools.i18n_maturity import (
    ManifestError,
    REQUIRED_STATES,
    audit_repository,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST = REPO_ROOT / "docs" / "i18n" / "maturity.v1.json"


def _fixture_manifest(
    target_declaration: str | dict[str, Any],
    *,
    required: str | list[str] = "all",
) -> dict[str, Any]:
    return {
        "manifest_version": 1,
        "policy": {
            "canonical_v1": "es",
            "parity_target_v1": "en",
            "docs_structural_baseline": "en",
        },
        "states": {state: {"description": state} for state in REQUIRED_STATES},
        "tiers": {
            "source": {"required": {"onboarding": "all"}},
            "target": {"required": {"onboarding": required}},
        },
        "locales": {
            "en": {"path": ".", "direction": "ltr", "tier": "source"},
            "de": {"path": "de", "direction": "ltr", "tier": "target"},
        },
        "surfaces": {
            "onboarding": {
                "source_locale": "en",
                "source_state": "parity",
                "subdir": ".",
                "inventory": "selected",
                "files": ["start.md"],
                "maturity": {
                    "en": {"default": "parity"},
                    "de": {"default": target_declaration},
                },
            }
        },
    }


def _write_fixture(
    tmp_path: Path,
    *,
    target_text: str | None,
    target_declaration: str | dict[str, Any],
    required: str | list[str] = "all",
) -> tuple[Path, Path]:
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "start.md").write_text("# English source\n", encoding="utf-8")
    if target_text is not None:
        target_dir = docs / "de"
        target_dir.mkdir()
        (target_dir / "start.md").write_text(target_text, encoding="utf-8")
    manifest_path = docs / "maturity.json"
    manifest_path.write_text(
        json.dumps(
            _fixture_manifest(target_declaration, required=required),
            indent=2,
        ),
        encoding="utf-8",
    )
    return docs, manifest_path


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _reviewed_declaration(source_text: str, target_text: str) -> dict[str, Any]:
    return {
        "state": "reviewed",
        "review": {
            "reviewer": "qualified-reviewer",
            "evidence": "https://github.com/example/repo/pull/1",
            "source_sha256": _digest(source_text),
            "target_sha256": _digest(target_text),
        },
    }


def test_repository_manifest_is_honest_and_explicit() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    assert manifest["policy"]["canonical_v1"] == "es"
    assert manifest["policy"]["parity_target_v1"] == "en"
    assert manifest["policy"]["chinese_scope"]["current"] == "zh-Hans"
    assert manifest["policy"]["chinese_scope"]["not_in_scope"] == ["zh-Hant"]
    assert manifest["locales"]["he"]["direction"] == "rtl"
    assert manifest["locales"]["zh-Hans"]["path"] == "zh"
    assert manifest["surfaces"]["onboarding"]["source_state"] == "parity"
    assert manifest["surfaces"]["governance"]["source_state"] == "canonical"
    assert (
        manifest["surfaces"]["governance"]["maturity"]["en"]["default"]
        == "canonical"
    )
    assert REQUIRED_STATES <= set(manifest["states"])

    result = audit_repository(REPO_ROOT)

    assert result.ok, "\n".join(result.errors)
    assert not result.warnings
    observed = {
        (item.locale, item.surface, item.filename): item
        for item in result.observations
    }
    assert observed[("he", "onboarding", "02_how_to_read_this_repo.md")].state == "missing"
    assert observed[("zh-Hans", "onboarding", "03_try_a_scenario.md")].state == "missing"
    assert observed[("es", "governance", "EVALUATION_STANDARD.md")].state == "stub"
    assert observed[
        ("es", "governance", "EVALUATION_STANDARD.md")
    ].identical_to_source


def test_byte_identical_copy_must_be_declared_stub(tmp_path: Path) -> None:
    docs, manifest_path = _write_fixture(
        tmp_path,
        target_text="# English source\n",
        target_declaration="review-needed",
    )

    result = audit_repository(
        tmp_path,
        docs_dir=docs,
        manifest_path=manifest_path,
    )

    assert not result.ok
    assert "byte-identical" in "\n".join(result.errors)


def test_explicit_stub_declaration_allows_identical_copy(tmp_path: Path) -> None:
    docs, manifest_path = _write_fixture(
        tmp_path,
        target_text="# English source\n",
        target_declaration="stub",
    )

    result = audit_repository(
        tmp_path,
        docs_dir=docs,
        manifest_path=manifest_path,
    )

    assert result.ok, "\n".join(result.errors)


def test_reviewed_requires_content_bound_reviewer_evidence(tmp_path: Path) -> None:
    docs, manifest_path = _write_fixture(
        tmp_path,
        target_text="# Deutsche Fassung\n",
        target_declaration="reviewed",
    )

    with pytest.raises(ManifestError, match="structured review record"):
        audit_repository(
            tmp_path,
            docs_dir=docs,
            manifest_path=manifest_path,
        )


def test_reviewed_with_evidence_can_pass(tmp_path: Path) -> None:
    source_text = "# English source\n"
    target_text = "# Deutsche Fassung\n"
    docs, manifest_path = _write_fixture(
        tmp_path,
        target_text=target_text,
        target_declaration=_reviewed_declaration(source_text, target_text),
    )

    result = audit_repository(
        tmp_path,
        docs_dir=docs,
        manifest_path=manifest_path,
    )

    assert result.ok, "\n".join(result.errors)


@pytest.mark.parametrize("changed_file", ["source", "target"])
def test_review_evidence_expires_when_reviewed_bytes_change(
    tmp_path: Path,
    changed_file: str,
) -> None:
    source_text = "# English source\n"
    target_text = "# Deutsche Fassung\n"
    docs, manifest_path = _write_fixture(
        tmp_path,
        target_text=target_text,
        target_declaration=_reviewed_declaration(source_text, target_text),
    )

    if changed_file == "source":
        (docs / "start.md").write_text("# Updated English source\n", encoding="utf-8")
    else:
        (docs / "de" / "start.md").write_text(
            "# Aktualisierte deutsche Fassung\n",
            encoding="utf-8",
        )

    result = audit_repository(
        tmp_path,
        docs_dir=docs,
        manifest_path=manifest_path,
    )

    assert not result.ok
    assert f"review {changed_file}_sha256" in "\n".join(result.errors)


def test_canonicality_is_surface_specific(tmp_path: Path) -> None:
    docs, manifest_path = _write_fixture(
        tmp_path,
        target_text="# Deutsche Fassung\n",
        target_declaration="review-needed",
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    surface = manifest["surfaces"]["onboarding"]
    surface["source_state"] = "canonical"
    surface["maturity"]["en"]["default"] = "canonical"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    source_result = audit_repository(
        tmp_path,
        docs_dir=docs,
        manifest_path=manifest_path,
    )
    assert source_result.ok, "\n".join(source_result.errors)

    manifest["surfaces"]["onboarding"]["maturity"]["de"]["default"] = "canonical"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    target_result = audit_repository(
        tmp_path,
        docs_dir=docs,
        manifest_path=manifest_path,
    )

    assert not target_result.ok
    assert "reserved for the onboarding source locale" in "\n".join(
        target_result.errors
    )


def test_missing_is_green_only_when_tier_does_not_require_file(tmp_path: Path) -> None:
    docs, manifest_path = _write_fixture(
        tmp_path,
        target_text=None,
        target_declaration="missing",
        required=[],
    )
    optional_result = audit_repository(
        tmp_path,
        docs_dir=docs,
        manifest_path=manifest_path,
    )
    assert optional_result.ok, "\n".join(optional_result.errors)

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["tiers"]["target"]["required"]["onboarding"] = "all"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    required_result = audit_repository(
        tmp_path,
        docs_dir=docs,
        manifest_path=manifest_path,
    )

    assert not required_result.ok
    assert "requires this file" in "\n".join(required_result.errors)


def test_i18n_cli_has_an_honest_green_result() -> None:
    result = subprocess.run(
        [sys.executable, "i18n_sync.py"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "he (rtl" in result.stdout
    assert "zh-Hans" in result.stdout
    assert "does not certify linguistic parity" in result.stdout


def test_governance_mirror_check_includes_hebrew_and_simplified_chinese(
    capsys: pytest.CaptureFixture[str],
) -> None:
    checker = MirrorChecker(repo_root=str(REPO_ROOT))

    assert checker.check_governance_structure() == 0
    output = capsys.readouterr().out
    assert "he (rtl" in output
    assert "zh-Hans" in output
    assert "does not certify linguistic parity" in output
