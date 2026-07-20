from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "site" / "operator" / "index.html"
SW = ROOT / "site" / "operator" / "sw.js"


def test_operator_product_buttons_have_handlers_and_no_broken_join():
    html = INDEX.read_text(encoding="utf-8")

    assert '].join("\\n");' in html
    assert '].join("\n");' not in html

    assert '$("product_analyze").addEventListener("click", runProductAnalyze);' in html
    assert '$("product_load_news_demo").addEventListener("click", loadProductNewsDemo);' in html
    assert '$("product_show_advanced").addEventListener("click", openAdvancedConsole);' in html


def test_operator_product_no_browser_backend_or_external_form():
    html = INDEX.read_text(encoding="utf-8")

    assert "fetch(" not in html
    assert "<form" not in html
    assert "<script src=" not in html


def test_operator_service_worker_cache_bumped_for_button_fix():
    sw = SW.read_text(encoding="utf-8")

    assert "hub-optimus-operator-v0-7" in sw


def test_operator_product_loader_pacing_present():
    html = INDEX.read_text(encoding="utf-8")
    sw = SW.read_text(encoding="utf-8")

    assert "melon-loader" in html
    assert "product_loader_percent" in html
    assert "runMelonLoaderPlan" in html
    assert "assembling possible scenarios" in html
    assert "rendering final output" in html
    assert "hub-optimus-operator-v0-8" in sw
