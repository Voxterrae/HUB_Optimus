import json
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "site" / "operator" / "learning-candidate.v1.js"
ADAPTER = ROOT / "site" / "operator" / "learning-store.v1.js"
RFC = ROOT / "docs" / "rfc" / "operator_local_learning_candidate.md"
OPERATOR = ROOT / "site" / "operator" / "index.html"
SERVICE_WORKER = ROOT / "site" / "operator" / "sw.js"
NODE = shutil.which("node")


HARNESS = r"""
const fs = require("fs");
const vm = require("vm");
const crypto = require("crypto");
vm.runInThisContext(fs.readFileSync(process.env.LEARNING_MODEL, "utf8"));
vm.runInThisContext(fs.readFileSync(process.env.LEARNING_STORE, "utf8"));
const model = globalThis.HUB_OPTIMUS_LEARNING_CANDIDATE_V1;
const storage = globalThis.HUB_OPTIMUS_LEARNING_STORE_V1;
const hashText = (value) => crypto.createHash("sha256").update(value, "utf8").digest("hex");

function clone(value) {
  if (value === undefined) return undefined;
  return JSON.parse(JSON.stringify(value));
}

function namedError(name, message) {
  const error = new Error(message || name);
  error.name = name;
  return error;
}

class FakeRequest {
  constructor() {
    this.result = undefined;
    this.error = null;
    this.onsuccess = null;
    this.onerror = null;
    this.onblocked = null;
    this.onupgradeneeded = null;
    this.transaction = null;
  }
}

class FakeTransaction {
  constructor(factory, mode) {
    this.factory = factory;
    this.mode = mode;
    this.error = null;
    this.oncomplete = null;
    this.onabort = null;
    this.onerror = null;
    this.pending = 0;
    this.completed = false;
    this.aborted = false;
    this.completeTimer = null;
    this.operations = [];
    this.started = false;
    this.waitingRequests = [];
    this.working = null;
    factory.enqueueTransaction(this);
  }

  start() {
    if (this.started || this.aborted) return;
    const source = this.factory.state.stores.get("learning_store");
    this.working = new Map([...source.entries()].map(([key, value]) => [key, clone(value)]));
    this.started = true;
    const waiting = this.waitingRequests.splice(0);
    waiting.forEach((execute) => execute());
  }

  objectStore(name) {
    if (name !== "learning_store") throw namedError("NotFoundError");
    return new FakeObjectStore(this);
  }

  request(operation, callback) {
    const request = new FakeRequest();
    this.operations.push(operation);
    this.pending += 1;
    clearTimeout(this.completeTimer);
    const execute = () => setTimeout(() => {
      if (this.aborted) return;
      try {
        request.result = clone(callback());
        if (request.onsuccess) request.onsuccess({target: request});
        this.pending -= 1;
        this.scheduleComplete();
      } catch (error) {
        request.error = error;
        this.error = error;
        if (request.onerror) request.onerror({target: request});
        this.abortInternal(error);
      }
    }, 0);
    if (this.started) execute();
    else this.waitingRequests.push(execute);
    return request;
  }

  scheduleComplete() {
    clearTimeout(this.completeTimer);
    this.completeTimer = setTimeout(() => {
      if (this.pending || this.aborted || this.completed) return;
      if (this.mode === "readwrite") {
        this.factory.state.stores.set(
          "learning_store",
          new Map([...this.working.entries()].map(([key, value]) => [key, clone(value)]))
        );
        this.factory.commitCount += 1;
      }
      this.completed = true;
      this.factory.releaseTransaction(this);
      if (this.oncomplete) this.oncomplete();
    }, 0);
  }

  abortInternal(error) {
    if (this.aborted || this.completed) return;
    clearTimeout(this.completeTimer);
    this.aborted = true;
    this.error = error || this.error;
    this.factory.abortCount += 1;
    this.factory.releaseTransaction(this);
    setTimeout(() => {
      if (this.onerror) this.onerror();
      if (this.onabort) this.onabort();
    }, 0);
  }

  abort() {
    if (this.completed) throw namedError("InvalidStateError");
    this.abortInternal(this.error);
  }
}

class FakeObjectStore {
  constructor(transaction) {
    this.transaction = transaction;
    this.keyPath = transaction.factory.storeKeyPath;
    this.autoIncrement = transaction.factory.storeAutoIncrement;
    this.indexNames = [...transaction.factory.storeIndexNames];
  }

  count() {
    return this.transaction.request("count", () => this.transaction.working.size);
  }

  get(key) {
    return this.transaction.request("get", () => this.transaction.working.get(key));
  }

  put(value, key) {
    return this.transaction.request("put", () => {
      if (this.transaction.mode !== "readwrite") throw namedError("ReadOnlyError");
      if (this.transaction.factory.quotaOnPut) throw namedError("QuotaExceededError");
      this.transaction.working.set(key, clone(value));
      return key;
    });
  }
}

class FakeDatabase {
  constructor(factory) {
    this.factory = factory;
    this.closed = false;
    this.onversionchange = null;
    factory.connections.push(this);
  }

  get objectStoreNames() {
    return [...this.factory.state.stores.keys()];
  }

  createObjectStore(name, options = {}) {
    if (this.factory.state.stores.has(name)) throw namedError("ConstraintError");
    this.factory.storeKeyPath = Object.prototype.hasOwnProperty.call(options, "keyPath")
      ? options.keyPath
      : null;
    this.factory.storeAutoIncrement = options.autoIncrement === true;
    this.factory.storeIndexNames = [];
    const data = new Map();
    this.factory.state.stores.set(name, data);
    return {
      put: (value, key) => {
        data.set(key, clone(value));
        const request = new FakeRequest();
        request.result = key;
        setTimeout(() => request.onsuccess && request.onsuccess({target: request}), 0);
        return request;
      }
    };
  }

  transaction(name, mode) {
    if (this.closed) throw namedError("InvalidStateError");
    if (!this.factory.state.stores.has(name)) throw namedError("NotFoundError");
    const transaction = new FakeTransaction(this.factory, mode);
    this.factory.transactions.push(transaction);
    return transaction;
  }

  close() {
    if (!this.closed) this.factory.closeCount += 1;
    this.closed = true;
  }
}

class FakeIndexedDB {
  constructor() {
    this.state = {version: 0, stores: new Map()};
    this.blocked = false;
    this.continueAfterBlocked = false;
    this.failOpen = null;
    this.quotaOnPut = false;
    this.commitCount = 0;
    this.abortCount = 0;
    this.closeCount = 0;
    this.transactions = [];
    this.connections = [];
    this.lastOpen = null;
    this.storeKeyPath = null;
    this.storeAutoIncrement = false;
    this.storeIndexNames = [];
    this.activeTransaction = null;
    this.transactionQueue = [];
  }

  enqueueTransaction(transaction) {
    if (!this.activeTransaction) {
      this.activeTransaction = transaction;
      transaction.start();
      return;
    }
    this.transactionQueue.push(transaction);
  }

  releaseTransaction(transaction) {
    if (this.activeTransaction !== transaction) {
      this.transactionQueue = this.transactionQueue.filter((item) => item !== transaction);
      return;
    }
    this.activeTransaction = null;
    const next = this.transactionQueue.shift();
    if (next) {
      this.activeTransaction = next;
      next.start();
    }
  }

  open(name, version) {
    const request = new FakeRequest();
    this.lastOpen = {name, version};
    setTimeout(() => {
      if (this.blocked) {
        if (request.onblocked) request.onblocked({target: request});
        if (!this.continueAfterBlocked) return;
      }
      if (this.failOpen) {
        request.error = namedError(this.failOpen);
        if (request.onerror) request.onerror({target: request});
        return;
      }
      if (this.state.version > version) {
        request.error = namedError("VersionError");
        if (request.onerror) request.onerror({target: request});
        return;
      }
      const database = new FakeDatabase(this);
      request.result = database;
      if (this.state.version < version) {
        let upgradeAborted = false;
        request.transaction = {abort() { upgradeAborted = true; }};
        if (request.onupgradeneeded) {
          request.onupgradeneeded({oldVersion: this.state.version, newVersion: version, target: request});
        }
        if (upgradeAborted) {
          request.error = namedError("AbortError");
          if (request.onerror) request.onerror({target: request});
          return;
        }
        this.state.version = version;
      }
      setTimeout(() => request.onsuccess && request.onsuccess({target: request}), 0);
    }, 0);
    return request;
  }

  rawRecord() {
    return clone(this.state.stores.get("learning_store")?.get("operator_learning_store.v1"));
  }

  setRawRecord(value) {
    this.state.stores.get("learning_store").set("operator_learning_store.v1", clone(value));
  }

  addExtraRecord() {
    this.state.stores.get("learning_store").set("unexpected", {bad: true});
  }
}

const caseRecord = {
  case_id: "operator-case-001",
  core_version_ref: "v1",
  revision_sha256: "",
  claims: [{claim_id: "claim-001", text: "The source states that review is delayed.", source_ref: "operator-source-001"}],
  evidence: [{evidence_id: "evidence-001", text: "The extracted source contains the submitted delay statement.", source_ref: "operator-source-001", limitations: ["Attribution only; not independent corroboration."]}],
  relationships: [{type: "SUPPORTS_ATTRIBUTION", from_ref: "evidence-001", to_ref: "claim-001"}]
};
caseRecord.revision_sha256 = model.computeCaseRevision(caseRecord, {hashText});

function buildCandidate(candidateId = "learning-00000000-0000-4000-8000-000000000001") {
  return model.buildCandidate({
    candidate_id: candidateId,
    case_record: caseRecord,
    outcome: "A source-bound local draft was prepared; the reported delay remains unverified.",
    signals: [
      {text: "The submitted text describes a delay.", claim_refs: ["claim-001"], evidence_refs: ["evidence-001"]},
      {text: "The source does not identify an independent verifier.", claim_refs: ["claim-001"], evidence_refs: ["evidence-001"]},
      {text: "The escalation step is not defined.", claim_refs: ["claim-001"], evidence_refs: ["evidence-001"]}
    ],
    diagnosis: {text: "The draft exposes a verification gap.", categories: ["weak_verification"], evidence_refs: ["evidence-001"]},
    gap: "No accountable verifier is recorded.",
    action: {change: "Add a verification owner.", reason: "Make follow-up inspectable.", verification_criterion: "A reviewer can identify the owner."},
    metrics: [{name: "clarity", value: 3}, {name: "verifiability", value: 1}, {name: "open_points", value: 2}],
    iteration_decision: "repeat_same_scenario",
    next_experiment: "Prepare the same case with a named verifier.",
    closure_check: {final_text: true, verification_owner: true, scope_and_deadlines: true, open_points: true, minimum_patch: true},
    creation_note: "Recorded manually after reviewing the draft."
  }, {hashText, now: "2026-08-01T12:00:00.000Z"});
}

function binding(candidate) {
  return model.evaluateFreshness(candidate, caseRecord, {hashText, now: "2026-08-01T12:01:00.000Z"});
}

function expectCode(error, code) {
  if (!error || error.code !== code) throw new Error(`expected ${code}, got ${error?.code}: ${error?.message}`);
}

function absentExpectations() {
  return {
    expectedCandidateSha256: null,
    expectedCaseRevisionSha256: null,
    expectedEntrySha256: null
  };
}

function expectations(presented) {
  return {
    expectedCandidateSha256: presented.candidate_sha256,
    expectedCaseRevisionSha256: presented.case_revision_sha256,
    expectedEntrySha256: presented.entry_sha256
  };
}
"""


def run_store_script(body: str):
    assert NODE, "Node.js is required for Operator learning-store tests"
    script = HARNESS + "\n(async () => {\n" + body + "\n})().catch((error) => { console.error(error); process.exit(1); });\n"
    completed = subprocess.run(
        [NODE, "-e", script],
        check=False,
        capture_output=True,
        text=True,
        env={
            "LEARNING_MODEL": str(MODEL),
            "LEARNING_STORE": str(ADAPTER),
        },
    )
    assert completed.returncode == 0, completed.stderr
    return completed.stdout


def test_learning_store_contract_is_loaded_without_ambient_side_channels():
    source = ADAPTER.read_text(encoding="utf-8")
    rfc = " ".join(RFC.read_text(encoding="utf-8").split())

    assert '"hub_optimus_operator_learning_v1"' in source
    assert "const DB_VERSION = 1" in source
    assert '"operator_learning_store.v1"' in source
    assert "16 * 1024 * 1024" in source
    assert "expectedCandidateSha256" in source
    assert "expectedCaseRevisionSha256" in source
    assert "expectedEntrySha256" in source
    assert "onblocked" in source
    assert "onversionchange" in source
    assert "QuotaExceededError" in source

    for forbidden in (
        "fetch(",
        "XMLHttpRequest",
        "WebSocket",
        "sendBeacon",
        "localStorage",
    ):
        assert forbidden not in source

    operator = OPERATOR.read_text(encoding="utf-8")
    service_worker = SERVICE_WORKER.read_text(encoding="utf-8")
    assert operator.index("learning-candidate.v1.js") < operator.index("learning-store.v1.js")
    assert operator.index("learning-store.v1.js") < operator.index("const $ =")
    assert '"./learning-candidate.v1.js"' in service_worker
    assert '"./learning-store.v1.js"' in service_worker
    assert '"./schemas/operator_learning_candidate.v1.schema.json"' in service_worker
    assert "service worker precaches both modules" in rfc
    assert "additional hard ceiling of 16 MiB" in rfc


def test_learning_store_upgrade_crud_import_export_and_atomic_transactions():
    run_store_script(
        r"""
const factory = new FakeIndexedDB();
const adapter = storage.createAdapter({indexedDB: factory, model, hashText, now: () => "2026-08-01T12:10:00.000Z"});
if (JSON.stringify(storage.errorCodes) !== JSON.stringify(["unavailable", "blocked", "corrupt", "quota", "conflict"])) throw new Error("error taxonomy drifted");
for (const method of ["list", "get", "upsert", "delete", "deleteCase", "clearExplicit", "import", "export"]) {
  if (typeof adapter[method] !== "function") throw new Error(`missing adapter API: ${method}`);
}
const initial = await adapter.list();
if (initial.entries.length !== 0) throw new Error("new store was not empty");
if (factory.lastOpen.name !== storage.dbName || factory.lastOpen.version !== 1) throw new Error("wrong database identity");
if (factory.state.stores.size !== 1 || factory.rawRecord().store_version !== model.storeVersion) throw new Error("upgrade did not create one versioned record");

const candidate = buildCandidate();
const entry = {candidate, binding: binding(candidate)};
const beforeTransactions = factory.transactions.length;
const inserted = await adapter.upsert(entry, absentExpectations());
if (factory.transactions.length !== beforeTransactions + 1) throw new Error("upsert used more than one transaction");
const insertTransaction = factory.transactions.at(-1);
if (insertTransaction.mode !== "readwrite" || insertTransaction.operations.join(",") !== "count,get,put") throw new Error("upsert was not one atomic read-latest transaction");

const fetched = await adapter.get(candidate.candidate_id);
if (!fetched || fetched.candidate_sha256 !== inserted.entry.candidate_sha256) throw new Error("get did not return inserted candidate");
const listed = await adapter.list();
if (listed.entries.length !== 1 || listed.store_sha256 !== inserted.store_sha256) throw new Error("list drifted from stored state");

const replacement = model.transitionCandidate(
  candidate,
  "accepted",
  "Accepted through a pure reviewed-state transition.",
  {hashText, liveCase: caseRecord, now: "2026-08-01T12:09:00.000Z"}
);
const replaced = await adapter.upsert(
  {candidate: replacement, binding: binding(replacement)},
  expectations(fetched)
);
if (replaced.entry.candidate_sha256 === fetched.candidate_sha256) throw new Error("replacement did not change candidate digest");

try {
  await adapter.exportCandidate(candidate.candidate_id);
  throw new Error("export without expected tokens succeeded");
} catch (error) { expectCode(error, "conflict"); }
try {
  await adapter.exportCandidate(candidate.candidate_id, {
    expectations: expectations(fetched)
  });
  throw new Error("export with stale expected tokens succeeded");
} catch (error) { expectCode(error, "conflict"); }
const exported = await adapter.exportCandidate(candidate.candidate_id, {
  expectations: expectations(replaced.entry),
  now: "2026-08-01T12:11:00.000Z"
});
if (exported.export_version !== model.exportVersion) throw new Error("export contract drifted");

await adapter.delete(candidate.candidate_id, {
  ...expectations(replaced.entry)
});
if ((await adapter.list()).entries.length !== 0) throw new Error("explicit candidate delete failed");

const imported = await adapter.importCandidate(
  JSON.stringify(exported),
  binding(replacement),
  absentExpectations()
);
if (imported.entry.candidate_sha256 !== replaced.entry.candidate_sha256) throw new Error("import/export round trip drifted");
const statefulImport = {calls: 0, toString() { this.calls += 1; return JSON.stringify(exported); }};
try {
  await adapter.importCandidate(
    statefulImport,
    binding(replacement),
    expectations(imported.entry)
  );
  throw new Error("non-string adapter import succeeded");
} catch (error) { expectCode(error, "corrupt"); }
if (statefulImport.calls !== 0) throw new Error("adapter coerced non-string import input");
"""
    )


def test_learning_store_conflicts_and_quota_abort_without_lost_updates():
    run_store_script(
        r"""
const factory = new FakeIndexedDB();
const adapter = storage.createAdapter({indexedDB: factory, model, hashText});
await adapter.list();
const candidate = buildCandidate();
const inserted = await adapter.upsert(
  {candidate, binding: binding(candidate)},
  absentExpectations()
);
const committed = JSON.stringify(factory.rawRecord());
const commitCount = factory.commitCount;

try {
  await adapter.upsert(
    {candidate, binding: binding(candidate)},
    {...expectations(inserted.entry), expectedCandidateSha256: "0".repeat(64)}
  );
  throw new Error("stale replacement succeeded");
} catch (error) { expectCode(error, "conflict"); }
if (JSON.stringify(factory.rawRecord()) !== committed || factory.commitCount !== commitCount) throw new Error("conflict changed committed bytes");
if (factory.transactions.at(-1).operations.join(",") !== "count,get") throw new Error("conflict wrote before expected-state check");

try {
  await adapter.delete(candidate.candidate_id, {
    ...expectations(inserted.entry),
    expectedCaseRevisionSha256: "f".repeat(64)
  });
  throw new Error("stale case revision deleted candidate");
} catch (error) { expectCode(error, "conflict"); }
if (JSON.stringify(factory.rawRecord()) !== committed || factory.commitCount !== commitCount) throw new Error("revision conflict changed committed bytes");

factory.quotaOnPut = true;
try {
  await adapter.delete(candidate.candidate_id, {
    ...expectations(inserted.entry)
  });
  throw new Error("quota failure committed deletion");
} catch (error) { expectCode(error, "quota"); }
if (JSON.stringify(factory.rawRecord()) !== committed || factory.commitCount !== commitCount) throw new Error("quota failure was not atomic");

const smallFactory = new FakeIndexedDB();
const smallAdapter = storage.createAdapter({indexedDB: smallFactory, model, hashText, maxAggregateBytes: 1024});
await smallAdapter.list();
try {
  await smallAdapter.upsert(
    {candidate, binding: binding(candidate)},
    absentExpectations()
  );
  throw new Error("aggregate cap accepted oversized store");
} catch (error) { expectCode(error, "quota"); }
if (smallFactory.rawRecord().entries.length !== 0) throw new Error("aggregate cap changed local state");

const fullFactory = new FakeIndexedDB();
const fullAdapter = storage.createAdapter({indexedDB: fullFactory, model, hashText});
await fullAdapter.list();
let fullStore = model.createStore();
for (let index = 0; index < 50; index += 1) {
  const fullCandidate = buildCandidate(`learning-full-${String(index).padStart(3, "0")}`);
  fullStore = model.insertEntry(fullStore, {candidate: fullCandidate, binding: binding(fullCandidate)}, {hashText});
}
fullFactory.setRawRecord(fullStore);
const overflowCandidate = buildCandidate("learning-full-050");
try {
  await fullAdapter.upsert(
    {candidate: overflowCandidate, binding: binding(overflowCandidate)},
    absentExpectations()
  );
  throw new Error("51st candidate was inserted");
} catch (error) { expectCode(error, "quota"); }
if (fullFactory.rawRecord().entries.length !== 50) throw new Error("full-store failure evicted a candidate");
"""
    )


def test_learning_store_rejects_getters_and_proxies_before_serialization():
    run_store_script(
        r"""
const factory = new FakeIndexedDB();
const adapter = storage.createAdapter({indexedDB: factory, model, hashText});
await adapter.list();
const candidate = buildCandidate("learning-unsafe-entry");
const freshness = binding(candidate);
let getterCalls = 0;
const getterEntry = {binding: freshness};
Object.defineProperty(getterEntry, "candidate", {
  enumerable: true,
  get() {
    getterCalls += 1;
    return candidate;
  }
});
try {
  await adapter.upsert(getterEntry, absentExpectations());
  throw new Error("getter entry was accepted");
} catch (error) { expectCode(error, "corrupt"); }
if (getterCalls !== 0) throw new Error("adapter invoked an untrusted entry getter");
if (factory.rawRecord().entries.length !== 0) throw new Error("getter rejection changed storage");

const proxyEntry = new Proxy({candidate, binding: freshness}, {});
try {
  await adapter.upsert(proxyEntry, absentExpectations());
  throw new Error("Proxy entry was accepted");
} catch (error) { expectCode(error, "corrupt"); }
if (factory.rawRecord().entries.length !== 0) throw new Error("Proxy rejection changed storage");

let expectationGetterCalls = 0;
const getterExpectations = {
  expectedCandidateSha256: null,
  expectedCaseRevisionSha256: null
};
Object.defineProperty(getterExpectations, "expectedEntrySha256", {
  enumerable: true,
  get() {
    expectationGetterCalls += 1;
    return null;
  }
});
try {
  await adapter.upsert({candidate, binding: freshness}, getterExpectations);
  throw new Error("getter expectations were accepted");
} catch (error) { expectCode(error, "conflict"); }
if (expectationGetterCalls !== 0) throw new Error("adapter invoked an expectation getter");

const inserted = await adapter.upsert({candidate, binding: freshness}, absentExpectations());
let exportGetterCalls = 0;
const getterExportOptions = {};
Object.defineProperty(getterExportOptions, "expectations", {
  enumerable: true,
  get() {
    exportGetterCalls += 1;
    return expectations(inserted.entry);
  }
});
try {
  await adapter.exportCandidate(candidate.candidate_id, getterExportOptions);
  throw new Error("getter export options were accepted");
} catch (error) { expectCode(error, "conflict"); }
if (exportGetterCalls !== 0) throw new Error("adapter invoked an export-options getter");
"""
    )


def test_learning_store_load_is_fail_closed_for_corruption_blocking_and_unavailability():
    run_store_script(
        r"""
const corruptFactory = new FakeIndexedDB();
const adapter = storage.createAdapter({indexedDB: corruptFactory, model, hashText});
await adapter.list();
const commits = corruptFactory.commitCount;
corruptFactory.setRawRecord({store_version: "operator_learning_store.v999", entries: []});
try { await adapter.list(); throw new Error("corrupt record loaded"); }
catch (error) { expectCode(error, "corrupt"); }
if (corruptFactory.commitCount !== commits) throw new Error("corruption triggered an implicit reset");

corruptFactory.setRawRecord(model.createStore());
corruptFactory.addExtraRecord();
try { await adapter.list(); throw new Error("extra record loaded"); }
catch (error) { expectCode(error, "corrupt"); }

const blockedFactory = new FakeIndexedDB();
blockedFactory.blocked = true;
const blockedAdapter = storage.createAdapter({indexedDB: blockedFactory, model, hashText});
try { await blockedAdapter.list(); throw new Error("blocked open succeeded"); }
catch (error) { expectCode(error, "blocked"); }

const blockedRaceFactory = new FakeIndexedDB();
blockedRaceFactory.blocked = true;
blockedRaceFactory.continueAfterBlocked = true;
const blockedRaceAdapter = storage.createAdapter({indexedDB: blockedRaceFactory, model, hashText});
try { await blockedRaceAdapter.list(); throw new Error("blocked race open succeeded"); }
catch (error) { expectCode(error, "blocked"); }
if (blockedRaceFactory.state.version !== 0 || blockedRaceFactory.state.stores.size !== 0) {
  throw new Error("blocked request mutated the database after rejection");
}

try {
  storage.createAdapter({indexedDB: null, model, hashText});
  throw new Error("missing IndexedDB created an adapter");
} catch (error) { expectCode(error, "unavailable"); }
try {
  storage.createAdapter({indexedDB: new FakeIndexedDB(), model, hashText: () => "0".repeat(64)});
  throw new Error("non-SHA-256 dependency created an adapter");
} catch (error) { expectCode(error, "unavailable"); }

for (const [label, mutateSchema] of [
  ["keyPath", (factory) => { factory.storeKeyPath = "store_version"; }],
  ["autoIncrement", (factory) => { factory.storeAutoIncrement = true; }],
  ["index", (factory) => { factory.storeIndexNames = ["candidate_id"]; }]
]) {
  const schemaFactory = new FakeIndexedDB();
  const schemaAdapter = storage.createAdapter({indexedDB: schemaFactory, model, hashText});
  await schemaAdapter.list();
  mutateSchema(schemaFactory);
  try { await schemaAdapter.list(); throw new Error(`${label} schema opened`); }
  catch (error) { expectCode(error, "corrupt"); }
}

const versionFactory = new FakeIndexedDB();
versionFactory.state.version = 2;
versionFactory.state.stores.set("learning_store", new Map([["operator_learning_store.v1", model.createStore()]]));
const versionAdapter = storage.createAdapter({indexedDB: versionFactory, model, hashText});
try { await versionAdapter.list(); throw new Error("newer database version opened"); }
catch (error) { expectCode(error, "unavailable"); }
"""
    )


def test_learning_store_seals_reviewed_candidate_bytes_and_allows_pure_transitions():
    run_store_script(
        r"""
function expectations(presented) {
  return {
    expectedCandidateSha256: presented.candidate_sha256,
    expectedCaseRevisionSha256: presented.case_revision_sha256,
    expectedEntrySha256: presented.entry_sha256
  };
}
async function expectConflict(callback, label) {
  try { await callback(); throw new Error(`${label} succeeded`); }
  catch (error) { expectCode(error, "conflict"); }
}

const factory = new FakeIndexedDB();
const adapter = storage.createAdapter({indexedDB: factory, model, hashText});
await adapter.list();

const originalDraft = buildCandidate("learning-reviewed-a");
const accepted = model.transitionCandidate(
  originalDraft,
  "accepted",
  "Accepted after explicit review.",
  {hashText, liveCase: caseRecord, now: "2026-08-01T12:02:00.000Z"}
);
const insertedAccepted = await adapter.upsert(
  {candidate: accepted, binding: binding(accepted)},
  absentExpectations()
);

const mutatedAccepted = clone(accepted);
mutatedAccepted.next_experiment = "Changed after acceptance without returning to draft.";
await expectConflict(
  () => adapter.upsert(
    {candidate: mutatedAccepted, binding: binding(mutatedAccepted)},
    expectations(insertedAccepted.entry)
  ),
  "same-state accepted edit"
);
const rewrittenAcceptedHistory = clone(accepted);
rewrittenAcceptedHistory.history[0].note = "Rewritten creation history.";
if (!model.validateCandidate(rewrittenAcceptedHistory, {hashText}).valid) {
  throw new Error("history rewrite fixture was not model-valid");
}
await expectConflict(
  () => adapter.upsert(
    {candidate: rewrittenAcceptedHistory, binding: binding(rewrittenAcceptedHistory)},
    expectations(insertedAccepted.entry)
  ),
  "same-state accepted history rewrite"
);

const invalidBinding = {
  freshness: "invalid",
  checked_case_sha256: null,
  reason: "The live case is not available in this view.",
  checked_at_utc: "2026-08-01T12:03:00.000Z"
};
const bindingOnly = await adapter.upsert(
  {candidate: accepted, binding: invalidBinding},
  expectations(insertedAccepted.entry)
);
if (bindingOnly.entry.candidate_sha256 !== insertedAccepted.entry.candidate_sha256
  || bindingOnly.entry.entry.binding.freshness !== "invalid") {
  throw new Error("binding-only reviewed update failed");
}
await expectConflict(
  () => adapter.upsert(
    {candidate: accepted, binding: binding(accepted)},
    expectations(insertedAccepted.entry)
  ),
  "stale binding-only update"
);

const returnedDraft = model.transitionCandidate(
  accepted,
  "draft",
  "Returned to draft before editing.",
  {hashText, now: "2026-08-01T12:04:00.000Z"}
);
const returned = await adapter.upsert(
  {candidate: returnedDraft, binding: binding(returnedDraft)},
  expectations(bindingOnly.entry)
);
const resetHistoryDraft = buildCandidate("learning-reviewed-a");
if (!model.validateCandidate(resetHistoryDraft, {hashText}).valid) {
  throw new Error("history reset fixture was not model-valid");
}
await expectConflict(
  () => adapter.upsert(
    {candidate: resetHistoryDraft, binding: binding(resetHistoryDraft)},
    expectations(returned.entry)
  ),
  "reviewed history truncation after return to draft"
);
const editedDraft = clone(returnedDraft);
editedDraft.next_experiment = "Attempted edit under the same append-only candidate ID.";
await expectConflict(
  () => adapter.upsert(
    {candidate: editedDraft, binding: binding(editedDraft)},
    expectations(returned.entry)
  ),
  "draft content replacement"
);
const revisedDraft = buildCandidate("learning-reviewed-a-revision-002");
revisedDraft.next_experiment = "Edited content receives a new append-only candidate ID.";
const revisedSaved = await adapter.upsert(
  {candidate: revisedDraft, binding: binding(revisedDraft)},
  absentExpectations()
);
if (revisedSaved.entry.candidate_id === returned.entry.candidate_id) {
  throw new Error("edited draft reused an append-only candidate ID");
}

const sourceDraft = buildCandidate("learning-reviewed-b");
const sourceSaved = await adapter.upsert(
  {candidate: sourceDraft, binding: binding(sourceDraft)},
  absentExpectations()
);
const rebasedDraft = clone(sourceDraft);
const rebasedCase = rebasedDraft.nodes.find((node) => node.node_type === "case");
const rebasedClaim = rebasedDraft.nodes.find((node) => node.node_type === "claim");
rebasedCase.revision_sha256 = hashText("different live-case revision");
rebasedClaim.text = "Different source claim embedded under the same candidate ID.";
rebasedClaim.text_sha256 = hashText(rebasedClaim.text);
const rebasedBinding = {
  freshness: "current",
  checked_case_sha256: rebasedCase.revision_sha256,
  reason: "Forged current binding for the rebased snapshot fixture.",
  checked_at_utc: "2026-08-01T12:04:30.000Z"
};
if (!model.validateCandidate(rebasedDraft, {hashText}).valid) {
  throw new Error("provenance rebase fixture was not model-valid");
}
await expectConflict(
  () => adapter.upsert(
    {candidate: rebasedDraft, binding: rebasedBinding},
    expectations(sourceSaved.entry)
  ),
  "draft provenance rebase"
);
const pureAccepted = model.transitionCandidate(
  sourceDraft,
  "accepted",
  "Accepted without bundled edits.",
  {hashText, liveCase: caseRecord, now: "2026-08-01T12:05:00.000Z"}
);
const acceptedSaved = await adapter.upsert(
  {candidate: pureAccepted, binding: binding(pureAccepted)},
  expectations(sourceSaved.entry)
);
if (acceptedSaved.entry.entry.candidate.state !== "accepted") {
  throw new Error("pure draft-to-accepted transition failed");
}

const bundledAcceptance = model.transitionCandidate(
  buildCandidate("learning-reviewed-c"),
  "accepted",
  "Transition fixture.",
  {hashText, liveCase: caseRecord, now: "2026-08-01T12:05:00.000Z"}
);
const bundledDraft = buildCandidate("learning-reviewed-c");
const bundledDraftSaved = await adapter.upsert(
  {candidate: bundledDraft, binding: binding(bundledDraft)},
  absentExpectations()
);
bundledAcceptance.next_experiment = "Bundled content edit.";
await expectConflict(
  () => adapter.upsert(
    {candidate: bundledAcceptance, binding: binding(bundledAcceptance)},
    expectations(bundledDraftSaved.entry)
  ),
  "bundled draft-to-accepted edit"
);

const bundledReturn = model.transitionCandidate(
  pureAccepted,
  "draft",
  "Return fixture.",
  {hashText, now: "2026-08-01T12:06:00.000Z"}
);
bundledReturn.next_experiment = "Bundled return edit.";
await expectConflict(
  () => adapter.upsert(
    {candidate: bundledReturn, binding: binding(bundledReturn)},
    expectations(acceptedSaved.entry)
  ),
  "bundled accepted-to-draft edit"
);
const rewrittenReturn = model.transitionCandidate(
  pureAccepted,
  "draft",
  "Return fixture.",
  {hashText, now: "2026-08-01T12:06:00.000Z"}
);
rewrittenReturn.history[0].note = "Rewritten history prefix.";
if (!model.validateCandidate(rewrittenReturn, {hashText}).valid) {
  throw new Error("prefix rewrite fixture was not model-valid");
}
await expectConflict(
  () => adapter.upsert(
    {candidate: rewrittenReturn, binding: binding(rewrittenReturn)},
    expectations(acceptedSaved.entry)
  ),
  "rewritten reviewed-to-draft history prefix"
);

const rejectedDraft = buildCandidate("learning-reviewed-d");
const rejectedDraftSaved = await adapter.upsert(
  {candidate: rejectedDraft, binding: binding(rejectedDraft)},
  absentExpectations()
);
const rejected = model.transitionCandidate(
  rejectedDraft,
  "rejected",
  "Rejected after review.",
  {hashText, now: "2026-08-01T12:07:00.000Z"}
);
const rejectedSaved = await adapter.upsert(
  {candidate: rejected, binding: binding(rejected)},
  expectations(rejectedDraftSaved.entry)
);
const mutatedRejected = clone(rejected);
mutatedRejected.next_experiment = "Changed after rejection.";
await expectConflict(
  () => adapter.upsert(
    {candidate: mutatedRejected, binding: binding(mutatedRejected)},
    expectations(rejectedSaved.entry)
  ),
  "same-state rejected edit"
);
"""
    )


def test_learning_store_serializes_concurrent_readwrite_transactions():
    run_store_script(
        r"""
const factory = new FakeIndexedDB();
const adapter = storage.createAdapter({indexedDB: factory, model, hashText});
await adapter.list();
const left = buildCandidate("learning-concurrent-left");
const right = buildCandidate("learning-concurrent-right");
const results = await Promise.all([
  adapter.upsert(
    {candidate: left, binding: binding(left)},
    absentExpectations()
  ),
  adapter.upsert(
    {candidate: right, binding: binding(right)},
    absentExpectations()
  )
]);
if (results.length !== 2 || (await adapter.list()).entries.length !== 2) {
  throw new Error("serialized concurrent inserts lost an entry");
}

const sameFactory = new FakeIndexedDB();
const sameAdapter = storage.createAdapter({indexedDB: sameFactory, model, hashText});
await sameAdapter.list();
const sameA = buildCandidate("learning-concurrent-same");
const sameB = clone(sameA);
sameB.next_experiment = "A competing draft under the same candidate ID.";
const settled = await Promise.allSettled([
  sameAdapter.upsert(
    {candidate: sameA, binding: binding(sameA)},
    absentExpectations()
  ),
  sameAdapter.upsert(
    {candidate: sameB, binding: binding(sameB)},
    absentExpectations()
  )
]);
if (settled.filter((item) => item.status === "fulfilled").length !== 1
  || settled.filter((item) => item.status === "rejected" && item.reason?.code === "conflict").length !== 1
  || (await sameAdapter.list()).entries.length !== 1) {
  throw new Error(`same-ID concurrency was not serialized: ${JSON.stringify(settled)}`);
}

const orderedFactory = new FakeIndexedDB();
const orderedAdapter = storage.createAdapter({indexedDB: orderedFactory, model, hashText});
await orderedAdapter.list();
const orderedCandidate = buildCandidate("learning-concurrent-ordered");
const pendingWrite = orderedAdapter.upsert(
  {candidate: orderedCandidate, binding: binding(orderedCandidate)},
  absentExpectations()
);
const pendingRead = orderedAdapter.list();
const [, orderedRead] = await Promise.all([pendingWrite, pendingRead]);
if (orderedRead.entries.length !== 1
  || orderedRead.entries[0].candidate_id !== orderedCandidate.candidate_id) {
  throw new Error("readonly transaction overtook an earlier readwrite transaction");
}
"""
    )


def test_learning_store_case_delete_and_clear_require_exact_explicit_snapshots():
    run_store_script(
        r"""
const factory = new FakeIndexedDB();
const adapter = storage.createAdapter({indexedDB: factory, model, hashText});
await adapter.list();
for (const id of ["learning-case-a", "learning-case-b"]) {
  const candidate = buildCandidate(id);
  await adapter.upsert(
    {candidate, binding: binding(candidate)},
    absentExpectations()
  );
}
const before = await adapter.list();
try {
  await adapter.deleteCase("operator-case-001", [before.entries[0]]);
  throw new Error("partial case expectation deleted records");
} catch (error) { expectCode(error, "conflict"); }
if ((await adapter.list()).entries.length !== 2) throw new Error("case conflict changed records");

const expected = before.entries.map((item) => ({
  candidate_id: item.candidate_id,
  candidate_sha256: item.candidate_sha256,
  case_revision_sha256: item.case_revision_sha256,
  entry_sha256: item.entry_sha256
}));
const deleted = await adapter.deleteCase("operator-case-001", expected);
if (deleted.removed !== 2 || (await adapter.list()).entries.length !== 0) throw new Error("atomic case delete failed");

const candidate = buildCandidate("learning-clear-a");
await adapter.upsert(
  {candidate, binding: binding(candidate)},
  absentExpectations()
);
const populated = await adapter.list();
try {
  await adapter.clearExplicit("yes", populated.store_sha256);
  throw new Error("weak confirmation cleared store");
} catch (error) { expectCode(error, "conflict"); }
try {
  await adapter.clearExplicit(storage.clearConfirmation, "0".repeat(64));
  throw new Error("stale store digest cleared store");
} catch (error) { expectCode(error, "conflict"); }
const cleared = await adapter.clearExplicit(storage.clearConfirmation, populated.store_sha256);
if (cleared.removed !== 1 || (await adapter.list()).entries.length !== 0) throw new Error("explicit clear failed");
"""
    )
