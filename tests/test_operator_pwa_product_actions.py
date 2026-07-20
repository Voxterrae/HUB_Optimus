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


def test_operator_product_loader_pacing_present():
    html = INDEX.read_text(encoding="utf-8")
    sw = SW.read_text(encoding="utf-8")

    assert "melon-loader" in html
    assert "product_loader_percent" in html
    assert "runMelonLoaderPlan" in html
    assert "assembling possible scenarios" in html
    assert "rendering final output" in html
    assert "hub-optimus-operator-v0-11" in sw


def test_operator_source_intelligence_v2_present():
    html = INDEX.read_text(encoding="utf-8")
    sw = SW.read_text(encoding="utf-8")

    assert "buildSourceProfile" in html
    assert "detectSignalDomain" in html
    assert "extractActors" in html
    assert "operator-source-intelligence-v0.2" in html
    assert "HUB_Optimus procedure" in html
    assert "evidence lock" in html
    assert "hub-optimus-operator-v0-11" in sw


def test_operator_memory_share_snapshot_present():
    html = INDEX.read_text(encoding="utf-8")
    sw = SW.read_text(encoding="utf-8")

    assert "hub_optimus_operator_memory_v1" in html
    assert "Save result memory" in html
    assert "Share memory link" in html
    assert "Share to WhatsApp" in html
    assert "candidate-signal-not-canonical" in html
    assert "buildMemoryShareUrl" in html
    assert "loadSharedMemoryFromHash" in html
    assert "https://wa.me/" in html
    assert "og:title" in html
    assert "hub-optimus-operator-v0-11" in sw
    assert "./og.svg" in sw


def test_operator_install_icon_reactor_mark_present():
    icon = (ROOT / "site" / "operator" / "icon.svg").read_text(encoding="utf-8")
    sw = SW.read_text(encoding="utf-8")

    assert "Melon nuke reactor icon" in icon
    assert "url(#segment)" in icon
    assert ">HO</text>" in icon
    assert "hub-optimus-operator-v0-11" in sw
