from __future__ import annotations

import importlib.util
import json
import sys
import urllib.parse
from pathlib import Path
from typing import Any

import pytest

PACKAGE_ROOT = Path(__file__).parents[1]
MODULE_PATH = PACKAGE_ROOT / "scripts" / "apply-dataverse-schema.py"
SPEC = importlib.util.spec_from_file_location("apply_dataverse_schema_odata", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
app = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = app
SPEC.loader.exec_module(app)


FAILING_SOLUTION_QUERY = (
    "solutions?$select=solutionid,uniquename,friendlyname,version,ismanaged"
    "&$filter=uniquename eq 'OptimusAdminGateway'"
    "&$expand=publisherid($select=uniquename,customizationprefix,customizationoptionvalueprefix)"
)


def test_odata_encoder_reproduces_and_repairs_failed_solution_filter() -> None:
    encoded = app.encode_odata_relative_path(FAILING_SOLUTION_QUERY)

    assert " " not in encoded
    assert "%20" in encoded
    assert urllib.parse.unquote(encoded) == FAILING_SOLUTION_QUERY
    assert encoded.startswith("solutions?")
    assert "$filter=uniquename%20eq%20'OptimusAdminGateway'" in encoded


def test_odata_encoder_preserves_existing_escapes_and_odata_syntax() -> None:
    relative = (
        "solutions?$select=solutionid,uniquename"
        "&$filter=friendlyname%20eq%20'Optimus%20Admin%20Gateway'"
        "&$expand=publisherid($select=uniquename,customizationprefix)"
    )

    encoded = app.encode_odata_relative_path(relative)

    assert encoded == relative
    assert "%2520" not in encoded


class _FakeHttpResponse:
    status = 200
    headers: dict[str, str] = {}

    def read(self) -> bytes:
        return json.dumps({"value": []}).encode("utf-8")

    def __enter__(self) -> "_FakeHttpResponse":
        return self

    def __exit__(self, *_args: Any) -> None:
        return None


def test_urllib_transport_sends_encoded_odata_url(monkeypatch: pytest.MonkeyPatch) -> None:
    observed: dict[str, Any] = {}

    def fake_urlopen(request: Any, *, timeout: int) -> _FakeHttpResponse:
        observed["url"] = request.full_url
        observed["timeout"] = timeout
        return _FakeHttpResponse()

    monkeypatch.setattr(app.urllib.request, "urlopen", fake_urlopen)
    transport = app.UrllibTransport(
        "https://example.crm4.dynamics.com/",
        "synthetic-token",
        timeout=17,
        max_attempts=1,
    )

    response = transport.request("GET", FAILING_SOLUTION_QUERY)

    assert response.status == 200
    assert observed["timeout"] == 17
    assert observed["url"].startswith(
        "https://example.crm4.dynamics.com/api/data/v9.2/solutions?"
    )
    assert " " not in observed["url"]
    assert "$filter=uniquename%20eq%20'OptimusAdminGateway'" in observed["url"]


@pytest.mark.parametrize(
    "relative",
    [
        "https://example.com/api/data/v9.2/solutions",
        "//example.com/api/data/v9.2/solutions",
        "solutions?$select=solutionid#fragment",
        "../solutions?$select=solutionid",
        "solutions?$filter=uniquename eq 'OptimusAdminGateway'\n",
        "solutions\\unsafe",
    ],
)
def test_odata_encoder_rejects_non_relative_or_unsafe_paths(relative: str) -> None:
    with pytest.raises(app.ApplicatorError):
        app.encode_odata_relative_path(relative)
