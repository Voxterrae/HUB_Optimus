import hashlib
import json
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "site" / "operator" / "learning-candidate.v1.js"
SCHEMA = (
    ROOT
    / "site"
    / "operator"
    / "schemas"
    / "operator_learning_candidate.v1.schema.json"
)
METHOD = ROOT / "v1_core" / "workflow" / "05_meta_learning.md"
RFC = ROOT / "docs" / "rfc" / "operator_local_learning_candidate.md"
NODE = shutil.which("node")


def run_model_smoke(body: str):
    assert NODE, "Node.js is required for Operator learning model tests"
    harness = r"""
const fs = require("fs");
const vm = require("vm");
const crypto = require("crypto");
vm.runInThisContext(fs.readFileSync(process.env.LEARNING_MODULE, "utf8"));
const api = globalThis.HUB_OPTIMUS_LEARNING_CANDIDATE_V1;
const hashText = (value) => crypto.createHash("sha256").update(value, "utf8").digest("hex");

const caseRecord = {
  case_id: "operator-case-001",
  core_version_ref: "v1",
  revision_sha256: "",
  claims: [{
    claim_id: "claim-001",
    text: "The source states that review is delayed.",
    source_ref: "operator-source-001"
  }],
  evidence: [{
    evidence_id: "evidence-001",
    text: "The extracted source contains the submitted delay statement.",
    source_ref: "operator-source-001",
    limitations: ["Attribution only; not independent corroboration."]
  }],
  relationships: [{
    type: "SUPPORTS_ATTRIBUTION",
    from_ref: "evidence-001",
    to_ref: "claim-001"
  }]
};
caseRecord.revision_sha256 = api.computeCaseRevision(caseRecord, {hashText});

function build(overrides = {}) {
  return api.buildCandidate({
    candidate_id: "learning-00000000-0000-4000-8000-000000000001",
    case_record: caseRecord,
    outcome: "A source-bound local draft was prepared; the reported delay remains unverified.",
    signals: [
      {text: "The submitted text describes a delay.", claim_refs: ["claim-001"], evidence_refs: ["evidence-001"]},
      {text: "The source does not identify an independent verifier.", claim_refs: ["claim-001"], evidence_refs: ["evidence-001"]},
      {text: "The next escalation step is not defined in the submitted material.", claim_refs: ["claim-001"], evidence_refs: ["evidence-001"]}
    ],
    diagnosis: {
      text: "The draft exposes a verification and sequencing gap.",
      categories: ["weak_verification", "wrong_sequence"],
      evidence_refs: ["evidence-001"]
    },
    gap: "No accountable verifier or escalation sequence is recorded.",
    action: {
      change: "Add one named verification owner and one escalation deadline.",
      reason: "This is the smallest change that makes follow-up inspectable.",
      verification_criterion: "A reviewer can identify both the owner and deadline in the next draft."
    },
    metrics: [
      {name: "clarity", value: 3},
      {name: "verifiability", value: 1},
      {name: "open_points", value: 2}
    ],
    iteration_decision: "repeat_same_scenario",
    next_experiment: "Prepare the same case with a named verifier and deadline, then compare metrics.",
    closure_check: {
      final_text: true,
      verification_owner: true,
      scope_and_deadlines: true,
      open_points: true,
      minimum_patch: true
    },
    creation_note: "Recorded manually after reviewing the draft.",
    ...overrides
  }, {hashText, now: "2026-08-01T12:00:00.000Z"});
}
"""
    completed = subprocess.run(
        [NODE, "-e", harness + body],
        check=False,
        capture_output=True,
        text=True,
        env={"LEARNING_MODULE": str(MODULE)},
    )
    assert completed.returncode == 0, completed.stderr
    return completed.stdout


def test_learning_schema_is_strict_versioned_and_bound_to_repository_method():
    import jsonschema

    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    method_digest = hashlib.sha256(METHOD.read_bytes()).hexdigest()

    jsonschema.Draft202012Validator.check_schema(schema)

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["additionalProperties"] is False
    assert schema["properties"]["schema_version"]["const"] == (
        "operator_learning_candidate.v1"
    )
    assert schema["properties"]["authority"]["const"] == "local-non-canonical"
    assert schema["properties"]["method_ref"]["properties"]["sha256"]["const"] == (
        method_digest
    )
    assert schema["properties"]["state"]["enum"] == [
        "draft",
        "accepted",
        "rejected",
    ]
    assert schema["properties"]["nodes"]["allOf"][4]["minContains"] == 3
    assert schema["properties"]["nodes"]["allOf"][4]["maxContains"] == 10
    assert schema["$defs"]["relation"]["properties"]["origin"]["enum"] == [
        "human-authored",
        "imported",
    ]
    assert schema["$defs"]["signal_node"]["properties"]["claim_refs"][
        "allOf"
    ][1]["minItems"] == 1

    for name, definition in schema["$defs"].items():
        if definition.get("type") == "object":
            assert definition.get("additionalProperties") is False, name


def test_learning_builder_produces_a_valid_connected_human_draft():
    import jsonschema

    output = run_model_smoke(
        r"""
const candidate = build();
const validation = api.validateCandidate(candidate, {hashText});
if (!validation.valid) throw new Error(JSON.stringify(validation.errors));
if (candidate.state !== "draft" || candidate.authority !== "local-non-canonical") {
  throw new Error("builder promoted authority or state");
}
if (candidate.nodes.filter((node) => node.node_type === "signal").length !== 3) {
  throw new Error("signal count changed");
}
if (!candidate.relations.some((edge) => edge.type === "ACTION_ADDRESSES_GAP")) {
  throw new Error("action is disconnected from the diagnosed gap");
}
if (candidate.relations.some((edge) => edge.origin === "system-suggested")) {
  throw new Error("v1 builder invented a system suggestion");
}
process.stdout.write(JSON.stringify(candidate));
"""
    )
    candidate = json.loads(output)
    validator = jsonschema.Draft202012Validator(
        json.loads(SCHEMA.read_text(encoding="utf-8")),
        format_checker=jsonschema.FormatChecker(),
    )
    validator.validate(candidate)
    assert candidate["history"] == [
        {
            "action": "created",
            "actor": "human-operator",
            "at_utc": "2026-08-01T12:00:00.000Z",
            "event_id": "history:001",
            "from_state": None,
            "note": "Recorded manually after reviewing the draft.",
            "to_state": "draft",
        }
    ]


def test_learning_schema_and_runtime_require_complete_closure_for_acceptance():
    import jsonschema

    accepted = json.loads(
        run_model_smoke(
            r"""
const candidate = build();
const accepted = api.transitionCandidate(
  candidate,
  "accepted",
  "Accepted after an explicit local review.",
  {hashText, liveCase: caseRecord, now: "2026-08-01T12:05:00.000Z"}
);
process.stdout.write(JSON.stringify(accepted));
"""
        )
    )
    validator = jsonschema.Draft202012Validator(
        json.loads(SCHEMA.read_text(encoding="utf-8")),
        format_checker=jsonschema.FormatChecker(),
    )
    validator.validate(accepted)

    incomplete = json.loads(json.dumps(accepted))
    incomplete["closure_check"]["minimum_patch"] = False
    assert list(validator.iter_errors(incomplete))

    run_model_smoke(
        r"""
const accepted = api.transitionCandidate(
  build(),
  "accepted",
  "Accepted after an explicit local review.",
  {hashText, liveCase: caseRecord, now: "2026-08-01T12:05:00.000Z"}
);
accepted.closure_check.minimum_patch = false;
if (api.validateCandidate(accepted, {hashText}).valid) {
  throw new Error("runtime accepted incomplete closure");
}
"""
    )


def test_learning_builder_rejects_non_json_input_without_coercion():
    run_model_smoke(
        r"""
const statefulOutcome = {
  calls: 0,
  toString() {
    this.calls += 1;
    return "coerced outcome";
  }
};
try {
  build({outcome: statefulOutcome});
  throw new Error("stateful outcome was accepted");
} catch (error) {
  if (!`${error.message}`.includes("plain JSON")) throw error;
}
if (statefulOutcome.calls !== 0) throw new Error("builder coerced stateful outcome input");

for (const [label, value] of [
  ["object outcome", {}],
  ["numeric signal", 42],
  ["object metric name", {}]
]) {
  try {
    if (label === "object outcome") build({outcome: value});
    if (label === "numeric signal") {
      const candidateSignals = [
        {text: value, claim_refs: ["claim-001"], evidence_refs: ["evidence-001"]},
        {text: "signal two", claim_refs: ["claim-001"], evidence_refs: ["evidence-001"]},
        {text: "signal three", claim_refs: ["claim-001"], evidence_refs: ["evidence-001"]}
      ];
      build({signals: candidateSignals});
    }
    if (label === "object metric name") {
      build({metrics: [{name: value, value: 1}, {name: "clarity", value: 1}, {name: "open_points", value: 1}]});
    }
    throw new Error(`${label} was coerced`);
  } catch (error) {
    if (!`${error.message}`.includes("shape")) throw error;
  }
}
const candidate = build();
const statefulNow = {
  calls: 0,
  toString() {
    this.calls += 1;
    return "2026-08-01T12:10:00.000Z";
  }
};
for (const operation of [
  () => api.transitionCandidate(candidate, "rejected", "Rejected.", {hashText, now: statefulNow}),
  () => api.evaluateFreshness(candidate, caseRecord, {hashText, now: statefulNow}),
  () => api.createExport(candidate, {hashText, now: statefulNow})
]) {
  try { operation(); throw new Error("stateful timestamp was accepted"); }
  catch (error) { if (!`${error.message}`.includes("timestamp")) throw error; }
}
if (statefulNow.calls !== 0) throw new Error("model coerced a stateful timestamp");
"""
    )


def test_learning_validator_rejects_tampering_dangling_edges_and_wrong_signatures():
    run_model_smoke(
        r"""
function mustFail(mutator, needle) {
  const candidate = build();
  mutator(candidate);
  const validation = api.validateCandidate(candidate, {hashText});
  if (validation.valid || !validation.errors.some((item) => `${item.path} ${item.message}`.includes(needle))) {
    throw new Error(`expected failure containing ${needle}: ${JSON.stringify(validation.errors)}`);
  }
}
mustFail((candidate) => { candidate.unexpected = true; }, "top-level");
mustFail((candidate) => { candidate.nodes[1].node_id = candidate.nodes[0].node_id; }, "duplicate node ID");
mustFail((candidate) => { candidate.nodes[1].text = "tampered"; }, "canonical text");
mustFail((candidate) => { candidate.relations[0].to_ref = "missing:node"; }, "dangling");
mustFail((candidate) => { candidate.relations[0].to_ref = "claim:claim-001"; }, "signature mismatch");
mustFail((candidate) => { candidate.nodes.find((node) => node.node_type === "diagnosis").categories = ["automatic_truth_score"]; }, "categories");
mustFail((candidate) => { candidate.metrics[1].name = "clarity"; }, "duplicate metric");
mustFail((candidate) => { candidate.candidate_id = "learning-"; }, "learning-*");
mustFail((candidate) => { candidate.candidate_id = `learning-${"a".repeat(500)}`; }, "learning-*");
mustFail((candidate) => { candidate.created_at_utc = "2026-02-30T12:00:00Z"; }, "timestamp");
mustFail((candidate) => {
  const diagnosis = candidate.nodes.find((node) => node.node_type === "diagnosis");
  diagnosis.signal_refs.pop();
}, "every signal");
mustFail((candidate) => {
  candidate.relations = candidate.relations.filter((edge) => !["SUPPORTS_ATTRIBUTION", "SUPPORTS_CLAIM", "CONTRADICTS_CLAIM"].includes(edge.type));
}, "evidence-to-claim");
mustFail((candidate) => {
  const edge = candidate.relations.find((item) => item.type === "DIAGNOSIS_INTERPRETS_SIGNAL");
  edge.origin = "system-suggested";
}, "forbidden in v1");
mustFail((candidate) => {
  candidate.relations.find((edge) => edge.type === "SUPPORTS_ATTRIBUTION").origin = "human-authored";
}, "must be imported");
mustFail((candidate) => {
  candidate.relations.find((edge) => edge.type === "ACTION_ADDRESSES_GAP").origin = "imported";
}, "must be human-authored");
mustFail((candidate) => {
  const actionEdge = candidate.relations.find((edge) => edge.type === "ACTION_ADDRESSES_GAP");
  actionEdge.epistemic_status = "inference";
}, "must be proposal");
mustFail((candidate) => {
  candidate.nodes.find((node) => node.node_type === "signal").claim_refs = [];
  candidate.relations = candidate.relations.filter((edge) => edge.type !== "SIGNAL_REFERENCES_CLAIM" || edge.from_ref !== "signal:001");
}, "claim reference");
mustFail((candidate) => {
  candidate.created_at_utc = "2026-08-01T11:59:00.000Z";
}, "first history event");
mustFail((candidate) => {
  candidate.updated_at_utc = "2026-08-01T12:30:00.000Z";
}, "last history event");
mustFail((candidate) => {
  const claim = candidate.nodes.find((node) => node.node_type === "claim");
  claim.text = "\ud800";
  claim.text_sha256 = hashText("\ufffd");
}, "Unicode safety");
mustFail((candidate) => {
  const evidenceNode = candidate.nodes.find((node) => node.node_type === "evidence");
  const extraEvidence = {...evidenceNode, node_id: "evidence:evidence-002", record_id: "evidence-002"};
  candidate.nodes.push(extraEvidence);
  candidate.relations.push({
    relation_id: "relation:999",
    type: "DIAGNOSIS_REFERENCES_EVIDENCE",
    from_ref: "diagnosis:001",
    to_ref: extraEvidence.node_id,
    origin: "human-authored",
    epistemic_status: "inference"
  });
}, "not declared");
"""
    )


def test_learning_source_references_are_redacted_and_canonical_text_is_stable():
    output = run_model_smoke(
        r"""
const privateCase = JSON.parse(JSON.stringify(caseRecord));
privateCase.claims[0].text = "Cafe\u0301\r\nline two";
privateCase.claims[0].source_ref = "https://Example.COM:443/private/case?token=secret#fragment";
privateCase.evidence[0].source_ref = "https://example.com/another/private/path?session=hidden";
privateCase.revision_sha256 = api.computeCaseRevision(privateCase, {hashText});
const candidate = build({case_record: privateCase});
const claim = candidate.nodes.find((node) => node.node_type === "claim");
const evidence = candidate.nodes.find((node) => node.node_type === "evidence");
if (claim.text !== "Café\nline two") throw new Error("text was not normalized to NFC/LF");
if (claim.source_ref !== "https://example.com" || evidence.source_ref !== "https://example.com") {
  throw new Error("source URL was not reduced to its origin");
}
const serialized = api.stableStringify(candidate);
if (serialized.includes("token") || serialized.includes("secret") || serialized.includes("/private") || serialized.includes("session")) {
  throw new Error("sensitive URL components leaked into the learning candidate");
}
let rejected = false;
try {
  const unsafeOpaque = JSON.parse(JSON.stringify(caseRecord));
  unsafeOpaque.claims[0].source_ref = "private?token=secret";
  unsafeOpaque.revision_sha256 = api.computeCaseRevision(unsafeOpaque, {hashText});
  build({case_record: unsafeOpaque});
} catch (error) {
  rejected = `${error.message}`.includes("source_ref");
}
if (!rejected) throw new Error("unsafe opaque source reference was accepted");
for (const privateOrigin of ["http://localhost/private", "http://192.168.1.10/secret", "http://127.1/admin", "http://[::1]/admin"]) {
  let privateRejected = false;
  try {
    const unsafePrivate = JSON.parse(JSON.stringify(caseRecord));
    unsafePrivate.claims[0].source_ref = privateOrigin;
    unsafePrivate.revision_sha256 = api.computeCaseRevision(unsafePrivate, {hashText});
    build({case_record: unsafePrivate});
  } catch (error) {
    privateRejected = `${error.message}`.includes("source_ref");
  }
  if (!privateRejected) throw new Error(`private source origin was accepted: ${privateOrigin}`);
}
process.stdout.write(serialized);
"""
    )
    assert "token" not in output
    assert "secret" not in output
    assert "/private" not in output


def test_learning_source_reference_schema_and_runtime_reject_the_same_private_forms():
    import jsonschema

    candidate = json.loads(
        run_model_smoke(
            r"""
const candidate = build();
for (const unsafe of [
  "http://localhost",
  "https://service.internal",
  "https://home.arpa",
  "http://192.168.1.10",
  "https://Example.COM",
  "https://example.com:8443"
]) {
  const mutated = JSON.parse(JSON.stringify(candidate));
  mutated.nodes.find((node) => node.node_type === "claim").source_ref = unsafe;
  if (api.validateCandidate(mutated, {hashText}).valid) {
    throw new Error(`runtime accepted unsafe source ref: ${unsafe}`);
  }
}
process.stdout.write(JSON.stringify(candidate));
"""
        )
    )
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    validator = jsonschema.Draft202012Validator(
        schema,
        format_checker=jsonschema.FormatChecker(),
    )
    claim = next(node for node in candidate["nodes"] if node["node_type"] == "claim")
    claim_index = candidate["nodes"].index(claim)

    for unsafe in (
        "http://localhost",
        "https://service.internal",
        "https://home.arpa",
        "http://192.168.1.10",
        "https://Example.COM",
        "https://example.com:8443",
    ):
        mutated = json.loads(json.dumps(candidate))
        mutated["nodes"][claim_index]["source_ref"] = unsafe
        assert list(validator.iter_errors(mutated)), unsafe

    surrogate = json.loads(json.dumps(candidate))
    surrogate["nodes"][claim_index]["text"] = "\ud800"
    assert list(validator.iter_errors(surrogate))

    wrong_source_origin = json.loads(json.dumps(candidate))
    next(
        edge
        for edge in wrong_source_origin["relations"]
        if edge["type"] == "SUPPORTS_ATTRIBUTION"
    )["origin"] = "human-authored"
    assert list(validator.iter_errors(wrong_source_origin))

    wrong_learning_origin = json.loads(json.dumps(candidate))
    next(
        edge
        for edge in wrong_learning_origin["relations"]
        if edge["type"] == "ACTION_ADDRESSES_GAP"
    )["origin"] = "imported"
    assert list(validator.iter_errors(wrong_learning_origin))

    validator.validate(candidate)


def test_learning_state_machine_requires_current_freshness_and_human_notes():
    run_model_smoke(
        r"""
const candidate = build();
function mustThrow(callback, needle) {
  try { callback(); } catch (error) {
    if (`${error.message}`.includes(needle)) return;
    throw error;
  }
  throw new Error(`expected error containing ${needle}`);
}
const changedLiveCase = JSON.parse(JSON.stringify(caseRecord));
changedLiveCase.claims[0].text = "The source text changed after the candidate was created.";
changedLiveCase.revision_sha256 = api.computeCaseRevision(changedLiveCase, {hashText});
mustThrow(() => api.transitionCandidate(candidate, "accepted", "reviewed", {hashText, freshness: "current", liveCase: changedLiveCase}), "current");
mustThrow(() => api.transitionCandidate(candidate, "accepted", "", {hashText, liveCase: caseRecord}), "note");
const incompleteClosure = build({closure_check: {
  final_text: true,
  verification_owner: false,
  scope_and_deadlines: true,
  open_points: true,
  minimum_patch: true
}});
mustThrow(() => api.transitionCandidate(incompleteClosure, "accepted", "reviewed", {hashText, liveCase: caseRecord}), "closure checks");
const accepted = api.transitionCandidate(candidate, "accepted", "Human review accepted this local candidate.", {hashText, liveCase: caseRecord, now: "2026-08-01T12:05:00.000Z"});
if (accepted.state !== "accepted" || candidate.state !== "draft") throw new Error("transition mutated its input or failed");
const forgedIncompleteAcceptance = JSON.parse(JSON.stringify(accepted));
forgedIncompleteAcceptance.closure_check.minimum_patch = false;
if (api.validateCandidate(forgedIncompleteAcceptance, {hashText}).valid) throw new Error("accepted candidate bypassed closure checks during validation");
const nonSequentialId = build();
nonSequentialId.history[0].event_id = "history:002";
if (!api.validateCandidate(nonSequentialId, {hashText}).valid) throw new Error("non-sequential imported history ID did not reproduce");
const acceptedWithoutCollision = api.transitionCandidate(nonSequentialId, "accepted", "Accepted after reviewing imported history.", {hashText, liveCase: caseRecord, now: "2026-08-01T12:05:00.000Z"});
if (acceptedWithoutCollision.history[1].event_id !== "history:003") throw new Error("history event ID did not advance from the numeric maximum");
mustThrow(() => api.transitionCandidate(accepted, "rejected", "direct flip", {hashText}), "Forbidden");
const bypass = JSON.parse(JSON.stringify(accepted));
bypass.state = "rejected";
bypass.updated_at_utc = "2026-08-01T12:06:00.000Z";
bypass.history.push({event_id: "history:003", at_utc: bypass.updated_at_utc, actor: "human-operator", action: "created", from_state: "accepted", to_state: "rejected", note: "Attempted bypass."});
if (api.validateCandidate(bypass, {hashText}).valid) throw new Error("created event bypassed the state machine");
const draftAgain = api.transitionCandidate(accepted, "draft", "Returned for revision.", {hashText, now: "2026-08-01T12:06:00.000Z"});
const rejected = api.transitionCandidate(draftAgain, "rejected", "Human review rejected this revision.", {hashText, now: "2026-08-01T12:07:00.000Z"});
if (rejected.state !== "rejected" || rejected.history.length !== 4) throw new Error("history was not preserved");
"""
    )


def test_learning_freshness_changes_without_rewriting_human_state():
    run_model_smoke(
        r"""
const candidate = build();
const current = api.evaluateFreshness(candidate, caseRecord, {hashText, now: "2026-08-01T12:01:00.000Z"});
if (current.freshness !== "current" || candidate.state !== "draft") throw new Error("current binding failed");
const changed = JSON.parse(JSON.stringify(caseRecord));
changed.claims[0].text = "The current claim text changed.";
changed.revision_sha256 = api.computeCaseRevision(changed, {hashText});
const stale = api.evaluateFreshness(candidate, changed, {hashText, now: "2026-08-01T12:02:00.000Z"});
if (stale.freshness !== "stale" || candidate.state !== "draft") throw new Error("stale changed candidate state");
const forged = JSON.parse(JSON.stringify(caseRecord));
forged.claims[0].text = "Tampered text under the old declared revision.";
const forgedBinding = api.evaluateFreshness(candidate, forged, {hashText, now: "2026-08-01T12:02:30.000Z"});
if (forgedBinding.freshness === "current") throw new Error("forged declared revision was accepted as current");
const missing = {...changed, evidence: []};
missing.revision_sha256 = api.computeCaseRevision(missing, {hashText});
const invalid = api.evaluateFreshness(candidate, missing, {hashText, now: "2026-08-01T12:03:00.000Z"});
if (invalid.freshness !== "invalid" || candidate.state !== "draft") throw new Error("invalid changed candidate state");
"""
    )


def test_case_revision_rejects_non_json_values_before_canonical_hashing():
    run_model_smoke(
        r"""
function mustReject(label, extension) {
  const unsafe = {...caseRecord, extension};
  try {
    api.computeCaseRevision(unsafe, {hashText});
    throw new Error(`${label} was canonicalized instead of rejected`);
  } catch (error) {
    if (!`${error.message}`.includes("case record")) throw error;
  }
}
const nullCase = {...caseRecord, extension: {score: null}};
const missingCase = {...caseRecord, extension: {}};
const nullRevision = api.computeCaseRevision(nullCase, {hashText});
const missingRevision = api.computeCaseRevision(missingCase, {hashText});
if (nullRevision === missingRevision) throw new Error("valid null and missing values shared a revision");
mustReject("NaN", {score: NaN});
mustReject("positive Infinity", {score: Infinity});
mustReject("negative Infinity", {score: -Infinity});
mustReject("undefined", {score: undefined});
mustReject("function", {score: () => 1});
mustReject("symbol", {score: Symbol("score")});
mustReject("bigint", {score: 1n});
mustReject("Date", {score: new Date("2026-08-01T12:00:00Z")});
const sparse = [];
sparse.length = 2;
sparse[1] = "present";
mustReject("sparse array", {score: sparse});
const arrayPrototype = Object.create(Array.prototype);
arrayPrototype.map = () => [];
const customArray = ["Alice"];
Object.setPrototypeOf(customArray, arrayPrototype);
mustReject("custom array prototype", {review_owner: customArray});
const candidate = build();
const customArrayCase = {...caseRecord, extension: customArray};
if (api.evaluateFreshness(candidate, customArrayCase, {hashText, now: "2026-08-01T12:01:00.000Z"}).freshness === "current") {
  throw new Error("custom array prototype was current");
}
customArray[0] = "Mallory";
if (api.evaluateFreshness(candidate, customArrayCase, {hashText, now: "2026-08-01T12:01:01.000Z"}).freshness === "current") {
  throw new Error("mutated custom array prototype was current");
}
const getterObject = {};
Object.defineProperty(getterObject, "review_owner", {enumerable: true, get() { return "Alice"; }});
mustReject("getter", getterObject);
const throwingProxy = new Proxy({}, {ownKeys() { throw new Error("proxy trap"); }});
mustReject("throwing proxy", throwingProxy);
const transparentProxy = new Proxy({review_owner: "Alice"}, {});
mustReject("transparent proxy", transparentProxy);
const proxiedCandidate = new Proxy(candidate, {});
if (api.validateCandidate(proxiedCandidate, {hashText}).valid) {
  throw new Error("transparent candidate Proxy passed validation");
}
if (api.evaluateFreshness(candidate, new Proxy(caseRecord, {}), {hashText, now: "2026-08-01T12:01:01.000Z"}).freshness !== "invalid") {
  throw new Error("transparent live-case Proxy was not invalid");
}
const decomposedKey = {};
decomposedKey["e\u0301"] = "value";
mustReject("non-NFC object key", decomposedKey);
const surrogateKey = {};
surrogateKey["\ud800"] = "value";
mustReject("surrogate object key", surrogateKey);

const inheritedPrototype = {...caseRecord, extension: {review_owner: "Alice"}, constructor: Object};
const inheritedCase = Object.create(inheritedPrototype);
inheritedCase.revision_sha256 = "0".repeat(64);
try {
  api.computeCaseRevision(inheritedCase, {hashText});
  throw new Error("inherited structural case fields were hashed");
} catch (error) {
  if (!`${error.message}`.includes("case record")) throw error;
}
inheritedPrototype.extension.review_owner = "Mallory";
if (api.evaluateFreshness(candidate, inheritedCase, {hashText, now: "2026-08-01T12:01:02.000Z"}).freshness === "current") {
  throw new Error("mutated inherited case was current");
}
try {
  build({case_record: inheritedCase});
  throw new Error("inherited structural case fields entered the builder");
} catch (error) {
  if (!`${error.message}`.includes("plain JSON")) throw error;
}

const customObjectPrototype = {extension: {review_owner: "Alice"}, constructor: Object};
const ownFieldsOnCustomPrototype = Object.assign(Object.create(customObjectPrototype), caseRecord);
if (api.evaluateFreshness(candidate, ownFieldsOnCustomPrototype, {hashText, now: "2026-08-01T12:01:03.000Z"}).freshness === "current") {
  throw new Error("own fields on a custom prototype were current");
}
try {
  api.computeCaseRevision(ownFieldsOnCustomPrototype, {hashText});
  throw new Error("custom object prototype entered the revision hash");
} catch (error) {
  if (!`${error.message}`.includes("case record")) throw error;
}
"""
    )


def test_learning_acceptance_requires_the_embedded_snapshot_to_match_the_live_case():
    run_model_smoke(
        r"""
function assertSnapshotRejected(label, mutate) {
  const candidate = build();
  mutate(candidate);
  const intrinsic = api.validateCandidate(candidate, {hashText});
  if (!intrinsic.valid) throw new Error(`${label} did not reproduce: ${JSON.stringify(intrinsic.errors)}`);
  const binding = api.evaluateFreshness(candidate, caseRecord, {hashText, now: "2026-08-01T12:01:00.000Z"});
  if (binding.freshness === "current") throw new Error(`${label} snapshot was considered current`);
  try {
    api.transitionCandidate(candidate, "accepted", `Reviewed ${label}.`, {hashText, liveCase: caseRecord, now: "2026-08-01T12:02:00.000Z"});
    throw new Error(`${label} snapshot was accepted`);
  } catch (error) {
    if (!`${error.message}`.includes("current")) throw error;
  }
}
assertSnapshotRejected("claim text/hash", (candidate) => {
  const claim = candidate.nodes.find((node) => node.node_type === "claim");
  claim.text = "A different but internally hashed claim.";
  claim.text_sha256 = hashText(claim.text);
});
assertSnapshotRejected("claim source", (candidate) => {
  candidate.nodes.find((node) => node.node_type === "claim").source_ref = "operator-source-002";
});
assertSnapshotRejected("core version", (candidate) => {
  candidate.nodes.find((node) => node.node_type === "case").core_version_ref = "v999";
});
assertSnapshotRejected("evidence limitations", (candidate) => {
  candidate.nodes.find((node) => node.node_type === "evidence").limitations = ["A different limitation."];
});
assertSnapshotRejected("source relation semantics", (candidate) => {
  const relation = candidate.relations.find((edge) => edge.type === "SUPPORTS_ATTRIBUTION");
  relation.type = "SUPPORTS_CLAIM";
  relation.epistemic_status = "corroboration";
});
"""
    )


def test_learning_freshness_returns_invalid_for_malformed_case_collections():
    run_model_smoke(
        r"""
const candidate = build();
for (const [field, value] of [
  ["claims", {}],
  ["evidence", {}],
  ["relationships", {}],
  ["claims", [null]],
  ["evidence", [{evidence_id: "evidence-001"}]],
  ["relationships", [null]]
]) {
  const malformed = JSON.parse(JSON.stringify(caseRecord));
  malformed[field] = value;
  const result = api.evaluateFreshness(candidate, malformed, {
    hashText,
    now: "2026-08-01T12:02:00.000Z"
  });
  if (result.freshness !== "invalid") {
    throw new Error(`${field} malformed collection returned ${result.freshness}`);
  }
  try {
    api.computeCaseRevision(malformed, {hashText});
    throw new Error(`${field} malformed collection was hashed`);
  } catch (error) {
    if (!`${error.message}`.includes("case record")) throw error;
  }
}
"""
    )


def test_learning_export_import_store_limits_conflicts_and_case_delete_are_fail_closed():
    run_model_smoke(
        r"""
const candidate = build();
const binding = api.evaluateFreshness(candidate, caseRecord, {hashText, now: "2026-08-01T12:01:00.000Z"});
const exported = api.createExport(candidate, {hashText, now: "2026-08-01T12:02:00.000Z"});
const imported = api.parseImport(JSON.stringify(exported), {hashText});
if (api.stableStringify(imported) !== api.stableStringify(candidate)) throw new Error("round trip drifted");

let store = api.insertEntry(api.createStore(), {candidate, binding}, {hashText});
if (api.validateStore(store) !== false) throw new Error("store validation succeeded without hash dependency");
const wrongBinding = {...binding, checked_case_sha256: hashText("different revision")};
try {
  api.insertEntry(api.createStore(), {candidate, binding: wrongBinding}, {hashText});
  throw new Error("mismatched current binding was accepted");
} catch (error) {
  if (!`${error.message}`.includes("binding")) throw error;
}
const same = api.insertEntry(store, {candidate, binding}, {hashText});
if (same.entries.length !== 1) throw new Error("exact duplicate was added twice");
const conflicting = JSON.parse(JSON.stringify(candidate));
conflicting.next_experiment = "Different bytes under the same ID.";
try {
  store = api.insertEntry(store, {candidate: conflicting, binding}, {hashText});
  throw new Error("conflict overwrote local record");
} catch (error) {
  if (!`${error.message}`.includes("conflict")) throw error;
}
try {
  api.insertEntry(store, {candidate: build({candidate_id: "learning-00000000-0000-4000-8000-000000000002"}), binding}, {hashText, maxEntries: 1});
  throw new Error("store silently evicted an entry");
} catch (error) {
  if (!`${error.message}`.includes("full")) throw error;
}
let boundedStore = api.createStore();
for (let index = 0; index < 50; index += 1) {
  const item = build({candidate_id: `learning-bounded-${String(index).padStart(3, "0")}`});
  boundedStore = api.insertEntry(boundedStore, {candidate: item, binding}, {hashText, maxEntries: 51});
}
try {
  const item = build({candidate_id: "learning-bounded-050"});
  api.insertEntry(boundedStore, {candidate: item, binding}, {hashText, maxEntries: 51});
  throw new Error("caller expanded the hard 50-entry limit");
} catch (error) {
  if (!`${error.message}`.includes("full")) throw error;
}
const removed = api.deleteCaseEntries(store, "operator-case-001", {hashText});
if (removed.removed !== 1 || removed.store.entries.length !== 0) throw new Error("case cascade failed");

const badChecksum = JSON.parse(JSON.stringify(exported));
badChecksum.candidate_sha256 = "0".repeat(64);
try { api.parseImport(JSON.stringify(badChecksum), {hashText}); throw new Error("bad checksum accepted"); }
catch (error) { if (!`${error.message}`.includes("checksum")) throw error; }
const badVersion = JSON.parse(JSON.stringify(exported));
badVersion.export_version = "operator_learning_export.v999";
try { api.parseImport(JSON.stringify(badVersion), {hashText}); throw new Error("unknown version accepted"); }
catch (error) { if (!`${error.message}`.includes("version")) throw error; }
try { api.createExport(candidate, {hashText, now: "not-a-timestamp"}); throw new Error("invalid export timestamp accepted"); }
catch (error) { if (!`${error.message}`.includes("timestamp")) throw error; }
const deepImport = `{"export_version":"operator_learning_export.v1","candidate_sha256":"${"0".repeat(64)}","exported_at_utc":"2026-08-01T12:00:00.000Z","candidate":${"[".repeat(12000)}null${"]".repeat(12000)}}`;
try { api.parseImport(deepImport, {hashText}); throw new Error("deep import accepted"); }
catch (error) {
  if (error instanceof RangeError || !`${error.message}`.includes("nesting")) throw error;
}
const statefulText = {
  calls: 0,
  toString() {
    this.calls += 1;
    return this.calls === 1 ? "{}" : " ".repeat(api.limits.maxImportBytes + 1) + JSON.stringify(exported);
  }
};
try { api.parseImport(statefulText, {hashText}); throw new Error("non-string import accepted"); }
catch (error) { if (!`${error.message}`.includes("JSON string")) throw error; }
if (statefulText.calls !== 0) throw new Error("import coerced an untrusted object");
"""
    )


def test_learning_store_validation_enforces_the_entry_byte_limit_on_reload():
    run_model_smoke(
        r"""
const largeCase = JSON.parse(JSON.stringify(caseRecord));
largeCase.claims = [];
largeCase.evidence = [];
largeCase.relationships = [];
for (let index = 0; index < 6; index += 1) {
  const suffix = String(index + 1).padStart(3, "0");
  largeCase.claims.push({claim_id: `claim-${suffix}`, text: `claim-${suffix}:` + "x".repeat(19800), source_ref: "operator-source-001"});
  largeCase.evidence.push({evidence_id: `evidence-${suffix}`, text: `evidence-${suffix}:` + "y".repeat(19800), source_ref: "operator-source-001", limitations: ["Human review required."]});
  largeCase.relationships.push({type: "SUPPORTS_ATTRIBUTION", from_ref: `evidence-${suffix}`, to_ref: `claim-${suffix}`});
}
largeCase.revision_sha256 = api.computeCaseRevision(largeCase, {hashText});
const candidate = build({case_record: largeCase});
const binding = api.evaluateFreshness(candidate, largeCase, {hashText, now: "2026-08-01T12:01:00.000Z"});
binding.reason = "r".repeat(20000);
const entry = {candidate, binding};
const candidateBytes = new TextEncoder().encode(api.stableStringify(candidate)).byteLength;
const entryBytes = new TextEncoder().encode(api.stableStringify(entry)).byteLength;
if (candidateBytes > api.limits.maxEntryBytes || entryBytes <= api.limits.maxEntryBytes) {
  throw new Error(`fixture did not straddle entry cap: candidate=${candidateBytes}, entry=${entryBytes}`);
}
const preloaded = {store_version: api.storeVersion, entries: [entry]};
if (api.validateStore(preloaded, {hashText})) throw new Error("oversized preloaded entry passed store validation");
try {
  api.insertEntry(api.createStore(), entry, {hashText});
  throw new Error("oversized new entry passed insertion");
} catch (error) {
  if (!`${error.message}`.includes("size limit")) throw error;
}
"""
    )


def test_learning_candidate_record_limit_is_enforced_before_storage_or_export():
    run_model_smoke(
        r"""
const largeCase = JSON.parse(JSON.stringify(caseRecord));
largeCase.claims = [];
largeCase.evidence = [];
largeCase.relationships = [];
for (let index = 0; index < 8; index += 1) {
  const suffix = String(index + 1).padStart(3, "0");
  largeCase.claims.push({claim_id: `claim-${suffix}`, text: `claim-${suffix}:` + "x".repeat(19900), source_ref: "operator-source-001"});
  largeCase.evidence.push({evidence_id: `evidence-${suffix}`, text: `evidence-${suffix}:` + "y".repeat(19900), source_ref: "operator-source-001", limitations: ["Human review required."]});
  largeCase.relationships.push({type: "SUPPORTS_ATTRIBUTION", from_ref: `evidence-${suffix}`, to_ref: `claim-${suffix}`});
}
largeCase.revision_sha256 = api.computeCaseRevision(largeCase, {hashText});
try {
  build({case_record: largeCase});
  throw new Error("oversized candidate was accepted");
} catch (error) {
  if (!`${error.message}`.includes("256 KiB")) throw error;
}
"""
    )


def test_learning_model_has_no_network_dom_or_automatic_training_path():
    source = MODULE.read_text(encoding="utf-8")

    for forbidden in (
        "fetch(",
        "XMLHttpRequest",
        "WebSocket",
        "sendBeacon",
        "innerHTML",
        "outerHTML",
        "insertAdjacentHTML",
    ):
        assert forbidden not in source

    assert "local-non-canonical" in source
    assert "system-suggested" in source
    assert "system-suggested relations are forbidden in v1" in source
    assert "Only a current candidate can be accepted locally" in source


def test_learning_rfc_marks_model_only_status_and_future_indexeddb_gate():
    text = RFC.read_text(encoding="utf-8")
    prose = " ".join(text.split())

    assert "Model-only prototype contract; not integrated into Operator" in prose
    assert "current Operator UI does not load this module" in prose
    assert "does not persist candidates" in prose
    assert "model-layer adapter uses IndexedDB database" in prose
    assert "additional hard ceiling of 16 MiB" in prose
    assert "Stored bytes are treated as untrusted" in prose
    assert "append-only per candidate ID" in prose
    assert "does not yet expose an edit-in-place API" in prose
