import importlib.util
import json
import os
import re
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OPERATOR = ROOT / "site" / "operator" / "index.html"
I18N = ROOT / "site" / "operator" / "i18n.v1.js"
MODEL = ROOT / "site" / "operator" / "learning-candidate.v1.js"
STORE = ROOT / "site" / "operator" / "learning-store.v1.js"
SCHEMA = ROOT / "site" / "operator" / "schemas" / "operator_learning_candidate.v1.schema.json"
SW = ROOT / "site" / "operator" / "sw.js"
NODE = shutil.which("node")


def _load_store_harness():
    path = ROOT / "tests" / "test_operator_learning_store.py"
    spec = importlib.util.spec_from_file_location("operator_learning_store_contract", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module.HARNESS


STORE_HARNESS = _load_store_harness()


def _learning_ui_source():
    source = OPERATOR.read_text(encoding="utf-8")
    return source.split("// OPERATOR_LOCAL_LEARNING_1836_START", 1)[1].split(
        "// OPERATOR_LOCAL_LEARNING_1836_END", 1
    )[0]


DOM_HARNESS = r"""
class FakeClassList {
  constructor(owner) { this.owner = owner; }
  toggle(name, enabled) {
    const names = new Set(String(this.owner.className || "").split(/\s+/).filter(Boolean));
    if (enabled) names.add(name); else names.delete(name);
    this.owner.className = [...names].join(" ");
  }
}

function datasetName(raw) {
  return raw.replace(/-([a-z])/g, (_, letter) => letter.toUpperCase());
}

function matchesSelector(node, selector) {
  if (!node || node.nodeType !== 1) return false;
  let candidate = selector.trim();
  const checked = candidate.endsWith(":checked");
  if (checked) candidate = candidate.slice(0, -8);
  if (checked && !node.checked) return false;
  const tag = /^([a-z][a-z0-9-]*)/i.exec(candidate)?.[1];
  if (tag && node.tagName !== tag.toUpperCase()) return false;
  const className = /\.([A-Za-z0-9_-]+)/.exec(candidate)?.[1];
  if (className && !String(node.className || "").split(/\s+/).includes(className)) return false;
  for (const match of candidate.matchAll(/\[([A-Za-z0-9_-]+)="([^"]*)"\]/g)) {
    const [, attribute, expected] = match;
    const actual = attribute.startsWith("data-")
      ? node.dataset[datasetName(attribute.slice(5))]
      : node[attribute];
    if (String(actual ?? "") !== expected) return false;
  }
  return Boolean(tag || className || candidate.startsWith("["));
}

class FakeText {
  constructor(text) { this.nodeType = 3; this.textContent = String(text); this.parentNode = null; }
}

class FakeElement {
  constructor(tagName, ownerDocument) {
    this.nodeType = 1;
    this.tagName = String(tagName).toUpperCase();
    this.ownerDocument = ownerDocument;
    this.children = [];
    this.parentNode = null;
    this.dataset = {};
    this.className = "";
    this.classList = new FakeClassList(this);
    this.value = "";
    this.checked = false;
    this.disabled = false;
    this.hidden = false;
    this.required = false;
    this.name = "";
    this.type = "";
    this.dir = "";
    this._id = "";
    this._text = "";
    this.listeners = {};
  }
  set id(value) {
    this._id = String(value);
    if (this._id) this.ownerDocument.byId.set(this._id, this);
  }
  get id() { return this._id; }
  set textContent(value) { this._text = String(value ?? ""); this.children = []; }
  get textContent() { return this._text + this.children.map((child) => child.textContent || "").join(""); }
  appendChild(child) {
    const node = typeof child === "string" ? new FakeText(child) : child;
    node.parentNode = this;
    this.children.push(node);
    return node;
  }
  append(...items) { items.forEach((item) => this.appendChild(item)); }
  replaceChildren(...items) {
    this.children.forEach((child) => { child.parentNode = null; });
    this.children = [];
    this._text = "";
    this.append(...items);
  }
  querySelectorAll(selector) {
    const found = [];
    const visit = (node) => {
      for (const child of node.children || []) {
        if (matchesSelector(child, selector)) found.push(child);
        visit(child);
      }
    };
    visit(this);
    return found;
  }
  querySelector(selector) { return this.querySelectorAll(selector)[0] || null; }
  addEventListener(type, callback) { (this.listeners[type] ||= []).push(callback); }
  focus() { this.ownerDocument.focused = this; }
  click() { (this.listeners.click || []).forEach((callback) => callback({target: this})); }
  remove() {
    if (!this.parentNode) return;
    this.parentNode.children = this.parentNode.children.filter((child) => child !== this);
    this.parentNode = null;
  }
  checkValidity() { return true; }
  reportValidity() { return true; }
  reset() {
    for (const node of this.querySelectorAll("input")) { node.value = ""; node.checked = false; }
    for (const node of this.querySelectorAll("textarea")) node.value = "";
    for (const node of this.querySelectorAll("select")) node.value = "";
  }
}

class FakeDocument {
  constructor() {
    this.byId = new Map();
    this.createdTags = [];
    this.body = new FakeElement("body", this);
    this.focused = null;
  }
  createElement(tagName) {
    this.createdTags.push(String(tagName).toUpperCase());
    return new FakeElement(tagName, this);
  }
  createTextNode(text) { return new FakeText(text); }
  getElementById(id) { return this.byId.get(id) || null; }
  querySelectorAll(selector) { return this.body.querySelectorAll(selector); }
}

const document = new FakeDocument();
const window = {confirm: () => true};
const $ = (id) => document.getElementById(id);
function opText(key, parameters = {}) {
  return String(key).replace(/\{([A-Za-z][A-Za-z0-9_]*)\}/g, (_, name) => String(parameters[name] ?? `{${name}}`));
}
function setOperatorMessage(target, key, parameters = {}) {
  const node = typeof target === "string" ? $(target) : target;
  node.textContent = opText(key, parameters);
  node.dataset.opMessageKey = key;
  node.dataset.opMessageParameters = JSON.stringify(parameters);
}
function compactText(raw, limit = 520) {
  const text = String(raw || "").replace(/\s+/g, " ").trim();
  return text.length <= limit ? text : `${text.slice(0, limit - 1)}…`;
}
function value(id) { return String($(id)?.value || ""); }
function sha256Hex(value) { return crypto.createHash("sha256").update(String(value), "utf8").digest("hex"); }

const learningModel = model;
const learningStoreModel = storage;
let learningAdapter = null;
let learningEntries = [];
let learningSignalCount = 3;
let learningCandidateSequence = 0;
let activeLearningCaseRevision = null;
let selectedLearningCandidateId = null;
let learningStorageFailure = null;
let preparedDraftReady = false;
let currentCaseMetadata = {};
let claims = [];
let evidence = [];

function addElement(id, tagName, parent) {
  const node = document.createElement(tagName || "div");
  node.id = id;
  (parent || document.body).appendChild(node);
  return node;
}

const workspace = addElement("learning_workspace", "section");
const form = addElement("learning_form", "form", workspace);
const formFields = addElement("learning_form_fields", "fieldset", form);
formFields.disabled = true;
addElement("learning_signals", "div", formFields);
addElement("learning_diagnosis_evidence", "div", formFields);
for (const [id, tag] of [
  ["case_id", "input"], ["core_version_ref", "input"],
  ["learning_outcome", "textarea"], ["learning_diagnosis", "textarea"],
  ["learning_gap", "textarea"], ["learning_action_change", "textarea"],
  ["learning_action_reason", "textarea"], ["learning_action_criterion", "textarea"],
  ["learning_metric_clarity", "input"], ["learning_metric_verifiability", "input"],
  ["learning_metric_viability", "input"], ["learning_metric_time", "input"],
  ["learning_metric_open_points", "input"], ["learning_decision", "select"],
  ["learning_next_experiment", "textarea"], ["learning_creation_note", "textarea"]
]) addElement(id, tag, formFields);

for (const category of [
  "ambiguity", "weak_verification", "misaligned_incentives", "wrong_sequence",
  "political_overload", "spoilers", "information_asymmetry"
]) {
  const input = addElement(`category_${category}`, "input", formFields);
  input.type = "checkbox";
  input.name = "learning_category";
  input.value = category;
}
for (const id of [
  "learning_closure_final_text", "learning_closure_verifier", "learning_closure_scope",
  "learning_closure_open_points", "learning_closure_minimum_patch"
]) {
  const input = addElement(id, "input", formFields);
  input.type = "checkbox";
}

addElement("learning_status", "p", workspace);
addElement("learning_store_count", "p", workspace);
addElement("learning_records", "div", workspace);
const inspector = addElement("learning_inspector", "section", workspace);
inspector.hidden = true;
addElement("learning_inspector_summary", "div", inspector);
addElement("learning_history", "div", inspector);
addElement("learning_state_note", "textarea", inspector);
addElement("learning_accept", "button", inspector);
addElement("learning_reject", "button", inspector);
addElement("learning_return_draft", "button", inspector);
addElement("learning_json", "pre", inspector);
"""


def _run_ui_harness(body: str):
    assert NODE, "Node.js is required for Operator learning UI tests"
    script = (
        STORE_HARNESS
        + DOM_HARNESS
        + "\neval(process.env.LEARNING_UI);\n"
        + "\n(async () => {\n"
        + body
        + "\n})().catch((error) => { console.error(error); process.exit(1); });\n"
    )
    completed = subprocess.run(
        [NODE, "-e", script],
        check=False,
        capture_output=True,
        text=True,
        env={
            **os.environ,
            "LEARNING_MODEL": str(MODEL),
            "LEARNING_STORE": str(STORE),
            "LEARNING_UI": _learning_ui_source(),
        },
    )
    assert completed.returncode == 0, completed.stderr
    return completed.stdout


def test_learning_workspace_is_fifth_visible_localized_accessible_step():
    source = OPERATOR.read_text(encoding="utf-8")
    product = source.index('id="product_intake"')
    learning = source.index('id="learning_workspace"')
    advanced = source.index('id="advanced_operator_console"')
    assert product < learning < advanced
    assert 'data-operator-primary-step="5"' in source
    assert 'id="learning_workspace"' in source and 'id="learning_workspace" hidden' not in source
    assert 'id="learning_form_fields" disabled' in source
    assert 'id="learning_json" lang="en" dir="ltr"' in source
    assert 'id="learning_inspector" aria-labelledby="learning_inspector_title" tabindex="-1"' in source
    assert 'id="learning_import_file" type="file" accept="application/json,.json"' in source
    assert "learningModel.limits.maxImportBytes" in source

    required_fields = [
        "learning_outcome", "learning_diagnosis", "learning_gap",
        "learning_action_change", "learning_action_reason", "learning_action_criterion",
        "learning_metric_clarity", "learning_metric_verifiability", "learning_metric_viability",
        "learning_decision", "learning_next_experiment", "learning_creation_note",
        "learning_state_note",
    ]
    for field_id in required_fields:
        assert re.search(rf'<label[^>]+for="{re.escape(field_id)}"', source), field_id
    for field_id in [
        "learning_outcome", "learning_diagnosis", "learning_gap", "learning_action_change",
        "learning_action_reason", "learning_action_criterion", "learning_next_experiment",
        "learning_creation_note", "learning_state_note",
    ]:
        assert re.search(rf'id="{field_id}"[^>]+dir="auto"', source), field_id

    css = source.split("<style>", 1)[1].split("</style>", 1)[0]
    learning_css = css.split(".learning-panel", 1)[1]
    assert "@media (max-width: 560px)" in learning_css
    assert "grid-template-columns: 1fr" in learning_css
    assert "border-inline-start" in learning_css
    assert ".learning-file input" in learning_css
    assert "min-block-size: 2.75rem" in learning_css


def test_learning_scripts_schema_and_offline_assets_are_versioned_in_order():
    source = OPERATOR.read_text(encoding="utf-8")
    assert source.index("./i18n.v1.js") < source.index("./learning-candidate.v1.js")
    assert source.index("./learning-candidate.v1.js") < source.index("./learning-store.v1.js")
    assert source.index("./learning-store.v1.js") < source.index("const $ =")
    service_worker = SW.read_text(encoding="utf-8")
    assert 'hub-optimus-operator-v0-26' in service_worker
    for asset in (
        './learning-candidate.v1.js',
        './learning-store.v1.js',
        './schemas/operator_learning_candidate.v1.schema.json',
    ):
        assert f'"{asset}"' in service_worker
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    assert schema["properties"]["schema_version"]["const"] == "operator_learning_candidate.v1"


def test_learning_labels_have_exact_six_locale_parity_and_rtl_is_preserved():
    assert NODE
    script = r"""
const fs = require("fs");
const vm = require("vm");
vm.runInThisContext(fs.readFileSync(process.env.I18N, "utf8"));
const catalog = globalThis.HUB_OPTIMUS_OPERATOR_I18N;
const keys = [
  "learningTitle", "learningBoundary", "learningOutcomeLabel", "learningSignalsLegend",
  "learningDiagnosisLegend", "learningActionLegend", "learningMetricsLegend",
  "learningClosureLegend", "learningCreationNoteLabel", "learningRecordsTitle",
  "learningInspectorTitle", "learningHistoryTitle", "learningJsonTitle",
  "learningFreshnessCurrent", "learningFreshnessStale", "learningFreshnessInvalid"
];
if (JSON.stringify(catalog.supportedLocales) !== JSON.stringify(["en","es","de","ru","he","zh-Hans"])) throw new Error("locale set drifted");
for (const locale of catalog.supportedLocales) {
  for (const key of keys) if (!catalog.messages[locale][key]) throw new Error(`${locale}.${key} missing`);
}
if (catalog.localeMeta.he.dir !== "rtl") throw new Error("Hebrew direction drifted");
"""
    completed = subprocess.run(
        [NODE, "-e", script],
        capture_output=True,
        text=True,
        env={**os.environ, "I18N": str(I18N)},
        check=False,
    )
    assert completed.returncode == 0, completed.stderr


def test_learning_ui_lock_create_store_reload_transition_import_and_invalidation():
    _run_ui_harness(
        r"""
const factory = new FakeIndexedDB();
globalThis.indexedDB = factory;
await initializeLearningWorkspace();
if (!formFields.disabled) throw new Error("learning form unlocked without a source-bound draft");
for (const host of ["http://127.1", "http://0177.0.0.1", "http://0x7f.0.0.1", "http://2130706433"]) {
  if (safeLearningSourceRef(host) !== "") throw new Error(`ambiguous numeric host accepted: ${host}`);
}

$("case_id").value = caseRecord.case_id;
$("core_version_ref").value = caseRecord.core_version_ref;
claims = clone(caseRecord.claims);
evidence = clone(caseRecord.evidence);
currentCaseMetadata = {
  normalizer_version: "operator-source-bound-v1",
  relationships: clone(caseRecord.relationships)
};
preparedDraftReady = true;
refreshLearningAvailability();
if (formFields.disabled) throw new Error("current source-bound draft did not unlock learning form");
if (!currentLearningCaseRecord()?.revision_sha256.match(/^[0-9a-f]{64}$/)) throw new Error("live case revision was not built");

$("learning_outcome").value = "<img src=x onerror=globalThis.injected=true> The reviewed outcome remains unverified.";
$("learning_diagnosis").value = "The reviewed material has a verification gap.";
$("learning_gap").value = "No independent verifier is recorded.";
$("learning_action_change").value = "Name one verifier.";
$("learning_action_reason").value = "Make the next review inspectable.";
$("learning_action_criterion").value = "The next draft names the verifier.";
$("learning_metric_clarity").value = "3";
$("learning_metric_verifiability").value = "2";
$("learning_metric_viability").value = "4";
$("learning_metric_time").value = "12.5";
$("learning_metric_open_points").value = "1";
$("learning_decision").value = "repeat_same_scenario";
$("learning_next_experiment").value = "Repeat once with the named verifier.";
$("learning_creation_note").value = "Created after explicit human review.";
    document.querySelectorAll('input[name="learning_category"]')[0].checked = true;
$("learning_diagnosis_evidence").querySelector('input[data-learning-ref="evidence"]').checked = true;
for (const signal of document.querySelectorAll(".learning-signal")) {
  signal.querySelector("textarea").value = "A human-observed signal linked to the current source.";
  signal.querySelector('input[data-learning-ref="claim"]').checked = true;
  signal.querySelector('input[data-learning-ref="evidence"]').checked = true;
}
for (const id of [
  "learning_closure_final_text", "learning_closure_verifier", "learning_closure_scope",
  "learning_closure_open_points", "learning_closure_minimum_patch"
]) $(id).checked = true;

await createLearningCandidate();
if (learningEntries.length !== 1) throw new Error("candidate was not stored");
const candidateId = learningEntries[0].candidate_id;
const created = learningEntries[0].entry.candidate;
if (created.state !== "draft" || created.history.length !== 1) throw new Error("creation changed human state");
if (created.nodes.filter((node) => node.node_type === "signal").length !== 3) throw new Error("signal graph count drifted");
if (!created.relations.some((edge) => edge.type === "SIGNAL_REFERENCES_CLAIM")
  || !created.relations.some((edge) => edge.type === "SIGNAL_GROUNDED_IN_EVIDENCE")) throw new Error("exact source links missing");
renderLearningInspector(candidateId);
if (document.createdTags.includes("IMG") || globalThis.injected) throw new Error("imported text reached an HTML sink");
if (!$("learning_json").textContent.includes("<img src=x")) throw new Error("technical JSON did not preserve text safely");

const secondAdapter = storage.createAdapter({indexedDB: factory, model, hashText: sha256Hex});
if ((await secondAdapter.list()).entries.length !== 1) throw new Error("reload lost IndexedDB candidate");

$("learning_state_note").value = "Accepted locally after checking the current source links.";
await transitionLearningCandidate("accepted");
const acceptedEntry = learningEntries.find((entry) => entry.candidate_id === candidateId);
if (acceptedEntry.entry.candidate.state !== "accepted" || acceptedEntry.entry.candidate.history.length !== 2) throw new Error("explicit acceptance did not append history");
const exported = await learningAdapter.export(candidateId, {expectations: learningExpectations(acceptedEntry)});

const storedDigest = acceptedEntry.candidate_sha256;
evidence[0].text += " Material change.";
const staleBinding = displayedLearningBinding(acceptedEntry);
if (staleBinding.freshness !== "stale") throw new Error(`expected stale, got ${staleBinding.freshness}`);
const unchanged = await learningAdapter.get(candidateId);
if (unchanged.entry.candidate.state !== "accepted" || unchanged.candidate_sha256 !== storedDigest) throw new Error("freshness rewrote human state");
preparedDraftReady = false;
if (displayedLearningBinding(acceptedEntry).freshness !== "invalid") throw new Error("missing live draft was not invalid");
refreshLearningAvailability();
if (!formFields.disabled) throw new Error("source invalidation did not relock authoring");
if ($("learning_outcome").value !== "") throw new Error("new case could inherit stale authoring text");

preparedDraftReady = true;
await deleteLearningCandidate(candidateId);
if (learningEntries.length !== 0) throw new Error("confirmed delete failed");
const importText = JSON.stringify(exported);
await importLearningCandidate({size: Buffer.byteLength(importText), text: async () => importText});
if (learningEntries.length !== 1 || learningEntries[0].entry.candidate.state !== "accepted") throw new Error("validated import did not preserve state/history");
const reloaded = await secondAdapter.list();
if (reloaded.entries.length !== 1) throw new Error("import was not durable");
await importLearningCandidate({size: Buffer.byteLength(importText), text: async () => importText});
if (learningEntries.length !== 1 || $("learning_status").dataset.opMessageKey !== "learningCandidateConflict") throw new Error("existing import ID did not fail as an explicit conflict");
"""
    )


def test_learning_ui_notes_and_mutations_are_bound_to_the_presented_entry():
    _run_ui_harness(
        r"""
const factory = new FakeIndexedDB();
globalThis.indexedDB = factory;
await initializeLearningWorkspace();

$("case_id").value = caseRecord.case_id;
$("core_version_ref").value = caseRecord.core_version_ref;
claims = clone(caseRecord.claims);
evidence = clone(caseRecord.evidence);
currentCaseMetadata = {
  normalizer_version: "operator-source-bound-v1",
  relationships: clone(caseRecord.relationships)
};
preparedDraftReady = true;

async function insertDraft(candidateId) {
  const candidate = buildCandidate(candidateId);
  return learningAdapter.upsert(
    {candidate, binding: binding(candidate)},
    absentExpectations()
  );
}

async function rejectExternally(adapter, candidateId, note) {
  const latest = await adapter.get(candidateId);
  const rejected = model.transitionCandidate(
    latest.entry.candidate,
    "rejected",
    note,
    {hashText, now: "2026-08-01T12:20:00.000Z"}
  );
  return adapter.upsert(
    {candidate: rejected, binding: binding(rejected)},
    expectations(latest)
  );
}

await insertDraft("learning-ui-note-a");
await insertDraft("learning-ui-note-b");
await reloadLearningEntries();
renderLearningInspector("learning-ui-note-a");
$("learning_state_note").value = "Note intended only for candidate A.";
renderLearningInspector("learning-ui-note-b");
if ($("learning_state_note").value !== "") throw new Error("transition note leaked from A to B");
$("learning_state_note").value = "Draft note for candidate B.";
renderLearningInspector("learning-ui-note-b");
if ($("learning_state_note").value !== "Draft note for candidate B.") {
  throw new Error("same-candidate localized rerender erased the operator note");
}

const rival = storage.createAdapter({indexedDB: factory, model, hashText});
renderLearningInspector("learning-ui-note-a");
const shownA = presentedLearningEntry("learning-ui-note-a");
const rejectedA = await rejectExternally(rival, "learning-ui-note-a", "Rejected in another tab.");
const returnedA = model.transitionCandidate(
  rejectedA.entry.entry.candidate,
  "draft",
  "Returned to draft in another tab.",
  {hashText, now: "2026-08-01T12:21:00.000Z"}
);
await rival.upsert(
  {candidate: returnedA, binding: binding(returnedA)},
  expectations(rejectedA.entry)
);
if (shownA.entry_sha256 === (await rival.get("learning-ui-note-a")).entry_sha256) {
  throw new Error("stale-view transition fixture did not change the entry digest");
}
$("learning_state_note").value = "Accept only the version I inspected.";
await transitionLearningCandidate("accepted");
await new Promise((resolve) => setTimeout(resolve, 40));
const afterTransition = await rival.get("learning-ui-note-a");
if (afterTransition.entry.candidate.state !== "draft" || afterTransition.entry.candidate.history.length !== 3) {
  throw new Error("stale visible draft was accepted");
}
if ($("learning_status").dataset.opMessageKey !== "learningCandidateConflict") {
  throw new Error("stale transition did not surface a conflict");
}
if (selectedLearningCandidateId !== null || !$("learning_inspector").hidden || $("learning_state_note").value !== "") {
  throw new Error("conflict did not force a clean reinspection");
}

await insertDraft("learning-ui-export-stale");
await reloadLearningEntries();
await rejectExternally(rival, "learning-ui-export-stale", "Export target changed elsewhere.");
let objectUrlCreated = false;
URL.createObjectURL = () => { objectUrlCreated = true; return "blob:unexpected"; };
URL.revokeObjectURL = () => {};
await exportLearningCandidate("learning-ui-export-stale");
await new Promise((resolve) => setTimeout(resolve, 40));
if (objectUrlCreated) throw new Error("stale visible candidate was exported");
if ($("learning_status").dataset.opMessageKey !== "learningCandidateConflict") {
  throw new Error("stale export did not surface a conflict");
}

await insertDraft("learning-ui-delete-stale");
await reloadLearningEntries();
await rejectExternally(rival, "learning-ui-delete-stale", "Delete target changed elsewhere.");
await deleteLearningCandidate("learning-ui-delete-stale");
await new Promise((resolve) => setTimeout(resolve, 40));
const afterDelete = await rival.get("learning-ui-delete-stale");
if (!afterDelete || afterDelete.entry.candidate.state !== "rejected") {
  throw new Error("stale visible candidate was deleted");
}
if ($("learning_status").dataset.opMessageKey !== "learningCandidateConflict") {
  throw new Error("stale delete did not surface a conflict");
}
"""
    )


def test_learning_ui_async_actions_do_not_retarget_or_clear_another_candidate():
    _run_ui_harness(
        r"""
const factory = new FakeIndexedDB();
globalThis.indexedDB = factory;
await initializeLearningWorkspace();

function buildForCase(candidateId, record) {
  return model.buildCandidate({
    candidate_id: candidateId,
    case_record: record,
    outcome: "A source-bound draft was prepared; the reported condition remains unverified.",
    signals: [
      {text: "The submitted text states a condition.", claim_refs: ["claim-001"], evidence_refs: ["evidence-001"]},
      {text: "The source does not name an independent verifier.", claim_refs: ["claim-001"], evidence_refs: ["evidence-001"]},
      {text: "The next review step is not established.", claim_refs: ["claim-001"], evidence_refs: ["evidence-001"]}
    ],
    diagnosis: {text: "The draft exposes a verification gap.", categories: ["weak_verification"], evidence_refs: ["evidence-001"]},
    gap: "No accountable verifier is recorded.",
    action: {change: "Add a verification owner.", reason: "Make follow-up inspectable.", verification_criterion: "A reviewer can identify the owner."},
    metrics: [{name: "clarity", value: 3}, {name: "verifiability", value: 1}, {name: "viability", value: 3}],
    iteration_decision: "repeat_same_scenario",
    next_experiment: "Prepare the same case with a named verifier.",
    closure_check: {final_text: true, verification_owner: true, scope_and_deadlines: true, open_points: true, minimum_patch: true},
    creation_note: "Recorded manually after reviewing the draft."
  }, {hashText, now: "2026-08-01T12:00:00.000Z"});
}

const candidateA = buildCandidate("learning-ui-async-a");
const candidateB = buildCandidate("learning-ui-async-b");
await learningAdapter.upsert({candidate: candidateA, binding: binding(candidateA)}, absentExpectations());
await learningAdapter.upsert({candidate: candidateB, binding: binding(candidateB)}, absentExpectations());
await reloadLearningEntries();

$("case_id").value = caseRecord.case_id;
$("core_version_ref").value = caseRecord.core_version_ref;
claims = clone(caseRecord.claims);
evidence = clone(caseRecord.evidence);
currentCaseMetadata = {normalizer_version: "operator-source-bound-v1", relationships: clone(caseRecord.relationships)};
preparedDraftReady = true;

const realUpsert = learningAdapter.upsert.bind(learningAdapter);
let releaseUpsert;
let markUpsertEntered;
const upsertEntered = new Promise((resolve) => { markUpsertEntered = resolve; });
const upsertGate = new Promise((resolve) => { releaseUpsert = resolve; });
let gateNextUpsert = true;
learningAdapter.upsert = async (...args) => {
  if (gateNextUpsert) {
    gateNextUpsert = false;
    markUpsertEntered();
    await upsertGate;
  }
  return realUpsert(...args);
};

renderLearningInspector(candidateA.candidate_id);
$("learning_state_note").value = "Accept A after reviewing A.";
const transition = transitionLearningCandidate("accepted");
await upsertEntered;
renderLearningInspector(candidateB.candidate_id);
$("learning_state_note").value = "UNSAVED NOTE FOR B";
releaseUpsert();
await transition;
if (selectedLearningCandidateId !== candidateB.candidate_id || $("learning_state_note").value !== "UNSAVED NOTE FOR B") {
  throw new Error("completion of A cleared or retargeted B's unsaved note");
}
if ((await learningAdapter.get(candidateA.candidate_id)).entry.candidate.state !== "accepted") {
  throw new Error("the captured transition target A was not updated");
}

const caseA = clone(caseRecord);
caseA.case_id = "operator-case-delete-a";
caseA.revision_sha256 = model.computeCaseRevision(caseA, {hashText});
const caseB = clone(caseRecord);
caseB.case_id = "operator-case-delete-b";
caseB.revision_sha256 = model.computeCaseRevision(caseB, {hashText});
const deleteA = buildForCase("learning-ui-delete-case-a", caseA);
const keepB = buildForCase("learning-ui-delete-case-b", caseB);
await learningAdapter.upsert(
  {candidate: deleteA, binding: model.evaluateFreshness(deleteA, caseA, {hashText})},
  absentExpectations()
);
await learningAdapter.upsert(
  {candidate: keepB, binding: model.evaluateFreshness(keepB, caseB, {hashText})},
  absentExpectations()
);
await reloadLearningEntries();

const realList = learningAdapter.list.bind(learningAdapter);
let releaseList;
let markListEntered;
const listEntered = new Promise((resolve) => { markListEntered = resolve; });
const listGate = new Promise((resolve) => { releaseList = resolve; });
let gateNextList = true;
learningAdapter.list = async () => {
  if (gateNextList) {
    gateNextList = false;
    markListEntered();
    await listGate;
  }
  return realList();
};

renderLearningInspector(deleteA.candidate_id);
const deletion = deleteLearningCase();
await listEntered;
renderLearningInspector(keepB.candidate_id);
$("learning_state_note").value = "UNSAVED NOTE FOR OTHER CASE B";
releaseList();
await deletion;
if (await learningAdapter.get(deleteA.candidate_id)) throw new Error("captured case A was not deleted");
if (!(await learningAdapter.get(keepB.candidate_id))) throw new Error("selection race retargeted deletion to case B");
if (selectedLearningCandidateId !== keepB.candidate_id || $("learning_state_note").value !== "UNSAVED NOTE FOR OTHER CASE B") {
  throw new Error("case A deletion cleared or hid case B's unsaved note");
}
"""
    )


def _function_slice(source: str, name: str, next_name: str):
    return source.split(f"function {name}", 1)[1].split(f"function {next_name}", 1)[0]


def test_learning_data_has_no_payload_memory_share_hash_or_network_path():
    source = OPERATOR.read_text(encoding="utf-8")
    for name, next_name in (
        ("buildPayload", "setActive"),
        ("buildMemoryRecord", "renderMemoryStatus"),
        ("buildHumanShareText", "shareMemoryLink"),
        ("readControlledUrlText", "currentShareableMemory"),
    ):
        block = _function_slice(source, name, next_name).lower()
        assert "learningcandidate" not in block
        assert "candidate_id" not in block
        assert "learning_status" not in block

    learning_ui = _learning_ui_source()
    assert "fetch(" not in learning_ui
    assert "xmlhttprequest" not in learning_ui.lower()
    assert "sendbeacon" not in learning_ui.lower()
    assert "websocket" not in learning_ui.lower()
    assert "localstorage" not in learning_ui.lower()
    assert "buildShareSnapshot" not in learning_ui
    assert "buildPayload" not in learning_ui
    assert "buildMemoryRecord" not in learning_ui
