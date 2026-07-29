import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "site" / "operator" / "index.html"
ICON = ROOT / "site" / "operator" / "icon.svg"
LOCKUP = ROOT / "site" / "assets" / "brand" / "hub-optimus-logo-lockup.png"
SW = ROOT / "site" / "operator" / "sw.js"
URL_INTAKE_SCHEMA = (
    ROOT / "ops" / "ec2" / "controlled_url_intake.v1.schema.json"
)
NODE = shutil.which("node")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


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


def test_operator_product_buttons_keep_existing_handlers():
    html = _read(INDEX)

    assert '].join("\\n");' in html
    assert '].join("\n");' not in html
    assert '$("product_analyze").addEventListener("click", runProductAnalyze);' in html
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
let currentIntakeRecord = {mode: "operator-pasted-text"};
let currentMemoryRecord = {stale: true};
let memoryActionsEnabled = true;
function setMemoryActionsEnabled(enabled) {
  memoryActionsEnabled = enabled;
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
    assert "<form" not in html
    assert "<script src=" not in html


def test_operator_uses_canonical_identity_and_explicit_prototype_boundary():
    html = _read(INDEX)

    assert '../assets/brand/hub-optimus-logo-lockup.png' in html
    assert LOCKUP.is_file()
    assert 'alt="HUB_Optimus"' in html
    assert "LOCAL-FIRST BROWSER PROTOTYPE" in html
    assert "It does not run the Python CLI or a Semantic Engine." in html
    assert "complete Semantic Engine" not in html
    assert "Local draft · human review required" in html
    assert re.search(
        r"\b(reactor|nuclear|nuke|melon|containment|sealed)\b",
        html,
        re.IGNORECASE,
    ) is None


def test_operator_progress_is_immediate_and_has_no_fake_delay_plan():
    html = _read(INDEX)
    sw = _read(SW)

    assert "signal-loader" in html
    assert "product_loader_percent" in html
    assert "completeProductProgress" in html
    assert "setTimeout" not in html
    assert "runSignalLoaderPlan" not in html
    assert "runMelonLoaderPlan" not in html
    assert "await wait(" not in html
    assert "hub-optimus-operator-v0-20" in sw


def test_operator_triage_is_generic_and_conservative():
    html = _read(INDEX)

    assert "operator-generic-triage-v1" in html
    assert "triage_profile=generic-conservative-v1" in html
    assert "No motives or incentives are inferred from the submitted text." in html
    assert "No substantive inference is generated by this browser prototype." in html
    assert "Human review checklist" in html
    assert "playbooks" not in html
    assert "scenarioCards" not in html
    assert "housing-finance" not in html
    assert "security-conflict" not in html
    assert "operator-topic-analysis" not in html


def test_operator_preserves_controlled_url_intake_provenance():
    html = _read(INDEX)

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
    assert "Intake provenance" in html


def test_pasted_text_with_url_is_marked_as_unverified_operator_attribution():
    html = _read(INDEX)

    assert '"operator-pasted-text-with-url"' in html
    assert '"operator-attribution-unverified"' in html
    assert '"operator-provided-url-not-fetched"' in html
    assert '"operator-pasted-text-with-unverified-url-attribution"' in html
    assert "Operator did not fetch the URL" in html


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
if (fetched.original_url !== "https://origin.example/report") throw new Error("original URL lost");
if (fetched.final_url !== "https://final.example/report") throw new Error("final URL lost");
if (fetched.source_domain !== "final.example") throw new Error("source domain lost");
if (fetched.retrieved_at !== "2026-07-28T10:00:00+00:00") throw new Error("retrieval time lost");
if (!Array.isArray(fetched.redirects) || fetched.redirects.length !== 2) throw new Error("redirect chain lost");
if (redirectCount(fetched.redirects) !== 2 || fetched.truncated !== true) throw new Error("fetch metadata lost");
if (fetched.status !== "ok" || fetched.verification_status !== "unreviewed") throw new Error("status lost");
if (sourceReferenceForIntake(fetched) !== "https://final.example/report") throw new Error("final source ref not used");

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


def test_operator_renders_redirect_chain_as_a_count():
    html = _read(INDEX)

    assert "redirects=${escapeHtml(redirectCount(intakeRecord.redirects))}" in html
    assert "redirects=${escapeHtml(intakeRecord.redirects" not in html


def test_operator_does_not_auto_save_or_duplicate_current_draft():
    html = _read(INDEX)

    assert "currentMemoryRecord = buildMemoryRecord();" in html
    assert "currentMemoryRecord = saveCurrentMemoryResult();" not in html
    assert "Memory already saved:" in html
    assert "Draft ready. Save it locally only if you choose to." in html

    share_helper = re.search(
        r"function currentShareableMemory\(\) \{(.*?)\n    \}",
        html,
        re.DOTALL,
    )
    assert share_helper is not None
    assert "saveCurrentMemoryResult" not in share_helper.group(1)


def test_operator_memory_and_sharing_controls_remain_compatible():
    html = _read(INDEX)

    assert "hub_optimus_operator_memory_v1" in html
    assert 'id="save_memory_result" type="button" disabled' in html
    assert 'id="share_memory_link" type="button" disabled' in html
    assert 'id="share_memory_whatsapp" type="button" disabled' in html
    assert "setMemoryActionsEnabled" in html
    assert "buildHumanShareText" in html
    assert "buildCleanOperatorUrl" in html
    assert "https://wa.me/" in html
    assert "Readable summary copied. Draft data is in the text, not the URL." in html
    assert "Boundary: unverified local draft; not a truth verdict or engine result." in html
    assert "`Open clean Operator: ${buildCleanOperatorUrl()}`" in html


@pytest.mark.skipif(NODE is None, reason="Node.js is required for JavaScript validation")
def test_share_text_preserves_pasted_text_and_url_provenance():
    helpers = _share_provenance_helpers(_read(INDEX))
    smoke = (
        """
function compactText(value, maxLength) {
  const normalized = String(value || "").trim();
  return normalized.length <= maxLength
    ? normalized
    : `${normalized.slice(0, maxLength - 1)}…`;
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
if (pasted[1] !== "Supplied URL (not fetched): https://example.com/source") {
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
if (fetched[1] !== "Retrieved URL: https://final.example/report") {
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

    assert "URL not accessible from controlled intake" in html
    assert "Paste the source text or relevant excerpt below and prepare the draft again." in html
    assert "Some sources block automated access" in html
    assert "Controlled intake service is unreachable" in html
    assert "readControlledUrlText" in html
    assert "renderUrlIntakeFallback" in html
    assert "Ready to read URL from controlled intake" in html


def test_operator_install_assets_use_institutional_mark_and_cache_v020():
    icon = _read(ICON)
    sw = _read(SW)

    assert "HUB_Optimus app mark" in icon
    assert re.search(
        r"\b(reactor|nuclear|nuke|melon|containment|sealed)\b",
        icon,
        re.IGNORECASE,
    ) is None
    assert "hub-optimus-operator-v0-20" in sw
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

    assert "Keep this as a draft until a human selects a concrete review state." in html
    assert "Review primary records, preserve uncertainty" in html
    assert "no Semantic Engine run occurred" in html
    assert "Result ready. Memory and sharing are available." not in html
