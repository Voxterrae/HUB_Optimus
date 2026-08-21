from __future__ import annotations

import importlib.util
import json
import pathlib
import types
from typing import Any

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
BASE_SHA = "b" * 40
MERGE_SHA = "c" * 40
OTHER_HEAD_SHA = "d" * 40
OTHER_BASE_SHA = "e" * 40
OTHER_MERGE_SHA = "f" * 40


def event() -> dict[str, object]:
    return {
        "repository": {
            "full_name": "Voxterrae/HUB_Optimus",
            "owner": {"login": "Voxterrae", "id": 249308740},
        },
        "pull_request": pull_payload(),
    }


def pull_payload(
    *,
    head_sha: str = HEAD_SHA,
    base_sha: str = BASE_SHA,
    merge_sha: str | None = MERGE_SHA,
    body: str = "Related to #1906",
) -> dict[str, Any]:
    return {
        "number": 1907,
        "state": "open",
        "merged": False,
        "body": body,
        "user": {"login": "Voxterrae", "id": 249308740},
        "head": {"sha": head_sha, "ref": "feature"},
        "base": {"sha": base_sha, "ref": "main"},
        "merge_commit_sha": merge_sha,
    }


def decision() -> types.SimpleNamespace:
    return types.SimpleNamespace(
        owner_authored=True,
        protected_paths=(".github/scripts/founder_authority_workflow.py",),
        owner_approval_required=False,
        governance_issues=(1906,),
        owner_key_attested=False,
        warnings=("hardware-backed owner key pending",),
    )


class FakeClient:
    pull_responses: list[dict[str, Any]] = []
    create_failure_at: int | None = None
    finalize_failure_ids: set[int] = set()
    instances: list["FakeClient"] = []

    def __init__(self, token: str, full_name: str) -> None:
        self.token = token
        self.full_name = full_name
        self.created_checks: list[tuple[int, str]] = []
        self.finalized_checks: list[tuple[int, str]] = []
        self.pull_index = 0
        self.last_pull_response: dict[str, Any] | None = None
        type(self).instances.append(self)

    def repository_request(
        self,
        path: str,
        *,
        method: str = "GET",
        payload: dict[str, Any] | None = None,
    ) -> Any:
        if path == "pulls/1907" and method == "GET":
            responses = type(self).pull_responses or [pull_payload()]
            index = min(self.pull_index, len(responses) - 1)
            self.pull_index += 1
            self.last_pull_response = json.loads(json.dumps(responses[index]))
            return json.loads(json.dumps(responses[index]))
        if path.startswith("commits/") and method == "GET":
            current = self.last_pull_response or pull_payload()
            return {
                "sha": path.split("/", 1)[1],
                "parents": [
                    {"sha": current["base"]["sha"]},
                    {"sha": current["head"]["sha"]},
                ],
            }
        if path == "check-runs" and method == "POST":
            create_number = len(self.created_checks) + 1
            if type(self).create_failure_at == create_number:
                raise WORKFLOW.WorkflowError(
                    f"cannot create check number {create_number}"
                )
            assert payload is not None
            check_id = 100 + create_number
            self.created_checks.append((check_id, payload["head_sha"]))
            return {"id": check_id}
        if path.startswith("check-runs/") and method == "PATCH":
            check_id = int(path.rsplit("/", 1)[1])
            if check_id in type(self).finalize_failure_ids:
                raise WORKFLOW.WorkflowError(f"cannot finalize check {check_id}")
            assert payload is not None
            self.finalized_checks.append((check_id, payload["conclusion"]))
            return {"id": check_id}
        raise AssertionError(f"unexpected request: {method} {path}")

    def create_check(self, target_sha: str, *, target_label: str) -> int:
        result = self.repository_request(
            "check-runs",
            method="POST",
            payload={"head_sha": target_sha},
        )
        return int(result["id"])

    def finalize_check(
        self,
        check_run_id: int,
        *,
        success: bool,
        summary: str,
    ) -> None:
        self.repository_request(
            f"check-runs/{check_run_id}",
            method="PATCH",
            payload={"conclusion": "success" if success else "failure"},
        )

    def paginated(self, path: str) -> list[dict[str, Any]]:
        raise AssertionError(f"paginated should be monkeypatched: {path}")


@pytest.fixture(autouse=True)
def reset_fake_client() -> None:
    FakeClient.pull_responses = []
    FakeClient.create_failure_at = None
    FakeClient.finalize_failure_ids = set()
    FakeClient.instances = []


def configure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pathlib.Path,
    *,
    evidence_values: list[dict[str, Any]] | None = None,
) -> None:
    manifest_path = tmp_path / "owner_identity.json"
    manifest_path.write_text("{}\n", encoding="utf-8")
    monkeypatch.setattr(WORKFLOW, "MANIFEST_PATH", manifest_path)
    monkeypatch.setattr(WORKFLOW, "EVIDENCE_PATH", tmp_path / "evidence.json")
    monkeypatch.setattr(WORKFLOW, "load_event", event)
    monkeypatch.setattr(WORKFLOW, "GitHubClient", FakeClient)

    values = evidence_values or [
        {"commits": [], "reviews": [], "governance_issues": [1906]},
        {"commits": [], "reviews": [], "governance_issues": [1906]},
    ]
    cursor = {"value": 0}

    def fake_collect(*args: object) -> dict[str, Any]:
        index = min(cursor["value"], len(values) - 1)
        cursor["value"] += 1
        return json.loads(json.dumps(values[index]))

    monkeypatch.setattr(WORKFLOW, "collect_evidence", fake_collect)
    monkeypatch.setattr(WORKFLOW, "load_owner_identity", lambda path: object())
    monkeypatch.setattr(
        WORKFLOW,
        "evaluate",
        lambda evidence, manifest, owner: decision(),
    )
    monkeypatch.setenv("GITHUB_TOKEN", "test-token")


def conclusions(client: FakeClient) -> list[str]:
    return [value for _, value in client.finalized_checks]


def test_success_is_published_on_head_and_live_merge_candidate(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pathlib.Path,
) -> None:
    configure(monkeypatch, tmp_path)

    assert WORKFLOW.run() == 0
    client = FakeClient.instances[0]
    assert [sha for _, sha in client.created_checks] == [HEAD_SHA, MERGE_SHA]
    assert conclusions(client) == ["success", "success"]


def test_semantic_failure_finalizes_both_checks_as_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pathlib.Path,
) -> None:
    configure(monkeypatch, tmp_path)
    monkeypatch.setattr(
        WORKFLOW,
        "evaluate",
        lambda *args: (_ for _ in ()).throw(
            WORKFLOW.GuardError("semantic policy rejected")
        ),
    )

    assert WORKFLOW.run() == 1
    assert conclusions(FakeClient.instances[0]) == ["failure", "failure"]


@pytest.mark.parametrize(
    ("second_pull", "message"),
    [
        (pull_payload(head_sha=OTHER_HEAD_SHA), "head changed"),
        (pull_payload(base_sha=OTHER_BASE_SHA), "base changed"),
        (pull_payload(merge_sha=OTHER_MERGE_SHA), "test merge commit changed"),
    ],
)
def test_target_change_before_finalization_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pathlib.Path,
    second_pull: dict[str, Any],
    message: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    FakeClient.pull_responses = [pull_payload(), second_pull]
    configure(monkeypatch, tmp_path)

    assert WORKFLOW.run() == 1
    assert conclusions(FakeClient.instances[0]) == ["failure", "failure"]
    assert message in capsys.readouterr().err


def test_missing_merge_candidate_produces_no_false_success(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pathlib.Path,
) -> None:
    FakeClient.pull_responses = [pull_payload(merge_sha=None)]
    configure(monkeypatch, tmp_path)

    assert WORKFLOW.run() == 1
    client = FakeClient.instances[0]
    assert client.created_checks == []
    assert client.finalized_checks == []


def test_second_check_creation_failure_marks_first_check_failed(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pathlib.Path,
) -> None:
    FakeClient.create_failure_at = 2
    configure(monkeypatch, tmp_path)

    assert WORKFLOW.run() == 1
    client = FakeClient.instances[0]
    assert client.created_checks == [(101, HEAD_SHA)]
    assert conclusions(client) == ["failure"]


def test_any_check_finalization_failure_returns_nonzero(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pathlib.Path,
) -> None:
    FakeClient.finalize_failure_ids = {102}
    configure(monkeypatch, tmp_path)

    assert WORKFLOW.run() == 1
    assert FakeClient.instances[0].finalized_checks == [(101, "success")]


def test_semantic_evidence_change_before_finalization_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pathlib.Path,
) -> None:
    configure(
        monkeypatch,
        tmp_path,
        evidence_values=[
            {"commits": [], "reviews": [], "governance_issues": [1906]},
            {
                "commits": [],
                "reviews": [{"state": "CHANGES_REQUESTED"}],
                "governance_issues": [1906],
            },
        ],
    )

    assert WORKFLOW.run() == 1
    assert conclusions(FakeClient.instances[0]) == ["failure", "failure"]


def test_initial_check_creation_failure_returns_nonzero(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: pathlib.Path,
) -> None:
    FakeClient.create_failure_at = 1
    configure(monkeypatch, tmp_path)

    assert WORKFLOW.main() == 1
