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


def test_operator_product_uses_only_controlled_url_intake_fetch_and_no_external_form():
    html = INDEX.read_text(encoding="utf-8")

    assert "CONTROLLED_URL_INTAKE_ENDPOINT" in html
    assert "https://api.huboptimus.dev/intake/url" in html
    assert "fetch(CONTROLLED_URL_INTAKE_ENDPOINT" in html
    assert "fetch(sourceUrl" not in html
    assert "fetch(url" not in html
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
    assert "hub-optimus-operator-v0-16" in sw


def test_operator_source_intelligence_v2_present():
    html = INDEX.read_text(encoding="utf-8")
    sw = SW.read_text(encoding="utf-8")

    assert "buildSourceProfile" in html
    assert "detectSignalDomain" in html
    assert "extractActors" in html
    assert "operator-source-intelligence-v0.2" in html
    assert "HUB_Optimus procedure" in html
    assert "evidence lock" in html
    assert "hub-optimus-operator-v0-16" in sw


def test_operator_memory_share_snapshot_present():
    html = INDEX.read_text(encoding="utf-8")
    sw = SW.read_text(encoding="utf-8")

    assert "hub_optimus_operator_memory_v1" in html
    assert "Save memory" in html
    assert "Copy share summary" in html
    assert "WhatsApp" in html
    assert "candidate-signal-not-canonical" in html
    assert "buildMemoryShareUrl" in html
    assert "loadSharedMemoryFromHash" in html
    assert "https://wa.me/" in html
    assert "og:title" in html
    assert "hub-optimus-operator-v0-16" in sw
    assert "./og.svg" in sw


def test_operator_install_icon_reactor_mark_present():
    icon = (ROOT / "site" / "operator" / "icon.svg").read_text(encoding="utf-8")
    sw = SW.read_text(encoding="utf-8")

    assert "Melon nuke reactor icon" in icon
    assert "url(#segment)" in icon
    assert ">HO</text>" in icon
    assert "hub-optimus-operator-v0-16" in sw


def test_operator_product_ux_controls_are_gated():
    html = INDEX.read_text(encoding="utf-8")
    sw = SW.read_text(encoding="utf-8")

    assert "Run an analysis to unlock memory and sharing." in html
    assert 'id="save_memory_result" type="button" disabled' in html
    assert 'id="share_memory_link" type="button" disabled' in html
    assert 'id="share_memory_whatsapp" type="button" disabled' in html
    assert "setMemoryActionsEnabled" in html
    assert "syncProductInputState" in html
    assert "Ready to read URL from controlled intake. If the source blocks access, paste the article text." in html
    assert "Result ready. Memory and sharing are available." in html
    assert ".status-strip" in html
    assert ".reactor-band" in html
    assert "hub-optimus-operator-v0-16" in sw


def test_operator_url_only_fallback_message_present():
    html = INDEX.read_text(encoding="utf-8")
    sw = SW.read_text(encoding="utf-8")

    assert "URL not accessible from controlled intake" in html
    assert "Paste the article text or relevant excerpt below and run Analyze again." in html
    assert "Some sources block automated access" in html
    assert "Controlled intake service is unreachable" in html
    assert "readControlledUrlText" in html
    assert "renderUrlIntakeFallback" in html
    assert "Ready to read URL from controlled intake" in html
    assert "hub-optimus-operator-v0-16" in sw


def test_operator_topic_aware_analysis_present():
    html = INDEX.read_text(encoding="utf-8")
    sw = SW.read_text(encoding="utf-8")

    assert "buildThematicAnalysis" in html
    assert "thematicAnalysisCard" in html
    assert "housing-finance" in html
    assert "vivienda / financiación doméstica" in html
    assert "El problema real no es solo que una vivienda sea barata o cara" in html
    assert "cuota mensual" in html
    assert "security-conflict" in html
    assert "geopolítica / conflicto internacional" in html
    assert "topic_analysis_version" in html
    assert "operator-topic-analysis-v0.1" in html
    assert "hub-optimus-operator-v0-16" in sw


def test_operator_geopolitical_conflict_analysis_is_specific():
    html = INDEX.read_text(encoding="utf-8")
    sw = SW.read_text(encoding="utf-8")

    assert "geopolítica / conflicto internacional" in html
    assert "Matriz de actores / intereses" in html
    assert "Preguntas geopolíticas" in html
    assert "Escenarios operativos" in html
    assert "Contradicciones a buscar" in html
    assert "propaganda, disuasión o negociación" in html
    assert "rutas comerciales" in html
    assert "alto el fuego" in html
    assert "Escenario B // escalada regional" in html
    assert "negociación bajo fuego" in html
    assert "hub-optimus-operator-v0-16" in sw


def test_operator_share_output_is_readable_without_encoded_snapshot_url():
    html = INDEX.read_text(encoding="utf-8")
    sw = SW.read_text(encoding="utf-8")

    assert "Copy share summary" in html
    assert "buildHumanShareText" in html
    assert "buildCleanOperatorUrl" in html
    assert "Resumen legible copiado. Sin URL codificada." in html
    assert "WhatsApp abierto con resumen legible. Sin URL codificada." in html
    assert "Límite: señal no verificada; no es veredicto de verdad." in html
    assert "`Abrir Operator: ${buildCleanOperatorUrl()}`" in html
    assert "const url = buildMemoryShareUrl(record);" not in html
    assert "record.claim,\n        url" not in html
    assert "hub-optimus-operator-v0-16" in sw
