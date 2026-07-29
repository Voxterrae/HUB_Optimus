"""Regression tests for the Catalunya fire-response documentation boundary."""

from __future__ import annotations

import json
import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DOCUMENT_PATH = (
    REPO_ROOT / "docs" / "es" / "operational" / "fire-response-catalunya.md"
)


def _document() -> str:
    return DOCUMENT_PATH.read_text(encoding="utf-8")


def _json_block_after(marker: str) -> object:
    text = _document()
    marker_offset = text.index(marker)
    match = re.search(r"```json\n(.*?)\n```", text[marker_offset:], re.DOTALL)
    assert match is not None, f"missing JSON block after {marker!r}"
    return json.loads(match.group(1))


def test_document_is_explicitly_non_implementing_and_non_authorizing() -> None:
    text = _document()
    normalized = " ".join(text.split())

    required_boundaries = (
        "no implementada ni autorizada para uso operativo",
        "este documento no describe una capacidad implementada",
        "Este documento no autoriza:",
        "no pueden interpretar este documento como backlog",
        "El issue #1685 autoriza únicamente corregir este límite documental.",
        "No hay checklist de despliegue, pipeline recomendado ni backlog activo",
    )
    for boundary in required_boundaries:
        assert boundary in normalized

    retired_implementation_language = (
        "## 14. Checklist técnico de despliegue",
        "## 15. Pipeline CI/CD recomendado",
        "## 16. Backlog inicial para Copilot",
        "El módulo se considerará listo para prueba controlada",
        "Crear módulo `services/fire-response`",
        "npm run validate:schemas",
    )
    for phrase in retired_implementation_language:
        assert phrase not in text


def test_hotspot_example_is_valid_geojson_feature_collection() -> None:
    payload = _json_block_after(
        "Salida conceptual. El repositorio no genera actualmente este objeto:"
    )

    assert isinstance(payload, dict)
    assert payload["type"] == "FeatureCollection"
    assert isinstance(payload["features"], list)
    assert payload["features"]
    assert "properties" not in payload
    assert payload["metadata"] == {
        "incident_id": "CAT-FIRE-2026-0001",
        "model": "hotspot_detector_v1",
        "generated_at": "2026-07-04T09:20:00Z",
    }
    assert all(feature["type"] == "Feature" for feature in payload["features"])


def test_operational_threshold_requires_an_authorized_human_role() -> None:
    payload = _json_block_after("### 6.2 Umbral 2 — Alerta operativa")

    assert isinstance(payload, dict)
    assert payload["requires_human_validation"] is True
    assert payload["requires_authorized_role"] is True
    assert payload["role_authority"] == "competent_public_authority"


def test_future_implementation_surfaces_remain_behind_governed_human_gates() -> None:
    text = _document()
    normalized = " ".join(text.split())

    assert (
        "| Código, API, conectores y modelos de IA | "
        "No implementados ni autorizados |"
    ) in text
    assert (
        "| Infraestructura como código, CI/CD y despliegue | "
        "No implementados ni autorizados |"
    ) in text
    assert (
        "| Dashboard, GIS y monitorización | "
        "No implementados ni autorizados |"
    ) in text
    assert "un RFC aprobado antes de implementar" in normalized
    assert (
        "| Backlog para Copilot u otra herramienta de IA | "
        "No existe ni está autorizado |"
    ) in text
    assert "RFC aprobado y backlog redactado y autorizado explícitamente" in text
    assert "autoridad pública competente, protocolo oficial" in normalized
    assert "Ninguno puede heredar autorización de este borrador." in normalized
