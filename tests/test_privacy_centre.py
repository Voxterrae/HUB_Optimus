"""Privacy publication gates: incomplete notices must not acquire verified status."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "site/privacy/privacy.v1.js"
NODE = shutil.which("node")


def evaluate(expression):
    assert SCRIPT.exists(), "Privacy centre is not implemented"
    if not NODE:
        pytest.skip("Node is needed for browser-independent privacy checks")
    result = subprocess.run(
        [NODE, "-e", f"const api = require({json.dumps(str(SCRIPT))});\n"
         f"console.log(JSON.stringify({expression}));"],
        cwd=ROOT, check=True, capture_output=True, text=True,
    )
    return json.loads(result.stdout)


def complete_config():
    return {
        "controller": {"name": "Example Controller", "verified": True},
        "contact": {"email": "privacy@example.org", "verified": True},
        "hosting": {"reviewed": True, "summary": {"es": "Alojamiento revisado", "en": "Reviewed hosting", "de": "Geprüftes Hosting"}},
        "retention": {"reviewed": True, "summary": {"es": "Conservación revisada", "en": "Reviewed retention", "de": "Geprüfte Aufbewahrung"}},
        "noticeApproved": True,
    }


def test_unknown_configuration_cannot_present_a_final_notice_or_contact():
    result = evaluate("api.assessPublication(null)")
    assert result == {
        "ready": False,
        "missing": ["controller", "contact", "hosting", "retention", "review"],
        "contactHref": None,
    }


def test_verified_complete_configuration_can_offer_its_private_contact():
    result = evaluate(f"api.assessPublication({json.dumps(complete_config())})")
    assert result == {
        "ready": True, "missing": [], "contactHref": "mailto:privacy@example.org"
    }


@pytest.mark.parametrize("field", ["controller", "contact", "hosting", "retention", "review"])
def test_one_missing_verification_keeps_the_notice_in_draft(field):
    config = complete_config()
    if field == "review":
        config["noticeApproved"] = False
    elif field in {"controller", "contact"}:
        config[field]["verified"] = False
    else:
        config[field]["reviewed"] = False
    result = evaluate(f"api.assessPublication({json.dumps(config)})")
    assert result["ready"] is False
    assert result["missing"] == [field]
    if field in {"contact", "controller"}:
        assert result["contactHref"] is None


@pytest.mark.parametrize("address", ["", "privacy@example.org?bcc=x@y.org", "x@y.org\r\nBcc:z@y.org", "javascript:alert(1)", "a.@example.org", "a..b@example.org", "a@x.-org.org", "a@x-.example.org", "a@ex..ample.org", None])
def test_contact_flag_cannot_turn_an_unsafe_or_empty_address_into_a_link(address):
    config = complete_config()
    config["contact"]["email"] = address
    result = evaluate(f"api.assessPublication({json.dumps(config)})")
    assert result["ready"] is False
    assert result["contactHref"] is None
    assert "contact" in result["missing"]


def test_empty_controller_name_cannot_pass_even_when_its_flag_is_true():
    config = complete_config()
    config["controller"]["name"] = "  "
    result = evaluate(f"api.assessPublication({json.dumps(config)})")
    assert result["ready"] is False
    assert result["contactHref"] is None


@pytest.mark.parametrize("field", ["hosting", "retention"])
def test_review_flag_without_descriptions_in_all_supported_languages_is_not_ready(field):
    config = complete_config()
    config[field]["summary"].pop("de")
    result = evaluate(f"api.assessPublication({json.dumps(config)})")
    assert result["ready"] is False
    assert result["missing"] == [field]


@pytest.mark.parametrize("value, expected", [("es-ES", "es"), ("DE-de", "de"), ("en", "en"), ("ru", "en"), ("<img src=x>", "en"), (None, "en")])
def test_locale_selection_has_a_safe_supported_fallback(value, expected):
    assert evaluate(f"api.resolveLanguage({json.dumps(value)})") == expected
