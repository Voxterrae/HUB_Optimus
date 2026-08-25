(() => {
  "use strict";

  const SCHEMA_VERSION = "operator_claim_set.v1";
  const NORMALIZER_VERSION = "operator-source-bound-v2";
  const MAX_EXCERPTS = 5;
  const MAX_EXCERPT_CODE_POINTS = 480;
  const MAX_CLAIMS_PER_EXCERPT = 20;
  const MAX_TOTAL_CLAIMS = 20;
  const MAX_CLAIM_CODE_POINTS = 480;
  const MAX_CONFIRMATION_NOTE_CODE_POINTS = 500;
  const SHA256_EMPTY = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855";
  const SHA256_ABC = "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad";
  const TOP_LEVEL_KEYS = Object.freeze([
    "schema_version",
    "normalizer_version",
    "source_text_fingerprint",
    "groups",
    "confirmation"
  ]);
  const GROUP_KEYS = Object.freeze([
    "excerpt_id",
    "source_text_fingerprint",
    "span_start",
    "span_end",
    "exact_excerpt",
    "claims"
  ]);
  const CLAIM_KEYS = Object.freeze([
    "draft_id",
    "text",
    "origin",
    "source_quote_type"
  ]);
  const CONFIRMATION_KEYS = Object.freeze([
    "status",
    "selection_sha256",
    "claim_set_sha256",
    "confirmation_note",
    "confirmation_sha256"
  ]);
  const CLAIM_ORIGINS = new Set(["mechanical-proposal", "human-edited"]);
  const SOURCE_QUOTE_TYPES = new Set(["exact", "paraphrase"]);
  const ABBREVIATIONS = new Set([
    "art", "dra", "dr", "etc", "fig", "hr", "mr", "mrs", "ms", "no", "nr",
    "prof", "sr", "sra", "st", "vs"
  ]);
  const CLOSING_PUNCTUATION = new Set(["\"", "'", "’", "”", ")", "]", "}", "»", "›"]);
  const STRONG_BOUNDARIES = new Set(["!", "?", "。", "！", "？", "؟", ";", "；", "؛"]);
  const NO_SPACE_BOUNDARIES = new Set(["。", "！", "？", "؟", "；", "؛"]);

  function normalizeString(value) {
    if (typeof value !== "string") return "";
    return value.replace(/\r\n?/g, "\n").normalize("NFC");
  }

  function normalizeClaimText(value) {
    return normalizeString(value).trim();
  }

  function claimIdentityText(value) {
    return normalizeClaimText(value).replace(/\s+/gu, " ");
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

  function codePointLength(value) {
    return Array.from(value).length;
  }

  function isPlainObject(value) {
    if (!value || typeof value !== "object" || Array.isArray(value)) return false;
    const prototype = Object.getPrototypeOf(value);
    return prototype === Object.prototype || prototype === null;
  }

  function sameKeys(value, expected) {
    if (!isPlainObject(value)) return false;
    const actual = Object.keys(value).sort();
    const wanted = [...expected].sort();
    return actual.length === wanted.length
      && actual.every((key, index) => key === wanted[index]);
  }

  function isSha256(value) {
    return typeof value === "string" && /^[0-9a-f]{64}$/.test(value);
  }

  function isSourceFingerprint(value) {
    return typeof value === "string" && /^sha256:[0-9a-f]{64}$/.test(value);
  }

  function isExcerptId(value) {
    return typeof value === "string"
      && /^[A-Za-z][A-Za-z0-9._:-]{0,127}$/.test(value);
  }

  function canonicalValue(value) {
    if (typeof value === "string") return normalizeString(value);
    if (Array.isArray(value)) return value.map(canonicalValue);
    if (isPlainObject(value)) {
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

  function deepFreeze(value) {
    if (!value || typeof value !== "object" || Object.isFrozen(value)) return value;
    Object.freeze(value);
    Object.values(value).forEach(deepFreeze);
    return value;
  }

  function requireHashText(hashText) {
    if (typeof hashText !== "function") throw new Error("hashText dependency is required");
    let empty;
    let abc;
    try {
      empty = hashText("");
      abc = hashText("abc");
    } catch {
      throw new Error("hashText dependency must implement synchronous SHA-256");
    }
    if (empty !== SHA256_EMPTY || abc !== SHA256_ABC) {
      throw new Error("hashText dependency must implement synchronous SHA-256");
    }
    return hashText;
  }

  function sourceTextOf(value) {
    const hasText = Object.prototype.hasOwnProperty.call(value, "text");
    const hasExact = Object.prototype.hasOwnProperty.call(value, "exact_excerpt");
    if (hasText === hasExact) return null;
    return hasText ? value.text : value.exact_excerpt;
  }

  function readExcerpt(value, path, errors, { requireHumanSelection = false } = {}) {
    if (!isPlainObject(value)) {
      errors.push({ path, code: "malformed", message: "Excerpt must be a plain object" });
      return null;
    }
    const text = sourceTextOf(value);
    if (!isExcerptId(value.excerpt_id)) {
      errors.push({ path: `${path}.excerpt_id`, code: "malformed", message: "Invalid excerpt ID" });
    }
    if (!isSourceFingerprint(value.source_text_fingerprint)) {
      errors.push({ path: `${path}.source_text_fingerprint`, code: "malformed", message: "Invalid source fingerprint" });
    }
    if (!Number.isSafeInteger(value.span_start) || value.span_start < 0) {
      errors.push({ path: `${path}.span_start`, code: "malformed", message: "Invalid Unicode span start" });
    }
    if (!Number.isSafeInteger(value.span_end) || value.span_end <= value.span_start) {
      errors.push({ path: `${path}.span_end`, code: "malformed", message: "Invalid Unicode span end" });
    }
    if (typeof text !== "string" || !text || hasUnpairedSurrogate(text)) {
      errors.push({ path, code: "empty", message: "Exact excerpt is empty or has malformed Unicode" });
    } else {
      if (normalizeString(text) !== text) {
        errors.push({ path, code: "malformed", message: "Exact excerpt must be NFC with LF line endings" });
      }
      const length = codePointLength(text);
      if (length > MAX_EXCERPT_CODE_POINTS) {
        errors.push({ path, code: "over-limit", message: "Exact excerpt exceeds the Unicode length limit" });
      }
      if (Number.isSafeInteger(value.span_start)
        && Number.isSafeInteger(value.span_end)
        && value.span_end - value.span_start !== length) {
        errors.push({ path, code: "malformed", message: "Unicode span does not locate the exact excerpt" });
      }
      if (!/[\p{L}\p{N}]/u.test(text)) {
        errors.push({ path, code: "empty", message: "Exact excerpt has no claim-bearing text" });
      }
    }
    if (Object.prototype.hasOwnProperty.call(value, "span_unit")
      && value.span_unit !== "unicode-code-point") {
      errors.push({ path: `${path}.span_unit`, code: "malformed", message: "Unsupported span unit" });
    }
    if (requireHumanSelection && value.selection_origin !== "human-confirmed") {
      errors.push({ path: `${path}.selection_origin`, code: "unconfirmed", message: "Excerpt selection is not human-confirmed" });
    }
    if (Object.prototype.hasOwnProperty.call(value, "passage_scope")
      && !["complete-candidate-passage", "partial-source-passage"].includes(value.passage_scope)) {
      errors.push({ path: `${path}.passage_scope`, code: "malformed", message: "Unsupported passage scope" });
    }
    if (errors.some((error) => error.path === path || error.path.startsWith(`${path}.`))) return null;
    return {
      excerpt_id: value.excerpt_id,
      source_text_fingerprint: value.source_text_fingerprint,
      span_start: value.span_start,
      span_end: value.span_end,
      exact_excerpt: text
    };
  }

  function validateExcerptCollection(excerpts, { requireHumanSelection = false } = {}) {
    const errors = [];
    if (!Array.isArray(excerpts) || excerpts.length < 1) {
      return { valid: false, errors: [{ path: "$", code: "empty", message: "At least one excerpt is required" }], excerpts: [] };
    }
    if (excerpts.length > MAX_EXCERPTS) {
      return { valid: false, errors: [{ path: "$", code: "over-limit", message: "Too many excerpts" }], excerpts: [] };
    }
    const normalized = excerpts.map((excerpt, index) => (
      readExcerpt(excerpt, `$[${index}]`, errors, { requireHumanSelection })
    ));
    if (errors.length) return { valid: false, errors, excerpts: [] };

    const ids = new Set();
    const exactTexts = new Set();
    const fingerprint = normalized[0].source_text_fingerprint;
    normalized.forEach((excerpt, index) => {
      if (ids.has(excerpt.excerpt_id)) {
        errors.push({ path: `$[${index}].excerpt_id`, code: "duplicate", message: "Duplicate excerpt ID" });
      }
      ids.add(excerpt.excerpt_id);
      if (exactTexts.has(excerpt.exact_excerpt)) {
        errors.push({ path: `$[${index}].exact_excerpt`, code: "duplicate", message: "Duplicate exact excerpt" });
      }
      exactTexts.add(excerpt.exact_excerpt);
      if (excerpt.source_text_fingerprint !== fingerprint) {
        errors.push({ path: `$[${index}].source_text_fingerprint`, code: "malformed", message: "Mixed source fingerprints are not allowed" });
      }
      normalized.slice(0, index).forEach((previous) => {
        if (excerpt.span_start < previous.span_end && excerpt.span_end > previous.span_start) {
          errors.push({ path: `$[${index}]`, code: "duplicate", message: "Overlapping excerpt spans are not allowed" });
        }
      });
    });
    return { valid: errors.length === 0, errors, excerpts: errors.length ? [] : normalized };
  }

  function selectionMaterial(excerpts) {
    return excerpts.map((excerpt) => ({
      excerpt_id: excerpt.excerpt_id,
      source_text_fingerprint: excerpt.source_text_fingerprint,
      span_start: excerpt.span_start,
      span_end: excerpt.span_end,
      exact_excerpt: excerpt.exact_excerpt
    }));
  }

  function computeSelectionSha256(excerpts, options = {}) {
    const hashText = requireHashText(options.hashText);
    const collection = validateExcerptCollection(excerpts, {
      requireHumanSelection: options.requireHumanSelection === true
    });
    if (!collection.valid) {
      throw new Error(`Invalid excerpt selection: ${collection.errors.map((error) => error.message).join("; ")}`);
    }
    return hashText(stableStringify(selectionMaterial(collection.excerpts)));
  }

  function nextNonSpace(points, start) {
    for (let index = start; index < points.length; index += 1) {
      if (!/\s/u.test(points[index])) return { value: points[index], index };
    }
    return null;
  }

  function previousToken(points, periodIndex) {
    let start = periodIndex - 1;
    while (start >= 0 && !/[\s!?。！？؟؛;；]/u.test(points[start])) start -= 1;
    return points.slice(start + 1, periodIndex).join("");
  }

  function asciiPeriodIsBoundary(points, index, afterClosers) {
    const previous = points[index - 1] || "";
    const immediateNext = points[index + 1] || "";
    if (/\p{N}/u.test(previous) && /\p{N}/u.test(immediateNext)) return false;
    const next = nextNonSpace(points, afterClosers);
    if (!next) return true;
    if (next.index === afterClosers) return false;
    const token = previousToken(points, index);
    if (/^(?:\p{L}\.)+\p{L}$/u.test(token)) return false;
    if (/^\p{L}$/u.test(token) && /^\p{L}$/u.test(next.value)) return false;
    if (ABBREVIATIONS.has(token.toLowerCase())) return false;
    return true;
  }

  function boundaryEnd(points, index) {
    const point = points[index];
    if (point === "\n") return index;
    if (point !== "." && !STRONG_BOUNDARIES.has(point)) return null;
    let end = index + 1;
    while (end < points.length && CLOSING_PUNCTUATION.has(points[end])) end += 1;
    if (point === "." && !asciiPeriodIsBoundary(points, index, end)) return null;
    if (end < points.length && !/\s/u.test(points[end]) && !NO_SPACE_BOUNDARIES.has(point)) return null;
    return end;
  }

  function proposeTexts(exactExcerpt) {
    const points = Array.from(exactExcerpt);
    const proposed = [];
    let start = 0;
    for (let index = 0; index < points.length; index += 1) {
      const end = boundaryEnd(points, index);
      if (end === null) continue;
      const text = normalizeClaimText(points.slice(start, end).join(""));
      if (text) proposed.push(text);
      start = end;
      while (start < points.length && /\s/u.test(points[start])) start += 1;
      index = start - 1;
    }
    const tail = normalizeClaimText(points.slice(start).join(""));
    if (tail) proposed.push(tail);
    return proposed;
  }

  function claimId(sourceFingerprint, excerptId, text, hashText) {
    return `claim-${hashText(stableStringify({
      source_text_fingerprint: sourceFingerprint,
      excerpt_id: excerptId,
      text: claimIdentityText(text)
    }))}`;
  }

  function computeDraftId(material, options = {}) {
    const hashText = requireHashText(options.hashText);
    if (!isPlainObject(material)
      || !isSourceFingerprint(material.source_text_fingerprint)
      || !isExcerptId(material.excerpt_id)
      || typeof material.text !== "string"
      || hasUnpairedSurrogate(material.text)) {
      throw new Error("Invalid claim ID material");
    }
    const text = normalizeClaimText(material.text);
    if (!text || !/[\p{L}\p{N}]/u.test(text) || codePointLength(text) > MAX_CLAIM_CODE_POINTS) {
      throw new Error("Invalid claim ID material");
    }
    return claimId(material.source_text_fingerprint, material.excerpt_id, text, hashText);
  }

  function proposeClaimSet(excerpts, options = {}) {
    const hashText = requireHashText(options.hashText);
    const collection = validateExcerptCollection(excerpts, { requireHumanSelection: true });
    if (!collection.valid) {
      throw new Error(`Invalid excerpt selection: ${collection.errors.map((error) => error.message).join("; ")}`);
    }
    let totalClaims = 0;
    const groups = collection.excerpts.map((excerpt) => {
      const texts = proposeTexts(excerpt.exact_excerpt);
      if (!texts.length) throw new Error("Excerpt produced no claim proposal");
      if (texts.length > MAX_CLAIMS_PER_EXCERPT) {
        throw new Error("Excerpt exceeds the claim proposal limit");
      }
      totalClaims += texts.length;
      if (totalClaims > MAX_TOTAL_CLAIMS) throw new Error("Claim set exceeds the total claim limit");
      return {
        excerpt_id: excerpt.excerpt_id,
        source_text_fingerprint: excerpt.source_text_fingerprint,
        span_start: excerpt.span_start,
        span_end: excerpt.span_end,
        exact_excerpt: excerpt.exact_excerpt,
        claims: texts.map((text) => ({
          draft_id: claimId(excerpt.source_text_fingerprint, excerpt.excerpt_id, text, hashText),
          text,
          origin: "mechanical-proposal",
          source_quote_type: "exact"
        }))
      };
    });
    const result = {
      schema_version: SCHEMA_VERSION,
      normalizer_version: NORMALIZER_VERSION,
      source_text_fingerprint: collection.excerpts[0].source_text_fingerprint,
      groups,
      confirmation: null
    };
    const validation = validateClaimSet(result, { hashText, requireConfirmed: false });
    if (!validation.valid) throw new Error(`Invalid proposed claim set: ${validation.errors.map((error) => error.message).join("; ")}`);
    return canonicalValue(result);
  }

  function baseClaimSet(value) {
    return {
      schema_version: value.schema_version,
      normalizer_version: value.normalizer_version,
      source_text_fingerprint: value.source_text_fingerprint,
      groups: value.groups,
      confirmation: null
    };
  }

  function validateClaimSet(value, options = {}) {
    const errors = [];
    let hashText;
    try {
      hashText = requireHashText(options.hashText);
    } catch (error) {
      return { valid: false, errors: [{ path: "$", code: "malformed", message: error.message }] };
    }
    if (!sameKeys(value, TOP_LEVEL_KEYS)) {
      return { valid: false, errors: [{ path: "$", code: "malformed", message: "Unknown or missing claim-set properties" }] };
    }
    if (value.schema_version !== SCHEMA_VERSION) {
      errors.push({ path: "$.schema_version", code: "malformed", message: "Unsupported claim-set schema" });
    }
    if (value.normalizer_version !== NORMALIZER_VERSION) {
      errors.push({ path: "$.normalizer_version", code: "malformed", message: "Unsupported claim normalizer" });
    }
    if (!isSourceFingerprint(value.source_text_fingerprint)) {
      errors.push({ path: "$.source_text_fingerprint", code: "malformed", message: "Invalid source fingerprint" });
    }
    if (!Array.isArray(value.groups) || value.groups.length < 1) {
      errors.push({ path: "$.groups", code: "empty", message: "At least one claim group is required" });
    } else if (value.groups.length > MAX_EXCERPTS) {
      errors.push({ path: "$.groups", code: "over-limit", message: "Too many claim groups" });
    }

    const groups = [];
    const claimIds = new Set();
    let totalClaims = 0;
    if (Array.isArray(value.groups)) value.groups.forEach((group, groupIndex) => {
      const groupPath = `$.groups[${groupIndex}]`;
      if (!sameKeys(group, GROUP_KEYS)) {
        errors.push({ path: groupPath, code: "malformed", message: "Unknown or missing claim-group properties" });
        return;
      }
      const excerptErrors = [];
      const excerpt = readExcerpt(group, groupPath, excerptErrors);
      errors.push(...excerptErrors);
      if (excerpt && excerpt.source_text_fingerprint !== value.source_text_fingerprint) {
        errors.push({ path: `${groupPath}.source_text_fingerprint`, code: "stale", message: "Claim group source fingerprint is stale" });
      }
      if (!Array.isArray(group.claims) || group.claims.length < 1) {
        errors.push({ path: `${groupPath}.claims`, code: "empty", message: "At least one claim is required per excerpt" });
      } else if (group.claims.length > MAX_CLAIMS_PER_EXCERPT) {
        errors.push({ path: `${groupPath}.claims`, code: "over-limit", message: "Too many claims for one excerpt" });
      }
      if (excerpt) groups.push(excerpt);
      if (!Array.isArray(group.claims)) return;
      const groupClaimTexts = new Set();
      totalClaims += group.claims.length;
      group.claims.forEach((claim, claimIndex) => {
        const claimPath = `${groupPath}.claims[${claimIndex}]`;
        if (!sameKeys(claim, CLAIM_KEYS)) {
          errors.push({ path: claimPath, code: "malformed", message: "Unknown or missing claim properties" });
          return;
        }
        const text = normalizeClaimText(claim.text);
        const identityText = claimIdentityText(claim.text);
        if (!text || hasUnpairedSurrogate(claim.text) || !/[\p{L}\p{N}]/u.test(text)) {
          errors.push({ path: `${claimPath}.text`, code: "empty", message: "Claim text is empty or malformed" });
        } else if (claim.text !== text) {
          errors.push({ path: `${claimPath}.text`, code: "malformed", message: "Claim text is not canonical" });
        } else if (codePointLength(text) > MAX_CLAIM_CODE_POINTS) {
          errors.push({ path: `${claimPath}.text`, code: "over-limit", message: "Claim text exceeds the Unicode length limit" });
        }
        if (!CLAIM_ORIGINS.has(claim.origin)) {
          errors.push({ path: `${claimPath}.origin`, code: "malformed", message: "Invalid claim origin" });
        }
        if (!SOURCE_QUOTE_TYPES.has(claim.source_quote_type)) {
          errors.push({ path: `${claimPath}.source_quote_type`, code: "malformed", message: "Claim must explicitly mark exact text or paraphrase" });
        }
        if (claim.source_quote_type === "paraphrase" && claim.origin !== "human-edited") {
          errors.push({ path: claimPath, code: "malformed", message: "A paraphrase must be explicitly human-edited" });
        }
        if (excerpt && claim.source_quote_type === "exact" && !excerpt.exact_excerpt.includes(text)) {
          errors.push({ path: claimPath, code: "malformed", message: "Exact claim text is not present in its excerpt" });
        }
        if (claim.origin === "mechanical-proposal" && claim.source_quote_type !== "exact") {
          errors.push({ path: claimPath, code: "malformed", message: "Mechanical proposals must preserve exact source text" });
        }
        if (excerpt && text) {
          const expectedId = claimId(excerpt.source_text_fingerprint, excerpt.excerpt_id, text, hashText);
          if (claim.draft_id !== expectedId) {
            errors.push({ path: `${claimPath}.draft_id`, code: "malformed", message: "Claim ID does not match canonical claim material" });
          }
        }
        if (groupClaimTexts.has(identityText)) {
          errors.push({ path: `${claimPath}.text`, code: "duplicate", message: "Duplicate claim text within one excerpt" });
        }
        groupClaimTexts.add(identityText);
        if (claimIds.has(claim.draft_id)) {
          errors.push({ path: `${claimPath}.draft_id`, code: "duplicate", message: "Duplicate claim ID" });
        }
        claimIds.add(claim.draft_id);
      });
    });
    if (totalClaims > MAX_TOTAL_CLAIMS) {
      errors.push({ path: "$.groups", code: "over-limit", message: "Claim set exceeds the total claim limit" });
    }

    if (Array.isArray(value.groups) && groups.length === value.groups.length) {
      const collection = validateExcerptCollection(groups);
      if (!collection.valid) {
        collection.errors.forEach((error) => errors.push({
          path: error.path.replace(/^\$/, "$.groups"),
          code: error.code,
          message: error.message
        }));
      }
    }

    let selectionSha256 = null;
    if (groups.length && Array.isArray(value.groups) && groups.length === value.groups.length) {
      try { selectionSha256 = computeSelectionSha256(groups, { hashText }); } catch { selectionSha256 = null; }
    }
    if (options.expectedSourceFingerprint !== undefined) {
      if (!isSourceFingerprint(options.expectedSourceFingerprint)) {
        errors.push({ path: "$", code: "malformed", message: "Invalid expected source fingerprint" });
      } else if (value.source_text_fingerprint !== options.expectedSourceFingerprint) {
        errors.push({ path: "$.source_text_fingerprint", code: "stale", message: "Claim set is stale for the current source" });
      }
    }
    if (options.expectedSelectionSha256 !== undefined) {
      if (!isSha256(options.expectedSelectionSha256)) {
        errors.push({ path: "$", code: "malformed", message: "Invalid expected selection checksum" });
      } else if (!selectionSha256 || selectionSha256 !== options.expectedSelectionSha256) {
        errors.push({ path: "$.groups", code: "stale", message: "Claim set is stale for the current excerpt selection" });
      }
    }

    const requireConfirmed = options.requireConfirmed !== false;
    if (value.confirmation === null) {
      if (requireConfirmed) {
        errors.push({ path: "$.confirmation", code: "unconfirmed", message: "Human claim-set confirmation is required" });
      }
    } else if (!sameKeys(value.confirmation, CONFIRMATION_KEYS)) {
      errors.push({ path: "$.confirmation", code: "malformed", message: "Unknown or missing confirmation properties" });
    } else {
      const confirmation = value.confirmation;
      if (confirmation.status !== "human-confirmed") {
        errors.push({ path: "$.confirmation.status", code: "unconfirmed", message: "Claim set is not human-confirmed" });
      }
      if (!isSha256(confirmation.selection_sha256) || confirmation.selection_sha256 !== selectionSha256) {
        errors.push({ path: "$.confirmation.selection_sha256", code: "stale", message: "Confirmation is stale for the excerpt selection" });
      }
      const expectedClaimSetSha = hashText(stableStringify(baseClaimSet(value)));
      if (!isSha256(confirmation.claim_set_sha256) || confirmation.claim_set_sha256 !== expectedClaimSetSha) {
        errors.push({ path: "$.confirmation.claim_set_sha256", code: "stale", message: "Confirmation is stale for the claim set" });
      }
      if (confirmation.confirmation_note !== null
        && (typeof confirmation.confirmation_note !== "string"
          || !confirmation.confirmation_note
          || normalizeString(confirmation.confirmation_note).trim() !== confirmation.confirmation_note
          || hasUnpairedSurrogate(confirmation.confirmation_note)
          || codePointLength(confirmation.confirmation_note) > MAX_CONFIRMATION_NOTE_CODE_POINTS)) {
        errors.push({ path: "$.confirmation.confirmation_note", code: "malformed", message: "Invalid confirmation note" });
      }
      const expectedConfirmationSha = hashText(stableStringify({
        status: "human-confirmed",
        selection_sha256: selectionSha256,
        claim_set_sha256: expectedClaimSetSha,
        confirmation_note: confirmation.confirmation_note
      }));
      if (!isSha256(confirmation.confirmation_sha256)
        || confirmation.confirmation_sha256 !== expectedConfirmationSha) {
        errors.push({ path: "$.confirmation.confirmation_sha256", code: "stale", message: "Confirmation checksum does not match" });
      }
    }
    return { valid: errors.length === 0, errors };
  }

  function confirmClaimSet(value, options = {}) {
    const hashText = requireHashText(options.hashText);
    const validation = validateClaimSet(value, {
      hashText,
      requireConfirmed: false,
      expectedSourceFingerprint: options.expectedSourceFingerprint,
      expectedSelectionSha256: options.expectedSelectionSha256
    });
    if (!validation.valid) {
      throw new Error(`Invalid claim set: ${validation.errors.map((error) => error.message).join("; ")}`);
    }
    if (value.confirmation !== null) throw new Error("Claim set is already confirmed");
    let confirmationNote = null;
    if (options.confirmationNote !== undefined && options.confirmationNote !== null) {
      if (typeof options.confirmationNote !== "string" || hasUnpairedSurrogate(options.confirmationNote)) {
        throw new Error("Invalid confirmation note");
      }
      confirmationNote = normalizeString(options.confirmationNote).trim();
      if (!confirmationNote || codePointLength(confirmationNote) > MAX_CONFIRMATION_NOTE_CODE_POINTS) {
        throw new Error("Invalid confirmation note");
      }
    }
    const canonical = canonicalValue(baseClaimSet(value));
    const selectionSha256 = computeSelectionSha256(canonical.groups, { hashText });
    const claimSetSha256 = hashText(stableStringify(canonical));
    const confirmation = {
      status: "human-confirmed",
      selection_sha256: selectionSha256,
      claim_set_sha256: claimSetSha256,
      confirmation_note: confirmationNote,
      confirmation_sha256: hashText(stableStringify({
        status: "human-confirmed",
        selection_sha256: selectionSha256,
        claim_set_sha256: claimSetSha256,
        confirmation_note: confirmationNote
      }))
    };
    const confirmed = canonicalValue({ ...canonical, confirmation });
    const confirmedValidation = validateClaimSet(confirmed, {
      hashText,
      requireConfirmed: true,
      expectedSourceFingerprint: options.expectedSourceFingerprint,
      expectedSelectionSha256: options.expectedSelectionSha256
    });
    if (!confirmedValidation.valid) {
      throw new Error(`Invalid confirmed claim set: ${confirmedValidation.errors.map((error) => error.message).join("; ")}`);
    }
    return deepFreeze(confirmed);
  }

  globalThis.HUB_OPTIMUS_CLAIM_DECOMPOSITION_V1 = Object.freeze({
    schemaVersion: SCHEMA_VERSION,
    normalizerVersion: NORMALIZER_VERSION,
    limits: Object.freeze({
      maxExcerpts: MAX_EXCERPTS,
      maxExcerptCodePoints: MAX_EXCERPT_CODE_POINTS,
      maxClaimsPerExcerpt: MAX_CLAIMS_PER_EXCERPT,
      maxTotalClaims: MAX_TOTAL_CLAIMS,
      maxClaimCodePoints: MAX_CLAIM_CODE_POINTS
    }),
    normalizeClaimText,
    canonicalValue,
    stableStringify,
    computeSelectionSha256,
    computeDraftId,
    proposeClaimSet,
    validateClaimSet,
    confirmClaimSet
  });
})();
