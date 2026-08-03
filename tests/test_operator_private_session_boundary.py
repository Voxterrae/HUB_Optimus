import re
import shutil
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "site" / "operator" / "index.html"
SW = ROOT / "site" / "operator" / "sw.js"
NODE = shutil.which("node")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _controlled_intake_contract(html: str) -> str:
    match = re.search(
        r"// OPERATOR_CONTROLLED_INTAKE_CONTRACT_START\n(.*?)\n"
        r"    // OPERATOR_CONTROLLED_INTAKE_CONTRACT_END",
        html,
        re.DOTALL,
    )
    assert match is not None
    return match.group(1)


def test_private_operator_exposes_deliberate_same_origin_sign_out():
    html = _read(INDEX)

    assert 'id="private_operator_session_actions" hidden' in html
    assert 'id="private_operator_sign_out"' in html
    assert (
        'href="https://api.huboptimus.dev/oauth2/sign_out?rd=%2Fsigned-out"'
        in html
    )
    assert 'data-op-i18n="privateIntakeSignOut"' in html
    assert (
        "privateSessionActions.hidden = !controlledUrlIntakeAvailable();"
        in html
    )
    assert 'privateSignOut?.addEventListener("click", (event) => {' in html
    assert "void removePrivateOperatorOfflineState().finally(() => {" in html
    assert "window.location.assign(signOutUrl);" in html


def test_private_operator_unregisters_and_deletes_offline_shell_instead_of_registering_it():
    html = _read(INDEX)
    sw = _read(SW)

    private_branch = html.index("if (controlledUrlIntakeAvailable()) {")
    unregister_call = html.index("void removePrivateOperatorOfflineState();", private_branch)
    branch_return = html.index("return;", unregister_call)
    public_register = html.index(
        'void navigator.serviceWorker.register("./sw.js");',
        branch_return,
    )
    assert private_branch < unregister_call < branch_return < public_register
    assert "registration.unregister()" in html
    assert 'key.startsWith("hub-optimus-operator-")' in html

    assert (
        'const PRIVATE_OPERATOR_ORIGIN = "https://api.huboptimus.dev";'
        in sw
    )
    assert "IS_PRIVATE_OPERATOR_ORIGIN" in sw
    assert "await self.registration.unregister();" in sw
    private_fetch_guard = sw.index("if (IS_PRIVATE_OPERATOR_ORIGIN) return;")
    cache_dispatch = sw.index("event.respondWith", private_fetch_guard)
    assert private_fetch_guard < cache_dispatch


@pytest.mark.skipif(NODE is None, reason="Node.js is required for browser-contract validation")
def test_pasted_text_after_auth_boundary_does_not_retry_private_api():
    contract = _controlled_intake_contract(_read(INDEX))
    smoke = contract + r"""
const matchingAuthFailure = {
  sourceUrl: "https://example.com/a",
  error: new ControlledIntakeError("authentication_required", 401, "edge-id")
};
const matchingRoleFailure = {
  sourceUrl: "https://example.com/a",
  error: new ControlledIntakeError("forbidden", 403, "edge-id")
};
if (!canUsePastedTextAfterPrivateBoundary(
  matchingAuthFailure,
  "https://example.com/a",
  "Operator-pasted source text"
)) throw new Error("authentication fallback retried the API");
if (!canUsePastedTextAfterPrivateBoundary(
  matchingRoleFailure,
  "https://example.com/a",
  "Operator-pasted source text"
)) throw new Error("authorization fallback retried the API");
if (canUsePastedTextAfterPrivateBoundary(
  matchingAuthFailure,
  "https://example.com/b",
  "Operator-pasted source text"
)) throw new Error("boundary failure crossed source URLs");
if (canUsePastedTextAfterPrivateBoundary(
  matchingAuthFailure,
  "https://example.com/a",
  ""
)) throw new Error("empty pasted text bypassed private intake");
if (canUsePastedTextAfterPrivateBoundary(
  {
    sourceUrl: "https://example.com/a",
    error: new ControlledIntakeError("url_fetch_timeout", 504, "edge-id")
  },
  "https://example.com/a",
  "Operator-pasted source text"
)) throw new Error("temporary retrieval failure silently changed provenance mode");
"""
    subprocess.run([NODE, "-e", smoke], check=True, cwd=ROOT)


def test_analyze_path_gates_private_fetch_on_the_reviewed_boundary_failure():
    html = _read(INDEX)

    assert "const priorIntakeFailure = currentIntakeFailure;" in html
    assert "const usePastedTextAfterBoundary = canUsePastedTextAfterPrivateBoundary(" in html
    assert "currentIntakeFailure = priorIntakeFailure;" in html
    assert re.search(
        r"renderProductOutput\(\);\s*currentMemoryRecord = buildMemoryRecord\(\);\s*"
        r"currentIntakeFailure = null;",
        html,
    )
    assert re.search(
        r"const useControlledUrlIntake = Boolean\(\s*"
        r"sourceUrl &&\s*controlledUrlIntakeAvailable\(\) &&\s*"
        r"!usePastedTextAfterBoundary\s*\);",
        html,
    )
