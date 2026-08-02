import json
import re
import shutil
import subprocess
from html.parser import HTMLParser
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
OPERATOR = ROOT / "site" / "operator"
INDEX = OPERATOR / "index.html"
CATALOG = OPERATOR / "i18n.v1.js"
SW = OPERATOR / "sw.js"
LOCALE_METADATA = ROOT / "site" / "i18n" / "locale-metadata.v1.json"
LOCALE_README = ROOT / "site" / "i18n" / "README.md"
NODE = shutil.which("node")
LOCALES = ("en", "es", "de", "ru", "he", "zh-Hans")
LEARNING_KEYS = frozenset(
    """
    learningTitle
    learningIntro
    learningBoundary
    learningLocked
    learningReady
    learningStatusAria
    learningStorageUnavailable
    learningStorageBlocked
    learningStorageCorrupt
    learningStorageQuota
    learningStoreCount
    learningOutcomeLabel
    learningOutcomeHint
    learningSignalsLegend
    learningSignalLabel
    learningSignalTextLabel
    learningSignalClaimsLegend
    learningSignalEvidenceLegend
    learningAddSignal
    learningRemoveSignal
    learningSignalLimit
    learningDiagnosisLegend
    learningDiagnosisTextLabel
    learningDiagnosisCategoriesLegend
    learningDiagnosisEvidenceLegend
    learningCategoryAmbiguity
    learningCategoryWeakVerification
    learningCategoryMisalignedIncentives
    learningCategoryWrongSequence
    learningCategoryPoliticalOverload
    learningCategorySpoilers
    learningCategoryInformationAsymmetry
    learningGapLabel
    learningActionLegend
    learningActionChangeLabel
    learningActionReasonLabel
    learningActionCriterionLabel
    learningMetricsLegend
    learningMetricClarity
    learningMetricVerifiability
    learningMetricViability
    learningMetricTime
    learningMetricOpenPoints
    learningMetricScaleHint
    learningDecisionLabel
    learningDecisionRepeat
    learningDecisionEscalate
    learningDecisionChange
    learningNextExperimentLabel
    learningClosureLegend
    learningClosureFinalText
    learningClosureVerifier
    learningClosureScope
    learningClosureOpenPoints
    learningClosureMinimumPatch
    learningCreationNoteLabel
    learningCreationNoteHint
    learningCreate
    learningReset
    learningRecordsTitle
    learningNoRecords
    learningInspect
    learningExport
    learningImport
    learningDelete
    learningDeleteCase
    learningInspectorTitle
    learningHistoryTitle
    learningJsonTitle
    learningStateNoteLabel
    learningAccept
    learningReject
    learningReturnDraft
    learningStateDraft
    learningStateAccepted
    learningStateRejected
    learningFreshnessCurrent
    learningFreshnessStale
    learningFreshnessInvalid
    learningCandidateSaved
    learningCandidateTransitioned
    learningCandidateImported
    learningCandidateDeleted
    learningCaseCandidatesDeleted
    learningCandidateConflict
    learningCandidateInvalid
    learningCandidateLimit
    learningAcceptanceBlocked
    learningDeleteConfirm
    learningDeleteCaseConfirm
    learningLocalAcceptanceBoundary
    """.split()
)
LEARNING_PLACEHOLDERS = {
    "{number}",
    "{count}",
    "{max}",
    "{candidate}",
    "{case}",
    "{state}",
    "{freshness}",
    "{code}",
}


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _function_source(name: str) -> str:
    match = re.search(
        rf"^    function {re.escape(name)}\(.*?^    \}}$",
        _read(INDEX),
        re.MULTILINE | re.DOTALL,
    )
    assert match is not None, name
    return match.group(0)


def _catalog_snapshot() -> dict:
    script = r"""
const fs = require("fs");
const vm = require("vm");
const context = {globalThis: {}};
vm.createContext(context);
vm.runInContext(fs.readFileSync(process.argv[2], "utf8"), context);
const catalog = context.globalThis.HUB_OPTIMUS_OPERATOR_I18N;
console.log(JSON.stringify({
  version: catalog.version,
  supportedLocales: [...catalog.supportedLocales],
  localeMeta: catalog.localeMeta,
  messages: catalog.messages,
  frozen: Object.isFrozen(catalog) && Object.values(catalog.messages).every(Object.isFrozen)
}));
"""
    result = subprocess.run(
        [NODE, "-", str(CATALOG)],
        input=script,
        text=True,
        capture_output=True,
        check=True,
    )
    return json.loads(result.stdout)


@pytest.mark.skipif(NODE is None, reason="Node.js is required for catalog validation")
def test_operator_catalog_has_six_locale_parity_and_plain_text_values():
    catalog = _catalog_snapshot()
    html = _read(INDEX)
    assert tuple(catalog["supportedLocales"]) == LOCALES
    assert catalog["frozen"] is True
    base_keys = set(catalog["messages"]["en"])
    assert len(base_keys) >= 280
    for locale in LOCALES:
        messages = catalog["messages"][locale]
        assert set(messages) == base_keys
        assert catalog["localeMeta"][locale]["dir"] == (
            "rtl" if locale == "he" else "ltr"
        )
        assert all(isinstance(value, str) for value in messages.values())
        assert not any(re.search(r"<[^>]*>", value) for value in messages.values())
        assert messages["translationReviewNotice"].strip()
        assert messages["sourceUrlDisclosure"].strip()
        assert messages["selectionAmbiguousPassage"].strip()

    assert 'id="translation_review_notice" role="note"' in html
    assert 'aria-describedby="translation_review_notice"' in html
    assert 'data-op-i18n="translationReviewNotice"' in html
    assert len({
        catalog["messages"][locale]["translationReviewNotice"]
        for locale in LOCALES
    }) == len(LOCALES)
    assert len({
        catalog["messages"][locale]["sourceUrlDisclosure"]
        for locale in LOCALES
    }) == len(LOCALES)
    assert len({
        catalog["messages"][locale]["selectionAmbiguousPassage"]
        for locale in LOCALES
    }) == len(LOCALES)
    assert 'aria-describedby="product_source_url_hint product_source_url_disclosure"' in html
    assert 'data-op-i18n="sourceUrlDisclosure"' in html


@pytest.mark.skipif(NODE is None, reason="Node.js is required for catalog validation")
def test_operator_catalog_version_matches_locale_metadata_readme_and_cache():
    catalog = _catalog_snapshot()
    metadata = json.loads(_read(LOCALE_METADATA))
    assert catalog["version"] == "1.3.2"
    assert metadata["manifest_version"] == catalog["version"]
    assert f'catalog version: `{catalog["version"]}`' in _read(LOCALE_README)
    assert "hub-optimus-operator-v0-27" in _read(SW)


@pytest.mark.skipif(NODE is None, reason="Node.js is required for catalog validation")
def test_future_learning_catalog_is_exact_localized_and_semantically_bounded():
    catalog = _catalog_snapshot()
    assert catalog["version"] == "1.3.2"
    assert len(LEARNING_KEYS) == 91

    messages = catalog["messages"]
    english_placeholders = {
        key: sorted(re.findall(r"\{[a-z][a-z0-9_]*\}", messages["en"][key]))
        for key in LEARNING_KEYS
    }
    forbidden_terms = {
        "en": r"\b(?:memory|truth)\b|automatic learning",
        "es": r"\b(?:memoria|verdad)\b|aprendizaje autom[aá]tico",
        "de": r"\b(?:Gedächtnis|Wahrheit)\b|automatisches Lernen",
        "ru": r"памят|истин|автоматическ\w*\s+обуч",
        "he": r"זיכרון|אמת|למידה אוטומטית",
        "zh-Hans": r"记忆|真相|真伪|自动学习",
    }
    local_markers = {
        "en": "local",
        "es": "local",
        "de": "lokal",
        "ru": "локаль",
        "he": "מקומ",
        "zh-Hans": "本地",
    }

    for locale in LOCALES:
        learning = {
            key: value
            for key, value in messages[locale].items()
            if key.startswith("learning")
        }
        assert set(learning) == LEARNING_KEYS
        assert all(value.strip() for value in learning.values())
        assert not any(re.search(r"<[^>]*>", value) for value in learning.values())
        for key, value in learning.items():
            placeholders = sorted(re.findall(r"\{[a-z][a-z0-9_]*\}", value))
            assert set(placeholders) <= LEARNING_PLACEHOLDERS
            assert placeholders == english_placeholders[key]

        combined = "\n".join(learning.values())
        assert re.search(forbidden_terms[locale], combined, re.IGNORECASE) is None
        assert "Semantic Engine" in learning["learningBoundary"]
        assert "Semantic Engine" in learning["learningLocalAcceptanceBoundary"]
        marker = local_markers[locale]
        assert marker.casefold() in learning["learningBoundary"].casefold()
        assert marker.casefold() in learning["learningLocalAcceptanceBoundary"].casefold()

    assert messages["he"]["learningTitle"] != messages["en"]["learningTitle"]
    assert catalog["localeMeta"]["he"]["dir"] == "rtl"
    assert all(
        re.search(r"[\u0590-\u05ff]", messages["he"][key])
        for key in LEARNING_KEYS
    )


@pytest.mark.skipif(NODE is None, reason="Node.js is required for catalog validation")
def test_every_literal_operator_i18n_reference_exists_in_every_locale():
    html = _read(INDEX)
    references = set()
    patterns = (
        r"\bopText\(\s*[\"']([^\"']+)[\"']",
        r"\boperatorTextFor\([^,]+,\s*[\"']([^\"']+)[\"']",
        r"\bsetOperatorMessage\([^,]+,\s*[\"']([^\"']+)[\"']",
        r"\brenderMemoryStatus\(\s*[\"']([^\"']+)[\"']",
        r"data-op-i18n(?:-aria|-placeholder)?=[\"']([^\"']+)[\"']",
    )
    for pattern in patterns:
        references.update(re.findall(pattern, html))
    catalog = _catalog_snapshot()
    for locale in LOCALES:
        assert references <= set(catalog["messages"][locale])
    for key in ("resultKeepDraft", "resultReviewRecords"):
        assert key in catalog["messages"]["en"]
    for category in ("One", "Few", "Many", "Other"):
        assert f"shareOmitted{category}" in catalog["messages"]["ru"]


@pytest.mark.skipif(NODE is None, reason="Node.js is required for locale resolver validation")
def test_locale_resolution_is_query_storage_navigator_then_en_with_strict_zh_rules():
    html = _read(INDEX)
    assert "const operatorLocales = [...(operatorI18n?.supportedLocales" in html
    resolver = re.search(
        r"function normalizeOperatorLanguage\(raw\) \{.*?\n    \}",
        html,
        re.DOTALL,
    )
    assert resolver is not None
    script = rf"""
const operatorLocales = ["en", "es", "de", "ru", "he", "zh-Hans"];
{resolver.group(0)}
const cases = {{
  iw: normalizeOperatorLanguage("iw-IL"),
  cn: normalizeOperatorLanguage("zh-CN"),
  sg: normalizeOperatorLanguage("zh-SG"),
  hans: normalizeOperatorLanguage("zh-Hans"),
  hant: normalizeOperatorLanguage("zh-Hant"),
  bare: normalizeOperatorLanguage("zh"),
  unknown: normalizeOperatorLanguage("fr-FR")
}};
console.log(JSON.stringify(cases));
"""
    result = subprocess.run(
        [NODE, "-"], input=script, text=True, capture_output=True, check=True
    )
    assert json.loads(result.stdout) == {
        "iw": "he",
        "cn": "zh-Hans",
        "sg": "zh-Hans",
        "hans": "zh-Hans",
        "hant": "en",
        "bare": "en",
        "unknown": "en",
    }
    initial = html[html.index("function initialOperatorLanguage"):]
    assert initial.index('URLSearchParams(window.location.search).get("lang")') < initial.index(
        "localStorage.getItem(operatorLanguageStorageKey)"
    ) < initial.index("window.navigator.language")


@pytest.mark.skipif(NODE is None, reason="Node.js is required for manifest/catalog parity")
def test_localized_manifests_share_identity_match_metadata_and_allow_all_orientations():
    catalog = _catalog_snapshot()["messages"]
    manifests = {
        locale: json.loads(_read(OPERATOR / f"manifest.{locale}.webmanifest"))
        for locale in LOCALES
    }
    assert {manifest["id"] for manifest in manifests.values()} == {"./"}
    for locale, manifest in manifests.items():
        assert manifest["lang"] == locale
        assert manifest["dir"] == ("rtl" if locale == "he" else "ltr")
        assert manifest["start_url"] == f"./?lang={locale}"
        assert manifest["description"] == catalog[locale]["metadataDescription"]
        assert "orientation" not in manifest

    sw = _read(SW)
    assert "hub-optimus-operator-v0-27" in sw
    assert '"./i18n.v1.js"' in sw
    for locale in LOCALES:
        assert f'"./manifest.{locale}.webmanifest"' in sw


def test_primary_dynamic_states_are_keyed_and_never_trust_backend_error_prose():
    html = _read(INDEX)
    assert "payload.message" not in html
    assert "CONTROLLED_INTAKE_ERROR_CODES" in html
    assert 'throw new ControlledIntakeError("empty_extraction"' in html
    assert "renderUrlIntakeFallback(sourceUrl, error);" in html
    assert 'data-op-i18n="msgInputRequiredTitle"' in html
    assert 'data-op-message-key="${escapeHtml(reasonKey)}"' in html
    assert "return Boolean(preparedDraftReady && currentMemoryRecord);" in html
    assert '!outputText.includes("Input required")' not in html
    assert 'shareRecordLines("claim", "shareClaims"' in html
    assert 'shareRecordLines("evidence", "shareEvidence"' in html
    assert "`${label.toLowerCase()}-legacy`" not in html


def test_locale_switch_rerenders_current_view_without_retrieval_or_analysis():
    html = _read(INDEX)
    start = html.rfind('document.querySelectorAll("[data-operator-language]")')
    end = html.index("applyOperatorLanguage(initialOperatorLanguage())", start)
    assert start >= 0
    body = html[start:end]
    assert "applyOperatorLanguage" in body
    assert "refreshRetrievedSourcePreviewMeta" in body
    assert "renderSharedMemorySnapshot" not in body
    assert "renderSourceSelectionValidation" in body
    assert "renderUrlIntakeFallback" in body
    assert "renderProductOutput" in body
    assert "runProductAnalyze" not in body
    assert "readControlledUrlText" not in body
    assert "normalizePreparedSignal" not in body
    assert 'data-op-i18n="msgInputRequiredTitle"' in html
    assert 'data-op-message-key="${escapeHtml(reasonKey)}"' in html
    assert 'id="operator_landing_link" href="../?lang=en" hreflang="en"' in html
    apply_language = _function_source("applyOperatorLanguage")
    assert 'landingLink.setAttribute("hreflang", activeOperatorLanguage)' in apply_language


def test_plural_selection_and_actionable_intake_error_groups_are_structural():
    html = _read(INDEX)
    assert 'pluralMessage("sourceSummary", excerpts.length' in html
    assert 'pluralMessage("triageProblem", profile.excerpts.length)' in html
    assert 'pluralMessage("resultEvidenceCount", resultEvidence.length)' in html
    assert 'pluralMessage("shareOmitted"' in html
    for key in (
        "msgIntakeActionUrl",
        "msgIntakeActionHost",
        "msgIntakeActionContent",
        "msgIntakeActionRedirect",
        "msgIntakeActionTemporary",
    ):
        assert key in html
    for code in (
        "invalid_url",
        "blocked_url_host",
        "unresolvable_url_host",
        "unsupported_content_type",
        "empty_extraction",
        "redirect_without_location",
        "too_many_redirects",
        "url_fetch_timeout",
        "url_fetch_unavailable",
    ):
        assert f'"{code}"' in html


def test_hebrew_ui_preserves_rtl_while_source_and_technical_values_are_isolated():
    html = _read(INDEX)
    assert 'document.documentElement.dir = activeOperatorLanguage === "he" ? "rtl" : "ltr"' in html
    assert 'id="product_source_url"' in html and 'spellcheck="false" dir="ltr"' in html
    assert 'id="product_source_text" name="source_text" dir="auto"' in html
    assert 'id="product_source_preview_text" dir="auto"' in html
    assert '<div class="grid advanced-body">' in html
    assert 'class="grid advanced-body" lang="en" dir="ltr"' not in html
    assert 'id="case_json" lang="en" dir="ltr"' in html
    assert 'id="result_input" lang="en" dir="ltr"' in html
    assert 'id="input_summary" dir="auto"' in html
    assert '<details class="advanced-shell" id="advanced_operator_console">' in html
    assert '<bdi dir="ltr">${escapeHtml(opText("cardReviewMeta"))}</bdi>' not in html
    assert '<bdi dir="ltr">${escapeHtml(opText("msgIntakeErrorCode"' not in html
    fallback = _function_source("renderUrlIntakeFallback")
    assert "msgIntakeErrorCode" not in fallback
    assert "httpStatus" not in fallback
    assert "fingerprint: ltrIsolate(state.fingerprint)" in html


@pytest.mark.skipif(NODE is None, reason="Node.js is required for primary output validation")
def test_primary_intake_card_and_operational_state_render_localized_concepts_only():
    script = rf"""
const fs = require("fs");
const vm = require("vm");
const context = {{globalThis: {{}}}};
vm.createContext(context);
vm.runInContext(fs.readFileSync(process.argv[2], "utf8"), context);
const operatorI18n = context.globalThis.HUB_OPTIMUS_OPERATOR_I18N;
let activeOperatorLanguage = "en";
function operatorTextFor(language, key, parameters = {{}}) {{
  const template = operatorI18n.messages[language]?.[key] ?? operatorI18n.messages.en[key] ?? key;
  return String(template).replace(/\{{([A-Za-z][A-Za-z0-9_]*)\}}/g, (match, name) => (
    Object.prototype.hasOwnProperty.call(parameters, name) ? String(parameters[name]) : match
  ));
}}
function opText(key, parameters = {{}}) {{
  return operatorTextFor(activeOperatorLanguage, key, parameters);
}}
function escapeHtml(value) {{
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}}
function redirectCount(redirects) {{
  if (Array.isArray(redirects)) return redirects.length;
  if (Number.isInteger(redirects) && redirects >= 0) return redirects;
  return 0;
}}
{_function_source("intakeRecordCard")}
{_function_source("operationalSignalLabel")}
const forbidden = [
  "controlled-url", "operator-pasted-text", "redirects=", "truncated=",
  "verification=", "operator-provided", "unreviewed", "text/html", "signal="
];
for (const locale of operatorI18n.supportedLocales) {{
  activeOperatorLanguage = locale;
  const html = intakeRecordCard({{
    mode: "controlled-url",
    original_url: "https://origin.example/",
    final_url: "https://final.example/",
    source_domain: "final.example",
    title: "Source title",
    retrieved_at: "2026-08-01T12:00:00Z",
    redirects: [{{status: 302}}],
    content_type: "text/html; charset=utf-8",
    truncated: false,
    status: "ok",
    verification_status: "unreviewed"
  }}, {{language: locale}});
  for (const raw of forbidden) {{
    if (html.includes(raw)) throw new Error(`${{locale}} leaked ${{raw}}`);
  }}
  for (const key of [
    "intakeModeControlled", "intakeRedirectCount", "intakeContentHtml",
    "intakeSnapshotComplete", "intakeStatusRetrieved"
  ]) {{
    const expected = operatorTextFor(locale, key, {{count: 1}});
    if (!html.includes(expected)) throw new Error(`${{locale}} omitted ${{key}}`);
  }}
  const triage = operationalSignalLabel("triage");
  if (triage !== operatorI18n.messages[locale].signalTriageLabel || triage === "triage") {{
    throw new Error(`${{locale}} did not localize operational state`);
  }}
}}
"""
    result = subprocess.run(
        [NODE, "-", str(CATALOG)],
        input=script,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_primary_templates_do_not_render_internal_record_or_learning_tokens():
    html = _read(INDEX)
    source_review = _function_source("sourceReviewCard")
    checklist = _function_source("reviewChecklistCard")
    primary_result = _function_source("primaryResultCard")
    share_records = _function_source("shareRecordLines")

    assert "excerpt.excerpt_id" not in source_review
    assert "review_profile=" not in source_review
    assert "review_profile=" not in checklist
    assert "renderSharedMemorySnapshot" not in html
    assert "signal=${escapeHtml(signal)}" not in primary_result
    assert "record.id" not in share_records
    assert 'operationalSignalLabel(signal)' in primary_result


class _PrimaryTextParser(HTMLParser):
    _VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}

    def __init__(self):
        super().__init__()
        self.stack = []
        self.in_advanced = False
        self.unkeyed = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "details" and attrs.get("id") == "advanced_operator_console":
            self.in_advanced = True
        keyed = any(name.startswith("data-op-i18n") for name in attrs)
        ignored = tag in {"style", "script", "noscript"}
        if tag not in self._VOID:
            self.stack.append((tag, keyed, ignored))

    def handle_endtag(self, tag):
        while self.stack:
            open_tag, _, _ = self.stack.pop()
            if open_tag == tag:
                break
        if tag == "details" and self.in_advanced:
            self.in_advanced = False

    def handle_data(self, data):
        text = " ".join(data.split())
        if not text or self.in_advanced:
            return
        if any(ignored for _, _, ignored in self.stack):
            return
        if self.stack and self.stack[-1][1]:
            return
        self.unkeyed.append(text)


def test_primary_static_text_has_no_unkeyed_english_residue():
    parser = _PrimaryTextParser()
    parser.feed(_read(INDEX))
    allowed = {
        "HUB_OPTIMUS // OPERATOR",
        "EN", "ES", "DE", "RU", "HE", "简中",
        "Operator", "HUB_Optimus",
        "HUB_Optimus Operator",
        "PWA shell", "WhatsApp",
        "01", "02", "03", "04", "0%",
        "·", "technical view",
    }
    assert set(parser.unkeyed) <= allowed, parser.unkeyed


def test_no_script_fallback_has_six_visible_language_guides_not_a_fake_form():
    html = _read(INDEX)
    match = re.search(r"<noscript>(.*?)</noscript>", html, re.DOTALL)
    assert match is not None
    fallback = match.group(1)
    assert '<section class="noscript-warning" role="note"' in fallback
    for locale in LOCALES:
        assert f'lang="{locale}"' in fallback
        assert f'href="../?lang={locale}"' in fallback
    assert "requires JavaScript" in fallback
    assert "necesita JavaScript" in fallback
    assert "benötigt JavaScript" in fallback
    assert "требуется JavaScript" in fallback
    assert "דורש JavaScript" in fallback
    assert "需要 JavaScript" in fallback
    assert 'href="https://github.com/Voxterrae/HUB_Optimus"' in fallback
    assert "<form" not in fallback and "<input" not in fallback and "<button" not in fallback


def test_source_snapshot_is_keyboard_focusable_and_accessibly_described():
    html = _read(INDEX)
    assert (
        '<blockquote id="product_source_preview_text" dir="auto" tabindex="0" '
        'aria-labelledby="product_source_preview_title" '
        'aria-describedby="product_source_preview_meta product_source_snapshot_status '
        'product_source_selection_criterion"></blockquote>'
    ) in html


@pytest.mark.skipif(NODE is None, reason="Node.js is required for Advanced i18n validation")
def test_advanced_ui_is_localized_in_six_languages_and_technical_data_stays_ltr():
    html = _read(INDEX)
    catalog = _catalog_snapshot()
    assert catalog["version"] == "1.3.2"
    advanced_keys = {
        key for key in catalog["messages"]["en"] if key.startswith("advanced")
    }
    assert len(advanced_keys) >= 100
    critical = {
        "advancedNormalizerTitle", "advancedCaseCore", "advancedClaimsIntro",
        "advancedEvidenceIntro", "advancedPrivacyBody", "advancedRuntimeHelp",
        "advancedOutputViewerHelp", "advancedDraftSaved",
        "advancedDeleteSavedConfirm", "advancedReviewBoundaryBody",
    }
    for locale in LOCALES:
        messages = catalog["messages"][locale]
        assert advanced_keys <= set(messages)
        assert all(messages[key].strip() for key in advanced_keys)
        if locale != "en":
            assert all(messages[key] != catalog["messages"]["en"][key] for key in critical)

    assert 'data-op-i18n="technicalViewEn">technical view</span>' in html
    assert '<div class="grid advanced-body">' in html
    assert 'class="grid advanced-body" lang="en" dir="ltr"' not in html
    assert 'id="case_json" lang="en" dir="ltr"' in html
    assert 'id="result_input" lang="en" dir="ltr"' in html
    assert re.search(r'\b(?:alert|confirm)\((?!opText\()', html) is None
    assert 'intakeRecordCard(intakeRecord, { language: "en" })' not in html
    assert 'operatorContextCard(payload.metadata?.operator_context, { language: "en" })' not in html
    rerender = _function_source("renderAdvancedLocalizedView")
    assert "renderClaims()" in rerender
    assert "renderEvidence()" in rerender
    assert "renderNormalizerReadout" in rerender
    assert "renderResult({ silent: true })" in rerender
    assert "fetch(" not in rerender
    assert "runProductAnalyze" not in rerender
    render_product = re.search(
        r"function renderProductOutput\(\) \{(.*?)\n    \}", html, re.DOTALL
    )
    assert render_product is not None
    assert "primaryResultCard()" in render_product.group(1)
    assert "resultView.innerHTML" not in render_product.group(1)
