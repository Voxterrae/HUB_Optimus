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


def test_operator_record_integrity_helpers_are_wired():
    html = INDEX.read_text(encoding="utf-8")

    assert 'claim_id: nextRecordId("claim"),' in html
    assert 'evidence_id: nextRecordId("evidence"),' in html
    assert "syncRecordSequences();" in html
    assert "recordSequences = { claim: 0, evidence: 0 };" in html
    assert "removeClaimAt(Number(event.target.dataset.removeClaim));" in html

    claim_removal = html.split(
        'if (event.target.dataset.removeClaim !== undefined) {', maxsplit=1
    )[1].split("}", maxsplit=1)[0]
    assert "renderClaims();" in claim_removal
    assert "renderEvidence();" in claim_removal


@pytest.mark.skipif(NODE is None, reason="Node.js is required for JavaScript validation")
def test_operator_inline_javascript_parses():
    html = INDEX.read_text(encoding="utf-8")
    completed = subprocess.run(
        [NODE, "--check", "-"],
        input=_inline_script(html),
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr


@pytest.mark.skipif(NODE is None, reason="Node.js is required for JavaScript validation")
def test_operator_record_ids_and_claim_references_remain_consistent():
    html = INDEX.read_text(encoding="utf-8")
    helpers = _record_integrity_helpers(html)
    smoke = (
        """
let claims = [
  {claim_id: "claim-001"},
  {claim_id: "claim-002"}
];
let evidence = [
  {
    evidence_id: "evidence-001",
    supports_claim_ids: ["claim-001", "claim-002"],
    contradicts_claim_ids: ["claim-001"]
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
if (evidence[0].supports_claim_ids.join(",") !== "claim-002") {
  throw new Error("stale support reference survived claim removal");
}
if (evidence[0].contradicts_claim_ids.length !== 0) {
  throw new Error("stale contradiction reference survived claim removal");
}

claims = [];
if (nextRecordId("claim") !== "claim-004") {
  throw new Error("claim ID was reused after records were removed");
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
