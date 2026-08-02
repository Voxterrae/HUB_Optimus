import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "site" / "operator" / "index.html"
ICON = ROOT / "site" / "operator" / "icon.svg"
LOCKUP = ROOT / "site" / "assets" / "brand" / "hub-optimus-logo-lockup.png"
SW = ROOT / "site" / "operator" / "sw.js"
OPERATOR_I18N = ROOT / "site" / "operator" / "i18n.v1.js"
URL_INTAKE_SCHEMA = (
    ROOT / "ops" / "ec2" / "controlled_url_intake.v1.schema.json"
)
NODE = shutil.which("node")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _operator_i18n_node_prelude() -> str:
    return _read(OPERATOR_I18N) + r"""
const operatorI18n = globalThis.HUB_OPTIMUS_OPERATOR_I18N;
let activeOperatorLanguage = "en";
function opText(key, parameters = {}) {
  const template = operatorI18n.messages[activeOperatorLanguage][key];
  return String(template).replace(/\{([A-Za-z][A-Za-z0-9_]*)\}/g, (match, name) => (
    Object.prototype.hasOwnProperty.call(parameters, name) ? String(parameters[name]) : match
  ));
}
function ltrIsolate(value) { return `\u2066${String(value ?? "")}\u2069`; }
function pluralMessage(baseKey, count, parameters = {}) {
  const category = new Intl.PluralRules(activeOperatorLanguage).select(count);
  const key = `${baseKey}${category[0].toUpperCase()}${category.slice(1)}`;
  return opText(
    Object.prototype.hasOwnProperty.call(operatorI18n.messages[activeOperatorLanguage], key)
      ? key
      : `${baseKey}Other`,
    {...parameters, count}
  );
}
"""


def _intake_record_helpers(html: str) -> str:
    match = re.search(
        r"// OPERATOR_INTAKE_RECORD_START\n(.*?)\n"
        r"    // OPERATOR_INTAKE_RECORD_END",
        html,
        re.DOTALL,
    )
    assert match is not None
    return match.group(1)


def _share_provenance_helpers(html: str) -> str:
    match = re.search(
        r"// OPERATOR_SHARE_PROVENANCE_START\n(.*?)\n"
        r"    // OPERATOR_SHARE_PROVENANCE_END",
        html,
        re.DOTALL,
    )
    assert match is not None
    return match.group(1)


def _canonical_intake_helpers(html: str) -> str:
    match = re.search(
        r"// OPERATOR_CANONICAL_INTAKE_START\n(.*?)\n"
        r"    // OPERATOR_CANONICAL_INTAKE_END",
        html,
        re.DOTALL,
    )
    assert match is not None
    return match.group(1)


def _source_bound_helpers(html: str) -> str:
    match = re.search(
        r"// OPERATOR_SOURCE_BOUND_START\n(.*?)\n"
        r"    // OPERATOR_SOURCE_BOUND_END",
        html,
        re.DOTALL,
    )
    assert match is not None
    return match.group(1)


def _controlled_intake_contract_helpers(html: str) -> str:
    match = re.search(
        r"// OPERATOR_CONTROLLED_INTAKE_CONTRACT_START\n(.*?)\n"
        r"    // OPERATOR_CONTROLLED_INTAKE_CONTRACT_END",
        html,
        re.DOTALL,
    )
    assert match is not None
    unicode_helper = re.search(
        r"    function hasWellFormedUnicode\(value\) \{.*?\n    \}",
        html,
        re.DOTALL,
    )
    assert unicode_helper is not None
    return unicode_helper.group(0) + "\n" + match.group(1)


def _source_selection_dom_helpers(html: str) -> str:
    match = re.search(
        r"    function refreshRetrievedSourcePreviewMeta\(\) \{(.*?)\n"
        r"    function draftSourceText",
        html,
        re.DOTALL,
    )
    assert match is not None
    return "function refreshRetrievedSourcePreviewMeta() {" + match.group(1)


def test_operator_product_buttons_keep_existing_handlers():
    html = _read(INDEX)

    assert '].join("\\n");' in html
    assert '].join("\n");' not in html
    assert '$("product_intake").addEventListener("submit", (event) => {' in html
    assert "event.preventDefault();" in html
    assert "void runProductAnalyze();" in html
    assert '$("product_load_news_demo").addEventListener("click", loadProductNewsDemo);' in html
    assert '$("product_show_advanced").addEventListener("click", openAdvancedConsole);' in html


def test_operator_has_one_editable_canonical_intake_surface():
    html = _read(INDEX)
    primary, advanced = html.split(
        '<details class="advanced-shell" id="advanced_operator_console">',
        maxsplit=1,
    )

    assert primary.count('id="product_source_url"') == 1
    assert primary.count('id="product_source_text"') == 1
    assert primary.count('id="signal_source_type"') == 1
    assert 'id="source_url"' not in advanced
    assert 'id="source_text"' not in advanced
    assert 'id="signal_source_type"' not in advanced
    assert 'id="audit_source_url"' in advanced
    assert 'id="audit_source_text"' in advanced
    assert 'id="audit_source_type"' in advanced
    assert re.search(
        r"<(?:input|textarea|select)[^>]+id=\"audit_source_",
        advanced,
    ) is None
    assert 'value("source_url")' not in html
    assert 'value("source_text")' not in html
    assert '$("source_url")' not in html
    assert '$("source_text")' not in html
    assert "setCanonicalIntake(" in html
    for helper_name in ("loadNewsDemo", "loadGithubDemo"):
        helper = re.search(
            rf"function {helper_name}\(\) \{{(.*?)\n    \}}",
            html,
            re.DOTALL,
        )
        assert helper is not None
        assert "setCanonicalIntake(" in helper.group(1)
    assert '$("signal_source_type").addEventListener("change"' in html


@pytest.mark.skipif(NODE is None, reason="Node.js is required for JavaScript validation")
def test_canonical_intake_syncs_audit_and_invalidates_stale_drafts():
    helpers = _canonical_intake_helpers(_read(INDEX))
    smoke = (
        """
const fields = {
  product_source_url: {value: "https://github.com/Voxterrae/HUB_Optimus/issues/1736"},
  product_source_text: {value: "Synthetic issue report for canonical intake testing."},
  signal_source_type: {value: "automatic"},
  audit_source_type: {textContent: ""},
  audit_source_url: {textContent: ""},
  audit_source_text: {textContent: ""},
  product_analyze: {disabled: true},
  product_wait_status: {textContent: ""}
};
const $ = (id) => fields[id];
function value(id) {
  return $(id).value.trim();
}
function opText(key, parameters = {}) {
  if (key === "advancedCharactersSupplied") {
    return `${parameters.count} characters supplied in primary intake`;
  }
  if (key === "valueNotProvided") return "not provided";
  return key;
}
let currentIntakeRecord = {mode: "operator-pasted-text"};
let currentMemoryRecord = {stale: true};
let currentRetrievedSourceText = "retrieved";
let currentRetrievedSourceUrl = fields.product_source_url.value;
let currentCaseMetadata = {normalizer_version: "stale"};
let currentSharedMemorySnapshot = null;
let currentIntakeFailure = null;
let intakeGeneration = 0;
let activeIntakeRequestToken = 0;
let activeIntakeAbortController = null;
let claims = [];
let evidence = [];
let memoryActionsEnabled = true;
let currentSourceSelectionState = {mode: "controlled-url"};
let currentConfirmedSourceSelection = {confirmed: true};
function unicodeCharacterCount(value) { return Array.from(String(value ?? "")).length; }
function invalidateSourceSelectionConfirmation() {
  currentConfirmedSourceSelection = null;
}
function renderSourceSelectionValidation() { return {ok: false}; }
function setMemoryActionsEnabled(enabled) {
  memoryActionsEnabled = enabled;
}
function setOperatorMessage(target, key) {
  const node = typeof target === "string" ? $(target) : target;
  node.textContent = key;
}
function clearRetrievedSourcePreview() {
  currentRetrievedSourceText = "";
  currentRetrievedSourceUrl = "";
}
function invalidatePreparedDraft() {
  currentMemoryRecord = null;
  currentCaseMetadata = {};
  setMemoryActionsEnabled(false);
}
"""
        + helpers
        + """
syncProductInputState();
if (fields.signal_source_type.value !== "automatic") {
  throw new Error("automatic source-type mode was not preserved");
}
if (
  fields.audit_source_type.textContent !== "github-issue" ||
  fields.audit_source_url.textContent !== fields.product_source_url.value ||
  fields.audit_source_text.textContent !== `${fields.product_source_text.value.length} characters supplied in primary intake`
) {
  throw new Error("advanced audit projection diverged from canonical intake");
}
if (currentIntakeRecord !== null || currentMemoryRecord !== null) {
  throw new Error("changed canonical input retained stale prepared state");
}
if (memoryActionsEnabled || fields.product_analyze.disabled) {
  throw new Error("changed canonical input did not reset actions correctly");
}

currentIntakeRecord = {mode: "controlled-url", original_url: fields.product_source_url.value};
currentMemoryRecord = {stale: true};
memoryActionsEnabled = true;
fields.signal_source_type.value = "documentation-drift";
syncProductInputState({resetIntakeRecord: false});
if (fields.audit_source_type.textContent !== "documentation-drift") {
  throw new Error("operator source-type correction was not projected to audit");
}
if (currentIntakeRecord?.mode !== "controlled-url") {
  throw new Error("source-type correction discarded valid retrieval provenance");
}
if (currentMemoryRecord !== null || memoryActionsEnabled) {
  throw new Error("source-type correction retained stale shareable output");
}

setCanonicalIntake(
  "https://example.com/report",
  "Synthetic advanced demo source text.",
  "news-article"
);
if (
  fields.product_source_url.value !== "https://example.com/report" ||
  fields.product_source_text.value !== "Synthetic advanced demo source text." ||
  fields.signal_source_type.value !== "news-article"
) {
  throw new Error("advanced action did not update the canonical public intake");
}
if (
  fields.audit_source_url.textContent !== "https://example.com/report" ||
  fields.audit_source_text.textContent !== "36 characters supplied in primary intake" ||
  fields.audit_source_type.textContent !== "news-article"
) {
  throw new Error("advanced action left a stale audit projection");
}
fields.product_source_text.value = "😀文";
syncAuditIntakeView();
if (fields.audit_source_text.textContent !== "2 characters supplied in primary intake") {
  throw new Error("audit projection counted UTF-16 units instead of Unicode code points");
}
"""
    )
    completed = subprocess.run(
        [NODE, "-"],
        input=smoke,
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr


@pytest.mark.skipif(NODE is None, reason="Node.js is required for JavaScript validation")
def test_automatic_text_only_classification_is_neutral_and_explicit_choice_is_preserved():
    helpers = _canonical_intake_helpers(_read(INDEX))
    smoke = r'''
const fields = {
  product_source_url: {value: ""},
  product_source_text: {value: "A copied GitHub-like issue body without a supplied URL."},
  signal_source_type: {value: "automatic"}
};
const $ = (id) => fields[id];
function value(id) { return String($(id).value || "").trim(); }
''' + helpers.split("function syncAuditIntakeView", 1)[0] + r'''
if (canonicalIntakeState().sourceType !== "external-source") {
  throw new Error("text-only automatic intake was classified as a human situation");
}
fields.signal_source_type.value = "human-situation";
if (canonicalIntakeState().sourceType !== "human-situation") {
  throw new Error("an explicit operator classification was overwritten");
}
'''
    completed = subprocess.run(
        [NODE, "-"], input=smoke, text=True, capture_output=True, check=False
    )
    assert completed.returncode == 0, completed.stderr


def test_context_edit_preserves_url_passage_confirmation_but_text_only_edit_clears_it():
    html = _read(INDEX)
    listener = re.search(
        r'\$\("product_source_text"\)\.addEventListener\("input", \(\) => \{(.*?)\n    \}\);',
        html,
        re.DOTALL,
    )
    assert listener is not None
    body = listener.group(1)
    assert "retrievedUrlIsCurrent" in body
    assert "resetRetrievedSource: !sourceUrlPresent" in body
    assert "preserveSourceSelectionConfirmation: retrievedUrlIsCurrent" in body


def test_operator_uses_only_controlled_url_intake_fetch():
    html = _read(INDEX)
    schema = json.loads(_read(URL_INTAKE_SCHEMA))
    request = schema["$defs"]["request"]
    success_fields = set(schema["$defs"]["success_response"]["required"])
    limits = schema["x-hub-optimus-runtime-limits"]

    assert "CONTROLLED_URL_INTAKE_ENDPOINT" in html
    assert f"https://api.huboptimus.dev{limits['endpoint']}" in html
    assert "fetch(CONTROLLED_URL_INTAKE_ENDPOINT" in html
    assert "JSON.stringify({ url: sourceUrl })" in html
    assert request["required"] == ["url"]
    assert set(request["properties"]) == {"url"}
    assert {"status", "text"} <= success_fields
    for field in (
        "url",
        "final_url",
        "source_domain",
        "title",
        "retrieved_at_utc",
        "redirects",
        "content_type",
        "truncated",
        "verification_status",
        "bytes_read",
    ):
        assert field in success_fields
        assert f"intakePayload.{field}" in html
    assert "fetch(sourceUrl" not in html
    assert "fetch(url" not in html
    assert '<form class="panel full product-intake"' in html
    assert 'id="product_source_url" name="source_url" type="url"' in html
    assert 'id="product_analyze" type="submit"' in html
    assert 'id="product_source_preview"' in html
    assert 'id="product_confirm_source" type="checkbox"' in html
    assert '<script src="./i18n.v1.js"></script>' in html
    assert re.search(r'<script[^>]+src="https?://', html) is None


def test_operator_browser_validator_mirrors_the_versioned_intake_contract():
    schema = json.loads(_read(URL_INTAKE_SCHEMA))
    contract = _controlled_intake_contract_helpers(_read(INDEX))

    def javascript_array(name: str):
        match = re.search(
            rf"const {name} = (?:Object\.freeze\(|new Set\()?" r"(\[.*?\])\)?;",
            contract,
            re.DOTALL,
        )
        assert match is not None
        return json.loads(match.group(1))

    assert set(javascript_array("CONTROLLED_INTAKE_SUCCESS_FIELDS")) == set(
        schema["$defs"]["success_response"]["required"]
    )
    assert set(javascript_array("CONTROLLED_INTAKE_ERROR_FIELDS")) == set(
        schema["$defs"]["error_response"]["required"]
    )
    assert set(javascript_array("CONTROLLED_INTAKE_REDIRECT_FIELDS")) == set(
        schema["$defs"]["redirect"]["required"]
    )
    assert set(javascript_array("CONTROLLED_INTAKE_REDIRECT_STATUSES")) == set(
        schema["$defs"]["redirect"]["properties"]["status"]["enum"]
    )

    error_map_match = re.search(
        r"const CONTROLLED_INTAKE_ERROR_HTTP_STATUS = Object\.freeze\(\{(.*?)\}\);",
        contract,
        re.DOTALL,
    )
    assert error_map_match is not None
    browser_error_map = {
        name: int(status)
        for name, status in re.findall(
            r'^\s+"([a-z_]+)":\s+(\d+),?$',
            error_map_match.group(1),
            re.MULTILINE,
        )
    }
    assert browser_error_map == schema["x-hub-optimus-error-http-status"]

    limits = schema["x-hub-optimus-runtime-limits"]
    for browser_name, schema_name in (
        ("urlCharacters", "url_characters"),
        ("rawResponseBytes", "raw_response_bytes"),
        ("extractedTextCharacters", "extracted_text_characters"),
        ("maximumReturnedTextCharacters", "maximum_returned_text_characters"),
        ("redirects", "redirects"),
    ):
        assert re.search(
            rf"\b{browser_name}:\s+{limits[schema_name]}\b",
            contract,
        )


@pytest.mark.skipif(NODE is None, reason="Node.js is required for JavaScript validation")
def test_controlled_intake_vm_rejects_incomplete_and_incoherent_responses():
    helpers = _controlled_intake_contract_helpers(_read(INDEX))
    smoke = (
        helpers
        + r'''
const sourceUrl = "https://origin.example/report";
let expectedRequestUrl = sourceUrl;
const responses = [];
async function fetch(endpoint, options) {
  if (endpoint !== CONTROLLED_URL_INTAKE_ENDPOINT) throw new Error("wrong endpoint");
  if (options.method !== "POST" || JSON.parse(options.body).url !== expectedRequestUrl) {
    throw new Error("wrong controlled request");
  }
  const response = responses.shift();
  return {
    ok: response.ok,
    status: response.status,
    async json() { return response.payload; }
  };
}
function successPayload(overrides = {}) {
  return Object.assign({
    status: "ok",
    intake_type: "controlled_url",
    url: sourceUrl,
    final_url: sourceUrl,
    source_domain: "origin.example",
    retrieved_at_utc: "2026-08-01T20:00:00+00:00",
    title: "Safety notice",
    text: "Recall 24-17\nStop use now.\nFire risk.",
    content_type: "text/html; charset=utf-8",
    bytes_read: 4096,
    truncated: false,
    redirects: [],
    verification_status: "unreviewed",
    learning_status: "candidate-source-not-verified",
    extraction_notes: ["Controlled extraction; human review required."]
  }, overrides);
}
async function expectInvalid(payload, status = 200, ok = true, requestUrl = sourceUrl) {
  expectedRequestUrl = requestUrl;
  responses.push({payload, status, ok});
  try {
    await readControlledUrlText(requestUrl);
  } catch (error) {
    if (error instanceof ControlledIntakeError && error.code === "invalid_response") return;
    throw error;
  }
  throw new Error("invalid controlled-intake response was accepted");
}
(async () => {
  const incomplete = successPayload();
  delete incomplete.final_url;
  await expectInvalid(incomplete);

  await expectInvalid(successPayload({source_domain: "other.example"}));
  await expectInvalid(successPayload({content_type: "image/png"}));
  await expectInvalid(successPayload({retrieved_at_utc: "2026-02-31T20:00:00+00:00"}));
  await expectInvalid(successPayload({title: "Broken \ud800 title"}));
  await expectInvalid(successPayload({text: "Broken \ud800 text"}));
  await expectInvalid(successPayload({content_type: "text/plain; broken=\ud800"}));
  await expectInvalid(successPayload({source_domain: "origin.example\ud800"}));
  await expectInvalid(successPayload({extraction_notes: ["Broken \ud800 note"]}));
  await expectInvalid(Object.assign(successPayload(), {unexpected: true}));
  await expectInvalid(successPayload({
    final_url: "https://final.example/report",
    source_domain: "final.example",
    redirects: [{
      from: "https://wrong.example/report",
      to: "https://final.example/report",
      status: 302
    }]
  }));
  await expectInvalid(successPayload(), 201, true);

  const validRedirected = successPayload({
    final_url: "https://final.example/report",
    source_domain: "final.example",
    content_type: "application/xhtml+xml",
    redirects: [{
      from: sourceUrl,
      to: "https://final.example/report",
      status: 308
    }]
  });
  responses.push({payload: validRedirected, status: 200, ok: true});
  const accepted = await readControlledUrlText(sourceUrl);
  if (
    accepted.final_url !== validRedirected.final_url ||
    accepted.redirects.length !== 1 ||
    accepted.text !== validRedirected.text
  ) {
    throw new Error("valid coherent response was not preserved");
  }

  const validOffsetTimestamp = successPayload({
    retrieved_at_utc: "2026-08-01T22:30:00+02:30"
  });
  expectedRequestUrl = sourceUrl;
  responses.push({payload: validOffsetTimestamp, status: 200, ok: true});
  const acceptedOffsetTimestamp = await readControlledUrlText(sourceUrl);
  if (acceptedOffsetTimestamp.retrieved_at_utc !== validOffsetTimestamp.retrieved_at_utc) {
    throw new Error("valid RFC 3339 offset timestamp was rejected");
  }

  const defaultPortUrl = "https://example.com:443/report";
  const explicitDefaultPort = successPayload({
    url: defaultPortUrl,
    final_url: defaultPortUrl,
    source_domain: "example.com"
  });
  expectedRequestUrl = defaultPortUrl;
  responses.push({payload: explicitDefaultPort, status: 200, ok: true});
  const acceptedDefaultPort = await readControlledUrlText(defaultPortUrl);
  if (acceptedDefaultPort.url !== defaultPortUrl) {
    throw new Error("explicit default HTTPS port was rejected");
  }

  const nonstandardPortUrl = "https://example.com:444/report";
  await expectInvalid(successPayload({
    url: nonstandardPortUrl,
    final_url: nonstandardPortUrl,
    source_domain: "example.com"
  }), 200, true, nonstandardPortUrl);

  expectedRequestUrl = sourceUrl;
  responses.push({
    ok: false,
    status: 502,
    payload: {
      status: "error",
      error: "url_fetch_failed",
      message: "Remote server returned HTTP 403.",
      url: sourceUrl,
      verification_status: "unreviewed"
    }
  });
  try {
    await readControlledUrlText(sourceUrl);
  } catch (error) {
    if (
      error instanceof ControlledIntakeError &&
      error.code === "url_fetch_failed" &&
      error.httpStatus === 502
    ) return;
    throw error;
  }
  throw new Error("valid application error was not surfaced");
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
'''
    )
    completed = subprocess.run(
        [NODE, "-"],
        input=smoke,
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr


@pytest.mark.skipif(NODE is None, reason="Node.js is required for JavaScript validation")
def test_controlled_intake_client_deadline_settles_and_preserves_caller_abort():
    helpers = _controlled_intake_contract_helpers(_read(INDEX))
    smoke = (
        helpers
        + r'''
const originalSetTimeout = globalThis.setTimeout;
const originalClearTimeout = globalThis.clearTimeout;
let deadlineDelay = null;
globalThis.setTimeout = (callback, delay) => {
  deadlineDelay = delay;
  queueMicrotask(callback);
  return 17;
};
globalThis.clearTimeout = () => {};
async function fetch(_endpoint, options) {
  return await new Promise((_resolve, reject) => {
    const rejectAbort = () => {
      const error = new Error("aborted");
      error.name = "AbortError";
      reject(error);
    };
    if (options.signal?.aborted) {
      rejectAbort();
      return;
    }
    options.signal?.addEventListener("abort", rejectAbort, {once: true});
  });
}

(async () => {
  try {
    await readControlledUrlText("https://origin.example/report");
  } catch (error) {
    if (!(error instanceof ControlledIntakeError) || error.code !== "url_fetch_timeout" || error.httpStatus !== 504) {
      throw error;
    }
    if (deadlineDelay !== CONTROLLED_INTAKE_CLIENT_TIMEOUT_MS || deadlineDelay !== 15000) {
      throw new Error("client deadline was not the bounded 15-second contract");
    }
  }

  globalThis.setTimeout = originalSetTimeout;
  globalThis.clearTimeout = originalClearTimeout;
  const caller = new AbortController();
  caller.abort();
  try {
    await readControlledUrlText("https://origin.example/report", {signal: caller.signal});
  } catch (error) {
    if (error?.name === "AbortError") return;
    throw error;
  }
  throw new Error("caller abort was converted into a timeout or success");
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
'''
    )
    completed = subprocess.run(
        [NODE, "-"], input=smoke, text=True, capture_output=True, check=False
    )
    assert completed.returncode == 0, completed.stderr


def test_operator_uses_canonical_identity_and_explicit_prototype_boundary():
    html = _read(INDEX)
    catalog = _read(OPERATOR_I18N)

    assert '../assets/brand/hub-optimus-logo-lockup.png' in html
    assert LOCKUP.is_file()
    assert 'alt="HUB_Optimus"' in html
    assert "LOCAL-FIRST BROWSER PROTOTYPE" in html
    assert "does not run the Python CLI or a Semantic Engine" in catalog
    assert "complete Semantic Engine" not in html
    assert "Local draft · human review required" in html
    assert re.search(
        r"\b(reactor|nuclear|nuke|melon|containment|sealed)\b",
        html,
        re.IGNORECASE,
    ) is None


def test_operator_progress_is_immediate_and_only_network_intake_has_a_deadline():
    html = _read(INDEX)
    sw = _read(SW)

    assert "signal-loader" in html
    assert "product_loader_percent" in html
    assert "completeProductProgress" in html
    assert "runSignalLoaderPlan" not in html
    assert "runMelonLoaderPlan" not in html
    assert "await wait(" not in html
    assert "const CONTROLLED_INTAKE_CLIENT_TIMEOUT_MS = 15000;" in html
    assert 'new ControlledIntakeError("url_fetch_timeout", 504)' in html
    assert "return await Promise.race([request, deadline]);" in html
    assert "hub-optimus-operator-v0-26" in sw


def test_operator_draft_is_source_bound_and_conservative():
    html = _read(INDEX)
    catalog = _read(OPERATOR_I18N)

    assert "operator-source-bound-v1" in html
    assert '<bdi dir="ltr">review_profile=source-bound-v1</bdi>' not in html
    assert 'normalizer_version: "operator-source-bound-v1"' in html
    assert "source_text_fingerprint" in html
    assert 'type: "SUPPORTS_ATTRIBUTION"' in html
    assert 'support_scope: "attribution-only"' in html
    assert "No motives or incentives are inferred from the submitted text." in catalog
    assert "No substantive inference is generated by this browser prototype." in catalog
    assert "Human review checklist" in catalog
    assert "playbooks" not in html
    assert "scenarioCards" not in html
    assert "housing-finance" not in html
    assert "security-conflict" not in html
    assert "operator-topic-analysis" not in html


@pytest.mark.skipif(NODE is None, reason="Node.js is required for JavaScript validation")
def test_source_bound_excerpts_are_exact_distinct_and_locatable():
    helpers = _source_bound_helpers(_read(INDEX))
    smoke = (
        _operator_i18n_node_prelude()
        + helpers
        + """
const first = "Alpha agency published the revised procedure on Friday. Independent records have not yet been reviewed.";
const second = "Beta council postponed the transport vote until Monday. Meeting minutes remain unavailable.";
const firstCanonical = canonicalSource(first);
const secondCanonical = canonicalSource(second);
const firstExcerpts = sourceExcerpts(firstCanonical.text, firstCanonical.fingerprint);
const secondExcerpts = sourceExcerpts(secondCanonical.text, secondCanonical.fingerprint);
if (!firstExcerpts.length || !secondExcerpts.length) throw new Error("source excerpts missing");
for (const excerpt of firstExcerpts) {
  if (first.slice(excerpt.span_start, excerpt.span_end) !== excerpt.text) {
    throw new Error("excerpt locator does not resolve to exact source text");
  }
  if (!excerpt.source_text_fingerprint.startsWith("sha256:") || excerpt.source_text_fingerprint.length !== 71) {
    throw new Error("source fingerprint missing");
  }
}
if (firstExcerpts[0].text === secondExcerpts[0].text) {
  throw new Error("different sources produced generic identical excerpts");
}
if (!buildSpecificClaim(firstExcerpts[0]).includes("Alpha agency")) {
  throw new Error("claim is not bound to the first source");
}
const profile = buildSourceProfile(first, "news-article", "https://example.com/report");
const records = buildSourceBoundRecords(profile, {
  sourceRef: "https://example.com/report",
  claimType: "external-report",
  retrieved: true
});
if (records.claims.length !== records.evidence.length || records.claims.length !== records.relationships.length) {
  throw new Error("source-bound records are not one-to-one");
}
for (let index = 0; index < records.claims.length; index += 1) {
  const claim = records.claims[index];
  const evidence = records.evidence[index];
  const relation = records.relationships[index];
  if (!first.includes(evidence.text)) throw new Error("evidence is not exact source text");
  if (evidence.supports_claim_ids[0] !== claim.claim_id) throw new Error("dangling claim support");
  if (relation.from_ref !== evidence.evidence_id || relation.to_ref !== claim.claim_id) {
    throw new Error("dangling structural relationship");
  }
  if (evidence.metadata.support_scope !== "attribution-only") {
    throw new Error("excerpt was promoted into corroboration");
  }
}
"""
    )
    completed = subprocess.run(
        [NODE, "-"],
        input=smoke,
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr


@pytest.mark.skipif(NODE is None, reason="Node.js is required for JavaScript validation")
def test_source_text_is_canonicalized_once_and_sha256_bound():
    helpers = _source_bound_helpers(_read(INDEX))
    smoke = (
        helpers
        + r'''
const raw = "Cafe\u0301 records a sufficiently detailed source statement.\r\nA second sentence remains available for review.";
const canonical = canonicalSource(raw);
if (canonical.text !== "Café records a sufficiently detailed source statement.\nA second sentence remains available for review.") {
  throw new Error("CRLF/NFC canonicalization changed unexpectedly");
}
if (sha256Hex("abc") !== "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad") {
  throw new Error("SHA-256 implementation failed known vector");
}
if (canonical.fingerprint !== sourceFingerprint(canonical.text) || canonical.fingerprint.length !== 71) {
  throw new Error("canonical fingerprint is not stable SHA-256");
}
const excerpts = sourceExcerpts(canonical.text, canonical.fingerprint);
if (!excerpts.length) throw new Error("canonical excerpts missing");
for (const excerpt of excerpts) {
  if (Array.from(canonical.text).slice(excerpt.span_start, excerpt.span_end).join("") !== excerpt.text) {
    throw new Error("canonical span does not locate exact excerpt");
  }
  if (excerpt.span_unit !== "unicode-code-point") throw new Error("span unit is ambiguous");
  if (excerpt.source_text_fingerprint !== canonical.fingerprint) {
    throw new Error("span and fingerprint used different source representations");
  }
}
const context = buildOperatorContextRecord("x".repeat(1300));
if (!context.truncated || context.original_character_count !== 1300 || context.stored_character_count !== 1200) {
  throw new Error("long operator context truncation was not explicit");
}
if (!context.source_text_fingerprint.startsWith("sha256:")) {
  throw new Error("long operator context fingerprint missing");
}
const emojiContextRaw = `${"a".repeat(1199)}😀Z`;
const emojiContext = buildOperatorContextRecord(emojiContextRaw);
if (
  !emojiContext.truncated ||
  emojiContext.original_character_count !== 1201 ||
  emojiContext.canonical_character_count !== 1201 ||
  emojiContext.stored_character_count !== 1200 ||
  !emojiContext.text.endsWith("😀") ||
  emojiContext.source_text_fingerprint !== sourceFingerprint(canonicalSource(emojiContextRaw).text)
) {
  throw new Error("operator context did not count, slice and fingerprint the full Unicode source consistently");
}
  const multilingual = canonicalSource(
    "😀 该来源记录了一个足够详细的中文陈述，并要求人工核对出处、日期、范围以及相关上下文。" +
    "\nتسجل هذه المادة بياناً عربياً مفصلاً بما يكفي للمراجعة البشرية وتوثيق المصدر والسياق؟"
);
const multilingualExcerpts = sourceExcerpts(multilingual.text, multilingual.fingerprint);
if (multilingualExcerpts.length !== 2) throw new Error("CJK/Arabic sentence boundaries collapsed");
for (const excerpt of multilingualExcerpts) {
  const located = Array.from(multilingual.text).slice(excerpt.span_start, excerpt.span_end).join("");
  if (located !== excerpt.text) throw new Error("Unicode code-point span is not interoperable");
  if (excerpt.span_unit !== "unicode-code-point") throw new Error("Unicode span unit missing");
}
'''
    )
    completed = subprocess.run(
        [NODE, "-"],
        input=smoke,
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr


@pytest.mark.skipif(NODE is None, reason="Node.js is required for JavaScript validation")
def test_exact_passage_selection_is_mechanical_unicode_safe_and_never_silently_cut():
    helpers = _source_bound_helpers(_read(INDEX))
    smoke = (
        _operator_i18n_node_prelude()
        + helpers
        + r'''
function assert(condition, message) {
  if (!condition) throw new Error(message);
}

const prose = canonicalSource(
  "Dr. Smith of the U.S. agency released v1.2.3 after a 2.5% change. No semantic splitting is allowed."
);
const proseInventory = sourceSelectionInventory(prose.text, prose.fingerprint);
assert(proseInventory.candidate_count === 1, "abbreviations, versions or decimals were sentence-split");
assert(proseInventory.proposed[0].text === prose.text, "the complete source line was changed");

const lines = [
  "First neutral source line.",
  "Second neutral source line.",
  "Third neutral source line.",
  "Fourth neutral source line.",
  "Fifth neutral source line.",
  "Sixth late line says the proposal is NOT approved.",
  "שורה מאוחרת בעברית נשמרת במדויק.",
  "后面的中文段落必须保持原样。"
];
const late = canonicalSource(lines.join("\n"));
const inventory = sourceSelectionInventory(late.text, late.fingerprint);
assert(inventory.candidate_count === 8, "candidate inventory lost late multilingual lines");
assert(inventory.proposed_count === 5 && inventory.omitted_count === 3, "proposal accounting is wrong");
assert(inventory.criterion === "first-five-distinct-eligible-source-lines-v1", "criterion drifted");

const chosen = [lines[5], lines[6], lines[7]].join(inventory.separator);
const selected = validateSourcePassageSelection(
  chosen, late.text, late.fingerprint, inventory.separator
);
assert(selected.ok && selected.excerpts.length === 3, "a late exact passage could not replace proposals");
assert(selected.excerpts.every((entry) => entry.selection_origin === "human-confirmed"), "selection origin missing");
for (const entry of selected.excerpts) {
  const located = Array.from(late.text).slice(entry.span_start, entry.span_end).join("");
  assert(located === entry.text, "Unicode code-point span does not locate exact selected text");
}

const emoji480 = `${"😀".repeat(478)}NO`;
const exact480 = canonicalSource(emoji480);
const valid480 = validateSourcePassageSelection(
  emoji480,
  exact480.text,
  exact480.fingerprint,
  sourceSelectionSeparator(exact480.text, exact480.fingerprint).value
);
assert(valid480.ok && valid480.excerpts[0].text === emoji480, "480 code points were not preserved exactly");
assert(unicodeCharacterCount(valid480.excerpts[0].text) === 480, "astral Unicode count used UTF-16 units");

const emoji481 = `${emoji480}X`;
const exact481 = canonicalSource(emoji481);
const rejected481 = validateSourcePassageSelection(
  emoji481,
  exact481.text,
  exact481.fingerprint,
  sourceSelectionSeparator(exact481.text, exact481.fingerprint).value
);
assert(!rejected481.ok && rejected481.code === "length" && rejected481.count === 481, "481 code points were cut or accepted");
assert(sourceExcerpts(exact481.text, exact481.fingerprint).length === 0, "an over-limit line was silently proposed as a cut passage");

const longSource = canonicalSource(`${"A".repeat(520)}\nThe decision is NOT approved beyond the old 480-character boundary.`);
const longInventory = sourceSelectionInventory(longSource.text, longSource.fingerprint);
const lateNegation = longSource.text.split("\n")[1];
const lateNegationResult = validateSourcePassageSelection(
  lateNegation,
  longSource.text,
  longSource.fingerprint,
  longInventory.separator
);
assert(lateNegationResult.ok, "a negation after the old cut boundary was unavailable");
assert(lateNegationResult.excerpts[0].text.includes("NOT approved"), "late negation changed");

const partialText = "NOT approved";
const partial = validateSourcePassageSelection(
  partialText,
  longSource.text,
  longSource.fingerprint,
  longInventory.separator
);
assert(partial.ok && partial.excerpts[0].passage_scope === "partial-source-passage", "partial scope was not explicit");
assert(buildSpecificClaim(partial.excerpts[0]).includes(partialText), "partial claim lost exact text");
assert(buildSpecificClaim(partial.excerpts[0]) !== buildSpecificClaim(lateNegationResult.excerpts[0]), "partial and complete claims are indistinguishable");

const duplicate = validateSourcePassageSelection(
  `${lines[5]}${inventory.separator}${lines[5]}`,
  late.text,
  late.fingerprint,
  inventory.separator
);
assert(!duplicate.ok && duplicate.code === "duplicate", "duplicate selection was accepted");
const repeatedSource = canonicalSource(
  "Repeated exact passage.\nA distinct middle line.\nRepeated exact passage."
);
const repeatedPassage = validateSourcePassageSelection(
  "Repeated exact passage.",
  repeatedSource.text,
  repeatedSource.fingerprint,
  sourceSelectionSeparator(repeatedSource.text, repeatedSource.fingerprint).value
);
assert(!repeatedPassage.ok && repeatedPassage.code === "ambiguous", "a repeated source passage was silently bound to the first occurrence");
const repeatedUnicodeSource = canonicalSource("前文 😀 唯一化。\n中間。\n前文 😀 唯一化。");
const repeatedUnicodePassage = validateSourcePassageSelection(
  "前文 😀 唯一化。",
  repeatedUnicodeSource.text,
  repeatedUnicodeSource.fingerprint,
  sourceSelectionSeparator(repeatedUnicodeSource.text, repeatedUnicodeSource.fingerprint).value
);
assert(!repeatedUnicodePassage.ok && repeatedUnicodePassage.code === "ambiguous", "a repeated Unicode passage was silently bound to the first occurrence");
const overlap = validateSourcePassageSelection(
  `${lines[5]}${inventory.separator}NOT approved`,
  late.text,
  late.fingerprint,
  inventory.separator
);
assert(!overlap.ok && overlap.code === "overlap", "overlapping selection was accepted");
const brokenUnicode = validateSourcePassageSelection(
  "broken \uD83D text",
  "broken \uD83D text",
  sourceFingerprint("broken \uD83D text"),
  "\n-- separator --\n"
);
assert(!brokenUnicode.ok && brokenUnicode.code === "unicode", "broken surrogate was accepted");
'''
    )
    completed = subprocess.run(
        [NODE, "-"],
        input=smoke,
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr


@pytest.mark.skipif(NODE is None, reason="Node.js is required for JavaScript validation")
def test_compact_text_counts_unicode_code_points_without_splitting_emoji():
    html = _read(INDEX)
    compact = re.search(
        r"function compactText\(raw, maxLength = 520\) \{(.*?)\n    \}",
        html,
        re.DOTALL,
    )
    assert compact is not None
    smoke = (
        "function unicodeCodePoints(value) { return Array.from(String(value ?? '')); }\n"
        + "function compactText(raw, maxLength = 520) {"
        + compact.group(1)
        + "\n}\n"
        + r'''
const result = compactText("😀😀😀ABC", 5);
if (result !== "😀😀😀A…" || Array.from(result).length !== 5) {
  throw new Error(`compact text split or miscounted Unicode: ${result}`);
}
for (let index = 0; index < result.length; index += 1) {
  const code = result.charCodeAt(index);
  if (code >= 0xd800 && code <= 0xdbff) {
    const next = result.charCodeAt(index + 1);
    if (!(next >= 0xdc00 && next <= 0xdfff)) throw new Error("compact text emitted an unpaired high surrogate");
    index += 1;
  } else if (code >= 0xdc00 && code <= 0xdfff) {
    throw new Error("compact text emitted an unpaired low surrogate");
  }
}
'''
    )
    completed = subprocess.run(
        [NODE, "-"], input=smoke, text=True, capture_output=True, check=False
    )
    assert completed.returncode == 0, completed.stderr


@pytest.mark.skipif(NODE is None, reason="Node.js is required for JavaScript validation")
def test_source_preview_dom_exposes_bounds_and_freezes_only_the_exact_confirmed_selection():
    html = _read(INDEX)
    smoke = (
        _operator_i18n_node_prelude()
        + _source_bound_helpers(html)
        + r'''
function node() {
  return {
    value: "", textContent: "", checked: false, disabled: false, hidden: true,
    attributes: {},
    setAttribute(name, value) { this.attributes[name] = String(value); },
    removeAttribute(name) { delete this.attributes[name]; },
    focus() { this.focused = true; }
  };
}
const fields = {
  product_source_preview_meta: node(),
  product_source_snapshot_status: node(),
  product_source_selection_summary: node(),
  product_source_selection_criterion: node(),
  product_source_selection_limits: node(),
  product_source_selection_status: node(),
  product_confirm_source: node(),
  product_source_preview: node(),
  product_source_preview_text: node(),
  product_source_selection: node()
};
const $ = (id) => fields[id];
function setOperatorMessage(target, key, parameters = {}) {
  const field = typeof target === "string" ? $(target) : target;
  field.textContent = opText(key, parameters);
}
let currentIntakeRecord = {
  mode: "controlled-url",
  title: "Retrieved title",
  original_url: "https://example.com/source",
  final_url: "https://example.com/final"
};
let currentRetrievedSourceText = "";
let currentRetrievedSourceUrl = "";
let currentSourceSelectionState = null;
let currentConfirmedSourceSelection = null;
'''
        + _source_selection_dom_helpers(html)
        + r'''
const source = "😀 First exact line.\nSecond exact line.\nThird exact line.";
renderRetrievedSourcePreview({text: source, truncated: true}, "https://example.com/source");
if (fields.product_source_preview.hidden) throw new Error("preview remained hidden");
if (!fields.product_source_snapshot_status.textContent.includes("truncated=true")) {
  throw new Error("truncated=true was not visible before confirmation");
}
if (!fields.product_source_snapshot_status.textContent.includes("24000")) {
  throw new Error("retrieval bound was not visible before confirmation");
}
if (fields.product_confirm_source.disabled || !fields.product_source_selection.value.includes("First exact line")) {
  throw new Error("valid mechanical proposals were not editable or confirmable");
}
if (!fields.product_source_preview_meta.textContent.includes("56")) {
  throw new Error(`preview did not report a Unicode code-point count: ${fields.product_source_preview_meta.textContent}`);
}

const validation = currentSourceSelectionValidation();
if (!validation.ok) throw new Error("default exact proposals were invalid");
fields.product_confirm_source.checked = true;
currentConfirmedSourceSelection = Object.freeze({
  source_text_fingerprint: currentSourceSelectionState.fingerprint,
  editor_value: fields.product_source_selection.value,
  excerpts: Object.freeze(validation.excerpts.map((excerpt) => Object.freeze({...excerpt})))
});
const confirmed = confirmedSourceExcerptsFor(source);
if (!confirmed || confirmed.map((entry) => entry.text).join("|") !== validation.excerpts.map((entry) => entry.text).join("|")) {
  throw new Error("confirmed selection was not frozen against the same snapshot");
}

const frozenEditorValue = fields.product_source_selection.value;
activeOperatorLanguage = "he";
refreshRetrievedSourcePreviewMeta();
renderSourceSelectionValidation();
if (fields.product_source_selection.value !== frozenEditorValue || !confirmedSourceExcerptsFor(source)) {
  throw new Error("locale switch changed or invalidated the exact confirmed selection");
}

fields.product_source_selection.value = `${frozenEditorValue} altered`;
invalidateSourceSelectionConfirmation();
renderSourceSelectionValidation();
if (fields.product_confirm_source.checked || currentConfirmedSourceSelection || confirmedSourceExcerptsFor(source)) {
  throw new Error("selection edit retained a stale confirmation");
}

activeOperatorLanguage = "en";
renderOperatorTextSelectionPreview("Text-only source line.\nAnother exact line.");
if (currentSourceSelectionState.mode !== "operator-text" || currentRetrievedSourceUrl) {
  throw new Error("text-only preview was mixed with URL retrieval state");
}
'''
    )
    completed = subprocess.run(
        [NODE, "-"], input=smoke, text=True, capture_output=True, check=False
    )
    assert completed.returncode == 0, completed.stderr


def test_payload_output_and_ephemeral_summary_all_require_the_confirmed_selection():
    html = _read(INDEX)
    normalized = re.search(
        r"function buildNormalizedPayload\(\) \{(.*?)\n    \}", html, re.DOTALL
    )
    output = re.search(r"function renderProductOutput\(\) \{(.*?)\n    \}", html, re.DOTALL)
    memory = re.search(r"function buildMemoryRecord\(\) \{(.*?)\n    \}", html, re.DOTALL)
    assert normalized is not None and output is not None and memory is not None
    assert "confirmedSourceExcerptsFor(raw)" in normalized.group(1)
    assert "excerpts: confirmedExcerpts" in normalized.group(1)
    for block in (output.group(1), memory.group(1)):
        assert "confirmedSourceExcerptsFor(sourceText) || []" in block
        assert "{ excerpts:" in block
    assert "currentMemoryRecord = buildMemoryRecord();" in html
    assert "setMemoryActionsEnabled(true);" in html
    assert "localStorage" not in memory.group(1)


@pytest.mark.skipif(NODE is None, reason="Node.js is required for JavaScript validation")
def test_brief_structured_multilingual_warnings_remain_exact_excerpts():
    helpers = _source_bound_helpers(_read(INDEX))
    smoke = (
        helpers
        + r'''
const examples = [
  {
    source: "Recall 24-17\nStop use now.\nFire risk.",
    expected: ["Recall 24-17", "Stop use now.", "Fire risk."]
  },
  {
    source: "立即停用。\n存在火灾风险。",
    expected: ["立即停用。", "存在火灾风险。"]
  },
  {
    source: "יש להפסיק שימוש מיד.\nסכנת אש.",
    expected: ["יש להפסיק שימוש מיד.", "סכנת אש."]
  }
];
for (const {source, expected} of examples) {
  const canonical = canonicalSource(source);
  const excerpts = sourceExcerpts(canonical.text, canonical.fingerprint);
  if (JSON.stringify(excerpts.map((item) => item.text)) !== JSON.stringify(expected)) {
    throw new Error(`brief source was emptied or changed: ${JSON.stringify(excerpts)}`);
  }
  for (const excerpt of excerpts) {
    const located = Array.from(canonical.text)
      .slice(excerpt.span_start, excerpt.span_end)
      .join("");
    if (located !== excerpt.text) throw new Error("brief excerpt locator is not exact");
    if (excerpt.span_unit !== "unicode-code-point") throw new Error("span unit changed");
    if (excerpt.source_text_fingerprint !== canonical.fingerprint) {
      throw new Error("brief excerpt fingerprint changed");
    }
  }
}
'''
    )
    completed = subprocess.run(
        [NODE, "-"],
        input=smoke,
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr


def test_advanced_normalizer_uses_the_primary_retrieval_gate():
    html = _read(INDEX)
    wrapper = re.search(
        r"function normalizeSignal\(\) \{(.*?)\n    \}",
        html,
        re.DOTALL,
    )
    run = re.search(
        r"async function runProductAnalyze\(\) \{(.*?)\n    \}",
        html,
        re.DOTALL,
    )
    assert wrapper is not None
    assert run is not None
    assert "runProductAnalyze" in wrapper.group(1)
    assert "buildNormalizedPayload" not in wrapper.group(1)
    assert "normalizePreparedSignal()" in run.group(1)
    assert "readControlledUrlText(sourceUrl, {" in run.group(1)
    assert "signal: requestAbortController?.signal" in run.group(1)
    assert "confirmedSourceExcerptsFor(currentRetrievedSourceText)" in run.group(1)


@pytest.mark.skipif(NODE is None, reason="Node.js is required for JavaScript validation")
def test_url_retrieval_discards_stale_async_responses_and_confirmation_removal():
    html = _read(INDEX)
    catalog = _read(OPERATOR_I18N)

    assert "let intakeGeneration = 0;" in html
    assert "let activeIntakeRequestToken = 0;" in html
    assert "const requestGeneration = intakeGeneration;" in html
    assert "const requestToken = ++intakeRequestSequence;" in html
    assert html.count("isCurrentIntakeRequest(requestToken, requestGeneration, sourceUrl)") >= 2
    assert "canonicalIntakeState().sourceUrl === sourceUrl" in html
    assert "intakeGeneration += 1;" in html
    assert "if (invalidateRetrieval)" in html
    assert 'setOperatorMessage("product_wait_status", "msgRetrievalContinues")' in html
    assert "advancedNormalizeButton.disabled = true" in html
    assert '$("product_confirm_source").addEventListener("change"' in html
    assert "Source confirmation was removed" in catalog
    assert "Source confirmation removed. The previous draft is stale and cannot be shared." in catalog

    guard = re.search(
        r"function isCurrentIntakeRequest\(token, generation, sourceUrl\) \{(.*?)\n    \}",
        html,
        re.DOTALL,
    )
    assert guard is not None
    smoke = (
        "let activeIntakeRequestToken = 7;\n"
        "let intakeGeneration = 3;\n"
        'function canonicalIntakeState() { return {sourceUrl: "https://current.example/source"}; }\n'
        "function isCurrentIntakeRequest(token, generation, sourceUrl) {"
        + guard.group(1)
        + "\n}\n"
        'if (!isCurrentIntakeRequest(7, 3, "https://current.example/source")) throw new Error("current request rejected");\n'
        'if (isCurrentIntakeRequest(6, 3, "https://current.example/source")) throw new Error("stale token accepted");\n'
        'if (isCurrentIntakeRequest(7, 2, "https://current.example/source")) throw new Error("stale generation accepted");\n'
        'if (isCurrentIntakeRequest(7, 3, "https://old.example/source")) throw new Error("stale URL accepted");\n'
    )
    completed = subprocess.run(
        [NODE, "-"],
        input=smoke,
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr


@pytest.mark.skipif(NODE is None, reason="Node.js is required for JavaScript validation")
def test_post_fetch_failure_settles_request_and_allows_recovery():
    html = _read(INDEX)
    request_guard = re.search(
        r"function isCurrentIntakeRequest\(token, generation, sourceUrl\) \{(.*?)\n    \}",
        html,
        re.DOTALL,
    )
    analyze = re.search(
        r"async function runProductAnalyze\(\) \{(.*?)\n    \}",
        html,
        re.DOTALL,
    )
    assert request_guard is not None
    assert analyze is not None
    smoke = (
        r'''
const fields = {
  product_analyze: {disabled: false, textContent: ""},
  normalize_signal: {disabled: false, textContent: ""},
  product_output: {innerHTML: ""},
  product_source_url: {focus() {}},
  product_confirm_source: {checked: false, focus() {}},
  product_source_preview: {
    hidden: true,
    scrollIntoView() { this.scrolled = true; }
  }
};
const $ = (id) => fields[id];
const intakeState = {
  sourceUrl: "https://origin.example/report",
  sourceText: "",
  sourceType: "external-source"
};
function canonicalIntakeState() { return {...intakeState}; }
let currentIntakeRecord = null;
let currentRetrievedSourceText = "";
let currentRetrievedSourceUrl = "";
let currentMemoryRecord = null;
let currentSharedMemorySnapshot = null;
let currentIntakeFailure = null;
let preparedDraftReady = false;
let intakeGeneration = 0;
let intakeRequestSequence = 0;
let activeIntakeRequestToken = 0;
let activeIntakeAbortController = null;
let fallbackCount = 0;
let profileAttempts = 0;
const reducedMotion = {matches: true};
function resetProductProgress() {}
function setMemoryActionsEnabled() {}
function confirmedSourceExcerptsFor() { return null; }
function renderSourceSelectionValidation() { return {ok: false}; }
function productStep() {}
function setProductLoader() {}
function setOperatorMessage(target, key) {
  const node = typeof target === "string" ? fields[target] : target;
  if (node) node.textContent = key;
}
async function readControlledUrlText(url, {signal} = {}) {
  if (signal?.aborted) throw Object.assign(new Error("aborted"), {name: "AbortError"});
  return {
    status: "ok",
    url,
    final_url: url,
    source_domain: "origin.example",
    text: "Recall 24-17\nStop use now.\nFire risk."
  };
}
function buildSourceProfile() {
  profileAttempts += 1;
  if (profileAttempts === 1) throw new Error("post-fetch validation failed");
  return {excerpts: [{text: "Recall 24-17"}]};
}
function buildIntakeRecord(text, url) {
  return {mode: "controlled-url", original_url: url, text};
}
function renderRetrievedSourcePreview(intake, url) {
  currentRetrievedSourceText = intake.text;
  currentRetrievedSourceUrl = url;
  fields.product_source_preview.hidden = false;
}
function syncAuditIntakeView() {}
function clearRetrievedSourcePreview() {
  currentRetrievedSourceText = "";
  currentRetrievedSourceUrl = "";
  fields.product_source_preview.hidden = true;
  fields.product_confirm_source.checked = false;
}
function renderUrlIntakeFallback(url, error) {
  fallbackCount += 1;
  currentIntakeFailure = {sourceUrl: url, error};
  fields.product_output.innerHTML = "actionable URL fallback";
}
'''
        + "function isCurrentIntakeRequest(token, generation, sourceUrl) {"
        + request_guard.group(1)
        + "\n}\n"
        + "async function runProductAnalyze() {"
        + analyze.group(1)
        + "\n}\n"
        + r'''
(async () => {
  await runProductAnalyze();
  if (
    fallbackCount !== 1 ||
    !fields.product_output.innerHTML.includes("actionable") ||
    fields.product_analyze.disabled ||
    fields.normalize_signal.disabled ||
    activeIntakeRequestToken !== 0
  ) {
    throw new Error("post-fetch error left the intake UI locked or silent");
  }

  await runProductAnalyze();
  if (
    fallbackCount !== 1 ||
    currentRetrievedSourceUrl !== intakeState.sourceUrl ||
    !currentRetrievedSourceText.includes("Recall 24-17") ||
    fields.product_source_preview.hidden ||
    !fields.product_source_preview.scrolled ||
    fields.product_analyze.disabled ||
    fields.normalize_signal.disabled ||
    activeIntakeRequestToken !== 0
  ) {
    throw new Error("intake did not recover after the handled post-fetch failure");
  }
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
'''
    )
    completed = subprocess.run(
        [NODE, "-"],
        input=smoke,
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr


@pytest.mark.skipif(NODE is None, reason="Node.js is required for JavaScript validation")
def test_url_and_text_intakes_complete_preview_confirmation_and_draft_flow():
    html = _read(INDEX)
    request_guard = re.search(
        r"function isCurrentIntakeRequest\(token, generation, sourceUrl\) \{(.*?)\n    \}",
        html,
        re.DOTALL,
    )
    analyze = re.search(
        r"async function runProductAnalyze\(\) \{(.*?)\n    \}",
        html,
        re.DOTALL,
    )
    assert request_guard is not None and analyze is not None
    smoke = r'''
function field(extra = {}) {
  return Object.assign({
    disabled: false, checked: false, textContent: "", innerHTML: "", hidden: true,
    focus() { this.focused = true; },
    scrollIntoView() { this.scrolled = true; }
  }, extra);
}
const fields = {
  product_analyze: field(),
  normalize_signal: field(),
  product_output: field(),
  product_source_url: field(),
  product_source_selection: field(),
  product_confirm_source: field(),
  product_source_preview: field()
};
const $ = (id) => fields[id];
let intakeState = {
  sourceUrl: "https://origin.example/report",
  sourceText: "operator context kept separate",
  sourceType: "external-source"
};
function canonicalIntakeState() { return {...intakeState}; }
let currentIntakeRecord = null;
let currentRetrievedSourceText = "";
let currentRetrievedSourceUrl = "";
let currentMemoryRecord = null;
let currentIntakeFailure = null;
let preparedDraftReady = false;
let intakeGeneration = 0;
let intakeRequestSequence = 0;
let activeIntakeRequestToken = 0;
let activeIntakeAbortController = null;
let selectionMode = null;
let confirmed = false;
let outputCount = 0;
let memoryCount = 0;
let retrievalCount = 0;
const reducedMotion = {matches: true};
function resetProductProgress() {}
function setMemoryActionsEnabled(enabled) { fields.shareEnabled = enabled; }
function productStep() {}
function setProductLoader() {}
function completeProductProgress() {}
function focusProductOutput() { fields.product_output.focused = true; }
function setOperatorMessage(target, key) {
  const node = typeof target === "string" ? fields[target] : target;
  if (node) node.textContent = key;
}
function buildSourceProfile(raw) {
  return {candidateCount: raw ? 1 : 0, excerpts: raw ? [{text: raw}] : []};
}
function buildIntakeRecord(text, url, intake = null) {
  return {
    mode: intake ? "controlled-url" : "operator-pasted-text",
    original_url: url || null,
    final_url: intake?.final_url || null,
    text
  };
}
function renderRetrievedSourcePreview(intake, url) {
  currentRetrievedSourceText = intake.text;
  currentRetrievedSourceUrl = url;
  selectionMode = "controlled-url";
  confirmed = false;
  fields.product_source_preview.hidden = false;
}
function renderOperatorTextSelectionPreview(raw) {
  currentRetrievedSourceText = "";
  currentRetrievedSourceUrl = "";
  selectionMode = "operator-text";
  confirmed = false;
  fields.product_source_preview.hidden = false;
}
function sourceSelectionSnapshotIsCurrent(raw, mode) {
  return selectionMode === mode;
}
function confirmedSourceExcerptsFor() {
  return confirmed ? [{text: "exact confirmed passage"}] : null;
}
function renderSourceSelectionValidation() {
  fields.product_confirm_source.disabled = false;
  return {ok: true, excerpts: [{text: "exact confirmed passage"}]};
}
function syncAuditIntakeView() {}
function normalizePreparedSignal() { return {status: "draft"}; }
function renderProductOutput() { outputCount += 1; }
function buildMemoryRecord() { memoryCount += 1; return {ephemeral: true}; }
function renderMemoryStatus() {}
function clearRetrievedSourcePreview() {
  currentRetrievedSourceText = "";
  currentRetrievedSourceUrl = "";
  selectionMode = null;
  confirmed = false;
  fields.product_source_preview.hidden = true;
}
function renderUrlIntakeFallback(url, error) {
  throw new Error(`unexpected fallback for ${url}: ${error}`);
}
class ControlledIntakeError extends Error {}
async function readControlledUrlText(url, {signal} = {}) {
  retrievalCount += 1;
  if (signal?.aborted) throw Object.assign(new Error("aborted"), {name: "AbortError"});
  return {
    status: "ok",
    url,
    final_url: url,
    source_domain: "origin.example",
    text: "Retrieved line one.\nRetrieved line two."
  };
}
''' + "function isCurrentIntakeRequest(token, generation, sourceUrl) {" + request_guard.group(1) + "\n}\n" + "async function runProductAnalyze() {" + analyze.group(1) + "\n}\n" + r'''
(async () => {
  await runProductAnalyze();
  if (retrievalCount !== 1 || selectionMode !== "controlled-url" || outputCount || memoryCount) {
    throw new Error("URL first step did not stop at exact-passage review");
  }
  confirmed = true;
  fields.product_confirm_source.checked = true;
  await runProductAnalyze();
  if (retrievalCount !== 1 || outputCount !== 1 || memoryCount !== 1 || !preparedDraftReady) {
    throw new Error("URL confirmation did not produce exactly one ephemeral draft");
  }

  intakeState = {
    sourceUrl: "",
    sourceText: "Pasted line one.\nPasted line two.",
    sourceType: "external-source"
  };
  currentIntakeRecord = null;
  clearRetrievedSourcePreview();
  preparedDraftReady = false;
  await runProductAnalyze();
  if (selectionMode !== "operator-text" || outputCount !== 1 || memoryCount !== 1) {
    throw new Error("text first step did not stop at exact-passage review");
  }
  confirmed = true;
  fields.product_confirm_source.checked = true;
  await runProductAnalyze();
  if (outputCount !== 2 || memoryCount !== 2 || !preparedDraftReady) {
    throw new Error("text confirmation did not produce exactly one additional ephemeral draft");
  }
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
'''
    completed = subprocess.run(
        [NODE, "-"], input=smoke, text=True, capture_output=True, check=False
    )
    assert completed.returncode == 0, completed.stderr


@pytest.mark.skipif(NODE is None, reason="Node.js is required for JavaScript validation")
def test_aborted_url_intake_is_silent_and_a_new_request_can_succeed():
    html = _read(INDEX)
    request_guard = re.search(
        r"function isCurrentIntakeRequest\(token, generation, sourceUrl\) \{(.*?)\n    \}",
        html,
        re.DOTALL,
    )
    analyze = re.search(
        r"async function runProductAnalyze\(\) \{(.*?)\n    \}",
        html,
        re.DOTALL,
    )
    assert request_guard is not None and analyze is not None
    smoke = r'''
const fields = {
  product_analyze: {disabled: false, textContent: ""},
  normalize_signal: {disabled: false, textContent: ""},
  product_output: {innerHTML: ""},
  product_source_url: {focus() {}},
  product_source_selection: {focus() {}},
  product_confirm_source: {checked: false, disabled: false, focus() {}},
  product_source_preview: {hidden: true, scrollIntoView() { this.scrolled = true; }}
};
const $ = (id) => fields[id];
let intakeState = {sourceUrl: "https://old.example/report", sourceText: "", sourceType: "external-source"};
function canonicalIntakeState() { return {...intakeState}; }
let currentIntakeRecord = null;
let currentRetrievedSourceText = "";
let currentRetrievedSourceUrl = "";
let currentMemoryRecord = null;
let currentIntakeFailure = null;
let preparedDraftReady = false;
let intakeGeneration = 0;
let intakeRequestSequence = 0;
let activeIntakeRequestToken = 0;
let activeIntakeAbortController = null;
let fallbackCount = 0;
let requestCount = 0;
const reducedMotion = {matches: true};
function resetProductProgress() {}
function setMemoryActionsEnabled() {}
function productStep() {}
function setProductLoader() {}
function setOperatorMessage(target, key) { const node = typeof target === "string" ? fields[target] : target; if (node) node.textContent = key; }
function buildSourceProfile() { return {candidateCount: 1, excerpts: [{text: "exact line"}]}; }
function buildIntakeRecord(text, url, intake) { return {mode: "controlled-url", original_url: url, final_url: intake.final_url, text}; }
function renderRetrievedSourcePreview(intake, url) { currentRetrievedSourceText = intake.text; currentRetrievedSourceUrl = url; fields.product_source_preview.hidden = false; }
function syncAuditIntakeView() {}
function clearRetrievedSourcePreview() { currentRetrievedSourceText = ""; currentRetrievedSourceUrl = ""; fields.product_source_preview.hidden = true; }
function renderUrlIntakeFallback() { fallbackCount += 1; }
function confirmedSourceExcerptsFor() { return null; }
function renderSourceSelectionValidation() { return {ok: false}; }
class ControlledIntakeError extends Error {}
async function readControlledUrlText(url, {signal} = {}) {
  requestCount += 1;
  if (requestCount === 1) {
    return new Promise((resolve, reject) => {
      signal.addEventListener("abort", () => reject(Object.assign(new Error("aborted"), {name: "AbortError"})), {once: true});
    });
  }
  return {status: "ok", url, final_url: url, source_domain: "new.example", text: "Fresh exact line."};
}
''' + "function isCurrentIntakeRequest(token, generation, sourceUrl) {" + request_guard.group(1) + "\n}\n" + "async function runProductAnalyze() {" + analyze.group(1) + "\n}\n" + r'''
(async () => {
  const stale = runProductAnalyze();
  await Promise.resolve();
  if (!activeIntakeAbortController || activeIntakeAbortController.signal.aborted) {
    throw new Error("first request did not expose a live AbortController");
  }
  activeIntakeAbortController.abort();
  activeIntakeAbortController = null;
  intakeGeneration += 1;
  activeIntakeRequestToken = 0;
  intakeState.sourceUrl = "https://new.example/report";
  await stale;
  if (fallbackCount !== 0 || fields.product_output.innerHTML) {
    throw new Error("AbortError was rendered as a stale URL fallback");
  }
  await runProductAnalyze();
  if (requestCount !== 2 || currentRetrievedSourceUrl !== intakeState.sourceUrl || fields.product_source_preview.hidden) {
    throw new Error("a fresh request did not recover after aborting the stale request");
  }
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
'''
    completed = subprocess.run(
        [NODE, "-"], input=smoke, text=True, capture_output=True, check=False
    )
    assert completed.returncode == 0, completed.stderr


def test_url_and_operator_context_are_kept_as_distinct_inputs():
    html = _read(INDEX)
    catalog = _read(OPERATOR_I18N)
    run = re.search(
        r"async function runProductAnalyze\(\) \{(.*?)\n    \}",
        html,
        re.DOTALL,
    )
    assert run is not None
    body = run.group(1)

    assert "if (sourceUrl)" in body
    assert "readControlledUrlText(sourceUrl, {" in body
    assert "signal: requestAbortController?.signal" in body
    assert '$("product_source_text").value = raw' not in body
    assert "renderRetrievedSourcePreview(intake, sourceUrl)" in body
    assert "confirmedSourceExcerptsFor(currentRetrievedSourceText)" in body
    assert "currentRetrievedSourceText" in body
    assert "operator-provided-context-not-attributed-to-source" in html
    assert "Every supplied URL is sent alone to controlled intake" in catalog
    assert 'sourceBoundDraftWasActive = currentCaseMetadata.normalizer_version === "operator-source-bound-v1"' in html
    assert "claims = [];" in html
    assert "evidence = [];" in html
    assert 'data-op-i18n="msgDraftInvalidatedTitle"' in html


@pytest.mark.skipif(NODE is None, reason="Node.js is required for JavaScript validation")
def test_operator_context_limit_is_disclosed_and_visible_in_every_locale():
    html = _read(INDEX)
    catalog = _read(OPERATOR_I18N)
    card = re.search(
        r"    function operatorContextCard\([^)]*\) \{.*?\n    \}",
        html,
        re.DOTALL,
    )
    assert card is not None
    assert "records up to 1,200 Unicode characters" in html
    assert "operatorContextCard(currentCaseMetadata.operator_context)" in html

    smoke = (
        catalog
        + r'''
function isPlainRecord(value) {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}
function unicodeCharacterCount(value) { return Array.from(String(value ?? "")).length; }
function escapeHtml(value) { return String(value ?? ""); }
function operatorTextFor(language, key, parameters = {}) {
  const template = globalThis.HUB_OPTIMUS_OPERATOR_I18N.messages[language][key];
  return String(template).replace(/\{([A-Za-z][A-Za-z0-9_]*)\}/g, (match, name) => (
    Object.prototype.hasOwnProperty.call(parameters, name) ? String(parameters[name]) : match
  ));
}
let activeOperatorLanguage = "en";
'''
        + card.group(0)
        + r'''
const context = {
  text: `${"a".repeat(1199)}😀`,
  canonical_character_count: 1201,
  truncated: true
};
for (const language of ["en", "es", "de", "ru", "he", "zh-Hans"]) {
  const rendered = operatorContextCard(context, {language});
  const title = globalThis.HUB_OPTIMUS_OPERATOR_I18N.messages[language].operatorContextTitle;
  if (!rendered.includes(title) || !rendered.includes("1200") || !rendered.includes("1201")) {
    throw new Error(`context truncation is not visible in ${language}`);
  }
  if (!rendered.includes("😀")) throw new Error(`Unicode context was split in ${language}`);
}
'''
    )
    completed = subprocess.run(
        [NODE, "-"], input=smoke, text=True, capture_output=True, check=False
    )
    assert completed.returncode == 0, completed.stderr


def test_primary_news_example_keeps_its_explicit_source_type():
    html = _read(INDEX)
    demo = re.search(
        r"function loadProductNewsDemo\(\) \{(.*?)\n    \}",
        html,
        re.DOTALL,
    )
    assert demo is not None
    assert '"news-article"' in demo.group(1)


def test_operator_preserves_controlled_url_intake_provenance():
    html = _read(INDEX)
    catalog = _read(OPERATOR_I18N)

    assert "operator-intake-record-v1" in html
    for field in (
        "original_url",
        "final_url",
        "source_domain",
        "title",
        "retrieved_at",
        "redirects",
        "content_type",
        "truncated",
        "status",
        "verification_status",
    ):
        assert f"{field}:" in html

    assert "intakePayload.retrieved_at_utc" in html
    assert "intakePayload.verification_status" in html
    assert "intake_record: intakeRecord" in html
    assert "Intake provenance" in catalog


def test_legacy_pasted_text_attribution_remains_explicit_for_old_local_drafts():
    html = _read(INDEX)
    catalog = _read(OPERATOR_I18N)

    assert '"operator-pasted-text-with-url"' in html
    assert '"operator-attribution-unverified"' in html
    assert '"operator-provided-url-not-fetched"' in html
    assert '"operator-pasted-text-with-unverified-url-attribution"' in html
    assert "Operator did not fetch the URL" in catalog


@pytest.mark.skipif(NODE is None, reason="Node.js is required for JavaScript validation")
def test_intake_record_behavior_preserves_fetch_and_operator_boundaries():
    helpers = _intake_record_helpers(_read(INDEX))
    smoke = (
        helpers
        + """
const fetched = buildIntakeRecord("", "https://origin.example/report", {
  status: "ok",
  url: "https://origin.example/report",
  final_url: "https://final.example/report",
  source_domain: "final.example",
  title: "Report",
  retrieved_at_utc: "2026-07-28T10:00:00+00:00",
  redirects: [
    {from: "https://origin.example/report", to: "https://middle.example/report", status: 302},
    {from: "https://middle.example/report", to: "https://final.example/report", status: 301}
  ],
  content_type: "text/html",
  truncated: true,
  verification_status: "unreviewed",
  bytes_read: 4096
});
if (fetched.original_url !== "https://origin.example/") throw new Error("original URL origin lost");
if (fetched.final_url !== "https://final.example/") throw new Error("final URL origin lost");
if (fetched.source_domain !== "final.example") throw new Error("source domain lost");
if (fetched.retrieved_at !== "2026-07-28T10:00:00+00:00") throw new Error("retrieval time lost");
if (!Array.isArray(fetched.redirects) || fetched.redirects.length !== 2) throw new Error("redirect chain lost");
if (redirectCount(fetched.redirects) !== 2 || fetched.truncated !== true) throw new Error("fetch metadata lost");
if (fetched.status !== "ok" || fetched.verification_status !== "unreviewed") throw new Error("status lost");
if (sourceReferenceForIntake(fetched) !== "https://final.example/") throw new Error("redacted final source origin not used");

const pasted = buildIntakeRecord("Operator supplied text", "https://example.com/source");
if (pasted.mode !== "operator-pasted-text-with-url") throw new Error("pasted+URL mode missing");
if (pasted.status !== "operator-attribution-unverified") throw new Error("unverified status missing");
if (pasted.final_url !== null || pasted.retrieved_at !== null) throw new Error("pasted URL was presented as fetched");
if (sourceReferenceForIntake(pasted) !== "operator-pasted-text-with-unverified-url-attribution") {
  throw new Error("pasted text was attributed to an unverified URL");
}
"""
    )
    completed = subprocess.run(
        [NODE, "-"],
        input=smoke,
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr


@pytest.mark.skipif(NODE is None, reason="Node.js is required for JavaScript validation")
def test_persisted_and_shared_urls_redact_sensitive_parameters():
    html = _read(INDEX)
    helpers = _intake_record_helpers(html)
    smoke = (
        helpers
        + r'''
const rawUrl = "https://user:pass@example.com/reset/path-secret?view=full&access_token=top-secret&clientSecret=hidden&ticket=ST-secret&SAMLResponse=assertion&otp=123456&redirect=https%3A%2F%2Fidp.test%2F%3Ftoken%3Dnested#private";
const persisted = redactUrlForPersistence(rawUrl);
if (persisted !== "https://example.com/") {
  throw new Error("sensitive URL data reached persistence");
}
const record = buildIntakeRecord("source", rawUrl, {
  status: "ok",
  url: rawUrl,
  final_url: "https://example.com/final?signature=secret-signature&lang=en",
  source_domain: "example.com",
  redirects: [{from: rawUrl, to: "https://example.com/final?token=redirect-secret", status: 302}],
  verification_status: "unreviewed"
});
const serialized = JSON.stringify(record);
for (const secret of ["path-secret", "top-secret", "hidden", "private", "ST-secret", "assertion", "123456", "nested", "secret-signature", "redirect-secret", "user", "pass"]) {
  if (serialized.includes(secret)) throw new Error(`secret persisted: ${secret}`);
}
'''
    )
    completed = subprocess.run(
        [NODE, "-"],
        input=smoke,
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert "JSON.stringify({ url: sourceUrl })" in html
    assert "JSON.stringify({ url: redactUrlForPersistence(sourceUrl) })" not in html


@pytest.mark.skipif(NODE is None, reason="Node.js is required for JavaScript validation")
def test_relationship_reconciliation_removes_every_dangling_reference():
    html = _read(INDEX)
    match = re.search(
        r"// OPERATOR_RECORD_INTEGRITY_START\n(.*?)\n"
        r"    // OPERATOR_RECORD_INTEGRITY_END",
        html,
        re.DOTALL,
    )
    assert match is not None
    smoke = (
        r'''
let claims = [{claim_id: "claim-001"}];
let evidence = [{
  evidence_id: "evidence-001",
  supports_claim_ids: ["claim-001", "claim-missing"],
  contradicts_claim_ids: ["claim-missing"]
}];
let currentCaseMetadata = {relationships: [
  {relationship_id: "keep", type: "SUPPORTS_CLAIM", from_ref: "evidence-001", to_ref: "claim-001"},
  {relationship_id: "drop-evidence", type: "SUPPORTS_CLAIM", from_ref: "evidence-missing", to_ref: "claim-001"},
  {relationship_id: "drop-claim", type: "SUPPORTS_CLAIM", from_ref: "evidence-001", to_ref: "claim-missing"}
]};
function setMemoryActionsEnabled() {}
function renderMemoryStatus() {}
function renderClaims() {}
function renderEvidence() {}
'''
        + match.group(1)
        + r'''
reconcileRecordRelationships();
if (evidence[0].supports_claim_ids.join(",") !== "claim-001" || evidence[0].contradicts_claim_ids.length) {
  throw new Error("dangling evidence-to-claim references survived");
}
if (currentCaseMetadata.relationships.length !== 1 || currentCaseMetadata.relationships[0].relationship_id !== "keep") {
  throw new Error("dangling structural relationships survived");
}
'''
    )
    completed = subprocess.run(
        [NODE, "-"],
        input=smoke,
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr


def test_operator_renders_redirect_count_as_a_localized_primary_concept():
    html = _read(INDEX)

    assert 't("intakeRedirectCount", { count: redirectCount(intakeRecord.redirects) })' in html
    assert "redirects=${escapeHtml(" not in html


def test_operator_does_not_auto_save_or_duplicate_current_draft():
    html = _read(INDEX)
    catalog = _read(OPERATOR_I18N)

    assert "currentMemoryRecord = buildMemoryRecord();" in html
    assert "currentMemoryRecord = saveCurrentMemoryResult();" not in html
    assert "Local draft already saved:" not in catalog
    assert "Draft ready. Save it locally only if you choose to." not in catalog
    assert "Operator does not save these summaries." in catalog

    share_helper = re.search(
        r"function currentShareableMemory\(\) \{(.*?)\n    \}",
        html,
        re.DOTALL,
    )
    assert share_helper is not None
    assert "saveCurrentMemoryResult" not in share_helper.group(1)


def test_advanced_saved_draft_has_an_explicit_privacy_lifecycle():
    html = _read(INDEX)

    assert 'id="delete_saved_draft" type="button"' in html
    assert "Save stores the complete current case in this browser profile" in html
    assert "Clearing the current fields does not delete a saved draft." in html
    assert 'id="clear_all" type="button" data-op-i18n="advancedClearFields">Clear current fields</button>' in html

    deletion = re.search(
        r"function deleteSavedDraft\(\) \{(.*?)\n    \}", html, re.DOTALL
    )
    clearing = re.search(r"function clearAll\(\) \{(.*?)\n    \}", html, re.DOTALL)
    loading = re.search(r"function loadDraft\(\) \{(.*?)\n    \}", html, re.DOTALL)
    saving = re.search(r"function saveDraft\(\) \{(.*?)\n    \}", html, re.DOTALL)
    assert deletion is not None and clearing is not None
    assert loading is not None and saving is not None
    assert "localStorage.removeItem(storageKey)" in deletion.group(1)
    assert "localStorage.removeItem" not in clearing.group(1)
    assert 'opText("advancedClearConfirm")' in clearing.group(1)
    assert "try {" in saving.group(1)
    assert "parseStoredDraft(raw)" in loading.group(1)
    assert 'opText("advancedSavedDraftInvalidJson")' in loading.group(1)
    assert "resetRetrievedSource: true" in loading.group(1)
    assert "invalidateRetrieval: true" in loading.group(1)
    assert '$("delete_saved_draft").addEventListener("click", deleteSavedDraft);' in html


@pytest.mark.skipif(NODE is None, reason="Node.js is required for JavaScript validation")
def test_advanced_saved_draft_can_be_loaded_deleted_and_rejects_corruption():
    html = _read(INDEX)
    functions = []
    for name in (
        "saveDraft",
        "isPlainRecord",
        "hasOnlyRecordKeys",
        "hasExactRecordKeys",
        "isNonEmptyDraftString",
        "isNonEmptyStringList",
        "isUniqueNonEmptyStringList",
        "isOptionalNonEmptyString",
        "isStoredClaimRecord",
        "isStoredEvidenceRecord",
        "isStoredCasePayload",
        "hasValidRecordIdentityAndReferences",
        "parseStoredDraft",
        "loadDraft",
        "deleteSavedDraft",
    ):
        match = re.search(
            rf"    function {name}\([^)]*\) \{{.*?\n    \}}", html, re.DOTALL
        )
        assert match is not None
        functions.append(match.group(0))

    smoke = (
        r'''
const storageKey = "hub_optimus_operator_case_v1";
const localDraftVersion = "operator-local-draft-v2";
const stored = new Map();
let storageFailure = "";
const localStorage = {
  setItem(key, value) {
    if (storageFailure === "set") throw new Error("blocked");
    stored.set(key, String(value));
  },
  getItem(key) {
    if (storageFailure === "get") throw new Error("blocked");
    return stored.has(key) ? stored.get(key) : null;
  },
  removeItem(key) {
    if (storageFailure === "remove") throw new Error("blocked");
    stored.delete(key);
  }
};
const notices = [];
function alert(message) { notices.push(message); }
function confirm() { return true; }
function opText(key) {
  return ({
    advancedDraftSaved: "Draft saved",
    advancedDraftSaveFailed: "Draft could not be saved",
    advancedDraftAccessFailed: "Saved draft cannot be accessed",
    advancedNoSavedDraft: "No saved draft",
    advancedSavedDraftInvalidJson: "Saved draft is not valid JSON",
    advancedSavedDraftUnsupported: "Saved draft has an unsupported structure",
    advancedDraftLoadFailedSafe: "Saved draft could not be loaded safely",
    advancedDraftLoadedReset: "Saved draft loaded",
    advancedDeleteSavedConfirm: "Delete saved draft?",
    advancedSavedDeleted: "Saved draft deleted",
    advancedSavedDeleteFailed: "Saved draft could not be deleted"
  })[key] || key;
}
function buildPayload() {
  return {
    case_id: "case-private-001",
    core_version_ref: "main",
    input_summary: "Private draft",
    evidence: [{
      evidence_id: "evidence-001",
      text: "Exact source excerpt",
      source_ref: "operator-pasted-text",
      supports_claim_ids: []
    }]
  };
}
function value() { return ""; }
let claims = [{claim_id: "claim-001"}];
let evidence = [{evidence_id: "evidence-001"}];
let loaded = null;
function loadPayload(payload) { loaded = payload; }
const fields = {
  product_source_url: {value: "https://source-b.example/private"},
  product_source_text: {value: "TEXT FROM B"},
  signal_source_type: {value: "external-source"}
};
function $(id) { return fields[id]; }
let resetOptions = null;
function syncProductInputState(options) { resetOptions = options; }
'''
        + "\n".join(functions)
        + r'''
saveDraft();
if (!stored.has(storageKey)) throw new Error("saved draft was not persisted");
loadDraft();
if (!loaded || loaded.case_id !== "case-private-001") {
  throw new Error("saved draft did not round-trip");
}
if (fields.product_source_url.value || fields.product_source_text.value) {
  throw new Error("primary source inputs survived a draft load");
}
if (!resetOptions?.resetIntakeRecord || !resetOptions?.resetRetrievedSource || !resetOptions?.invalidateRetrieval) {
  throw new Error("draft load did not invalidate the live intake binding");
}
const duplicateNarrativePayload = {
  case_id: "case-duplicates-allowed",
  core_version_ref: "main",
  input_summary: "Schema-valid repeated narrative text",
  inferences: ["Repeated observation", "Repeated observation"],
  evidence: [{
    evidence_id: "evidence-duplicates-allowed",
    text: "Exact source excerpt",
    source_ref: "operator-pasted-text",
    limitations: ["Same limitation", "Same limitation"]
  }]
};
if (!isStoredCasePayload(duplicateNarrativePayload)) {
  throw new Error("schema-valid repeated narrative strings were rejected");
}
if (isStoredEvidenceRecord({
  evidence_id: "evidence-duplicate-ids",
  text: "Exact source excerpt",
  source_ref: "operator-pasted-text",
  supports_claim_ids: ["claim-001", "claim-001"]
})) {
  throw new Error("duplicate relationship IDs were accepted");
}
fields.product_source_text.value = "live fields remain";
deleteSavedDraft();
if (stored.has(storageKey)) throw new Error("explicit deletion left draft data behind");
if (fields.product_source_text.value !== "live fields remain") {
  throw new Error("saved-draft deletion changed live fields");
}

loaded = null;
stored.set(storageKey, "{not-json");
loadDraft();
if (loaded !== null) throw new Error("corrupt draft reached the loader");
if (!notices.some((message) => message.includes("not valid JSON"))) {
  throw new Error("corrupt draft did not produce a bounded diagnostic");
}

loaded = {case_id: "unchanged"};
stored.set(storageKey, JSON.stringify({
  version: localDraftVersion,
  payload: {
    case_id: "case-corrupt",
    core_version_ref: "main",
    input_summary: "Corrupt nested record",
    evidence: [null]
  }
}));
loadDraft();
if (loaded.case_id !== "unchanged") {
  throw new Error("unsupported nested structure mutated the current case");
}
if (!notices.some((message) => message.includes("unsupported structure"))) {
  throw new Error("unsupported nested structure did not produce a bounded diagnostic");
}

for (const failure of ["get", "set", "remove"]) {
  storageFailure = failure;
  if (failure === "get") loadDraft();
  if (failure === "set") saveDraft();
  if (failure === "remove") deleteSavedDraft();
  storageFailure = "";
}
if (!notices.some((message) => message.includes("cannot be accessed"))) {
  throw new Error("storage read failure was not bounded");
}
if (!notices.some((message) => message.includes("could not be saved"))) {
  throw new Error("storage write failure was not bounded");
}
if (!notices.some((message) => message.includes("could not be deleted"))) {
  throw new Error("storage delete failure was not bounded");
}
'''
    )
    completed = subprocess.run(
        [NODE, "-"], input=smoke, text=True, capture_output=True, check=False
    )
    assert completed.returncode == 0, completed.stderr


@pytest.mark.skipif(NODE is None, reason="Node.js is required for JavaScript validation")
def test_advanced_case_metadata_never_rebinds_primary_live_intake():
    html = _read(INDEX)
    sources = []
    for name in ("buildPayload", "loadPayload"):
        match = re.search(
            rf"    function {name}\([^)]*\) \{{.*?\n    \}}", html, re.DOTALL
        )
        assert match is not None
        sources.append(match.group(0))

    smoke = (
        r'''
const fields = {
  case_id: {value: "case-live"},
  core_version_ref: {value: "main"},
  input_summary: {value: "Live advanced case"},
  operational_signal: {value: "triage"},
  intake_channel: {value: "operator-pwa"},
  inferences: {value: ""},
  uncertainties: {value: ""},
  narrative_amplification: {value: ""},
  result_input: {value: "REPORT FROM SOURCE B"},
  result_view: {
    textContent: "REPORT FROM SOURCE B",
    replaceChildren() { this.textContent = ""; }
  }
};
function $(id) { return fields[id]; }
function value(id) { return fields[id]?.value?.trim() || ""; }
function lines() { return []; }
function reconcileRecordRelationships() {}
function invalidateShareableResult() {}
function syncRecordSequences() {}
function renderClaims() {}
function renderEvidence() {}
function updateJson() {}
let claims = [];
let evidence = [];
const intakeA = {mode: "controlled-url", original_url: "https://source-a.example/"};
const intakeB = {mode: "controlled-url", original_url: "https://source-b.example/"};
let currentCaseMetadata = {intake_record: intakeA, operator_mode: "browser-local-source-bound-draft"};
let currentIntakeRecord = intakeB;
'''
        + "\n".join(sources)
        + r'''
const first = buildPayload();
if (first.metadata.intake_record.original_url !== "https://source-a.example/") {
  throw new Error("live Primary intake replaced Advanced case provenance");
}

loadPayload({
  case_id: "case-a",
  core_version_ref: "main",
  input_summary: "Saved A",
  metadata: {intake_record: intakeA, intake_channel: "operator-pwa-source-normalizer"}
});
if (currentIntakeRecord.original_url !== "https://source-b.example/") {
  throw new Error("loading Advanced case rebound Primary live intake");
}
if (currentCaseMetadata.intake_record.original_url !== "https://source-a.example/") {
  throw new Error("loaded Advanced provenance was not preserved inside the case");
}
if (fields.result_input.value || fields.result_view.textContent) {
  throw new Error("loading a different case retained a stale Advanced result");
}
'''
    )
    completed = subprocess.run(
        [NODE, "-"], input=smoke, text=True, capture_output=True, check=False
    )
    assert completed.returncode == 0, completed.stderr


def test_operator_memory_and_sharing_controls_remain_compatible():
    html = _read(INDEX)
    catalog = _read(OPERATOR_I18N)

    assert "hub_optimus_operator_memory_v1" not in html
    assert 'id="save_memory_result"' not in html
    assert 'id="share_memory_link" type="button" disabled' in html
    assert 'id="share_memory_whatsapp" type="button" disabled' in html
    assert "setMemoryActionsEnabled" in html
    assert "buildHumanShareText" in html
    assert "buildCleanOperatorUrl" in html
    assert "https://wa.me/" in html
    assert "localStorage" not in re.search(
        r"async function shareMemoryLink\(\) \{(.*?)\n    \}", html, re.DOTALL
    ).group(1)
    assert "localStorage" not in re.search(
        r"function shareMemoryWhatsapp\(\) \{(.*?)\n    \}", html, re.DOTALL
    ).group(1)
    assert "#memory=" not in html
    assert "loadSharedMemoryFromHash" not in html
    assert "Readable summary copied. Draft data is in the text, not the URL." in catalog
    assert "Boundary: unverified local draft; not a truth verdict or engine result." in catalog
    assert 'opText("shareOpenOperator", { url: ltrIsolate(buildCleanOperatorUrl()) })' in html


def test_every_case_edit_invalidates_sharing_and_share_counts_records():
    html = _read(INDEX)

    assert "function invalidateShareableResult(" in html
    assert "currentMemoryRecord = null;" in html
    assert "removeClaimAt" in html and "removeEvidenceAt" in html
    assert "reconcileRecordRelationships();\n      invalidateShareableResult();" in html
    assert "result_input" in html
    assert '$("result_input").addEventListener("input"' in html
    assert "claim_count: claimRecords.length" in html
    assert "evidence_count: evidenceRecords.length" in html
    assert '...shareRecordLines("claim", "shareClaims", claimRecords, record.claim)' in html
    assert '...shareRecordLines("evidence", "shareEvidence", evidenceRecords, record.evidence)' in html
    assert 'pluralMessage("shareOmitted"' in html


@pytest.mark.skipif(NODE is None, reason="Node.js is required for JavaScript validation")
def test_share_text_preserves_pasted_text_and_url_provenance():
    html = _read(INDEX)
    helpers = _intake_record_helpers(html) + "\n" + _share_provenance_helpers(html)
    smoke = (
        _operator_i18n_node_prelude()
        + """
function compactText(value, maxLength) {
  const normalized = String(value || "").trim();
  return normalized.length <= maxLength
    ? normalized
    : `${normalized.slice(0, maxLength - 1)}…`;
}
function withoutIsolates(value) {
  return value.replace(/[\u2066\u2069]/g, "");
}
"""
        + helpers
        + """
const pasted = shareProvenanceLines({
  source_url: "https://example.com/source",
  intake_record: {
    mode: "operator-pasted-text-with-url",
    original_url: "https://example.com/source",
    final_url: null,
    attribution: "operator-provided-url-not-fetched"
  }
});
if (!pasted[0].includes("Operator did not fetch the URL")) {
  throw new Error("pasted text and URL boundary lost");
}
if (withoutIsolates(pasted[1]) !== "Supplied URL, not fetched: https://example.com/") {
  throw new Error("unfetched URL label lost");
}

const fetched = shareProvenanceLines({
  source_url: "https://final.example/report",
  intake_record: {
    mode: "controlled-url",
    original_url: "https://origin.example/report",
    final_url: "https://final.example/report"
  }
});
if (!fetched[0].includes("controlled URL intake")) {
  throw new Error("controlled intake provenance lost");
}
if (withoutIsolates(fetched[1]) !== "Retrieved URL: https://final.example/") {
  throw new Error("retrieved URL label lost");
}
"""
    )
    completed = subprocess.run(
        [NODE, "-"],
        input=smoke,
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr


def test_operator_url_fallback_remains_actionable():
    html = _read(INDEX)
    catalog = _read(OPERATOR_I18N)

    assert "URL not accessible from controlled intake" in catalog
    assert "paste the source text" in catalog.lower()
    assert "Some sources block automated access" in catalog
    assert "msgIntakeActionTemporary" in catalog
    assert "readControlledUrlText" in html
    assert "renderUrlIntakeFallback" in html
    assert "Ready to read the URL through controlled intake" in catalog


def test_operator_install_assets_use_institutional_mark_and_cache_v023():
    icon = _read(ICON)
    sw = _read(SW)

    assert "HUB_Optimus app mark" in icon
    assert re.search(
        r"\b(reactor|nuclear|nuke|melon|containment|sealed)\b",
        icon,
        re.IGNORECASE,
    ) is None
    assert "hub-optimus-operator-v0-26" in sw
    assert "./index.html" in sw
    assert "../assets/brand/hub-optimus-logo-lockup.png" in sw
    assert "./og.svg" in sw
    assert "STATIC_ASSET_URLS.has(url.href)" in sw
    assert "event.respondWith(cacheFirst(event.request))" in sw


@pytest.mark.skipif(NODE is None, reason="Node.js is required for JavaScript validation")
def test_operator_service_worker_serves_precached_brand_asset_offline():
    smoke = (
        """
const handlers = {};
globalThis.self = {
  location: {
    origin: "https://huboptimus.dev",
    href: "https://huboptimus.dev/operator/sw.js"
  },
  addEventListener(name, handler) {
    handlers[name] = handler;
  },
  skipWaiting() {},
  clients: {claim() {}}
};
globalThis.caches = {
  async match(request) {
    if (request.url === "https://huboptimus.dev/assets/brand/hub-optimus-logo-lockup.png") {
      return {source: "precache"};
    }
    return null;
  },
  async open() {
    return {
      async addAll() {},
      async put() {}
    };
  },
  async keys() {
    return [];
  },
  async delete() {
    return true;
  }
};
globalThis.fetch = async () => {
  throw new Error("offline");
};
"""
        + _read(SW)
        + """
(async () => {
  let responsePromise = null;
  handlers.fetch({
    request: {
      method: "GET",
      mode: "no-cors",
      url: "https://huboptimus.dev/assets/brand/hub-optimus-logo-lockup.png"
    },
    respondWith(value) {
      responsePromise = value;
    }
  });
  if (!responsePromise) throw new Error("brand request bypassed service worker");
  const response = await responsePromise;
  if (response?.source !== "precache") throw new Error("precache response not used");
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
"""
    )
    completed = subprocess.run(
        [NODE, "-"],
        input=smoke,
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr


def test_operator_result_copy_matches_local_draft_semantics():
    html = _read(INDEX)
    catalog = _read(OPERATOR_I18N)

    assert "Keep this as a draft until a human selects a concrete review state." in catalog
    assert "Review primary records, preserve uncertainty" in catalog
    assert "no Semantic Engine run occurred" in catalog
    assert "Result ready. Memory and sharing are available." not in html


@pytest.mark.skipif(NODE is None, reason="Node.js is required for JavaScript validation")
def test_advanced_result_viewer_rejects_arbitrary_or_stale_output_fail_closed(tmp_path: Path):
    html = _read(INDEX)
    functions = []
    for name in (
        "isPlainRecord",
        "hasOnlyRecordKeys",
        "hasExactRecordKeys",
        "isNonEmptyDraftString",
        "isNonEmptyStringList",
        "isUniqueNonEmptyStringList",
        "isOptionalNonEmptyString",
        "isStoredClaimRecord",
        "isStoredEvidenceRecord",
        "hasValidRecordIdentityAndReferences",
        "isSafeJsonValue",
        "isStoredDecisionTraceRecord",
        "isStoredAuditLogRecord",
        "isCompleteAnalysisClaimRecord",
        "isCompleteAnalysisEvidenceRecord",
        "isStoredAnalysisResult",
        "parseValidatedResultEnvelope",
        "currentResultCaseIdentity",
        "buildNormalizedDraftResponse",
        "firstArrayItem",
        "renderList",
        "clearRenderedResult",
        "renderResult",
    ):
        match = re.search(
            rf"    function {name}\([^)]*\) \{{.*?\n    \}}", html, re.DOTALL
        )
        assert match is not None, name
        functions.append(match.group(0))

    smoke = (
        r'''
const ADVANCED_RESULT_MAX_CHARACTERS = 1000000;
const ADVANCED_RESULT_MAX_DEPTH = 32;
const ADVANCED_RESULT_MAX_COLLECTION_ITEMS = 10000;
const fields = {
  result_input: {value: ""},
  case_id: {value: "case-001"},
  core_version_ref: {value: "main@verified"},
  input_summary: {value: "Exact bounded result"},
  result_view: {
    innerHTML: "",
    replaceChildren() { this.innerHTML = ""; }
  }
};
let flowRendered = null;
const notices = [];
function $(id) { return fields[id]; }
function value(id) { return String(fields[id]?.value || "").trim(); }
function unicodeCharacterCount(raw) { return Array.from(String(raw ?? "")).length; }
function escapeHtml(raw) { return String(raw ?? "").replaceAll("<", "&lt;"); }
function opText(key) { return key; }
function pluralMessage(key, count) { return `${key}:${count}`; }
function operationalSignalLabel(signal) { return signal; }
function refreshFlow(rendered) { flowRendered = rendered; }
function alert(message) { notices.push(message); }
function buildPayload() {
  return {
    case_id: "case-001",
    core_version_ref: "main@verified",
    input_summary: "Exact bounded result",
    claims: [],
    evidence: [],
    metadata: {}
  };
}
'''
        + "\n".join(functions)
        + r'''
const validEnvelope = {
  status: "ok",
  run_id: "20260801T120000Z.Ab12Cd",
  run_path: "/srv/hub/runs/20260801T120000Z.Ab12Cd",
  analysis_result: {
    case_id: "case-001",
    core_version_ref: "main@verified",
    input_summary: "Exact bounded result",
    claims: [{
      claim_id: "claim-001",
      text: "The selected source states X.",
      source_ref: "source-sha256:abc",
      claim_type: "source-statement",
      requires_evidence: true,
      status: "draft",
      metadata: {}
    }],
    evidence: [{
      evidence_id: "evidence-001",
      text: "Exact source passage X.",
      source_ref: "source-sha256:abc",
      source_type: "controlled-url-snapshot",
      supports_claim_ids: ["claim-001"],
      contradicts_claim_ids: [],
      limitations: ["Independent verification required."],
      metadata: {}
    }],
    inferences: [],
    uncertainties: ["Independent verification required."],
    narrative_amplification: [],
    operational_signal: "triage",
    status: "draft",
    decision_trace: [],
    audit_log: [],
    metadata: {}
  }
};
fields.result_input.value = JSON.stringify(validEnvelope);
if (!renderResult() || !fields.result_view.innerHTML.includes("The selected source states X.")) {
  throw new Error("a valid structured result did not render");
}
if (flowRendered !== true) throw new Error("valid result did not activate the output flow");
const localDraftEnvelope = buildNormalizedDraftResponse();
if (!parseValidatedResultEnvelope(
  JSON.stringify(localDraftEnvelope),
  currentResultCaseIdentity()
).ok) {
  throw new Error("the complete local normalized-draft envelope was rejected");
}
fields.input_summary.value = "";
fields.result_input.value = JSON.stringify({
  ...validEnvelope,
  analysis_result: {
    ...validEnvelope.analysis_result,
    input_summary: "Unrelated summary under default case identifiers"
  }
});
if (renderResult() !== false || fields.result_view.innerHTML !== "") {
  throw new Error("an unrelated summary passed when the visible input summary was empty");
}
fields.input_summary.value = "Exact bounded result";

const invalidCases = [
  {analysis_result: {input_summary: "arbitrary"}},
  {...validEnvelope, status: "banana", run_id: "x", run_path: "x"},
  {...validEnvelope, analysis_result: {...validEnvelope.analysis_result, case_id: "other-case"}},
  {...validEnvelope, analysis_result: {...validEnvelope.analysis_result, claims: [null]}},
  {...validEnvelope, analysis_result: {
    ...validEnvelope.analysis_result,
    evidence: [{...validEnvelope.analysis_result.evidence[0], supports_claim_ids: "claim-001"}]
  }},
  {...validEnvelope, analysis_result: {
    ...validEnvelope.analysis_result,
    evidence: [{...validEnvelope.analysis_result.evidence[0], supports_claim_ids: ["claim-missing"]}]
  }},
  validEnvelope.analysis_result
];
for (const invalid of invalidCases) {
  fields.result_input.value = JSON.stringify(invalid);
  let rendered;
  try { rendered = renderResult(); } catch (error) {
    throw new Error(`invalid result escaped as an exception: ${error.message}`);
  }
  if (rendered !== false || fields.result_view.innerHTML !== "" || flowRendered !== false) {
    throw new Error("invalid result retained or rendered stale output");
  }
}

const prototypeKey = JSON.stringify(validEnvelope).replace(
  '"metadata":{}',
  '"metadata":{"__proto__":{"polluted":true}}'
);
if (parseValidatedResultEnvelope(prototypeKey).ok) {
  throw new Error("prototype-shaped metadata was accepted");
}
if (parseValidatedResultEnvelope("x".repeat(ADVANCED_RESULT_MAX_CHARACTERS + 1)).ok) {
  throw new Error("oversized result was accepted");
}
if (!notices.some((message) => message === "advancedInvalidResultStructure")) {
  throw new Error("invalid structure did not produce a localized bounded diagnostic");
}
if (!notices.some((message) => message === "advancedResultCaseMismatch")) {
  throw new Error("a cross-case result did not produce a localized bounded diagnostic");
}
fields.result_input.value = "{";
if (renderResult() !== false || notices.at(-1) !== "advancedInvalidResultJson") {
  throw new Error("malformed JSON did not use the stable localized diagnostic");
}
'''
    )
    completed = subprocess.run(
        [NODE, "-"], input=smoke, text=True, capture_output=True, check=False
    )
    assert completed.returncode == 0, completed.stderr

    listener = re.search(
        r'\$\("result_input"\)\.addEventListener\("input", \(\) => \{(.*?)\n    \}\);',
        html,
        re.DOTALL,
    )
    assert listener is not None
    assert "invalidateShareableResult();" in listener.group(1)
    assert "clearRenderedResult();" in listener.group(1)

    parser = re.search(
        r"function parseValidatedResultEnvelope\(.*?\n    \}", html, re.DOTALL
    )
    assert parser is not None
    assert "error.message" not in parser.group(0)
    assert 'alert(opText("advancedInvalidResultJson"));' in html
    assert 'advancedInvalidResultJson", { message:' not in html

    command = re.search(
        r"function buildAnalyzeCommand\(\) \{(.*?)\n    \}", html, re.DOTALL
    )
    assert command is not None
    assert "Incomplete analysis_result identity" in command.group(1)
    assert "analysis_result evidence references an unknown claim" in command.group(1)

    generated = subprocess.run(
        [NODE, "-"],
        input=(
            "function buildPayload() { return {case_id: 'case-001', "
            "core_version_ref: 'main', input_summary: 'Bound case'}; }\n"
            + command.group(0)
            + "\nprocess.stdout.write(buildAnalyzeCommand());\n"
        ),
        text=True,
        capture_output=True,
        check=False,
    )
    assert generated.returncode == 0, generated.stderr
    shell_syntax = subprocess.run(
        ["bash", "-n"],
        input=generated.stdout,
        text=True,
        capture_output=True,
        check=False,
    )
    assert shell_syntax.returncode == 0, shell_syntax.stderr
    python_check = generated.stdout.split("python3 - <<'PY_CHECK'\n", 1)[1].rsplit(
        "\nPY_CHECK", 1
    )[0]
    compile(python_check, "operator-handoff-check", "exec")

    case_path = tmp_path / "case.json"
    response_path = tmp_path / "response.json"
    case_payload = {
        "case_id": "case-001",
        "core_version_ref": "main",
        "input_summary": "Bound case",
    }
    case_path.write_text(json.dumps(case_payload), encoding="utf-8")
    executable_check = python_check.replace(
        "/tmp/hub-optimus-operator-case.json", str(case_path)
    ).replace("/tmp/hub-optimus-operator-response.json", str(response_path))

    valid_result = {
        "case_id": "case-001",
        "core_version_ref": "main",
        "input_summary": "Bound case",
        "claims": [],
        "evidence": [],
        "inferences": [],
        "uncertainties": [],
        "narrative_amplification": [],
        "operational_signal": "none",
        "status": "draft",
        "decision_trace": [],
        "audit_log": [],
        "metadata": {},
    }
    valid_response = {
        "status": "ok",
        "run_id": "20260801T120000Z.Ab12Cd",
        "run_path": "/srv/hub/runs/20260801T120000Z.Ab12Cd",
        "analysis_result": valid_result,
    }

    def run_handoff_check(payload: dict) -> subprocess.CompletedProcess[str]:
        response_path.write_text(json.dumps(payload), encoding="utf-8")
        return subprocess.run(
            [sys.executable, "-c", executable_check],
            text=True,
            capture_output=True,
            check=False,
        )

    assert run_handoff_check(valid_response).returncode == 0

    invalid_trace = json.loads(json.dumps(valid_response))
    invalid_trace["analysis_result"]["decision_trace"] = [{}]
    assert run_handoff_check(invalid_trace).returncode != 0

    duplicate_evidence = {
        "evidence_id": "evidence-001",
        "text": "Exact passage",
        "source_ref": "source-sha256:abc",
        "source_type": "controlled-url-snapshot",
        "supports_claim_ids": [],
        "contradicts_claim_ids": [],
        "limitations": [],
        "metadata": {},
    }
    invalid_evidence_ids = json.loads(json.dumps(valid_response))
    invalid_evidence_ids["analysis_result"]["evidence"] = [
        duplicate_evidence,
        duplicate_evidence,
    ]
    assert run_handoff_check(invalid_evidence_ids).returncode != 0

    invalid_duplicate_refs = json.loads(json.dumps(valid_response))
    invalid_duplicate_refs["analysis_result"]["claims"] = [{
        "claim_id": "claim-001",
        "text": "Source states X",
        "source_ref": "source-sha256:abc",
        "claim_type": "source-statement",
        "requires_evidence": True,
        "status": "draft",
        "metadata": {},
    }]
    invalid_duplicate_refs["analysis_result"]["evidence"] = [{
        **duplicate_evidence,
        "supports_claim_ids": ["claim-001", "claim-001"],
    }]
    assert run_handoff_check(invalid_duplicate_refs).returncode != 0
