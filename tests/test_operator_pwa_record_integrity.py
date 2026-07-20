import re
import shutil
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "site" / "operator" / "index.html"
NODE = shutil.which("node")


def _inline_script(html: str) -> str:
    match = re.search(r"<script>\s*(.*?)\s*</script>", html, re.DOTALL)
    assert match is not None
    return match.group(1)


def _record_integrity_helpers(html: str) -> str:
    match = re.search(
        r"// OPERATOR_RECORD_INTEGRITY_START\n(.*?)\n"
        r"    // OPERATOR_RECORD_INTEGRITY_END",
        html,
        re.DOTALL,
    )
    assert match is not None
    return match.group(1)


def _run_node(source: str, *args: str) -> subprocess.CompletedProcess[str]:
    assert NODE is not None
    return subprocess.run(
        [NODE, *args],
        input=source,
        text=True,
        capture_output=True,
        check=False,
    )


def test_operator_record_integrity_helpers_are_wired():
    html = INDEX.read_text(encoding="utf-8")

    assert 'claim_id: nextRecordId("claim")' in html
    assert 'evidence_id: nextRecordId("evidence")' in html
    assert "syncRecordSequences();" in html
    assert "recordSequences = { claim: 0, evidence: 0 };" in html
    assert "removeClaimAt(Number(event.target.dataset.removeClaim));" in html

    removal = re.search(
        r"function removeClaimAt\(index\) \{(.*?)\n    \}",
        html,
        re.DOTALL,
    )
    assert removal is not None
    assert "supports_claim_ids" in removal.group(1)
    assert "contradicts_claim_ids" in removal.group(1)
    assert "renderClaims();" in removal.group(1)
    assert "renderEvidence();" in removal.group(1)


@pytest.mark.skipif(NODE is None, reason="Node.js is required for JavaScript validation")
def test_operator_inline_javascript_parses():
    completed = _run_node(
        _inline_script(INDEX.read_text(encoding="utf-8")),
        "--check",
        "-",
    )
    assert completed.returncode == 0, completed.stderr


@pytest.mark.skipif(NODE is None, reason="Node.js is required for JavaScript validation")
def test_operator_record_ids_and_claim_references_remain_consistent():
    helpers = _record_integrity_helpers(INDEX.read_text(encoding="utf-8"))
    smoke = (
        """
function renderClaims() {}
function renderEvidence() {}

let claims = [
  {claim_id: "claim-001"},
  {claim_id: "claim-002"}
];
let evidence = [
  {
    evidence_id: "evidence-001",
    supports_claim_ids: ["claim-001", "claim-002", "claim-999"],
    contradicts_claim_ids: ["claim-001", "claim-002"]
  },
  {
    evidence_id: "evidence-004",
    supports_claim_ids: ["claim-002"],
    contradicts_claim_ids: []
  }
];
"""
        + helpers
        + """
syncRecordSequences();
if (nextRecordId("claim") !== "claim-003") {
  throw new Error("claim ID did not advance from the highest existing ID");
}
if (nextRecordId("evidence") !== "evidence-005") {
  throw new Error("evidence ID did not advance from the highest existing ID");
}

removeClaimAt(0);
if (claims.length !== 1 || claims[0].claim_id !== "claim-002") {
  throw new Error("claim removal did not preserve the remaining claim");
}
if (evidence[0].supports_claim_ids.join(",") !== "claim-002,claim-999") {
  throw new Error("stale support reference survived claim removal");
}
if (evidence[0].contradicts_claim_ids.join(",") !== "claim-002") {
  throw new Error("stale contradiction reference survived claim removal");
}

claims = [];
if (nextRecordId("claim") !== "claim-004") {
  throw new Error("claim ID was reused after records were removed");
}

claims = [{claim_id: "claim-009"}];
evidence = [{evidence_id: "evidence-007", supports_claim_ids: [], contradicts_claim_ids: []}];
syncRecordSequences();
if (nextRecordId("claim") !== "claim-010") {
  throw new Error("loaded claim IDs did not advance the sequence baseline");
}
if (nextRecordId("evidence") !== "evidence-008") {
  throw new Error("loaded evidence IDs did not advance the sequence baseline");
}
"""
    )
    completed = _run_node(smoke, "-")
    assert completed.returncode == 0, completed.stderr
