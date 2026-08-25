import json
import shutil
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "site" / "operator" / "claim-decomposition.v1.js"
NODE = shutil.which("node")


def run_module(body: str) -> str:
    assert NODE, "Node.js is required for Operator claim-decomposition tests"
    harness = r"""
const fs = require("fs");
const vm = require("vm");
const crypto = require("crypto");
vm.runInThisContext(fs.readFileSync(process.env.CLAIM_MODULE, "utf8"));
const api = globalThis.HUB_OPTIMUS_CLAIM_DECOMPOSITION_V1;
const hashText = (value) => crypto.createHash("sha256").update(value, "utf8").digest("hex");
const clone = (value) => JSON.parse(JSON.stringify(value));
function assert(condition, message) {
  if (!condition) throw new Error(message);
}
function mustThrow(callback, fragment) {
  try {
    callback();
  } catch (error) {
    if (fragment && !String(error.message).toLowerCase().includes(fragment.toLowerCase())) {
      throw new Error(`Expected error containing ${fragment}, got: ${error.message}`);
    }
    return;
  }
  throw new Error(`Expected error containing ${fragment || "an error"}`);
}
function sourceFingerprint(text) {
  return `sha256:${hashText(text)}`;
}
function excerpt(text, fingerprint, excerptId = "excerpt-001", spanStart = 0) {
  return {
    excerpt_id: excerptId,
    text,
    span_start: spanStart,
    span_end: spanStart + Array.from(text).length,
    span_unit: "unicode-code-point",
    source_text_fingerprint: fingerprint,
    passage_scope: "complete-candidate-passage",
    selection_origin: "human-confirmed"
  };
}
"""
    completed = subprocess.run(
        [NODE, "-e", harness + body],
        check=False,
        capture_output=True,
        text=True,
        env={"CLAIM_MODULE": str(MODULE)},
    )
    assert completed.returncode == 0, completed.stderr
    return completed.stdout


def test_claim_module_is_local_deterministic_and_exposes_the_versioned_api():
    source = MODULE.read_text(encoding="utf-8")
    for forbidden in (
        "Intl.Segmenter",
        "fetch(",
        "XMLHttpRequest",
        "Math.random",
        "new Date",
        "Date.now",
    ):
        assert forbidden not in source

    output = run_module(
        r"""
assert(api && Object.isFrozen(api), "versioned global API is missing or mutable");
assert(api.schemaVersion === "operator_claim_set.v1", "schema version drifted");
assert(api.normalizerVersion === "operator-source-bound-v2", "normalizer version drifted");
for (const name of [
  "computeSelectionSha256",
  "computeDraftId",
  "proposeClaimSet",
  "validateClaimSet",
  "confirmClaimSet"
]) assert(typeof api[name] === "function", `${name} is not exposed`);
process.stdout.write(JSON.stringify(api.limits));
"""
    )
    limits = json.loads(output)
    assert limits == {
        "maxExcerpts": 5,
        "maxExcerptCodePoints": 480,
        "maxClaimsPerExcerpt": 20,
        "maxTotalClaims": 20,
        "maxClaimCodePoints": 480,
    }


@pytest.mark.skipif(NODE is None, reason="Node.js is required")
def test_proposals_are_unicode_safe_exact_and_multi_claim_per_excerpt():
    output = run_module(
        r"""
const first = "Dr. Álvarez informó un cambio del 2.5%. La medida no está aprobada; otra revisión sigue abierta.";
const second = "该来源记录了第一项陈述。第二项仍不确定！ العربية تبقى محفوظة؟";
const completeSource = `${first}\n${second}`;
const fingerprint = sourceFingerprint(completeSource);
const selected = [
  excerpt(first, fingerprint),
  excerpt(second, fingerprint, "excerpt-002", Array.from(first).length + 1)
];
const firstSet = api.proposeClaimSet(selected, {hashText});
const secondSet = api.proposeClaimSet(clone(selected), {hashText});
assert(JSON.stringify(firstSet) === JSON.stringify(secondSet), "same input was not byte-stable");
assert(firstSet.groups.length === 2, "excerpt grouping changed");
assert(firstSet.groups[0].claims.length === 3, "period/semicolon proposals were not decomposed");
assert(firstSet.groups[1].claims.length === 3, "CJK/Arabic boundaries were not decomposed");
assert(firstSet.groups[0].claims[0].text.includes("Dr. Álvarez"), "abbreviation was split");
assert(firstSet.groups[0].claims[0].text.includes("2.5%"), "decimal was split");
for (const group of firstSet.groups) {
  assert(group.source_text_fingerprint === fingerprint, "source fingerprint was lost");
  assert(group.exact_excerpt === selected.find((item) => item.excerpt_id === group.excerpt_id).text,
    "exact excerpt provenance changed");
  assert(group.span_end - group.span_start === Array.from(group.exact_excerpt).length,
    "Unicode code-point span changed");
  for (const claim of group.claims) {
    assert(claim.origin === "mechanical-proposal", "proposal origin changed");
    assert(claim.source_quote_type === "exact", "proposal was mislabeled as a paraphrase");
    assert(group.exact_excerpt.includes(claim.text), "exact proposal is absent from its excerpt");
    assert(/^claim-[0-9a-f]{64}$/.test(claim.draft_id), "claim ID is not a full SHA-256 ID");
  }
}
assert(firstSet.confirmation === null, "proposal silently confirmed itself");
assert(api.computeSelectionSha256(selected, {hashText, requireHumanSelection: true})
  === api.computeSelectionSha256(firstSet.groups, {hashText}), "selection binding changed across representations");
process.stdout.write(JSON.stringify(firstSet));
"""
    )
    claim_set = json.loads(output)
    assert claim_set["schema_version"] == "operator_claim_set.v1"
    assert claim_set["normalizer_version"] == "operator-source-bound-v2"


@pytest.mark.skipif(NODE is None, reason="Node.js is required")
def test_human_paraphrases_have_explicit_markers_and_deterministic_ids():
    run_module(
        r"""
const text = "The source attributes one decision to the council. A second review remains pending.";
const fingerprint = sourceFingerprint(text);
const proposed = api.proposeClaimSet([excerpt(text, fingerprint)], {hashText});
const edited = clone(proposed);
const claim = edited.groups[0].claims[0];
claim.text = "The source attributes a decision to the council.";
claim.origin = "human-edited";
claim.source_quote_type = "paraphrase";
claim.draft_id = api.computeDraftId({
  source_text_fingerprint: fingerprint,
  excerpt_id: edited.groups[0].excerpt_id,
  text: claim.text
}, {hashText});

const draftValidation = api.validateClaimSet(edited, {hashText, requireConfirmed: false});
assert(draftValidation.valid, JSON.stringify(draftValidation.errors));
const defaultValidation = api.validateClaimSet(edited, {hashText});
assert(!defaultValidation.valid
  && defaultValidation.errors.some((error) => error.code === "unconfirmed"),
  "unconfirmed human edits passed the default gate");

const alternateSpacingId = api.computeDraftId({
  source_text_fingerprint: fingerprint,
  excerpt_id: edited.groups[0].excerpt_id,
  text: "The source  attributes a decision to the council."
}, {hashText});
assert(alternateSpacingId === claim.draft_id, "claim identity was not based on normalized text");

const wrongMarker = clone(edited);
wrongMarker.groups[0].claims[0].origin = "mechanical-proposal";
assert(!api.validateClaimSet(wrongMarker, {hashText, requireConfirmed: false}).valid,
  "a mechanical paraphrase passed validation");
const falseQuote = clone(edited);
falseQuote.groups[0].claims[0].source_quote_type = "exact";
assert(!api.validateClaimSet(falseQuote, {hashText, requireConfirmed: false}).valid,
  "a paraphrase was accepted as exact source text");
"""
    )


@pytest.mark.skipif(NODE is None, reason="Node.js is required")
def test_confirmation_is_deterministic_deeply_immutable_and_tamper_evident():
    run_module(
        r"""
const text = "One claim is recorded. Another claim remains uncertain.";
const fingerprint = sourceFingerprint(text);
const selected = [excerpt(text, fingerprint)];
const selectionSha256 = api.computeSelectionSha256(selected, {hashText, requireHumanSelection: true});
const proposedA = api.proposeClaimSet(selected, {hashText});
const proposedB = api.proposeClaimSet(clone(selected), {hashText});
const options = {
  hashText,
  confirmationNote: "Reviewed by the human operator.",
  expectedSourceFingerprint: fingerprint,
  expectedSelectionSha256: selectionSha256
};
const confirmedA = api.confirmClaimSet(proposedA, options);
const confirmedB = api.confirmClaimSet(proposedB, options);
assert(JSON.stringify(confirmedA) === JSON.stringify(confirmedB), "confirmation was not deterministic");
assert(confirmedA.confirmation.status === "human-confirmed", "confirmation status missing");
assert(/^[0-9a-f]{64}$/.test(confirmedA.confirmation.confirmation_sha256),
  "deterministic confirmation checksum missing");
assert(Object.isFrozen(confirmedA)
  && Object.isFrozen(confirmedA.groups)
  && Object.isFrozen(confirmedA.groups[0])
  && Object.isFrozen(confirmedA.groups[0].claims)
  && Object.isFrozen(confirmedA.groups[0].claims[0])
  && Object.isFrozen(confirmedA.confirmation), "confirmed claim set is not deeply immutable");
const validation = api.validateClaimSet(confirmedA, {
  hashText,
  expectedSourceFingerprint: fingerprint,
  expectedSelectionSha256: selectionSha256
});
assert(validation.valid, JSON.stringify(validation.errors));

const tampered = clone(confirmedA);
tampered.groups[0].claims[0].text = "A changed claim.";
tampered.groups[0].claims[0].origin = "human-edited";
tampered.groups[0].claims[0].source_quote_type = "paraphrase";
tampered.groups[0].claims[0].draft_id = api.computeDraftId({
  source_text_fingerprint: fingerprint,
  excerpt_id: tampered.groups[0].excerpt_id,
  text: tampered.groups[0].claims[0].text
}, {hashText});
const tamperedValidation = api.validateClaimSet(tampered, {hashText});
assert(!tamperedValidation.valid
  && tamperedValidation.errors.some((error) => error.code === "stale"),
  "post-confirmation claim edits were not detected");
mustThrow(() => api.confirmClaimSet(confirmedA, options), "already confirmed");
"""
    )


@pytest.mark.skipif(NODE is None, reason="Node.js is required")
def test_empty_duplicate_malformed_over_limit_and_unconfirmed_inputs_fail_closed():
    run_module(
        r"""
mustThrow(() => api.proposeClaimSet([], {hashText}), "at least one excerpt");
const text = "A valid source sentence with enough content.";
const fingerprint = sourceFingerprint(text);
const valid = excerpt(text, fingerprint);
mustThrow(() => api.proposeClaimSet([{...valid, selection_origin: "mechanical"}], {hashText}), "human-confirmed");
mustThrow(() => api.proposeClaimSet([valid, {...valid}], {hashText}), "duplicate");
mustThrow(() => api.proposeClaimSet([{...valid, text: "\ud800"}], {hashText}), "malformed unicode");
mustThrow(() => api.proposeClaimSet([{...valid, text: "x".repeat(481), span_end: 481}], {hashText}), "length limit");
mustThrow(() => api.proposeClaimSet(Array.from({length: 6}, (_, index) => ({
  ...valid,
  excerpt_id: `excerpt-${index + 1}`,
  span_start: index * 50,
  span_end: index * 50 + Array.from(text).length,
  text: `${text.slice(0, -1)} ${index}.`
})), {hashText}), "too many excerpts");

const tooManyClaimsText = Array.from({length: 21}, (_, index) => `Claim ${index}.`).join(" ");
mustThrow(() => api.proposeClaimSet([
  excerpt(tooManyClaimsText, sourceFingerprint(tooManyClaimsText))
], {hashText}), "claim proposal limit");

const proposed = api.proposeClaimSet([valid], {hashText});
assert(!api.validateClaimSet(proposed, {hashText}).valid, "unconfirmed set passed default validation");
const unknown = clone(proposed);
unknown.shadow_authority = true;
assert(!api.validateClaimSet(unknown, {hashText, requireConfirmed: false}).valid,
  "unknown claim-set property passed");
for (const invalidGroups of [null, undefined]) {
  const malformedGroups = clone(proposed);
  malformedGroups.groups = invalidGroups;
  const malformedValidation = api.validateClaimSet(malformedGroups, {hashText, requireConfirmed: false});
  assert(!malformedValidation.valid && Array.isArray(malformedValidation.errors),
    "non-array groups threw or passed instead of failing closed");
}
const duplicate = clone(proposed);
duplicate.groups[0].claims.push(clone(duplicate.groups[0].claims[0]));
const duplicateValidation = api.validateClaimSet(duplicate, {hashText, requireConfirmed: false});
assert(!duplicateValidation.valid
  && duplicateValidation.errors.some((error) => error.code === "duplicate"),
  "duplicate claim passed");
const emptyClaim = clone(proposed);
emptyClaim.groups[0].claims[0].text = "   ";
assert(!api.validateClaimSet(emptyClaim, {hashText, requireConfirmed: false}).valid,
  "empty claim passed");
const badId = clone(proposed);
badId.groups[0].claims[0].draft_id = `claim-${"0".repeat(64)}`;
assert(!api.validateClaimSet(badId, {hashText, requireConfirmed: false}).valid,
  "non-canonical claim ID passed");
mustThrow(() => api.proposeClaimSet([valid], {hashText: () => "0".repeat(64)}), "sha-256");
"""
    )


@pytest.mark.skipif(NODE is None, reason="Node.js is required")
def test_repeated_statement_in_distinct_excerpts_remains_two_occurrences():
    run_module(
        r"""
const first = "The vote passed. Context A remains unverified.";
const second = "The vote passed. Context B remains unverified.";
const source = `${first}\n${second}`;
const fingerprint = sourceFingerprint(source);
const proposed = api.proposeClaimSet([
  excerpt(first, fingerprint),
  excerpt(second, fingerprint, "excerpt-002", Array.from(first).length + 1)
], {hashText});
const repeated = proposed.groups.map((group) => (
  group.claims.find((claim) => claim.text === "The vote passed.")
));
assert(repeated.every(Boolean), "repeated statement occurrence was dropped");
assert(repeated[0].draft_id !== repeated[1].draft_id,
  "separate excerpt occurrences were silently merged");
assert(api.validateClaimSet(proposed, {hashText, requireConfirmed: false}).valid,
  "separate excerpt occurrences were rejected as duplicates");
"""
    )


@pytest.mark.skipif(NODE is None, reason="Node.js is required")
def test_current_source_and_exact_selection_checks_reject_stale_sets():
    run_module(
        r"""
const text = "The first record is selected. The second claim remains open.";
const fingerprint = sourceFingerprint(text);
const selected = [excerpt(text, fingerprint)];
const currentSelection = api.computeSelectionSha256(selected, {hashText, requireHumanSelection: true});
const proposed = api.proposeClaimSet(selected, {hashText});
const differentFingerprint = `sha256:${hashText("different source")}`;
const staleSource = api.validateClaimSet(proposed, {
  hashText,
  requireConfirmed: false,
  expectedSourceFingerprint: differentFingerprint
});
assert(!staleSource.valid && staleSource.errors.some((error) => error.code === "stale"),
  "changed source fingerprint was not stale");
const staleSelection = api.validateClaimSet(proposed, {
  hashText,
  requireConfirmed: false,
  expectedSourceFingerprint: fingerprint,
  expectedSelectionSha256: hashText("different exact selection")
});
assert(!staleSelection.valid && staleSelection.errors.some((error) => error.code === "stale"),
  "changed exact selection was not stale");
assert(api.validateClaimSet(proposed, {
  hashText,
  requireConfirmed: false,
  expectedSourceFingerprint: fingerprint,
  expectedSelectionSha256: currentSelection
}).valid, "current exact selection was rejected");
"""
    )
