(() => {
  "use strict";

  const SCHEMA_VERSION = "operator_learning_candidate.v1";
  const STORE_VERSION = "operator_learning_store.v1";
  const EXPORT_VERSION = "operator_learning_export.v1";
  const METHOD_PATH = "v1_core/workflow/05_meta_learning.md";
  const METHOD_SHA256 = "74f4e5ff32de47f4ec970de606f5674c5cd40c7eed7d356fc0a12a23acc3561c";
  const MAX_ENTRIES = 50;
  const MAX_ENTRY_BYTES = 256 * 1024;
  const MAX_IMPORT_BYTES = 1024 * 1024;

  const STATES = new Set(["draft", "accepted", "rejected"]);
  const CATEGORIES = new Set([
    "ambiguity",
    "weak_verification",
    "misaligned_incentives",
    "wrong_sequence",
    "political_overload",
    "spoilers",
    "information_asymmetry"
  ]);
  const DECISIONS = new Set([
    "repeat_same_scenario",
    "escalate_variant",
    "change_approach"
  ]);
  const METRICS = new Set([
    "clarity",
    "verifiability",
    "viability",
    "time_to_draft_minutes",
    "open_points"
  ]);
  const RELATION_SIGNATURES = Object.freeze({
    OUTCOME_OF_CASE: ["outcome", "case"],
    SUPPORTS_ATTRIBUTION: ["evidence", "claim"],
    SUPPORTS_CLAIM: ["evidence", "claim"],
    CONTRADICTS_CLAIM: ["evidence", "claim"],
    SIGNAL_REFERENCES_CLAIM: ["signal", "claim"],
    SIGNAL_GROUNDED_IN_EVIDENCE: ["signal", "evidence"],
    DIAGNOSIS_INTERPRETS_SIGNAL: ["diagnosis", "signal"],
    DIAGNOSIS_REFERENCES_EVIDENCE: ["diagnosis", "evidence"],
    GAP_IDENTIFIED_BY_DIAGNOSIS: ["gap", "diagnosis"],
    ACTION_ADDRESSES_GAP: ["action", "gap"]
  });
  const RELATION_EPISTEMIC_STATUS = Object.freeze({
    OUTCOME_OF_CASE: "observation",
    SUPPORTS_ATTRIBUTION: "submitted-claim",
    SUPPORTS_CLAIM: "corroboration",
    CONTRADICTS_CLAIM: "corroboration",
    SIGNAL_REFERENCES_CLAIM: "observation",
    SIGNAL_GROUNDED_IN_EVIDENCE: "observation",
    DIAGNOSIS_INTERPRETS_SIGNAL: "inference",
    DIAGNOSIS_REFERENCES_EVIDENCE: "inference",
    GAP_IDENTIFIED_BY_DIAGNOSIS: "inference",
    ACTION_ADDRESSES_GAP: "proposal"
  });
  const IMPORTED_RELATION_TYPES = new Set([
    "SUPPORTS_ATTRIBUTION",
    "SUPPORTS_CLAIM",
    "CONTRADICTS_CLAIM"
  ]);
  const NODE_KEYS = Object.freeze({
    case: ["node_id", "node_type", "case_id", "core_version_ref", "revision_sha256"],
    claim: ["node_id", "node_type", "record_id", "text", "text_sha256", "source_ref"],
    evidence: ["node_id", "node_type", "record_id", "text", "text_sha256", "source_ref", "limitations"],
    outcome: ["node_id", "node_type", "text"],
    signal: ["node_id", "node_type", "text", "claim_refs", "evidence_refs"],
    diagnosis: ["node_id", "node_type", "text", "categories", "signal_refs", "evidence_refs"],
    gap: ["node_id", "node_type", "text"],
    action: ["node_id", "node_type", "change", "reason", "verification_criterion"]
  });
  const REQUIRED_CASE_FIELDS = Object.freeze([
    "case_id",
    "core_version_ref",
    "revision_sha256",
    "claims",
    "evidence",
    "relationships"
  ]);

  function normalizeString(value) {
    if (value === null || value === undefined) return "";
    return String(value).replace(/\r\n?/g, "\n").normalize("NFC");
  }

  function hasUnpairedSurrogate(value) {
    if (typeof value !== "string") return false;
    for (let index = 0; index < value.length; index += 1) {
      const code = value.charCodeAt(index);
      if (code >= 0xd800 && code <= 0xdbff) {
        const next = value.charCodeAt(index + 1);
        if (!(next >= 0xdc00 && next <= 0xdfff)) return true;
        index += 1;
      } else if (code >= 0xdc00 && code <= 0xdfff) {
        return true;
      }
    }
    return false;
  }

  function canonicalValue(value) {
    if (typeof value === "string") return normalizeString(value);
    if (Array.isArray(value)) {
      const canonical = [];
      for (let index = 0; index < value.length; index += 1) canonical.push(canonicalValue(value[index]));
      return canonical;
    }
    if (value && typeof value === "object") {
      return Object.fromEntries(
        Object.keys(value)
          .sort()
          .map((key) => [key, canonicalValue(value[key])])
      );
    }
    return value;
  }

  function stableStringify(value) {
    return JSON.stringify(canonicalValue(value));
  }

  function byteLength(value) {
    return new TextEncoder().encode(String(value)).byteLength;
  }

  function isObject(value) {
    return Boolean(value) && typeof value === "object" && !Array.isArray(value);
  }

  function isNonEmptyString(value) {
    return typeof value === "string"
      && !hasUnpairedSurrogate(value)
      && value.trim().length > 0
      && value.length <= 20000;
  }

  function isId(value) {
    return typeof value === "string" && /^[A-Za-z][A-Za-z0-9._:-]{0,127}$/.test(value);
  }

  function isSha256(value) {
    return typeof value === "string" && /^[0-9a-f]{64}$/.test(value);
  }

  function isTimestamp(value) {
    if (typeof value !== "string") return false;
    const match = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.(\d{1,3}))?Z$/.exec(value);
    if (!match) return false;
    const epoch = Date.parse(value);
    if (!Number.isFinite(epoch)) return false;
    const instant = new Date(epoch);
    return instant.getUTCFullYear() === Number(match[1])
      && instant.getUTCMonth() + 1 === Number(match[2])
      && instant.getUTCDate() === Number(match[3])
      && instant.getUTCHours() === Number(match[4])
      && instant.getUTCMinutes() === Number(match[5])
      && instant.getUTCSeconds() === Number(match[6]);
  }

  function sameKeys(value, expected) {
    if (!isObject(value)) return false;
    const actual = Object.keys(value).sort();
    const wanted = [...expected].sort();
    return actual.length === wanted.length && actual.every((key, index) => key === wanted[index]);
  }

  function uniqueStrings(value) {
    return Array.isArray(value)
      && value.length <= 128
      && value.every(isNonEmptyString)
      && new Set(value).size === value.length;
  }

  function safeSourceRef(value) {
    const normalized = normalizeString(value);
    if (!/^https?:\/\//i.test(normalized)) return isId(normalized) ? normalized : "";
    if (typeof URL !== "function") return "";
    try {
      const parsed = new URL(normalized);
      if (!["http:", "https:"].includes(parsed.protocol) || parsed.username || parsed.password || parsed.port) return "";
      const hostname = parsed.hostname.toLowerCase().replace(/\.$/, "");
      const blockedSuffixes = ["localhost", "local", "internal", "localdomain", "home.arpa"];
      const dnsName = /^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)+$/;
      if (hostname.length > 253 || !dnsName.test(hostname)) return "";
      if (blockedSuffixes.some((suffix) => hostname === suffix || hostname.endsWith(`.${suffix}`))) return "";
      if (/^\d+(?:\.\d+){1,3}$/.test(hostname)) return "";
      return `${parsed.protocol}//${hostname}`;
    } catch { return ""; }
  }

  function isSafeSourceRef(value) {
    if (!isNonEmptyString(value) || value.length > 2048) return false;
    return safeSourceRef(value) === value;
  }

  function findNonCanonicalString(value, path = "$") {
    if (typeof value === "string") {
      return value === normalizeString(value) && !hasUnpairedSurrogate(value) ? null : path;
    }
    if (Array.isArray(value)) {
      for (let index = 0; index < value.length; index += 1) {
        const found = findNonCanonicalString(value[index], `${path}[${index}]`);
        if (found) return found;
      }
      return null;
    }
    if (isObject(value)) {
      for (const [key, child] of Object.entries(value)) {
        const found = findNonCanonicalString(child, `${path}.${key}`);
        if (found) return found;
      }
    }
    return null;
  }

  function snapshotJsonValue(value, maxDepth = 32, maxNodes = 50000) {
    let seen = 0;
    function visit(current, depth) {
      seen += 1;
      if (seen > maxNodes || depth > maxDepth) throw new Error("JSON structure limit exceeded");
      if (current === null || typeof current === "boolean") return current;
      if (typeof current === "number") {
        if (!Number.isFinite(current)) throw new Error("non-finite number");
        return current;
      }
      if (typeof current === "string") {
        if (hasUnpairedSurrogate(current)) throw new Error("unpaired surrogate");
        return current;
      }
      if (Array.isArray(current)) {
        if (Object.getPrototypeOf(current) !== Array.prototype) throw new Error("non-plain array");
        const keys = Object.keys(current);
        const names = Object.getOwnPropertyNames(current);
        if (Object.getOwnPropertySymbols(current).length
          || keys.length !== current.length
          || names.length !== current.length + 1) throw new Error("non-JSON array properties");
        const snapshot = [];
        for (let index = 0; index < current.length; index += 1) {
          if (keys[index] !== String(index)) throw new Error("sparse array");
          const descriptor = Object.getOwnPropertyDescriptor(current, String(index));
          if (!descriptor || !descriptor.enumerable || !("value" in descriptor)) throw new Error("array accessor");
          snapshot.push(visit(descriptor.value, depth + 1));
        }
        return snapshot;
      }
      if (typeof current === "object") {
        const prototype = Object.getPrototypeOf(current);
        if (prototype !== null && prototype !== Object.prototype) throw new Error("non-plain object");
        if (Object.getOwnPropertySymbols(current).length) throw new Error("symbol property");
        const entries = [];
        for (const key of Object.getOwnPropertyNames(current)) {
          if (hasUnpairedSurrogate(key) || key !== normalizeString(key)) {
            throw new Error("non-canonical object key");
          }
          const descriptor = Object.getOwnPropertyDescriptor(current, key);
          if (!descriptor || !descriptor.enumerable || !("value" in descriptor)) throw new Error("object accessor");
          entries.push([key, visit(descriptor.value, depth + 1)]);
        }
        return Object.fromEntries(entries);
      }
      throw new Error("non-JSON value");
    }
    try {
      const snapshot = visit(value, 0);
      if (value !== null && typeof value === "object") {
        if (typeof globalThis.structuredClone !== "function") {
          throw new Error("structured clone validation is unavailable");
        }
        // The descriptor walk above rejects accessors and unsafe JSON values
        // without invoking them. A structured clone then supplies the browser's
        // native, fail-closed Proxy check: even a transparent Proxy is not
        // structured-cloneable.
        globalThis.structuredClone(value);
      }
      return { valid: true, value: snapshot };
    } catch {
      return { valid: false, value: null };
    }
  }

  function hasSafeJsonShape(value, maxDepth = 32, maxNodes = 50000) {
    return snapshotJsonValue(value, maxDepth, maxNodes).valid;
  }

  function relationKey(type, fromRef, toRef) {
    return `${type}\u0000${fromRef}\u0000${toRef}`;
  }

  function ownCanonicalCaseRecord(caseRecord) {
    const captured = snapshotJsonValue(caseRecord);
    if (!captured.valid || !isObject(captured.value)
      || REQUIRED_CASE_FIELDS.some((field) => !Object.prototype.hasOwnProperty.call(captured.value, field))) return null;
    const structured = Array.isArray(captured.value.claims)
      && captured.value.claims.every((record) => isObject(record)
        && ["claim_id", "text", "source_ref"].every((field) => typeof record[field] === "string"))
      && Array.isArray(captured.value.evidence)
      && captured.value.evidence.every((record) => isObject(record)
        && ["evidence_id", "text", "source_ref"].every((field) => typeof record[field] === "string")
        && Array.isArray(record.limitations)
        && record.limitations.every((item) => typeof item === "string"))
      && Array.isArray(captured.value.relationships)
      && captured.value.relationships.every((record) => isObject(record)
        && ["type", "from_ref", "to_ref"].every((field) => typeof record[field] === "string"))
      && typeof captured.value.case_id === "string"
      && typeof captured.value.core_version_ref === "string"
      && typeof captured.value.revision_sha256 === "string";
    if (!structured) return null;
    return canonicalValue(captured.value);
  }

  function caseRevisionMaterial(caseRecord) {
    const snapshot = ownCanonicalCaseRecord(caseRecord);
    if (!snapshot) return null;
    return canonicalValue(Object.fromEntries(
      Object.entries(snapshot).filter(([key]) => key !== "revision_sha256")
    ));
  }

  function computeCaseRevision(caseRecord, options = {}) {
    if (typeof options.hashText !== "function") throw new Error("hashText dependency is required");
    const material = caseRevisionMaterial(caseRecord);
    if (!material) throw new Error("case record is required");
    return options.hashText(stableStringify(material));
  }

  function boundedLimit(value, fallback, label) {
    if (value === undefined) return fallback;
    if (!Number.isInteger(value) || value < 1) throw new Error(`${label} must be a positive integer`);
    return Math.min(value, fallback);
  }

  function addError(errors, path, message) {
    errors.push({ path, message });
  }

  function validateNode(node, index, hashText, errors) {
    const path = `nodes[${index}]`;
    const expected = NODE_KEYS[node?.node_type];
    if (!expected || !sameKeys(node, expected)) {
      addError(errors, path, "unknown node type or properties");
      return;
    }
    if (!isId(node.node_id)) addError(errors, `${path}.node_id`, "invalid ID");

    if (node.node_type === "case") {
      if (!isNonEmptyString(node.case_id)) addError(errors, `${path}.case_id`, "required");
      if (!isNonEmptyString(node.core_version_ref)) addError(errors, `${path}.core_version_ref`, "required");
      if (!isSha256(node.revision_sha256)) addError(errors, `${path}.revision_sha256`, "invalid SHA-256");
      return;
    }

    if (["claim", "evidence"].includes(node.node_type)) {
      if (!isId(node.record_id)) addError(errors, `${path}.record_id`, "invalid record ID");
      if (!isNonEmptyString(node.text)) addError(errors, `${path}.text`, "required");
      if (node.text !== normalizeString(node.text)) addError(errors, `${path}.text`, "must use NFC and LF canonical form");
      if (!isSafeSourceRef(node.source_ref)) addError(errors, `${path}.source_ref`, "must be an opaque ref or URL origin only");
      if (!isSha256(node.text_sha256)) {
        addError(errors, `${path}.text_sha256`, "invalid SHA-256");
      } else if (hashText(normalizeString(node.text)) !== node.text_sha256) {
        addError(errors, `${path}.text_sha256`, "does not match canonical text");
      }
      if (node.node_type === "evidence" && !uniqueStrings(node.limitations)) {
        addError(errors, `${path}.limitations`, "must be a unique string list");
      }
      return;
    }

    if (["outcome", "signal", "diagnosis", "gap"].includes(node.node_type)) {
      if (!isNonEmptyString(node.text)) addError(errors, `${path}.text`, "required");
    }
    if (node.node_type === "signal") {
      if (!uniqueStrings(node.claim_refs)) addError(errors, `${path}.claim_refs`, "must be unique strings");
      if (!uniqueStrings(node.evidence_refs)) addError(errors, `${path}.evidence_refs`, "must be unique strings");
      if (!node.claim_refs.length) addError(errors, `${path}.claim_refs`, "at least one claim reference is required");
      if (!node.evidence_refs.length) addError(errors, `${path}.evidence_refs`, "at least one evidence reference is required");
    }
    if (node.node_type === "diagnosis") {
      if (!Array.isArray(node.categories) || !node.categories.length || new Set(node.categories).size !== node.categories.length || node.categories.some((item) => !CATEGORIES.has(item))) {
        addError(errors, `${path}.categories`, "invalid diagnosis categories");
      }
      if (!uniqueStrings(node.signal_refs) || !node.signal_refs.length) {
        addError(errors, `${path}.signal_refs`, "must cite at least one signal");
      }
      if (!uniqueStrings(node.evidence_refs) || !node.evidence_refs.length) addError(errors, `${path}.evidence_refs`, "at least one unique evidence reference is required");
    }
    if (node.node_type === "action") {
      ["change", "reason", "verification_criterion"].forEach((field) => {
        if (!isNonEmptyString(node[field])) addError(errors, `${path}.${field}`, "required");
      });
    }
  }

  function validateHistory(history, state, createdAt, updatedAt, errors) {
    if (!Array.isArray(history) || !history.length || history.length > 512) {
      addError(errors, "history", "at least one history event is required");
      return;
    }
    const ids = new Set();
    let expectedState = null;
    let previousTime = -Infinity;
    history.forEach((event, index) => {
      const path = `history[${index}]`;
      const keys = ["event_id", "at_utc", "actor", "action", "from_state", "to_state", "note"];
      if (!sameKeys(event, keys)) {
        addError(errors, path, "unknown history properties");
        return;
      }
      if (!isId(event.event_id) || ids.has(event.event_id)) addError(errors, `${path}.event_id`, "invalid or duplicate ID");
      ids.add(event.event_id);
      if (!isTimestamp(event.at_utc)) addError(errors, `${path}.at_utc`, "invalid timestamp");
      const time = Date.parse(event.at_utc);
      if (time < previousTime) addError(errors, `${path}.at_utc`, "history is not chronological");
      previousTime = time;
      if (event.actor !== "human-operator") addError(errors, `${path}.actor`, "must remain human-operator");
      if (!["created", "edited", "state-change", "imported", "revalidated"].includes(event.action)) addError(errors, `${path}.action`, "unknown action");
      if (event.from_state !== expectedState) addError(errors, `${path}.from_state`, "does not continue history state");
      if (!STATES.has(event.to_state)) addError(errors, `${path}.to_state`, "unknown state");
      if (!isNonEmptyString(event.note)) addError(errors, `${path}.note`, "human note required");
      if (index === 0 && (event.action !== "created" || event.from_state !== null || event.to_state !== "draft")) {
        addError(errors, path, "first event must create a draft");
      }
      if (index > 0 && event.action === "created") addError(errors, path, "created is allowed only for the first history event");
      if (["edited", "imported", "revalidated"].includes(event.action) && event.from_state !== event.to_state) {
        addError(errors, path, "non-transition event cannot change state");
      }
      if (index > 0 && event.from_state !== event.to_state && event.action !== "state-change") {
        addError(errors, path, "state changes require a state-change event");
      }
      if (event.action === "state-change") {
        const allowed = (
          (event.from_state === "draft" && ["accepted", "rejected"].includes(event.to_state))
          || (["accepted", "rejected"].includes(event.from_state) && event.to_state === "draft")
        );
        if (!allowed) addError(errors, path, "forbidden state transition");
      }
      expectedState = event.to_state;
    });
    if (history[0]?.at_utc !== createdAt) addError(errors, "created_at_utc", "must match the first history event");
    if (history[history.length - 1]?.at_utc !== updatedAt) addError(errors, "updated_at_utc", "must match the last history event");
    if (expectedState !== state) addError(errors, "state", "does not match history tail");
  }

  function validateCandidate(candidate, options = {}) {
    const errors = [];
    const hashText = options.hashText;
    if (typeof hashText !== "function") {
      return { valid: false, errors: [{ path: "$", message: "hashText dependency is required" }] };
    }
    if (!hasSafeJsonShape(candidate)) {
      return { valid: false, errors: [{ path: "$", message: "candidate exceeds nesting, node, or Unicode safety limits" }] };
    }
    const topKeys = [
      "schema_version", "candidate_id", "method_ref", "authority", "case_ref", "state",
      "created_at_utc", "updated_at_utc", "nodes", "relations", "metrics",
      "iteration_decision", "next_experiment", "closure_check", "history"
    ];
    if (!sameKeys(candidate, topKeys)) {
      return { valid: false, errors: [{ path: "$", message: "unknown or missing top-level properties" }] };
    }
    const nonCanonicalPath = findNonCanonicalString(candidate);
    if (nonCanonicalPath) addError(errors, nonCanonicalPath, "must use NFC and LF canonical form");
    if (candidate.schema_version !== SCHEMA_VERSION) addError(errors, "schema_version", "unsupported version");
    if (!isId(candidate.candidate_id) || !/^learning-[A-Za-z0-9._:-]+$/.test(candidate.candidate_id)) addError(errors, "candidate_id", "must be a learning-* ID");
    if (!sameKeys(candidate.method_ref, ["path", "sha256"]) || candidate.method_ref.path !== METHOD_PATH || candidate.method_ref.sha256 !== METHOD_SHA256) {
      addError(errors, "method_ref", "method path or digest differs from the versioned workflow");
    }
    if (candidate.authority !== "local-non-canonical") addError(errors, "authority", "must remain local-non-canonical");
    if (!isNonEmptyString(candidate.case_ref)) addError(errors, "case_ref", "required");
    if (!STATES.has(candidate.state)) addError(errors, "state", "unknown state");
    if (!isTimestamp(candidate.created_at_utc)) addError(errors, "created_at_utc", "invalid timestamp");
    if (!isTimestamp(candidate.updated_at_utc)) addError(errors, "updated_at_utc", "invalid timestamp");
    if (Date.parse(candidate.updated_at_utc) < Date.parse(candidate.created_at_utc)) addError(errors, "updated_at_utc", "precedes creation");
    if (byteLength(stableStringify(candidate)) > MAX_ENTRY_BYTES) addError(errors, "$", "candidate exceeds 256 KiB record limit");

    if (!Array.isArray(candidate.nodes)) {
      addError(errors, "nodes", "must be an array");
      return { valid: false, errors };
    }
    if (candidate.nodes.length < 8 || candidate.nodes.length > 512) addError(errors, "nodes", "node count outside contract");
    candidate.nodes.forEach((node, index) => validateNode(node, index, hashText, errors));
    const nodesById = new Map();
    const recordIds = new Set();
    candidate.nodes.forEach((node, index) => {
      if (nodesById.has(node.node_id)) addError(errors, `nodes[${index}].node_id`, "duplicate node ID");
      nodesById.set(node.node_id, node);
      if (node.record_id) {
        if (recordIds.has(node.record_id)) addError(errors, `nodes[${index}].record_id`, "duplicate record ID");
        recordIds.add(node.record_id);
      }
    });
    const counts = Object.fromEntries([...Object.keys(NODE_KEYS)].map((type) => [type, 0]));
    candidate.nodes.forEach((node) => { if (Object.hasOwn(counts, node.node_type)) counts[node.node_type] += 1; });
    [["case", 1, 1], ["claim", 1, Infinity], ["evidence", 1, Infinity], ["outcome", 1, 1], ["signal", 3, 10], ["diagnosis", 1, 1], ["gap", 1, 1], ["action", 1, 1]].forEach(([type, min, max]) => {
      if (counts[type] < min || counts[type] > max) addError(errors, "nodes", `${type} count outside contract`);
    });
    const caseNode = candidate.nodes.find((node) => node.node_type === "case");
    if (caseNode && caseNode.case_id !== candidate.case_ref) addError(errors, "case_ref", "does not match case node");
    if (options.caseRevisionSha256 && caseNode?.revision_sha256 !== options.caseRevisionSha256) addError(errors, "nodes.case.revision_sha256", "does not match current case revision");

    if (!Array.isArray(candidate.relations)) {
      addError(errors, "relations", "must be an array");
    } else {
      if (candidate.relations.length < 8 || candidate.relations.length > 2048) addError(errors, "relations", "relation count outside contract");
      const relationIds = new Set();
      const relationKeys = new Set();
      candidate.relations.forEach((relation, index) => {
        const path = `relations[${index}]`;
        const keys = ["relation_id", "type", "from_ref", "to_ref", "origin", "epistemic_status"];
        if (!sameKeys(relation, keys)) {
          addError(errors, path, "unknown relation properties");
          return;
        }
        if (!isId(relation.relation_id) || relationIds.has(relation.relation_id)) addError(errors, `${path}.relation_id`, "invalid or duplicate ID");
        relationIds.add(relation.relation_id);
        const key = relationKey(relation.type, relation.from_ref, relation.to_ref);
        if (relationKeys.has(key)) addError(errors, path, "duplicate semantic edge");
        relationKeys.add(key);
        const signature = RELATION_SIGNATURES[relation.type];
        const from = nodesById.get(relation.from_ref);
        const to = nodesById.get(relation.to_ref);
        if (!signature) addError(errors, `${path}.type`, "unknown relation type");
        if (!from || !to) addError(errors, path, "dangling relation reference");
        if (signature && from && to && (from.node_type !== signature[0] || to.node_type !== signature[1])) addError(errors, path, "relation signature mismatch");
        if (relation.origin === "system-suggested") {
          addError(errors, `${path}.origin`, "system-suggested relations are forbidden in v1");
        } else if (!["human-authored", "imported"].includes(relation.origin)) {
          addError(errors, `${path}.origin`, "unknown origin");
        }
        const expectedOrigin = IMPORTED_RELATION_TYPES.has(relation.type) ? "imported" : "human-authored";
        if (RELATION_SIGNATURES[relation.type] && relation.origin !== expectedOrigin) {
          addError(errors, `${path}.origin`, `${relation.type} must be ${expectedOrigin}`);
        }
        if (!["observation", "submitted-claim", "corroboration", "inference", "proposal"].includes(relation.epistemic_status)) addError(errors, `${path}.epistemic_status`, "unknown epistemic status");
        if (RELATION_EPISTEMIC_STATUS[relation.type] && relation.epistemic_status !== RELATION_EPISTEMIC_STATUS[relation.type]) {
          addError(errors, `${path}.epistemic_status`, `must be ${RELATION_EPISTEMIC_STATUS[relation.type]} for ${relation.type}`);
        }
        if (from?.node_type === "signal") {
          const expectedList = relation.type === "SIGNAL_REFERENCES_CLAIM" ? from.claim_refs : from.evidence_refs;
          if (!expectedList?.includes(relation.to_ref)) addError(errors, path, "signal relation is not declared in node references");
        }
        if (from?.node_type === "diagnosis") {
          const expectedList = relation.type === "DIAGNOSIS_INTERPRETS_SIGNAL" ? from.signal_refs : from.evidence_refs;
          if (!expectedList?.includes(relation.to_ref)) addError(errors, path, "diagnosis relation is not declared in node references");
        }
      });
      const evidenceClaimEdges = candidate.relations.filter((relation) => (
        ["SUPPORTS_ATTRIBUTION", "SUPPORTS_CLAIM", "CONTRADICTS_CLAIM"].includes(relation.type)
      ));
      if (!evidenceClaimEdges.length) addError(errors, "relations", "at least one evidence-to-claim relation is required");

      candidate.nodes.filter((node) => node.node_type === "signal").forEach((node) => {
        node.claim_refs.forEach((ref) => {
          if (!relationKeys.has(relationKey("SIGNAL_REFERENCES_CLAIM", node.node_id, ref))) addError(errors, node.node_id, `missing claim relation to ${ref}`);
        });
        node.evidence_refs.forEach((ref) => {
          if (!relationKeys.has(relationKey("SIGNAL_GROUNDED_IN_EVIDENCE", node.node_id, ref))) addError(errors, node.node_id, `missing evidence relation to ${ref}`);
        });
      });
      const diagnosis = candidate.nodes.find((node) => node.node_type === "diagnosis");
      if (diagnosis) {
        const signalNodeIds = candidate.nodes
          .filter((node) => node.node_type === "signal")
          .map((node) => node.node_id)
          .sort();
        if (stableStringify([...diagnosis.signal_refs].sort()) !== stableStringify(signalNodeIds)) {
          addError(errors, diagnosis.node_id, "diagnosis must interpret every signal exactly once");
        }
        diagnosis.signal_refs.forEach((ref) => {
          if (!relationKeys.has(relationKey("DIAGNOSIS_INTERPRETS_SIGNAL", diagnosis.node_id, ref))) addError(errors, diagnosis.node_id, `missing signal relation to ${ref}`);
        });
        diagnosis.evidence_refs.forEach((ref) => {
          if (!relationKeys.has(relationKey("DIAGNOSIS_REFERENCES_EVIDENCE", diagnosis.node_id, ref))) addError(errors, diagnosis.node_id, `missing evidence relation to ${ref}`);
        });
      }
      const outcome = candidate.nodes.find((node) => node.node_type === "outcome");
      const gap = candidate.nodes.find((node) => node.node_type === "gap");
      const action = candidate.nodes.find((node) => node.node_type === "action");
      if (outcome && caseNode && !relationKeys.has(relationKey("OUTCOME_OF_CASE", outcome.node_id, caseNode.node_id))) addError(errors, "relations", "outcome is not linked to case");
      if (gap && diagnosis && !relationKeys.has(relationKey("GAP_IDENTIFIED_BY_DIAGNOSIS", gap.node_id, diagnosis.node_id))) addError(errors, "relations", "gap is not linked to diagnosis");
      if (action && gap && !relationKeys.has(relationKey("ACTION_ADDRESSES_GAP", action.node_id, gap.node_id))) addError(errors, "relations", "action is not linked to gap");
    }

    if (!Array.isArray(candidate.metrics) || candidate.metrics.length < 3 || candidate.metrics.length > 5) {
      addError(errors, "metrics", "three to five manual metrics are required");
    } else {
      const metricNames = new Set();
      candidate.metrics.forEach((metric, index) => {
        const path = `metrics[${index}]`;
        if (!sameKeys(metric, ["name", "value"]) || !METRICS.has(metric.name) || metricNames.has(metric.name)) {
          addError(errors, path, "unknown or duplicate metric");
          return;
        }
        metricNames.add(metric.name);
        const bounded = ["clarity", "verifiability", "viability"].includes(metric.name);
        if (bounded && (!Number.isInteger(metric.value) || metric.value < 0 || metric.value > 5)) addError(errors, `${path}.value`, "must be an integer from 0 to 5");
        if (metric.name === "open_points" && (!Number.isInteger(metric.value) || metric.value < 0)) addError(errors, `${path}.value`, "must be a non-negative integer");
        if (metric.name === "open_points" && metric.value > 1000000) addError(errors, `${path}.value`, "exceeds metric limit");
        if (metric.name === "time_to_draft_minutes" && (!Number.isFinite(metric.value) || metric.value < 0 || metric.value > 1000000)) addError(errors, `${path}.value`, "must be within the metric limit");
      });
    }
    if (!DECISIONS.has(candidate.iteration_decision)) addError(errors, "iteration_decision", "unknown decision");
    if (!isNonEmptyString(candidate.next_experiment)) addError(errors, "next_experiment", "required");
    const closureKeys = ["final_text", "verification_owner", "scope_and_deadlines", "open_points", "minimum_patch"];
    const validClosure = sameKeys(candidate.closure_check, closureKeys)
      && closureKeys.every((key) => typeof candidate.closure_check[key] === "boolean");
    if (!validClosure) addError(errors, "closure_check", "invalid closure checklist");
    if (candidate.state === "accepted" && validClosure
      && closureKeys.some((key) => candidate.closure_check[key] !== true)) {
      addError(errors, "closure_check", "accepted candidates require all closure checks");
    }
    validateHistory(candidate.history, candidate.state, candidate.created_at_utc, candidate.updated_at_utc, errors);
    return { valid: errors.length === 0, errors };
  }

  function safeNodeId(prefix, recordId) {
    const cleaned = normalizeString(recordId).replace(/[^A-Za-z0-9._:-]/g, "-");
    return `${prefix}:${cleaned}`.slice(0, 128);
  }

  function nextHistoryEventId(history) {
    let maximum = 0n;
    history.forEach((event) => {
      const match = /^history:(\d+)$/.exec(event.event_id);
      if (match) maximum = maximum > BigInt(match[1]) ? maximum : BigInt(match[1]);
    });
    const eventId = `history:${String(maximum + 1n).padStart(3, "0")}`;
    if (!isId(eventId)) throw new Error("History event ID space is exhausted");
    return eventId;
  }

  function candidateSnapshotMatchesLiveCase(candidate, liveCase, hashText) {
    const caseNode = candidate.nodes.find((node) => node.node_type === "case");
    if (!caseNode || !isObject(liveCase) || !Array.isArray(liveCase.claims)
      || !Array.isArray(liveCase.evidence) || !Array.isArray(liveCase.relationships)) return false;
    if (caseNode.case_id !== normalizeString(liveCase.case_id)
      || caseNode.core_version_ref !== normalizeString(liveCase.core_version_ref)
      || caseNode.revision_sha256 !== liveCase.revision_sha256) return false;

    const claimNodes = candidate.nodes.filter((node) => node.node_type === "claim");
    const evidenceNodes = candidate.nodes.filter((node) => node.node_type === "evidence");
    if (claimNodes.length !== liveCase.claims.length || evidenceNodes.length !== liveCase.evidence.length) return false;
    const claimsByRecord = new Map(claimNodes.map((node) => [node.record_id, node]));
    const evidenceByRecord = new Map(evidenceNodes.map((node) => [node.record_id, node]));
    if (claimsByRecord.size !== claimNodes.length || evidenceByRecord.size !== evidenceNodes.length) return false;

    for (const record of liveCase.claims) {
      const node = claimsByRecord.get(record.claim_id);
      const text = normalizeString(record.text);
      const sourceRef = safeSourceRef(record.source_ref);
      if (!node || !sourceRef || node.node_id !== safeNodeId("claim", record.claim_id)
        || node.text !== text || node.text_sha256 !== hashText(text)
        || node.source_ref !== sourceRef) return false;
    }
    for (const record of liveCase.evidence) {
      const node = evidenceByRecord.get(record.evidence_id);
      const text = normalizeString(record.text);
      const sourceRef = safeSourceRef(record.source_ref);
      const limitations = Array.isArray(record.limitations) ? record.limitations.map(normalizeString) : [];
      if (!node || !sourceRef || node.node_id !== safeNodeId("evidence", record.evidence_id)
        || node.text !== text || node.text_sha256 !== hashText(text)
        || node.source_ref !== sourceRef
        || stableStringify(node.limitations) !== stableStringify(limitations)) return false;
    }

    const expectedRelations = [];
    for (const relation of liveCase.relationships) {
      if (!isObject(relation) || !["SUPPORTS_ATTRIBUTION", "SUPPORTS_CLAIM", "CONTRADICTS_CLAIM"].includes(relation.type)) return false;
      const from = evidenceByRecord.get(relation.from_ref);
      const to = claimsByRecord.get(relation.to_ref);
      if (!from || !to) return false;
      expectedRelations.push(stableStringify({
        type: relation.type,
        from_ref: from.node_id,
        to_ref: to.node_id,
        origin: "imported",
        epistemic_status: RELATION_EPISTEMIC_STATUS[relation.type]
      }));
    }
    const actualRelations = candidate.relations
      .filter((relation) => ["SUPPORTS_ATTRIBUTION", "SUPPORTS_CLAIM", "CONTRADICTS_CLAIM"].includes(relation.type))
      .map((relation) => stableStringify({
        type: relation.type,
        from_ref: relation.from_ref,
        to_ref: relation.to_ref,
        origin: relation.origin,
        epistemic_status: relation.epistemic_status
      }));
    return stableStringify(expectedRelations.sort()) === stableStringify(actualRelations.sort());
  }

  function buildCandidate(input, options = {}) {
    const hashText = options.hashText;
    const nowValue = options.now === undefined ? new Date().toISOString() : options.now;
    if (typeof hashText !== "function") throw new Error("hashText dependency is required");
    if (typeof nowValue !== "string") throw new Error("A valid UTC creation timestamp is required");
    const now = normalizeString(nowValue);
    const capturedInput = snapshotJsonValue(input);
    if (!capturedInput.valid || !isObject(capturedInput.value)) {
      throw new Error("Learning candidate input must contain only own, plain JSON data");
    }
    const submitted = capturedInput.value;
    const requiredInputKeys = [
      "candidate_id", "case_record", "outcome", "signals", "diagnosis", "gap",
      "action", "metrics", "iteration_decision", "next_experiment", "closure_check"
    ];
    const allowedInputKeys = new Set([...requiredInputKeys, "creation_note"]);
    const inputShapeValid = requiredInputKeys.every((key) => Object.prototype.hasOwnProperty.call(submitted, key))
      && Object.keys(submitted).every((key) => allowedInputKeys.has(key))
      && typeof submitted.candidate_id === "string"
      && typeof submitted.outcome === "string"
      && typeof submitted.gap === "string"
      && typeof submitted.iteration_decision === "string"
      && typeof submitted.next_experiment === "string"
      && (submitted.creation_note === undefined || typeof submitted.creation_note === "string")
      && Array.isArray(submitted.signals)
      && submitted.signals.every((signal) => sameKeys(signal, ["text", "claim_refs", "evidence_refs"])
        && typeof signal.text === "string"
        && Array.isArray(signal.claim_refs) && signal.claim_refs.every((ref) => typeof ref === "string")
        && Array.isArray(signal.evidence_refs) && signal.evidence_refs.every((ref) => typeof ref === "string"))
      && sameKeys(submitted.diagnosis, ["text", "categories", "evidence_refs"])
      && typeof submitted.diagnosis.text === "string"
      && Array.isArray(submitted.diagnosis.categories)
      && submitted.diagnosis.categories.every((item) => typeof item === "string")
      && Array.isArray(submitted.diagnosis.evidence_refs)
      && submitted.diagnosis.evidence_refs.every((ref) => typeof ref === "string")
      && sameKeys(submitted.action, ["change", "reason", "verification_criterion"])
      && ["change", "reason", "verification_criterion"].every((key) => typeof submitted.action[key] === "string")
      && Array.isArray(submitted.metrics)
      && submitted.metrics.every((metric) => sameKeys(metric, ["name", "value"])
        && typeof metric.name === "string" && typeof metric.value === "number")
      && isObject(submitted.closure_check);
    if (!inputShapeValid) throw new Error("Learning candidate input shape is invalid");
    if (!isObject(submitted.case_record)) throw new Error("case_record is required");
    const caseRecord = ownCanonicalCaseRecord(submitted.case_record);
    if (!caseRecord) throw new Error("case_record must contain only own, plain JSON data");
    if (!isSha256(caseRecord.revision_sha256) || computeCaseRevision(caseRecord, { hashText }) !== caseRecord.revision_sha256) {
      throw new Error("case_record revision_sha256 does not match its canonical content");
    }
    const caseNodeId = safeNodeId("case", caseRecord.case_id);
    const claimMap = new Map();
    const evidenceMap = new Map();
    const nodes = [{
      node_id: caseNodeId,
      node_type: "case",
      case_id: normalizeString(caseRecord.case_id),
      core_version_ref: normalizeString(caseRecord.core_version_ref),
      revision_sha256: normalizeString(caseRecord.revision_sha256)
    }];
    (caseRecord.claims || []).forEach((record) => {
      const nodeId = safeNodeId("claim", record.claim_id);
      claimMap.set(record.claim_id, nodeId);
      const text = normalizeString(record.text);
      nodes.push({ node_id: nodeId, node_type: "claim", record_id: record.claim_id, text, text_sha256: hashText(text), source_ref: safeSourceRef(record.source_ref) });
    });
    (caseRecord.evidence || []).forEach((record) => {
      const nodeId = safeNodeId("evidence", record.evidence_id);
      evidenceMap.set(record.evidence_id, nodeId);
      const text = normalizeString(record.text);
      nodes.push({ node_id: nodeId, node_type: "evidence", record_id: record.evidence_id, text, text_sha256: hashText(text), source_ref: safeSourceRef(record.source_ref), limitations: (record.limitations || []).map(normalizeString) });
    });
    const outcomeId = "outcome:001";
    const diagnosisId = "diagnosis:001";
    const gapId = "gap:001";
    const actionId = "action:001";
    nodes.push({ node_id: outcomeId, node_type: "outcome", text: normalizeString(submitted.outcome) });
    const signalIds = [];
    submitted.signals.forEach((signal, index) => {
      const nodeId = `signal:${String(index + 1).padStart(3, "0")}`;
      signalIds.push(nodeId);
      nodes.push({
        node_id: nodeId,
        node_type: "signal",
        text: normalizeString(signal.text),
        claim_refs: (signal.claim_refs || []).map((ref) => claimMap.get(ref) || ref),
        evidence_refs: (signal.evidence_refs || []).map((ref) => evidenceMap.get(ref) || ref)
      });
    });
    const diagnosisEvidenceRefs = submitted.diagnosis.evidence_refs.map((ref) => evidenceMap.get(ref) || ref);
    nodes.push({ node_id: diagnosisId, node_type: "diagnosis", text: normalizeString(submitted.diagnosis.text), categories: [...submitted.diagnosis.categories], signal_refs: [...signalIds], evidence_refs: diagnosisEvidenceRefs });
    nodes.push({ node_id: gapId, node_type: "gap", text: normalizeString(submitted.gap) });
    nodes.push({ node_id: actionId, node_type: "action", change: normalizeString(submitted.action.change), reason: normalizeString(submitted.action.reason), verification_criterion: normalizeString(submitted.action.verification_criterion) });

    const relations = [];
    function addRelation(type, fromRef, toRef, epistemicStatus, origin = "human-authored") {
      relations.push({ relation_id: `relation:${String(relations.length + 1).padStart(3, "0")}`, type, from_ref: fromRef, to_ref: toRef, origin, epistemic_status: epistemicStatus });
    }
    addRelation("OUTCOME_OF_CASE", outcomeId, caseNodeId, "observation");
    (caseRecord.relationships || []).forEach((relation) => {
      const from = evidenceMap.get(relation.from_ref);
      const to = claimMap.get(relation.to_ref);
      if (!from || !to || !["SUPPORTS_ATTRIBUTION", "SUPPORTS_CLAIM", "CONTRADICTS_CLAIM"].includes(relation.type)) return;
      addRelation(relation.type, from, to, relation.type === "SUPPORTS_ATTRIBUTION" ? "submitted-claim" : "corroboration", "imported");
    });
    nodes.filter((node) => node.node_type === "signal").forEach((signal) => {
      signal.claim_refs.forEach((ref) => addRelation("SIGNAL_REFERENCES_CLAIM", signal.node_id, ref, "observation"));
      signal.evidence_refs.forEach((ref) => addRelation("SIGNAL_GROUNDED_IN_EVIDENCE", signal.node_id, ref, "observation"));
      addRelation("DIAGNOSIS_INTERPRETS_SIGNAL", diagnosisId, signal.node_id, "inference");
    });
    diagnosisEvidenceRefs.forEach((ref) => addRelation("DIAGNOSIS_REFERENCES_EVIDENCE", diagnosisId, ref, "inference"));
    addRelation("GAP_IDENTIFIED_BY_DIAGNOSIS", gapId, diagnosisId, "inference");
    addRelation("ACTION_ADDRESSES_GAP", actionId, gapId, "proposal");

    const candidate = {
      schema_version: SCHEMA_VERSION,
      candidate_id: normalizeString(submitted.candidate_id),
      method_ref: { path: METHOD_PATH, sha256: METHOD_SHA256 },
      authority: "local-non-canonical",
      case_ref: normalizeString(caseRecord.case_id),
      state: "draft",
      created_at_utc: now,
      updated_at_utc: now,
      nodes,
      relations,
      metrics: submitted.metrics.map((metric) => ({ name: metric.name, value: metric.value })),
      iteration_decision: submitted.iteration_decision,
      next_experiment: normalizeString(submitted.next_experiment),
      closure_check: { ...submitted.closure_check },
      history: [{ event_id: "history:001", at_utc: now, actor: "human-operator", action: "created", from_state: null, to_state: "draft", note: normalizeString(submitted.creation_note || "Created by the human operator as a local candidate.") }]
    };
    const validation = validateCandidate(candidate, { hashText });
    if (!validation.valid) throw new Error(`Invalid learning candidate: ${validation.errors.map((item) => `${item.path}: ${item.message}`).join("; ")}`);
    if (!candidateSnapshotMatchesLiveCase(candidate, caseRecord, hashText)) {
      throw new Error("Learning candidate snapshot does not match the supplied case record");
    }
    return canonicalValue(candidate);
  }

  function transitionCandidate(candidate, nextState, note, options = {}) {
    const hashText = options.hashText;
    const before = validateCandidate(candidate, { hashText });
    if (!before.valid) throw new Error("Cannot transition an invalid learning candidate");
    if (!STATES.has(nextState)) throw new Error("Unknown candidate state");
    if (!isNonEmptyString(note)) throw new Error("A human transition note is required");
    if (nextState === "accepted") {
      const closureKeys = ["final_text", "verification_owner", "scope_and_deadlines", "open_points", "minimum_patch"];
      if (closureKeys.some((key) => candidate.closure_check[key] !== true)) {
        throw new Error("All closure checks must be satisfied before local acceptance");
      }
      const liveBinding = evaluateFreshness(candidate, options.liveCase, { hashText, now: options.now });
      if (liveBinding.freshness !== "current") throw new Error("Only a current candidate can be accepted locally");
    }
    const fromState = candidate.state;
    const allowed = (
      (fromState === "draft" && ["accepted", "rejected"].includes(nextState))
      || (["accepted", "rejected"].includes(fromState) && nextState === "draft")
    );
    if (!allowed) throw new Error(`Forbidden state transition: ${fromState} -> ${nextState}`);
    const nowValue = options.now === undefined ? new Date().toISOString() : options.now;
    if (typeof nowValue !== "string") throw new Error("A valid UTC transition timestamp is required");
    const now = normalizeString(nowValue);
    const updated = canonicalValue(candidate);
    updated.state = nextState;
    updated.updated_at_utc = now;
    updated.history.push({ event_id: nextHistoryEventId(updated.history), at_utc: now, actor: "human-operator", action: "state-change", from_state: fromState, to_state: nextState, note: normalizeString(note) });
    const validation = validateCandidate(updated, { hashText });
    if (!validation.valid) throw new Error("State transition produced an invalid learning candidate");
    return canonicalValue(updated);
  }

  function evaluateFreshness(candidate, liveCase, options = {}) {
    const nowValue = options.now === undefined ? new Date().toISOString() : options.now;
    if (typeof nowValue !== "string") throw new Error("A valid UTC freshness timestamp is required");
    const checkedAt = normalizeString(nowValue);
    const hashText = options.hashText;
    if (!isTimestamp(checkedAt)) throw new Error("A valid UTC freshness timestamp is required");
    if (typeof hashText !== "function") {
      return { freshness: "invalid", checked_case_sha256: null, reason: "hash dependency is unavailable", checked_at_utc: checkedAt };
    }
    const candidateValidation = validateCandidate(candidate, { hashText });
    if (!candidateValidation.valid) {
      return { freshness: "invalid", checked_case_sha256: null, reason: "learning candidate is invalid", checked_at_utc: checkedAt };
    }
    const caseNode = candidate.nodes.find((node) => node.node_type === "case");
    const liveSnapshot = ownCanonicalCaseRecord(liveCase);
    if (!liveSnapshot) {
      return { freshness: "invalid", checked_case_sha256: null, reason: "live case is not own, plain JSON data", checked_at_utc: checkedAt };
    }
    if (liveSnapshot.case_id !== candidate.case_ref || liveSnapshot.case_id !== caseNode?.case_id) {
      return { freshness: "invalid", checked_case_sha256: liveSnapshot.revision_sha256 || null, reason: "case identity changed", checked_at_utc: checkedAt };
    }
    let computedRevision;
    try {
      computedRevision = computeCaseRevision(liveSnapshot, { hashText });
    } catch {
      return { freshness: "invalid", checked_case_sha256: null, reason: "case revision cannot be computed", checked_at_utc: checkedAt };
    }
    if (!isSha256(liveSnapshot.revision_sha256) || computedRevision !== liveSnapshot.revision_sha256) {
      return { freshness: "invalid", checked_case_sha256: computedRevision, reason: "declared case revision does not match current content", checked_at_utc: checkedAt };
    }
    const claimIds = new Set((liveSnapshot.claims || []).map((record) => record.claim_id));
    const evidenceIds = new Set((liveSnapshot.evidence || []).map((record) => record.evidence_id));
    const missing = candidate.nodes.some((node) => (
      (node.node_type === "claim" && !claimIds.has(node.record_id))
      || (node.node_type === "evidence" && !evidenceIds.has(node.record_id))
    ));
    if (missing) return { freshness: "invalid", checked_case_sha256: computedRevision, reason: "referenced claim or evidence is missing", checked_at_utc: checkedAt };
    if (computedRevision !== caseNode.revision_sha256) return { freshness: "stale", checked_case_sha256: computedRevision, reason: "case content changed", checked_at_utc: checkedAt };
    if (!candidateSnapshotMatchesLiveCase(candidate, liveSnapshot, hashText)) {
      return { freshness: "invalid", checked_case_sha256: computedRevision, reason: "candidate snapshot differs from the live case", checked_at_utc: checkedAt };
    }
    return { freshness: "current", checked_case_sha256: computedRevision, reason: "case identity, full snapshot and revision match", checked_at_utc: checkedAt };
  }

  function createStore() {
    return { store_version: STORE_VERSION, entries: [] };
  }

  function validateStore(store, options = {}) {
    if (typeof options.hashText !== "function") return false;
    if (!hasSafeJsonShape(store, 32, 2000000)) return false;
    const structurallyValid = sameKeys(store, ["store_version", "entries"])
      && store.store_version === STORE_VERSION
      && Array.isArray(store.entries)
      && store.entries.length <= MAX_ENTRIES
      && store.entries.every((entry) => sameKeys(entry, ["candidate", "binding"]));
    if (!structurallyValid) return false;
    const ids = store.entries.map((entry) => entry.candidate?.candidate_id);
    if (new Set(ids).size !== ids.length) return false;
    return store.entries.every((entry) => (
      byteLength(stableStringify(entry)) <= MAX_ENTRY_BYTES
      && validateBinding(entry.binding)
      && validateCandidate(entry.candidate, { hashText: options.hashText }).valid
      && bindingMatchesCandidate(entry.binding, entry.candidate)
    ));
  }

  function validateBinding(binding) {
    return sameKeys(binding, ["freshness", "checked_case_sha256", "reason", "checked_at_utc"])
      && ["current", "stale", "invalid"].includes(binding.freshness)
      && (binding.checked_case_sha256 === null || isSha256(binding.checked_case_sha256))
      && isNonEmptyString(binding.reason)
      && isTimestamp(binding.checked_at_utc);
  }

  function bindingMatchesCandidate(binding, candidate) {
    const caseNode = candidate.nodes.find((node) => node.node_type === "case");
    if (!caseNode) return false;
    if (binding.freshness === "current") return binding.checked_case_sha256 === caseNode.revision_sha256;
    if (binding.freshness === "stale") {
      return isSha256(binding.checked_case_sha256)
        && binding.checked_case_sha256 !== caseNode.revision_sha256;
    }
    return binding.freshness === "invalid";
  }

  function insertEntry(store, entry, options = {}) {
    if (!validateStore(store, { hashText: options.hashText })) throw new Error("Invalid learning store");
    if (!sameKeys(entry, ["candidate", "binding"])) throw new Error("Invalid learning entry");
    if (!validateBinding(entry.binding)) throw new Error("Invalid learning freshness binding");
    const validation = validateCandidate(entry.candidate, { hashText: options.hashText });
    if (!validation.valid) throw new Error("Invalid learning candidate cannot be stored");
    if (!bindingMatchesCandidate(entry.binding, entry.candidate)) throw new Error("Learning freshness binding does not match candidate revision");
    const maxEntries = boundedLimit(options.maxEntries, MAX_ENTRIES, "maxEntries");
    const maxEntryBytes = boundedLimit(options.maxEntryBytes, MAX_ENTRY_BYTES, "maxEntryBytes");
    if (byteLength(stableStringify(entry)) > maxEntryBytes) throw new Error("Learning candidate exceeds local size limit");
    const existing = store.entries.find((item) => item.candidate.candidate_id === entry.candidate.candidate_id);
    if (existing) {
      if (stableStringify(existing) === stableStringify(entry)) return canonicalValue(store);
      throw new Error("Candidate ID conflict; existing local record was not overwritten");
    }
    if (store.entries.length >= maxEntries) throw new Error("Learning store is full; export or delete records before saving another");
    return canonicalValue({ store_version: STORE_VERSION, entries: [...store.entries, entry] });
  }

  function deleteCaseEntries(store, caseId, options = {}) {
    if (typeof options.hashText !== "function") throw new Error("hashText dependency is required");
    if (!validateStore(store, { hashText: options.hashText })) throw new Error("Invalid learning store");
    const removed = store.entries.filter((entry) => entry.candidate.case_ref === caseId).length;
    return { removed, store: canonicalValue({ store_version: STORE_VERSION, entries: store.entries.filter((entry) => entry.candidate.case_ref !== caseId) }) };
  }

  function createExport(candidate, options = {}) {
    const hashText = options.hashText;
    if (typeof hashText !== "function") throw new Error("hashText dependency is required");
    const validation = validateCandidate(candidate, { hashText });
    if (!validation.valid) throw new Error("Invalid learning candidate cannot be exported");
    const nowValue = options.now === undefined ? new Date().toISOString() : options.now;
    if (typeof nowValue !== "string") throw new Error("A valid UTC export timestamp is required");
    const exportedAt = normalizeString(nowValue);
    if (!isTimestamp(exportedAt)) throw new Error("A valid UTC export timestamp is required");
    return canonicalValue({
      export_version: EXPORT_VERSION,
      candidate_sha256: hashText(stableStringify(candidate)),
      exported_at_utc: exportedAt,
      candidate: canonicalValue(candidate)
    });
  }

  function parseImport(text, options = {}) {
    const hashText = options.hashText;
    if (typeof hashText !== "function") throw new Error("hashText dependency is required");
    if (typeof text !== "string") throw new Error("Import must be a JSON string");
    const maxImportBytes = boundedLimit(options.maxImportBytes, MAX_IMPORT_BYTES, "maxImportBytes");
    if (byteLength(text) > maxImportBytes) throw new Error("Import exceeds 1 MiB limit");
    let payload;
    try { payload = JSON.parse(text); } catch { throw new Error("Import is not valid JSON"); }
    if (!hasSafeJsonShape(payload)) throw new Error("Import exceeds nesting, node, or Unicode safety limits");
    if (!sameKeys(payload, ["export_version", "candidate_sha256", "exported_at_utc", "candidate"])) throw new Error("Unknown or missing export properties");
    if (payload.export_version !== EXPORT_VERSION) throw new Error("Unsupported learning export version");
    if (!isTimestamp(payload.exported_at_utc)) throw new Error("Invalid export timestamp");
    if (hashText(stableStringify(payload.candidate)) !== payload.candidate_sha256) throw new Error("Learning export checksum mismatch");
    const validation = validateCandidate(payload.candidate, { hashText });
    if (!validation.valid) throw new Error(`Invalid imported candidate: ${validation.errors.map((item) => `${item.path}: ${item.message}`).join("; ")}`);
    return canonicalValue(payload.candidate);
  }

  globalThis.HUB_OPTIMUS_LEARNING_CANDIDATE_V1 = Object.freeze({
    schemaVersion: SCHEMA_VERSION,
    storeVersion: STORE_VERSION,
    exportVersion: EXPORT_VERSION,
    methodPath: METHOD_PATH,
    methodSha256: METHOD_SHA256,
    limits: Object.freeze({ maxEntries: MAX_ENTRIES, maxEntryBytes: MAX_ENTRY_BYTES, maxImportBytes: MAX_IMPORT_BYTES }),
    normalizeString,
    canonicalValue,
    stableStringify,
    hasSafeJsonShape,
    computeCaseRevision,
    validateCandidate,
    buildCandidate,
    transitionCandidate,
    evaluateFreshness,
    createStore,
    validateStore,
    insertEntry,
    deleteCaseEntries,
    createExport,
    parseImport
  });
})();
