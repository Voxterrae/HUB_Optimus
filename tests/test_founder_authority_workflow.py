from __future__ import annotations

import importlib.util
import json
import pathlib
import types

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / ".github" / "scripts" / "founder_authority_workflow.py"
SPEC = importlib.util.spec_from_file_location(
    "founder_authority_workflow_under_test", MODULE_PATH
)
assert SPEC is not None and SPEC.loader is not None
WORKFLOW = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(WORKFLOW)

HEAD_SHA = "a" * 40


def event() -> dict[str, object]:
    return {
        "repository": {"full_name": "Voxterrae/HUB_Optimus"},
        "pull_request": {
            "number": 1862,
            "head": {"sha": HEAD_SHA},
        },
    }


def decision() -> types.SimpleNamespace:
    return types.SimpleNamespace(
        owner_authored=True,
        protected_paths=("docs/governance/FOUNDER_OWNERSHIP_AND_AUTHORITY.md",),
        owner_approval_required=False,
        governance_issues=(1861,),
        owner_key_attested=False,
        warnings=("hardware-backed owner key pending",),
    )


def configure_success_path(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pathlib.Path,
    client_type: type[object],
) -> None:
    manifest_path = tmp_path / "owner_identity.json"
    manifest_path.write_text("{}\n", encoding="utf-8")
    monkeypatch.setattr(WORKFLOW, "MANIFEST_PATH", manifest_path)
    monkeypatch.setattr(WORKFLOW, "EVIDENCE_PATH", tmp_path / "evidence.json")
    monkeypatch.setattr(WORKFLOW, "load_event", event)
    monkeypatch.setattr(WORKFLOW, "GitHubClient", client_type)
    monkeypatch.setattr(
        WORKFLOW,
        "collect_evidence",
        lambda client, payload, manifest: {"commits": []},
    )
    monkeypatch.setattr(WORKFLOW, "load_owner_identity", lambda path: object())
    monkeypatch.setattr(
        WORKFLOW,
        "evaluate",
        lambda evidence_payload, manifest, owner: decision(),
    )
    monkeypatch.setenv("GITHUB_TOKEN", "test-token")


def test_run_binds_check_to_exact_head_and_finalizes_success(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pathlib.Path,
) -> None:
    calls: list[tuple[object, ...]] = []

    class Client:
        def __init__(self, token: str, full_name: str) -> None:
            calls.append(("init", token, full_name))

        def create_head_check(self, head_sha: str) -> int:
            calls.append(("create", head_sha))
            return 1862

        def finalize_head_check(
            self,
            check_run_id: int,
            *,
            success: bool,
            summary: str,
        ) -> None:
            calls.append(("finalize", check_run_id, success, summary))

    configure_success_path(monkeypatch, tmp_path, Client)

    assert WORKFLOW.run() == 0
    assert ("create", HEAD_SHA) in calls
    finalize = next(call for call in calls if call[0] == "finalize")
    assert finalize[1] == 1862
    assert finalize[2] is True
    assert "FOUNDER_AUTHORITY_GUARD: PASS" in str(finalize[3])
    evidence = json.loads((tmp_path / "evidence.json").read_text(encoding="utf-8"))
    assert evidence == {"commits": []}


def test_collection_failure_finalizes_same_check_as_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pathlib.Path,
) -> None:
    finalized: list[tuple[int, bool, str]] = []

    class Client:
        def __init__(self, token: str, full_name: str) -> None:
            pass

        def create_head_check(self, head_sha: str) -> int:
            assert head_sha == HEAD_SHA
            return 73

        def finalize_head_check(
            self,
            check_run_id: int,
            *,
            success: bool,
            summary: str,
        ) -> None:
            finalized.append((check_run_id, success, summary))

    configure_success_path(monkeypatch, tmp_path, Client)

    def fail_collection(client: object, payload: object, manifest: object) -> object:
        raise WORKFLOW.WorkflowError("evidence collection failed")

    monkeypatch.setattr(WORKFLOW, "collect_evidence", fail_collection)

    assert WORKFLOW.run() == 1
    assert finalized == [
        (73, False, "FOUNDER_AUTHORITY_GUARD: FAIL: evidence collection failed")
    ]


def test_check_creation_failure_returns_nonzero_without_false_success(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pathlib.Path,
) -> None:
    class Client:
        def __init__(self, token: str, full_name: str) -> None:
            pass

        def create_head_check(self, head_sha: str) -> int:
            raise WORKFLOW.WorkflowError("cannot create exact-head check")

    configure_success_path(monkeypatch, tmp_path, Client)

    assert WORKFLOW.main() == 1


def test_check_finalization_failure_returns_nonzero(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pathlib.Path,
) -> None:
    class Client:
        def __init__(self, token: str, full_name: str) -> None:
            pass

        def create_head_check(self, head_sha: str) -> int:
            return 91

        def finalize_head_check(
            self,
            check_run_id: int,
            *,
            success: bool,
            summary: str,
        ) -> None:
            raise WORKFLOW.WorkflowError("cannot finalize exact-head check")

    configure_success_path(monkeypatch, tmp_path, Client)

    assert WORKFLOW.main() == 1
