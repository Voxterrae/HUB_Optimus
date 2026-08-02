(() => {
  "use strict";

  const DB_NAME = "hub_optimus_operator_learning_v1";
  const DB_VERSION = 1;
  const OBJECT_STORE_NAME = "learning_store";
  const RECORD_KEY = "operator_learning_store.v1";
  const STORE_VERSION = "operator_learning_store.v1";
  const MAX_AGGREGATE_BYTES = 16 * 1024 * 1024;
  const CLEAR_CONFIRMATION = "DELETE ALL LOCAL LEARNING CANDIDATES";
  const SHA256_TEST_VECTORS = Object.freeze([
    Object.freeze(["", "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"]),
    Object.freeze(["abc", "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"])
  ]);
  const REVIEWED_STATES = new Set(["accepted", "rejected"]);
  const CLOSURE_KEYS = Object.freeze([
    "final_text",
    "verification_owner",
    "scope_and_deadlines",
    "open_points",
    "minimum_patch"
  ]);
  const ERROR_CODES = Object.freeze([
    "unavailable",
    "blocked",
    "corrupt",
    "quota",
    "conflict"
  ]);

  class LearningStoreError extends Error {
    constructor(code, message, cause) {
      super(message);
      this.name = "LearningStoreError";
      this.code = ERROR_CODES.includes(code) ? code : "corrupt";
      if (cause !== undefined) this.cause = cause;
    }
  }

  function classified(error, fallback = "corrupt") {
    if (error instanceof LearningStoreError) return error;
    const name = String(error?.name || "");
    if (name === "QuotaExceededError") {
      return new LearningStoreError("quota", "IndexedDB quota prevented the learning-store write", error);
    }
    if (["VersionError", "InvalidStateError", "NotSupportedError", "SecurityError"].includes(name)) {
      return new LearningStoreError("unavailable", "IndexedDB is unavailable for the learning store", error);
    }
    return new LearningStoreError(fallback, "The local learning store operation failed closed", error);
  }

  function requestResult(request, fallback = "corrupt") {
    return new Promise((resolve, reject) => {
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(classified(request.error, fallback));
    });
  }

  function transactionCompletion(transaction) {
    return new Promise((resolve, reject) => {
      transaction.oncomplete = () => resolve();
      transaction.onabort = () => reject(classified(transaction.error, "corrupt"));
      transaction.onerror = () => {};
    });
  }

  function objectStoreNames(database) {
    const names = [];
    for (let index = 0; index < database.objectStoreNames.length; index += 1) {
      names.push(database.objectStoreNames[index]);
    }
    return names;
  }

  function indexNames(objectStore) {
    const names = [];
    for (let index = 0; index < objectStore.indexNames.length; index += 1) {
      names.push(objectStore.indexNames[index]);
    }
    return names;
  }

  function hasExpectedObjectStoreSchema(objectStore) {
    try {
      return objectStore.keyPath === null
        && objectStore.autoIncrement === false
        && indexNames(objectStore).length === 0;
    } catch {
      return false;
    }
  }

  function exactKeys(value, keys) {
    if (!value || typeof value !== "object" || Array.isArray(value)) return false;
    const actual = Object.keys(value).sort();
    const expected = [...keys].sort();
    return actual.length === expected.length
      && actual.every((key, index) => key === expected[index]);
  }

  function isSha256(value) {
    return typeof value === "string" && /^[0-9a-f]{64}$/.test(value);
  }

  function isCandidateId(value) {
    return typeof value === "string" && /^learning-[A-Za-z0-9._:-]+$/.test(value) && value.length <= 128;
  }

  function boundedAggregateLimit(value) {
    if (value === undefined) return MAX_AGGREGATE_BYTES;
    if (!Number.isInteger(value) || value < 1) {
      throw new LearningStoreError("unavailable", "maxAggregateBytes must be a positive integer");
    }
    return Math.min(value, MAX_AGGREGATE_BYTES);
  }

  function isSha256Dependency(hashText) {
    if (typeof hashText !== "function") return false;
    try {
      return SHA256_TEST_VECTORS.every(([input, expected]) => hashText(input) === expected);
    } catch {
      return false;
    }
  }

  function createAdapter(options = {}) {
    const model = options.model || globalThis.HUB_OPTIMUS_LEARNING_CANDIDATE_V1;
    const factory = Object.prototype.hasOwnProperty.call(options, "indexedDB")
      ? options.indexedDB
      : globalThis.indexedDB;
    const hashText = options.hashText;
    const maxAggregateBytes = boundedAggregateLimit(options.maxAggregateBytes);
    const now = typeof options.now === "function" ? options.now : () => new Date().toISOString();

    const requiredModelMethods = [
      "createStore",
      "validateStore",
      "insertEntry",
      "deleteCaseEntries",
      "stableStringify",
      "canonicalValue",
      "hasSafeJsonShape",
      "parseImport",
      "createExport"
    ];
    if (!model || requiredModelMethods.some((name) => typeof model[name] !== "function")) {
      throw new LearningStoreError("unavailable", "The versioned learning-candidate model is unavailable");
    }
    if (model.storeVersion !== STORE_VERSION || !isSha256Dependency(hashText)) {
      throw new LearningStoreError("unavailable", "The learning-store model version or hash dependency is unavailable");
    }
    if (!model.limits || model.limits.maxEntries !== 50 || model.limits.maxEntryBytes !== 256 * 1024) {
      throw new LearningStoreError("unavailable", "The learning-store entry limits do not match version 1");
    }
    if (!factory || typeof factory.open !== "function" || typeof TextEncoder !== "function") {
      throw new LearningStoreError("unavailable", "IndexedDB is unavailable for the learning store");
    }

    function byteLength(value) {
      return new TextEncoder().encode(String(value)).byteLength;
    }

    function canonicalClone(value) {
      return JSON.parse(model.stableStringify(value));
    }

    function digest(value) {
      const result = hashText(model.stableStringify(value));
      if (!isSha256(result)) {
        throw new LearningStoreError("unavailable", "The hash dependency did not return a SHA-256 digest");
      }
      return result;
    }

    function caseRevision(candidate) {
      const caseNodes = candidate.nodes.filter((node) => node.node_type === "case");
      if (caseNodes.length !== 1 || !isSha256(caseNodes[0].revision_sha256)) {
        throw new LearningStoreError("corrupt", "The candidate has no unique case revision");
      }
      return caseNodes[0].revision_sha256;
    }

    function candidateToken(entry) {
      return Object.freeze({
        candidate_id: entry.candidate.candidate_id,
        candidate_sha256: digest(entry.candidate),
        case_revision_sha256: caseRevision(entry.candidate),
        entry_sha256: digest(entry)
      });
    }

    function presentEntry(entry) {
      return Object.freeze({
        ...candidateToken(entry),
        entry: canonicalClone(entry)
      });
    }

    function assertStore(store, phase = "load") {
      let valid = false;
      try {
        valid = model.validateStore(store, { hashText });
      } catch (error) {
        throw new LearningStoreError("corrupt", "The local learning store could not be validated", error);
      }
      if (!valid) {
        throw new LearningStoreError("corrupt", "The local learning store failed model validation");
      }
      const bytes = byteLength(model.stableStringify(store));
      if (bytes > maxAggregateBytes) {
        const code = phase === "write" ? "quota" : "corrupt";
        throw new LearningStoreError(code, "The local learning store exceeds the aggregate byte limit");
      }
      return canonicalClone(store);
    }

    function normalizeEntry(entry) {
      if (!model.hasSafeJsonShape(entry)) {
        throw new LearningStoreError("corrupt", "The learning entry is not safe plain JSON data");
      }
      let entryBytes;
      try {
        entryBytes = byteLength(model.stableStringify(entry));
      } catch (error) {
        throw new LearningStoreError("corrupt", "The learning entry is not canonical JSON", error);
      }
      if (entryBytes > model.limits.maxEntryBytes) {
        throw new LearningStoreError("quota", "The learning entry exceeds the 256 KiB limit");
      }
      const single = { store_version: STORE_VERSION, entries: [entry] };
      const validated = assertStore(single, "write");
      return validated.entries[0];
    }

    function storeDigest(store) {
      return digest(store);
    }

    function transitionInvariant(candidate) {
      const invariant = canonicalClone(candidate);
      delete invariant.state;
      delete invariant.updated_at_utc;
      delete invariant.history;
      return invariant;
    }

    function assertPureTransition(previous, next) {
      if (model.stableStringify(transitionInvariant(previous))
        !== model.stableStringify(transitionInvariant(next))) {
        throw new LearningStoreError("conflict", "A reviewed-state transition cannot bundle candidate edits");
      }
      if (!Array.isArray(previous.history) || !Array.isArray(next.history)
        || next.history.length !== previous.history.length + 1) {
        throw new LearningStoreError("conflict", "A reviewed-state transition must append exactly one history event");
      }
      for (let index = 0; index < previous.history.length; index += 1) {
        if (model.stableStringify(previous.history[index]) !== model.stableStringify(next.history[index])) {
          throw new LearningStoreError("conflict", "A reviewed-state transition cannot rewrite history");
        }
      }
      const event = next.history[next.history.length - 1];
      if (!event || event.action !== "state-change"
        || event.from_state !== previous.state
        || event.to_state !== next.state
        || event.at_utc !== next.updated_at_utc) {
        throw new LearningStoreError("conflict", "The appended history event does not match the state transition");
      }
    }

    function assertCandidateReplacement(previous, next, binding) {
      if (model.stableStringify(previous) === model.stableStringify(next)) return;
      const from = previous.state;
      const to = next.state;
      if (REVIEWED_STATES.has(from) && to === "draft") {
        assertPureTransition(previous, next);
        return;
      }
      if (from === "draft" && REVIEWED_STATES.has(to)) {
        assertPureTransition(previous, next);
        if (to === "accepted") {
          if (CLOSURE_KEYS.some((key) => next.closure_check?.[key] !== true)
            || binding.freshness !== "current") {
            throw new LearningStoreError("conflict", "Local acceptance requires complete closure and a current binding");
          }
        }
        return;
      }
      throw new LearningStoreError("conflict", "Candidate content is append-only for a candidate ID; create a new draft ID for edited content");
    }

    function expectedState(expectations, existing) {
      const keys = [
        "expectedCandidateSha256",
        "expectedCaseRevisionSha256",
        "expectedEntrySha256"
      ];
      if (!model.hasSafeJsonShape(expectations) || !exactKeys(expectations, keys)) {
        throw new LearningStoreError("conflict", "All previous entry tokens are required");
      }
      if (!existing) {
        if (expectations.expectedCandidateSha256 !== null
          || expectations.expectedCaseRevisionSha256 !== null
          || expectations.expectedEntrySha256 !== null) {
          throw new LearningStoreError("conflict", "The expected candidate no longer matches local state");
        }
        return;
      }
      if (!isSha256(expectations.expectedCandidateSha256)
        || !isSha256(expectations.expectedCaseRevisionSha256)
        || !isSha256(expectations.expectedEntrySha256)) {
        throw new LearningStoreError("conflict", "The expected entry tokens are invalid");
      }
      const actual = candidateToken(existing);
      if (actual.candidate_sha256 !== expectations.expectedCandidateSha256
        || actual.case_revision_sha256 !== expectations.expectedCaseRevisionSha256
        || actual.entry_sha256 !== expectations.expectedEntrySha256) {
        throw new LearningStoreError("conflict", "The candidate changed since it was read");
      }
    }

    function expectedCaseSet(store, caseId, expectedCandidates) {
      if (!model.hasSafeJsonShape(expectedCandidates) || !Array.isArray(expectedCandidates)) {
        throw new LearningStoreError("conflict", "Expected case candidate tokens are required");
      }
      const actual = store.entries
        .filter((entry) => entry.candidate.case_ref === caseId)
        .map(candidateToken)
        .sort((left, right) => left.candidate_id.localeCompare(right.candidate_id));
      const expected = expectedCandidates.map((item) => {
        if (!exactKeys(item, ["candidate_id", "candidate_sha256", "case_revision_sha256", "entry_sha256"])
          || !isCandidateId(item.candidate_id)
          || !isSha256(item.candidate_sha256)
          || !isSha256(item.case_revision_sha256)
          || !isSha256(item.entry_sha256)) {
          throw new LearningStoreError("conflict", "Expected case candidate tokens are invalid");
        }
        return { ...item };
      }).sort((left, right) => left.candidate_id.localeCompare(right.candidate_id));
      if (model.stableStringify(actual) !== model.stableStringify(expected)) {
        throw new LearningStoreError("conflict", "The case candidate set changed since it was read");
      }
    }

    function openDatabase() {
      return new Promise((resolve, reject) => {
        let request;
        let settled = false;
        let upgradeError = null;
        try {
          request = factory.open(DB_NAME, DB_VERSION);
        } catch (error) {
          reject(classified(error, "unavailable"));
          return;
        }
        request.onupgradeneeded = (event) => {
          if (settled) {
            try { request.transaction.abort(); } catch {}
            return;
          }
          try {
            if (event.oldVersion !== 0 || request.result.objectStoreNames.length !== 0) {
              throw new LearningStoreError("corrupt", "Unexpected IndexedDB schema during initial upgrade");
            }
            const objectStore = request.result.createObjectStore(OBJECT_STORE_NAME);
            const seedRequest = objectStore.put(model.createStore(), RECORD_KEY);
            seedRequest.onerror = () => {
              upgradeError = classified(seedRequest.error, "corrupt");
            };
          } catch (error) {
            upgradeError = classified(error, "corrupt");
            try { request.transaction.abort(); } catch {}
          }
        };
        request.onblocked = () => {
          if (settled) return;
          settled = true;
          reject(new LearningStoreError("blocked", "IndexedDB open or upgrade is blocked by another page"));
        };
        request.onerror = () => {
          if (settled) return;
          settled = true;
          reject(upgradeError || classified(request.error, "unavailable"));
        };
        request.onsuccess = () => {
          const database = request.result;
          if (settled) {
            database.close();
            return;
          }
          const names = objectStoreNames(database);
          if (names.length !== 1 || names[0] !== OBJECT_STORE_NAME) {
            settled = true;
            database.close();
            reject(new LearningStoreError("corrupt", "IndexedDB contains an unexpected learning-store schema"));
            return;
          }
          database.onversionchange = () => database.close();
          settled = true;
          resolve(database);
        };
      });
    }

    async function withTransaction(mode, operation) {
      const database = await openDatabase();
      let transaction;
      try {
        transaction = database.transaction(OBJECT_STORE_NAME, mode);
      } catch (error) {
        database.close();
        throw classified(error, "unavailable");
      }
      const completion = transactionCompletion(transaction);
      try {
        const objectStore = transaction.objectStore(OBJECT_STORE_NAME);
        if (!hasExpectedObjectStoreSchema(objectStore)) {
          throw new LearningStoreError("corrupt", "IndexedDB contains incompatible learning-store metadata");
        }
        const result = await operation(objectStore, transaction);
        await completion;
        return result;
      } catch (error) {
        try { transaction.abort(); } catch {}
        try { await completion; } catch {}
        throw classified(error, error instanceof LearningStoreError ? error.code : "corrupt");
      } finally {
        database.close();
      }
    }

    async function readLatest(objectStore) {
      const countRequest = objectStore.count();
      const getRequest = objectStore.get(RECORD_KEY);
      const [count, stored] = await Promise.all([
        requestResult(countRequest),
        requestResult(getRequest)
      ]);
      if (count !== 1) {
        throw new LearningStoreError("corrupt", "IndexedDB must contain exactly one learning-store record");
      }
      if (stored === undefined) {
        throw new LearningStoreError("corrupt", "The versioned learning-store record is missing");
      }
      return assertStore(stored, "load");
    }

    async function mutate(transform) {
      const database = await openDatabase();
      return new Promise((resolve, reject) => {
        let transaction;
        let failure = null;
        let result;
        try {
          transaction = database.transaction(OBJECT_STORE_NAME, "readwrite");
          const objectStore = transaction.objectStore(OBJECT_STORE_NAME);
          if (!hasExpectedObjectStoreSchema(objectStore)) {
            try { transaction.abort(); } catch {}
            database.close();
            reject(new LearningStoreError("corrupt", "IndexedDB contains incompatible learning-store metadata"));
            return;
          }
          const countRequest = objectStore.count();
          countRequest.onerror = () => {
            failure = classified(countRequest.error, "corrupt");
          };
          countRequest.onsuccess = () => {
            if (countRequest.result !== 1) {
              failure = new LearningStoreError("corrupt", "IndexedDB must contain exactly one learning-store record");
              try { transaction.abort(); } catch {}
              return;
            }
            const getRequest = objectStore.get(RECORD_KEY);
            getRequest.onerror = () => {
              failure = classified(getRequest.error, "corrupt");
            };
            getRequest.onsuccess = () => {
              try {
                if (getRequest.result === undefined) {
                  throw new LearningStoreError("corrupt", "The versioned learning-store record is missing");
                }
                const current = assertStore(getRequest.result, "load");
                const change = transform(current);
                if (!change || !exactKeys(change, ["store", "result"])) {
                  throw new LearningStoreError("corrupt", "The learning-store mutation returned an invalid result");
                }
                const written = assertStore(change.store, "write");
                const putRequest = objectStore.put(written, RECORD_KEY);
                putRequest.onerror = () => {
                  failure = classified(putRequest.error, "corrupt");
                };
                putRequest.onsuccess = () => {
                  result = typeof change.result === "function" ? change.result(written) : change.result;
                };
              } catch (error) {
                failure = classified(error, error instanceof LearningStoreError ? error.code : "corrupt");
                try { transaction.abort(); } catch {}
              }
            };
          };
          transaction.oncomplete = () => {
            database.close();
            resolve(result);
          };
          transaction.onabort = () => {
            database.close();
            reject(failure || classified(transaction.error, "corrupt"));
          };
          transaction.onerror = () => {};
        } catch (error) {
          database.close();
          reject(classified(error, "unavailable"));
        }
      });
    }

    function upsertChange(current, entry, expectations) {
      const normalized = normalizeEntry(entry);
      const candidateId = normalized.candidate.candidate_id;
      const index = current.entries.findIndex((item) => item.candidate.candidate_id === candidateId);
      const existing = index >= 0 ? current.entries[index] : null;
      expectedState(expectations, existing);
      if (existing) {
        assertCandidateReplacement(existing.candidate, normalized.candidate, normalized.binding);
      }
      let next;
      if (!existing) {
        if (current.entries.length >= model.limits.maxEntries) {
          throw new LearningStoreError("quota", "The learning store already contains 50 candidates");
        }
        try {
          next = model.insertEntry(current, normalized, { hashText });
        } catch (error) {
          throw new LearningStoreError("corrupt", "The candidate could not be inserted into the validated store", error);
        }
      } else {
        next = {
          store_version: STORE_VERSION,
          entries: current.entries.map((item, itemIndex) => itemIndex === index ? normalized : item)
        };
      }
      return {
        store: next,
        result: (written) => ({
          store_sha256: storeDigest(written),
          entry: presentEntry(written.entries.find((item) => item.candidate.candidate_id === candidateId))
        })
      };
    }

    async function list() {
      return withTransaction("readonly", async (objectStore) => {
        const store = await readLatest(objectStore);
        return {
          store_sha256: storeDigest(store),
          entries: store.entries
            .map(presentEntry)
            .sort((left, right) => left.candidate_id.localeCompare(right.candidate_id))
        };
      });
    }

    async function get(candidateId) {
      if (!isCandidateId(candidateId)) {
        throw new LearningStoreError("conflict", "A valid learning candidate ID is required");
      }
      return withTransaction("readonly", async (objectStore) => {
        const store = await readLatest(objectStore);
        const entry = store.entries.find((item) => item.candidate.candidate_id === candidateId);
        return entry ? presentEntry(entry) : null;
      });
    }

    async function upsert(entry, expectations) {
      return mutate((current) => upsertChange(current, entry, expectations));
    }

    async function deleteCandidate(candidateId, expectations) {
      if (!isCandidateId(candidateId)) {
        throw new LearningStoreError("conflict", "A valid learning candidate ID is required");
      }
      return mutate((current) => {
        const existing = current.entries.find((item) => item.candidate.candidate_id === candidateId) || null;
        expectedState(expectations, existing);
        if (!existing) {
          throw new LearningStoreError("conflict", "The candidate no longer exists");
        }
        const next = {
          store_version: STORE_VERSION,
          entries: current.entries.filter((item) => item.candidate.candidate_id !== candidateId)
        };
        return {
          store: next,
          result: (written) => ({ removed: 1, store_sha256: storeDigest(written) })
        };
      });
    }

    async function deleteCase(caseId, expectedCandidates) {
      if (typeof caseId !== "string" || !caseId.trim()) {
        throw new LearningStoreError("conflict", "A case ID is required for explicit case deletion");
      }
      return mutate((current) => {
        expectedCaseSet(current, caseId, expectedCandidates);
        let deletion;
        try {
          deletion = model.deleteCaseEntries(current, caseId, { hashText });
        } catch (error) {
          throw new LearningStoreError("corrupt", "The case candidates could not be deleted", error);
        }
        return {
          store: deletion.store,
          result: (written) => ({ removed: deletion.removed, store_sha256: storeDigest(written) })
        };
      });
    }

    async function clearExplicit(confirmation, expectedStoreSha256) {
      if (confirmation !== CLEAR_CONFIRMATION || !isSha256(expectedStoreSha256)) {
        throw new LearningStoreError("conflict", "Explicit clear confirmation and the expected store digest are required");
      }
      return mutate((current) => {
        if (storeDigest(current) !== expectedStoreSha256) {
          throw new LearningStoreError("conflict", "The learning store changed before explicit clear");
        }
        const removed = current.entries.length;
        return {
          store: model.createStore(),
          result: (written) => ({ removed, store_sha256: storeDigest(written) })
        };
      });
    }

    async function importCandidate(text, binding, expectations) {
      let candidate;
      try {
        candidate = model.parseImport(text, { hashText });
      } catch (error) {
        throw new LearningStoreError("corrupt", "The learning candidate import failed validation", error);
      }
      return mutate((current) => upsertChange(current, { candidate, binding }, expectations));
    }

    async function exportCandidate(candidateId, exportOptions = {}) {
      if (!isCandidateId(candidateId)) {
        throw new LearningStoreError("conflict", "A valid learning candidate ID is required");
      }
      return withTransaction("readonly", async (objectStore) => {
        const store = await readLatest(objectStore);
        const entry = store.entries.find((item) => item.candidate.candidate_id === candidateId);
        if (!entry) throw new LearningStoreError("conflict", "The candidate no longer exists");
        if (!model.hasSafeJsonShape(exportOptions)
          || !exportOptions || typeof exportOptions !== "object"
          || !Object.prototype.hasOwnProperty.call(exportOptions, "expectations")) {
          throw new LearningStoreError("conflict", "Current candidate tokens are required for export");
        }
        expectedState(exportOptions.expectations, entry);
        try {
          return model.createExport(entry.candidate, {
            hashText,
            now: exportOptions.now || now()
          });
        } catch (error) {
          throw new LearningStoreError("corrupt", "The learning candidate could not be exported", error);
        }
      });
    }

    return Object.freeze({
      list,
      get,
      upsert,
      delete: deleteCandidate,
      deleteCase,
      clearExplicit,
      import: importCandidate,
      export: exportCandidate,
      importCandidate,
      exportCandidate
    });
  }

  globalThis.HUB_OPTIMUS_LEARNING_STORE_V1 = Object.freeze({
    dbName: DB_NAME,
    dbVersion: DB_VERSION,
    objectStoreName: OBJECT_STORE_NAME,
    recordKey: RECORD_KEY,
    storeVersion: STORE_VERSION,
    clearConfirmation: CLEAR_CONFIRMATION,
    limits: Object.freeze({ maxAggregateBytes: MAX_AGGREGATE_BYTES }),
    errorCodes: ERROR_CODES,
    LearningStoreError,
    createAdapter
  });
})();
