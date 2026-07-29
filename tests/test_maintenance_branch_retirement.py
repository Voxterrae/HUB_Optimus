from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import re
import shutil
import subprocess
from collections.abc import Iterator
from pathlib import Path

import pytest
import yaml

from tools import retire_maintenance_branches as retirement


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = (
    ROOT
    / "docs"
    / "maintenance"
    / "issue-1788"
    / "maintenance-branches.manifest.v1.json"
)
BUNDLE_PATH = (
    ROOT
    / "docs"
    / "maintenance"
    / "issue-1788"
    / "maintenance-branches.bundle"
)
WORKFLOW_PATH = (
    ROOT / ".github" / "workflows" / "retire-maintenance-branches.yml"
)
APPROVED_MAIN = "a" * 40


def _manifest() -> retirement.Manifest:
    return retirement.load_manifest(MANIFEST_PATH, ROOT)


def _state(
    manifest: retirement.Manifest,
    *,
    include_candidates: bool = True,
    additions: dict[str, str] | None = None,
    protected_branch: str | None = None,
    pulls: tuple[retirement.PullRequest, ...] = (),
) -> retirement.LiveState:
    refs = {
        "main": APPROVED_MAIN,
        "feature/kept": "b" * 40,
        **manifest.exclusions,
    }
    if include_candidates:
        refs.update(manifest.candidate_refs)
    if additions:
        refs.update(additions)
    protected = {name: False for name in refs}
    protected["main"] = True
    if protected_branch:
        protected[protected_branch] = True
    return retirement.LiveState(
        refs=refs,
        protected=protected,
        open_pull_requests=pulls,
    )


def _copy_manifest_package(tmp_path: Path) -> tuple[Path, Path]:
    root = tmp_path / "repo"
    package = root / "docs" / "maintenance" / "issue-1788"
    package.mkdir(parents=True)
    manifest_path = package / MANIFEST_PATH.name
    bundle_path = package / BUNDLE_PATH.name
    shutil.copyfile(MANIFEST_PATH, manifest_path)
    shutil.copyfile(BUNDLE_PATH, bundle_path)
    return root, manifest_path


def _git(repository: Path, *arguments: str, check: bool = True) -> str:
    result = subprocess.run(
        ["git", *arguments],
        cwd=repository,
        check=check,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return result.stdout.strip()


def test_manifest_fixes_exact_audited_scope_and_six_semantic_exclusions():
    raw = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    manifest = _manifest()

    assert raw["source_base_sha"] == "df0ef345e5ac627f3e2735573c802fe2f60821f4"
    assert raw["observed_remote"] == {
        "observed_at": "2026-07-29T18:48:19Z",
        "main_sha": "1b5ec140f8abed41d430393ed57cea2e0cfaa6bf",
        "total_branches": 1060,
        "maintenance_branches": 887,
        "numeric_maintenance_branches": 884,
        "candidate_branches": 881,
        "expected_remaining_branches_if_executed_at_observation": 179,
        "expected_remaining_maintenance_branches": 6,
        "open_pull_requests": [
            {
                "number": 1773,
                "head_branch": "agent/rfc-constitutional-reconciliation",
                "head_sha": "84f2717202f9970276d5ae63047993f46a214ca2",
                "head_repository": "Voxterrae/HUB_Optimus",
            }
        ],
        "sources": [
            "git ls-remote --heads origin",
            "GitHub REST GET /repos/Voxterrae/HUB_Optimus/branches",
            "GitHub REST GET /repos/Voxterrae/HUB_Optimus/pulls?state=open",
        ],
    }
    assert len(manifest.candidates) == 881
    assert manifest.exclusions == retirement.EXPECTED_EXCLUSIONS
    assert set(manifest.candidate_refs).isdisjoint(manifest.exclusions)
    assert all(
        re.fullmatch(retirement.EXPECTED_PATTERN, candidate.branch)
        for candidate in manifest.candidates
    )
    assert manifest.candidates[-1].tip_committed_at < manifest.cutoff
    assert min(candidate.tip_committed_at for candidate in manifest.candidates) == (
        dt.datetime(2026, 3, 9, 13, 49, 10, tzinfo=dt.timezone.utc)
    )
    assert max(candidate.tip_committed_at for candidate in manifest.candidates) == (
        dt.datetime(2026, 5, 11, 7, 32, 39, tzinfo=dt.timezone.utc)
    )


def test_manifest_canonical_head_digest_is_space_delimited_and_ref_sorted():
    manifest = _manifest()
    names = [candidate.branch for candidate in manifest.candidates]
    serialized = "".join(
        f"{candidate.tip_sha} refs/heads/{candidate.branch}\n"
        for candidate in manifest.candidates
    ).encode()

    assert names == sorted(names)
    assert hashlib.sha256(serialized).hexdigest() == (
        "77d1310f63ee4f38681c370703484ad8747e8df3d8dd87cb81eec72e19137270"
    )
    assert manifest.canonical_heads_sha256 == hashlib.sha256(serialized).hexdigest()


def test_standalone_bundle_restores_every_exact_ref_and_passes_strict_fsck():
    manifest = _manifest()

    retirement.verify_archive(manifest, repository_root=ROOT)

    assert BUNDLE_PATH.stat().st_size == 957_017
    assert hashlib.sha256(BUNDLE_PATH.read_bytes()).hexdigest() == (
        "3d896c256061c2d0435c2acd26a36d24a7895053207a375690cd07d05681b3b3"
    )


def test_tampered_bundle_fails_before_any_remote_operation(tmp_path: Path):
    root, manifest_path = _copy_manifest_package(tmp_path)
    manifest = retirement.load_manifest(manifest_path, root)
    archive = manifest.archive_path
    content = bytearray(archive.read_bytes())
    content[-1] ^= 1
    archive.write_bytes(content)

    with pytest.raises(retirement.GuardError, match="SHA-256"):
        retirement.verify_archive(manifest, repository_root=root)


def test_manifest_rejects_duplicate_keys_and_bundle_header_rejects_prerequisites(
    tmp_path: Path,
):
    root, manifest_path = _copy_manifest_package(tmp_path)
    source = manifest_path.read_text(encoding="utf-8")
    manifest_path.write_text(
        source.replace(
            '"format_version": 1,',
            '"format_version": 1, "format_version": 1,',
            1,
        ),
        encoding="utf-8",
    )
    with pytest.raises(retirement.GuardError, match="duplicate JSON key"):
        retirement.load_manifest(manifest_path, root)

    thin = tmp_path / "thin.bundle"
    thin.write_bytes(
        b"# v2 git bundle\n"
        + b"-"
        + (b"a" * 40)
        + b" prerequisite\n\nPACK"
    )
    assert retirement._bundle_has_prerequisites(thin)  # noqa: SLF001


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda data: data["candidates"][0].update(protected=True), "unprotected"),
        (
            lambda data: data["candidates"][0].update(
                tip_committed_at="2026-05-12T00:00:00Z"
            ),
            "cutoff",
        ),
        (
            lambda data: data["selection"]["semantic_exclusions"].pop(),
            "six semantic exclusions",
        ),
    ],
)
def test_manifest_mutations_fail_closed(
    tmp_path: Path,
    mutation,
    message: str,
):
    root, manifest_path = _copy_manifest_package(tmp_path)
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    mutation(data)
    manifest_path.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(retirement.GuardError, match=message):
        retirement.load_manifest(manifest_path, root)


def test_manifest_and_archive_symlinks_are_rejected(tmp_path: Path):
    root, manifest_path = _copy_manifest_package(tmp_path)
    real_manifest = manifest_path.with_suffix(".real")
    manifest_path.rename(real_manifest)
    manifest_path.symlink_to(real_manifest.name)
    with pytest.raises(retirement.GuardError, match="non-symlink"):
        retirement.load_manifest(manifest_path, root)

    manifest_path.unlink()
    real_manifest.rename(manifest_path)
    manifest = retirement.load_manifest(manifest_path, root)
    archive = manifest.archive_path
    real_archive = archive.with_suffix(".real")
    archive.rename(real_archive)
    archive.symlink_to(real_archive.name)
    with pytest.raises(retirement.GuardError, match="non-symlink"):
        retirement.verify_archive(manifest, repository_root=root)


@pytest.mark.parametrize(
    ("mutator", "message"),
    [
        (
            lambda manifest, state: state.refs.__setitem__(
                manifest.candidates[0].branch,
                "c" * 40,
            ),
            "moved or disappeared",
        ),
        (
            lambda manifest, state: state.refs.pop(manifest.candidates[0].branch),
            "namespace changed",
        ),
        (
            lambda _manifest, state: state.refs.__setitem__(
                "chore/maintenance-999999",
                "c" * 40,
            ),
            "namespace changed",
        ),
        (
            lambda _manifest, state: state.refs.__setitem__(
                "chore/maintenance-unreviewed",
                "c" * 40,
            ),
            "namespace changed",
        ),
        (
            lambda manifest, state: state.protected.__setitem__(
                manifest.candidates[0].branch,
                True,
            ),
            "protected",
        ),
        (
            lambda manifest, state: object.__setattr__(
                state,
                "open_pull_requests",
                (
                    retirement.PullRequest(
                        number=99,
                        head_branch=manifest.candidates[0].branch,
                    ),
                ),
            ),
            "open pull request",
        ),
        (
            lambda manifest, state: state.refs.__setitem__(
                next(iter(manifest.exclusions)),
                "c" * 40,
            ),
            "moved or disappeared",
        ),
        (
            lambda _manifest, state: state.refs.__setitem__("main", "c" * 40),
            "Live main",
        ),
    ],
)
def test_live_guard_blocks_every_scope_or_safety_drift(mutator, message: str):
    manifest = _manifest()
    state = _state(manifest)
    mutator(manifest, state)

    with pytest.raises(retirement.GuardError, match=message):
        retirement.validate_live_state(manifest, state, APPROVED_MAIN)


def test_live_guard_allows_unrelated_new_branch_but_not_maintenance_drift():
    manifest = _manifest()
    state = _state(
        manifest,
        additions={"feature/concurrent-but-unrelated": "c" * 40},
    )

    retirement.validate_live_state(manifest, state, APPROVED_MAIN)


def test_push_plan_has_one_atomic_transaction_and_exact_lease_per_candidate():
    manifest = _manifest()
    command = retirement.build_push_command(manifest, dry_run=False)
    leases = [value for value in command if value.startswith("--force-with-lease=")]
    deletions = [value for value in command if value.startswith(":refs/heads/")]

    assert command[:6] == [
        "git",
        "push",
        "--atomic",
        "--porcelain",
        "--no-follow-tags",
        "--no-verify",
    ]
    assert command.count("--atomic") == 1
    assert "--dry-run" not in command
    assert command[-(len(manifest.candidates) + 2) : -len(manifest.candidates)] == [
        "--",
        retirement.CANONICAL_GITHUB_URL,
    ]
    assert len(leases) == len(deletions) == 881
    assert leases == [
        f"--force-with-lease={candidate.full_ref}:{candidate.tip_sha}"
        for candidate in manifest.candidates
    ]
    assert deletions == [
        f":{candidate.full_ref}" for candidate in manifest.candidates
    ]
    command_refs = {
        value.removeprefix(":refs/heads/")
        for value in deletions
    }
    assert command_refs.isdisjoint(manifest.exclusions)

    dry_run = retirement.build_push_command(manifest, dry_run=True)
    assert dry_run == command[:6] + ["--dry-run"] + command[6:]


def test_atomic_git_push_with_881_leases_is_all_or_nothing(tmp_path: Path):
    source = tmp_path / "source"
    remote = tmp_path / "remote.git"
    source.mkdir()
    _git(source, "init", "-b", "main")
    (source / "seed.txt").write_text("one\n", encoding="utf-8")
    _git(source, "add", "seed.txt")
    _git(
        source,
        "-c",
        "user.name=Retirement Test",
        "-c",
        "user.email=retirement@example.invalid",
        "commit",
        "-m",
        "seed",
    )
    first_sha = _git(source, "rev-parse", "HEAD")
    _git(tmp_path, "init", "--bare", str(remote))
    _git(source, "push", str(remote), f"{first_sha}:refs/heads/main")

    timestamp = dt.datetime(2026, 1, 1, tzinfo=dt.timezone.utc)
    candidates = tuple(
        retirement.Candidate(
            branch=f"chore/maintenance-{number}",
            tip_sha=first_sha,
            tree_sha="d" * 40,
            tip_committed_at=timestamp,
        )
        for number in range(10_000, 10_881)
    )
    fake_manifest = retirement.Manifest(
        path=MANIFEST_PATH,
        repository=retirement.EXPECTED_REPOSITORY,
        cutoff=dt.datetime(2026, 5, 12, tzinfo=dt.timezone.utc),
        candidates=candidates,
        exclusions={},
        archive_path=BUNDLE_PATH,
        archive_sha256="e" * 64,
        archive_size=1,
        canonical_heads_sha256="f" * 64,
        confirmation_template="unused {expected_main_sha}",
    )
    updates = "".join(
        f"create refs/heads/{candidate.branch} {first_sha}\n"
        for candidate in candidates
    )
    subprocess.run(
        ["git", f"--git-dir={remote}", "update-ref", "--stdin"],
        input=updates,
        text=True,
        check=True,
        capture_output=True,
    )

    command = retirement.build_push_command(fake_manifest, dry_run=False)
    command[command.index(retirement.CANONICAL_GITHUB_URL)] = str(remote)
    success = subprocess.run(command, cwd=source, capture_output=True, text=True)
    assert success.returncode == 0, success.stderr
    assert _git(remote, "for-each-ref", "--format=%(refname)", "refs/heads/chore") == ""

    subprocess.run(
        ["git", f"--git-dir={remote}", "update-ref", "--stdin"],
        input=updates,
        text=True,
        check=True,
        capture_output=True,
    )
    _git(remote, "config", "receive.advertiseAtomic", "false")
    unsupported = subprocess.run(command, cwd=source, capture_output=True, text=True)
    assert unsupported.returncode != 0
    assert "atomic" in (unsupported.stderr + unsupported.stdout).lower()
    assert len(
        _git(
            remote,
            "for-each-ref",
            "--format=%(refname)",
            "refs/heads/chore",
        ).splitlines()
    ) == 881
    _git(remote, "config", "receive.advertiseAtomic", "true")

    (source / "seed.txt").write_text("two\n", encoding="utf-8")
    _git(source, "add", "seed.txt")
    _git(
        source,
        "-c",
        "user.name=Retirement Test",
        "-c",
        "user.email=retirement@example.invalid",
        "commit",
        "-m",
        "move one",
    )
    second_sha = _git(source, "rev-parse", "HEAD")
    moved = candidates[0].branch
    _git(source, "push", str(remote), f"{second_sha}:refs/heads/{moved}")

    failure = subprocess.run(command, cwd=source, capture_output=True, text=True)
    assert failure.returncode != 0
    remaining = _git(
        remote,
        "for-each-ref",
        "--format=%(refname)",
        "refs/heads/chore",
    ).splitlines()
    assert len(remaining) == 881
    assert _git(remote, "rev-parse", f"refs/heads/{moved}") == second_sha


def test_postflight_requires_all_candidates_absent_and_non_candidates_intact():
    manifest = _manifest()
    before = _state(manifest)
    after = _state(manifest, include_candidates=False)

    complete, detail = retirement.validate_post_state(manifest, before, after)
    assert complete
    assert "absent" in detail

    after.refs[manifest.candidates[0].branch] = manifest.candidates[0].tip_sha
    complete, detail = retirement.validate_post_state(manifest, before, after)
    assert not complete
    assert "remaining_candidates" in detail

    after.refs.pop(manifest.candidates[0].branch)
    after.refs["feature/kept"] = "c" * 40
    complete, detail = retirement.validate_post_state(manifest, before, after)
    assert not complete
    assert "changed_or_missing_non_candidates" in detail

    after.refs["feature/kept"] = before.refs["feature/kept"]
    object.__setattr__(
        after,
        "open_pull_requests",
        (
            retirement.PullRequest(
                number=321,
                head_branch=manifest.candidates[0].branch,
            ),
        ),
    )
    complete, detail = retirement.validate_post_state(manifest, before, after)
    assert not complete
    assert "postflight_open_candidate_prs" in detail


class _RecordingRunner:
    def __init__(
        self,
        results: Iterator[retirement.CommandResult] | None = None,
        error_on_call: int | None = None,
    ):
        self.calls: list[list[str]] = []
        self.results = results
        self.error_on_call = error_on_call

    def __call__(self, arguments, *, cwd, timeout):
        self.calls.append(list(arguments))
        if self.error_on_call == len(self.calls):
            raise subprocess.TimeoutExpired(arguments, timeout)
        if self.results is None:
            return retirement.CommandResult(0, "", "")
        return next(self.results)


def _patch_static_guards(
    monkeypatch: pytest.MonkeyPatch,
    states: Iterator[retirement.LiveState],
) -> None:
    monkeypatch.setattr(retirement, "verify_archive", lambda *args, **kwargs: None)
    monkeypatch.setattr(retirement, "validate_checkout", lambda *args, **kwargs: None)
    def collect(*args, **kwargs):
        try:
            return next(states)
        except StopIteration as error:
            raise retirement.GuardError("simulated postflight outage") from error

    monkeypatch.setattr(retirement, "collect_live_state", collect)


def test_default_dry_run_never_invokes_receive_pack(
    monkeypatch: pytest.MonkeyPatch,
):
    manifest = _manifest()
    runner = _RecordingRunner()
    _patch_static_guards(monkeypatch, iter([_state(manifest)]))

    code, report = retirement.run_retirement(
        mode="dry-run",
        expected_main_sha=APPROVED_MAIN,
        confirmation="",
        manifest_path=MANIFEST_PATH,
        remote="origin",
        repository_root=ROOT,
        runner=runner,
    )

    assert code == 0
    assert report["status"] == "ready"
    assert runner.calls == []
    assert retirement.parse_args(
        ["--expected-main-sha", APPROVED_MAIN]
    ).mode == "dry-run"


def test_execute_requires_exact_confirmation_before_git_push(
    monkeypatch: pytest.MonkeyPatch,
):
    manifest = _manifest()
    runner = _RecordingRunner()
    _patch_static_guards(monkeypatch, iter([_state(manifest)]))

    code, report = retirement.run_retirement(
        mode="execute",
        expected_main_sha=APPROVED_MAIN,
        confirmation="almost",
        manifest_path=MANIFEST_PATH,
        remote="origin",
        repository_root=ROOT,
        runner=runner,
    )

    assert code == 2
    assert report["status"] == "blocked"
    assert "Exact retirement confirmation" in report["detail"]
    assert runner.calls == []


@pytest.mark.parametrize("drift", ["moved", "protected", "open-pr"])
def test_second_live_read_blocks_real_push_when_guard_changes(
    monkeypatch: pytest.MonkeyPatch,
    drift: str,
):
    manifest = _manifest()
    before = _state(manifest)
    changed = _state(manifest)
    branch = manifest.candidates[0].branch
    if drift == "moved":
        changed.refs[branch] = "c" * 40
    elif drift == "protected":
        changed.protected[branch] = True
    else:
        object.__setattr__(
            changed,
            "open_pull_requests",
            (retirement.PullRequest(number=123, head_branch=branch),),
        )
    runner = _RecordingRunner()
    _patch_static_guards(monkeypatch, iter([before, changed]))

    code, report = retirement.run_retirement(
        mode="execute",
        expected_main_sha=APPROVED_MAIN,
        confirmation=manifest.expected_confirmation(APPROVED_MAIN),
        manifest_path=MANIFEST_PATH,
        remote="origin",
        repository_root=ROOT,
        runner=runner,
    )

    assert code == 2
    assert report["status"] == "blocked"
    assert len(runner.calls) == 1
    assert "--dry-run" in runner.calls[0]


def test_execute_dry_runs_refreshes_then_pushes_and_accepts_verified_lost_ack(
    monkeypatch: pytest.MonkeyPatch,
):
    manifest = _manifest()
    before = _state(manifest)
    after = _state(manifest, include_candidates=False)
    runner = _RecordingRunner(
        iter(
            [
                retirement.CommandResult(0, "dry", ""),
                retirement.CommandResult(1, "", "lost acknowledgement"),
            ]
        )
    )
    _patch_static_guards(monkeypatch, iter([before, before, after]))

    code, report = retirement.run_retirement(
        mode="execute",
        expected_main_sha=APPROVED_MAIN,
        confirmation=manifest.expected_confirmation(APPROVED_MAIN),
        manifest_path=MANIFEST_PATH,
        remote="origin",
        repository_root=ROOT,
        runner=runner,
    )

    assert code == 0
    assert report["status"] == "completed"
    assert report["push_returncode"] == 1
    assert "postflight proves" in report["detail"]
    assert len(runner.calls) == 2
    assert "--dry-run" in runner.calls[0]
    assert "--dry-run" not in runner.calls[1]


def test_execute_timeout_still_postflights_and_accepts_proven_completion(
    monkeypatch: pytest.MonkeyPatch,
):
    manifest = _manifest()
    before = _state(manifest)
    after = _state(manifest, include_candidates=False)
    runner = _RecordingRunner(error_on_call=2)
    _patch_static_guards(monkeypatch, iter([before, before, after]))

    code, report = retirement.run_retirement(
        mode="execute",
        expected_main_sha=APPROVED_MAIN,
        confirmation=manifest.expected_confirmation(APPROVED_MAIN),
        manifest_path=MANIFEST_PATH,
        remote="origin",
        repository_root=ROOT,
        runner=runner,
    )

    assert code == 0
    assert report["status"] == "completed"
    assert "TimeoutExpired" in report["detail"]


def test_execute_reports_indeterminate_when_postflight_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
):
    manifest = _manifest()
    before = _state(manifest)
    runner = _RecordingRunner(error_on_call=2)
    states: Iterator[retirement.LiveState] = iter([before, before])
    _patch_static_guards(monkeypatch, states)

    code, report = retirement.run_retirement(
        mode="execute",
        expected_main_sha=APPROVED_MAIN,
        confirmation=manifest.expected_confirmation(APPROVED_MAIN),
        manifest_path=MANIFEST_PATH,
        remote="origin",
        repository_root=ROOT,
        runner=runner,
    )

    assert code == 3
    assert report["status"] == "indeterminate"
    assert "postflight could not establish" in report["detail"]


def test_failed_atomic_push_is_blocked_only_when_all_leases_remain(
    monkeypatch: pytest.MonkeyPatch,
):
    manifest = _manifest()
    before = _state(manifest)
    runner = _RecordingRunner(
        iter(
            [
                retirement.CommandResult(0, "", ""),
                retirement.CommandResult(1, "", "atomic rejected"),
            ]
        )
    )
    _patch_static_guards(monkeypatch, iter([before, before, before]))

    code, report = retirement.run_retirement(
        mode="execute",
        expected_main_sha=APPROVED_MAIN,
        confirmation=manifest.expected_confirmation(APPROVED_MAIN),
        manifest_path=MANIFEST_PATH,
        remote="origin",
        repository_root=ROOT,
        runner=runner,
    )

    assert code == 2
    assert report["status"] == "blocked"
    assert "all audited candidate refs remain" in report["detail"]


def test_failed_push_with_concurrent_exclusion_drift_is_inconsistent(
    monkeypatch: pytest.MonkeyPatch,
):
    manifest = _manifest()
    before = _state(manifest)
    changed = _state(manifest)
    changed.refs[next(iter(manifest.exclusions))] = "c" * 40
    runner = _RecordingRunner(
        iter(
            [
                retirement.CommandResult(0, "", ""),
                retirement.CommandResult(1, "", "atomic rejected"),
            ]
        )
    )
    _patch_static_guards(monkeypatch, iter([before, before, changed]))

    code, report = retirement.run_retirement(
        mode="execute",
        expected_main_sha=APPROVED_MAIN,
        confirmation=manifest.expected_confirmation(APPROVED_MAIN),
        manifest_path=MANIFEST_PATH,
        remote="origin",
        repository_root=ROOT,
        runner=runner,
    )

    assert code == 3
    assert report["status"] == "inconsistent"
    assert "changed_or_missing_non_candidates" in report["detail"]


def test_partial_post_state_is_inconsistent_not_success(
    monkeypatch: pytest.MonkeyPatch,
):
    manifest = _manifest()
    before = _state(manifest)
    partial = _state(manifest, include_candidates=False)
    partial.refs[manifest.candidates[0].branch] = manifest.candidates[0].tip_sha
    runner = _RecordingRunner(
        iter(
            [
                retirement.CommandResult(0, "", ""),
                retirement.CommandResult(0, "", ""),
            ]
        )
    )
    _patch_static_guards(monkeypatch, iter([before, before, partial]))

    code, report = retirement.run_retirement(
        mode="execute",
        expected_main_sha=APPROVED_MAIN,
        confirmation=manifest.expected_confirmation(APPROVED_MAIN),
        manifest_path=MANIFEST_PATH,
        remote="origin",
        repository_root=ROOT,
        runner=runner,
    )

    assert code == 3
    assert report["status"] == "inconsistent"
    assert "Recovery review required" in report["detail"]


def test_run_retirement_rejects_unknown_mode_before_any_guard():
    with pytest.raises(retirement.GuardError, match="Mode must be exactly"):
        retirement.run_retirement(
            mode="other",
            expected_main_sha=APPROVED_MAIN,
            confirmation="",
            manifest_path=MANIFEST_PATH,
            remote="origin",
            repository_root=ROOT,
        )


def test_remote_configuration_requires_one_exact_fetch_and_push_url():
    manifest = _manifest()
    calls: list[list[str]] = []

    def runner(arguments, *, cwd, timeout):
        calls.append(list(arguments))
        if "--push" in arguments:
            return retirement.CommandResult(
                0,
                (
                    f"{retirement.CANONICAL_GITHUB_URL}\n"
                    "https://github.com/attacker/other.git\n"
                ),
                "",
            )
        return retirement.CommandResult(0, retirement.CANONICAL_GITHUB_URL + "\n", "")

    with pytest.raises(retirement.GuardError, match="exactly one"):
        retirement._configured_remote_urls(  # noqa: SLF001 - safety unit test
            "origin",
            repository_root=ROOT,
            runner=runner,
        )
    assert calls == [
        ["git", "remote", "get-url", "--all", "origin"],
        ["git", "remote", "get-url", "--push", "--all", "origin"],
    ]
    with pytest.raises(retirement.GuardError, match="unsupported"):
        retirement._configured_remote_urls(  # noqa: SLF001 - safety unit test
            "--upload-pack=bad",
            repository_root=ROOT,
            runner=runner,
        )
    retirement._validate_remote_url(  # noqa: SLF001 - safety unit test
        retirement.CANONICAL_GITHUB_URL,
        manifest,
    )
    with pytest.raises(retirement.GuardError, match="exact HTTPS"):
        retirement._validate_remote_url(  # noqa: SLF001 - safety unit test
            "https://github.com/attacker/HUB_Optimus.git",
            manifest,
        )
    with pytest.raises(retirement.GuardError, match="exact HTTPS"):
        retirement._validate_remote_url(  # noqa: SLF001 - safety unit test
            "https://github.com/Voxterrae/HUB_Optimus",
            manifest,
        )


def test_git_url_rewrites_and_environment_overrides_are_rejected():
    def rewrite_runner(arguments, *, cwd, timeout):
        return retirement.CommandResult(
            0,
            (
                "file:/tmp/config\t"
                "url.https://attacker.invalid/.insteadof "
                f"{retirement.CANONICAL_GITHUB_URL}\n"
            ),
            "",
        )

    with pytest.raises(retirement.GuardError, match="rewrites are forbidden"):
        retirement._reject_git_url_rewrites(  # noqa: SLF001 - safety unit test
            repository_root=ROOT,
            runner=rewrite_runner,
        )

    manifest = _manifest()
    with pytest.raises(retirement.GuardError, match="Unsafe Git environment"):
        retirement.validate_checkout(
            manifest,
            APPROVED_MAIN,
            remote="origin",
            repository_root=ROOT,
            runner=_RecordingRunner(),
            environment={"GIT_CONFIG_COUNT": "1"},
        )


def test_rest_and_git_inventory_disagreement_fails_before_push():
    manifest = _manifest()
    runner = _RecordingRunner(
        iter(
            [
                retirement.CommandResult(
                    0,
                    f"{'b' * 40}\trefs/heads/main\n",
                    "",
                )
            ]
        )
    )

    def api_reader(url: str, token: str | None):
        if "/branches?" in url:
            return [
                {
                    "name": "main",
                    "commit": {"sha": "c" * 40},
                    "protected": True,
                }
            ]
        return []

    with pytest.raises(retirement.GuardError, match="inventories differ"):
        retirement.collect_live_state(
            manifest,
            remote_url=retirement.CANONICAL_GITHUB_URL,
            token=None,
            repository_root=ROOT,
            runner=runner,
            api_reader=api_reader,
        )
    assert len(runner.calls) == 1
    assert runner.calls[0][:4] == ["git", "ls-remote", "--heads", "--"]


def test_manual_workflow_defaults_read_only_and_merge_cannot_activate_it():
    workflow = yaml.safe_load(WORKFLOW_PATH.read_text(encoding="utf-8"))
    triggers = workflow["on"]
    dispatch = triggers["workflow_dispatch"]
    jobs = workflow["jobs"]

    assert set(triggers) == {"workflow_dispatch"}
    assert dispatch["inputs"]["mode"]["default"] == "dry-run"
    assert dispatch["inputs"]["mode"]["options"] == ["dry-run", "execute"]
    assert dispatch["inputs"]["expected_main_sha"]["required"] is True
    assert dispatch["inputs"]["confirmation"]["required"] is False
    assert workflow["permissions"] == {"contents": "read"}
    assert jobs["dry-run"]["permissions"] == {
        "contents": "read",
        "pull-requests": "read",
    }
    assert jobs["execute"]["permissions"] == {
        "contents": "write",
        "issues": "write",
        "pull-requests": "read",
    }
    assert jobs["dry-run"]["if"] == "inputs.mode == 'dry-run'"
    assert jobs["execute"]["if"] == "inputs.mode == 'execute'"


def test_manual_workflow_uses_pinned_actions_and_trusted_main_guards():
    text = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert text.count(
        "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1"
    ) == 2
    assert text.count(
        "actions/setup-python@5fda3b95a4ea91299a34e894583c3862153e4b97"
    ) == 2
    assert text.count("persist-credentials: false") == 2
    assert text.count("ref: main") == 2
    assert text.count('"${GITHUB_REF}" != "refs/heads/main"') == 2
    assert text.count('"${GITHUB_REPOSITORY}" != "Voxterrae/HUB_Optimus"') == 2
    assert text.count('"${checked_out}" != "${EXPECTED_MAIN_SHA}"') == 2
    assert text.count('"${checked_out}" != "${GITHUB_SHA}"') == 2
    assert text.count('"${checked_out}" != "${remote_main}"') == 2
    assert "secrets." not in text
    assert "cancel-in-progress: false" in text

    workflow = yaml.safe_load(text)
    for job in workflow["jobs"].values():
        for step in job["steps"]:
            assert "${{ inputs." not in step.get("run", "")


def test_execute_workflow_has_ephemeral_auth_exact_confirmation_and_durable_report():
    text = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert "gh auth setup-git" in text
    assert "--mode execute" in text
    assert '--confirmation "${RETIREMENT_CONFIRMATION}"' in text
    assert "if: always()" in text
    assert "gh issue comment 1788" in text
    assert '--body-file "${REPORT_MARKDOWN}"' in text
    assert "--mode dry-run" in text
    assert "Audit retirement without receive-pack" in text
    assert "schedule:" not in text
    assert "\n  push:" not in text
    assert "\n  pull_request:" not in text
