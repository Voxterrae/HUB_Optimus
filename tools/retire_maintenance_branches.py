#!/usr/bin/env python3
"""Retire the exact stale maintenance refs audited for issue #1788.

The default mode is read-only.  Execution is available only when the checked
out commit is the caller-supplied live ``main`` SHA, every live maintenance ref
matches the versioned manifest, the recovery bundle restores cleanly, and the
caller supplies the manifest-derived confirmation sentence.

The deletion is one atomic Git push with an exact force-with-lease for every
ref.  There is deliberately no batching or non-atomic fallback.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Iterable, Mapping, Sequence


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = (
    REPOSITORY_ROOT
    / "docs"
    / "maintenance"
    / "issue-1788"
    / "maintenance-branches.manifest.v1.json"
)
EXPECTED_REPOSITORY = "Voxterrae/HUB_Optimus"
EXPECTED_ISSUE = 1788
EXPECTED_CANDIDATE_COUNT = 881
EXPECTED_PATTERN = r"^chore/maintenance-[0-9]+$"
EXPECTED_PREFIX = "chore/maintenance-"
EXPECTED_EXCLUSIONS = {
    "chore/maintenance-19": "5d7a61840c56671323a9c4f579d6f41d91a16b80",
    "chore/maintenance-21": "97b8476749c62b2a2a19645a6fe2b28c70d883a1",
    "chore/maintenance-25": "03fcc983f00dcdfaae7fa765dea72ca67e18dd4d",
    "chore/maintenance-D": "3198ce3e641ac14a4b1767b4f40b2e9d23d5a421",
    "chore/maintenance-bot-v2": "008c3fb78d805b8e35fb721e4659bcb4277b271d",
    "chore/maintenance-workflow-fix": (
        "40983c1bd2b4dc5c3f5bc11810b63c79f64e4d28"
    ),
}
SHA1_PATTERN = re.compile(r"^[0-9a-f]{40}$")
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
MAX_API_PAGES = 1_000
API_PAGE_SIZE = 100
COMMAND_TIMEOUT_SECONDS = 300
CANONICAL_GITHUB_URL = f"https://github.com/{EXPECTED_REPOSITORY}.git"


class GuardError(RuntimeError):
    """A safety invariant failed before or after the remote operation."""


@dataclass(frozen=True)
class Candidate:
    branch: str
    tip_sha: str
    tree_sha: str
    tip_committed_at: dt.datetime

    @property
    def full_ref(self) -> str:
        return f"refs/heads/{self.branch}"


@dataclass(frozen=True)
class Manifest:
    path: Path
    repository: str
    cutoff: dt.datetime
    candidates: tuple[Candidate, ...]
    exclusions: Mapping[str, str]
    archive_path: Path
    archive_sha256: str
    archive_size: int
    canonical_heads_sha256: str
    confirmation_template: str

    @property
    def candidate_refs(self) -> Mapping[str, str]:
        return {candidate.branch: candidate.tip_sha for candidate in self.candidates}

    def expected_confirmation(self, expected_main_sha: str) -> str:
        return self.confirmation_template.format(
            expected_main_sha=expected_main_sha
        )


@dataclass(frozen=True)
class PullRequest:
    number: int
    head_branch: str


@dataclass(frozen=True)
class LiveState:
    refs: Mapping[str, str]
    protected: Mapping[str, bool]
    open_pull_requests: tuple[PullRequest, ...]

    @property
    def total_branches(self) -> int:
        return len(self.refs)

    @property
    def maintenance_branches(self) -> int:
        return sum(name.startswith(EXPECTED_PREFIX) for name in self.refs)


@dataclass(frozen=True)
class CommandResult:
    returncode: int
    stdout: str
    stderr: str


Runner = Callable[..., CommandResult]
ApiPageReader = Callable[[str, str | None], list[Any]]


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise GuardError(f"Manifest contains duplicate JSON key {key!r}.")
        result[key] = value
    return result


def _require_mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise GuardError(f"{label} must be a JSON object.")
    return value


def _require_list(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise GuardError(f"{label} must be a JSON array.")
    return value


def _require_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise GuardError(f"{label} must be a non-empty string.")
    return value


def _require_int(value: Any, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise GuardError(f"{label} must be an integer.")
    return value


def _parse_sha1(value: Any, label: str) -> str:
    text = _require_string(value, label)
    if not SHA1_PATTERN.fullmatch(text):
        raise GuardError(f"{label} must be a full lowercase SHA-1.")
    return text


def _parse_sha256(value: Any, label: str) -> str:
    text = _require_string(value, label)
    if not SHA256_PATTERN.fullmatch(text):
        raise GuardError(f"{label} must be a full lowercase SHA-256.")
    return text


def _parse_utc(value: Any, label: str) -> dt.datetime:
    text = _require_string(value, label)
    if not text.endswith("Z"):
        raise GuardError(f"{label} must use canonical UTC with a trailing Z.")
    try:
        parsed = dt.datetime.fromisoformat(text[:-1] + "+00:00")
    except ValueError as error:
        raise GuardError(f"{label} is not a valid timestamp.") from error
    if parsed.tzinfo != dt.timezone.utc:
        raise GuardError(f"{label} must be UTC.")
    return parsed


def _resolve_versioned_path(root: Path, relative: Any, label: str) -> Path:
    text = _require_string(relative, label)
    posix_path = PurePosixPath(text)
    if posix_path.is_absolute() or ".." in posix_path.parts:
        raise GuardError(f"{label} must stay inside the repository.")
    resolved_root = root.resolve()
    resolved = (resolved_root / Path(*posix_path.parts)).resolve()
    try:
        resolved.relative_to(resolved_root)
    except ValueError as error:
        raise GuardError(f"{label} escapes the repository.") from error
    return resolved


def _canonical_heads(candidates: Iterable[Candidate]) -> bytes:
    return "".join(
        f"{candidate.tip_sha} {candidate.full_ref}\n" for candidate in candidates
    ).encode("utf-8")


def load_manifest(path: Path, repository_root: Path = REPOSITORY_ROOT) -> Manifest:
    """Load and strictly validate the versioned retirement manifest."""

    try:
        file_stat = path.lstat()
        if not stat.S_ISREG(file_stat.st_mode) or path.is_symlink():
            raise GuardError("Manifest must be a regular, non-symlink file.")
        raw = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise GuardError(f"Cannot read valid UTF-8 JSON manifest: {error}") from error
    document = _require_mapping(raw, "manifest")

    if document.get("format_version") != 1:
        raise GuardError("Only maintenance retirement manifest format_version 1 is valid.")
    if document.get("repository") != EXPECTED_REPOSITORY:
        raise GuardError(f"Manifest repository must be {EXPECTED_REPOSITORY}.")
    if document.get("issue") != EXPECTED_ISSUE:
        raise GuardError(f"Manifest authority must be issue #{EXPECTED_ISSUE}.")
    _parse_sha1(document.get("source_base_sha"), "source_base_sha")

    cutoff_document = _require_mapping(document.get("cutoff"), "cutoff")
    if cutoff_document.get("field") != "tip_committed_at":
        raise GuardError("The cutoff field must be tip_committed_at.")
    if cutoff_document.get("operator") != "strictly_before":
        raise GuardError("The cutoff must be exclusive.")
    cutoff = _parse_utc(cutoff_document.get("exclusive_utc"), "cutoff.exclusive_utc")

    selection = _require_mapping(document.get("selection"), "selection")
    if selection.get("candidate_pattern") != EXPECTED_PATTERN:
        raise GuardError("The candidate pattern differs from the issue #1788 scope.")
    if selection.get("maintenance_prefix") != EXPECTED_PREFIX:
        raise GuardError("The maintenance prefix differs from the issue #1788 scope.")
    if selection.get("candidate_count") != EXPECTED_CANDIDATE_COUNT:
        raise GuardError(
            f"The audited candidate count must be {EXPECTED_CANDIDATE_COUNT}."
        )

    exclusions_document = _require_list(
        selection.get("semantic_exclusions"),
        "selection.semantic_exclusions",
    )
    exclusions: dict[str, str] = {}
    for index, raw_exclusion in enumerate(exclusions_document):
        exclusion = _require_mapping(
            raw_exclusion,
            f"selection.semantic_exclusions[{index}]",
        )
        branch = _require_string(
            exclusion.get("branch"),
            f"selection.semantic_exclusions[{index}].branch",
        )
        sha = _parse_sha1(
            exclusion.get("tip_sha"),
            f"selection.semantic_exclusions[{index}].tip_sha",
        )
        _require_string(
            exclusion.get("reason"),
            f"selection.semantic_exclusions[{index}].reason",
        )
        if branch in exclusions:
            raise GuardError(f"Duplicate semantic exclusion {branch}.")
        exclusions[branch] = sha
    if exclusions != EXPECTED_EXCLUSIONS:
        raise GuardError("The six semantic exclusions or their audited SHAs changed.")

    raw_candidates = _require_list(document.get("candidates"), "candidates")
    if len(raw_candidates) != EXPECTED_CANDIDATE_COUNT:
        raise GuardError(
            f"Manifest must contain exactly {EXPECTED_CANDIDATE_COUNT} candidates."
        )
    candidate_pattern = re.compile(EXPECTED_PATTERN)
    candidates: list[Candidate] = []
    seen: set[str] = set()
    for index, raw_candidate in enumerate(raw_candidates):
        candidate = _require_mapping(raw_candidate, f"candidates[{index}]")
        branch = _require_string(
            candidate.get("branch"),
            f"candidates[{index}].branch",
        )
        if not candidate_pattern.fullmatch(branch):
            raise GuardError(f"Candidate {branch!r} is outside the numeric scope.")
        if branch in exclusions:
            raise GuardError(f"Semantic branch {branch} cannot be a candidate.")
        if branch in seen:
            raise GuardError(f"Duplicate candidate {branch}.")
        if candidate.get("protected") is not False:
            raise GuardError(f"Candidate {branch} was not audited as unprotected.")
        if candidate.get("open_pull_requests") != []:
            raise GuardError(f"Candidate {branch} was not audited as PR-free.")
        tip_sha = _parse_sha1(
            candidate.get("tip_sha"),
            f"candidates[{index}].tip_sha",
        )
        tree_sha = _parse_sha1(
            candidate.get("tree_sha"),
            f"candidates[{index}].tree_sha",
        )
        committed_at = _parse_utc(
            candidate.get("tip_committed_at"),
            f"candidates[{index}].tip_committed_at",
        )
        if committed_at >= cutoff:
            raise GuardError(f"Candidate {branch} is not strictly before the cutoff.")
        seen.add(branch)
        candidates.append(
            Candidate(
                branch=branch,
                tip_sha=tip_sha,
                tree_sha=tree_sha,
                tip_committed_at=committed_at,
            )
        )
    if [candidate.branch for candidate in candidates] != sorted(seen):
        raise GuardError("Candidates must be unique and sorted by branch name.")

    observed = _require_mapping(document.get("observed_remote"), "observed_remote")
    if observed.get("candidate_branches") != len(candidates):
        raise GuardError("Observed candidate count does not match the manifest.")
    if observed.get("maintenance_branches") != (
        len(candidates) + len(exclusions)
    ):
        raise GuardError("Observed maintenance count is internally inconsistent.")
    expected_numeric = len(candidates) + sum(
        bool(candidate_pattern.fullmatch(branch)) for branch in exclusions
    )
    if observed.get("numeric_maintenance_branches") != expected_numeric:
        raise GuardError("Observed numeric maintenance count is inconsistent.")
    if observed.get("expected_remaining_maintenance_branches") != len(exclusions):
        raise GuardError("Expected remaining maintenance count is inconsistent.")
    total_observed = _require_int(
        observed.get("total_branches"),
        "observed_remote.total_branches",
    )
    if observed.get("expected_remaining_branches_if_executed_at_observation") != (
        total_observed - len(candidates)
    ):
        raise GuardError("Observed post-retirement branch count is inconsistent.")
    _parse_sha1(observed.get("main_sha"), "observed_remote.main_sha")
    _parse_utc(observed.get("observed_at"), "observed_remote.observed_at")

    archive = _require_mapping(document.get("archive"), "archive")
    archive_path = _resolve_versioned_path(
        repository_root,
        archive.get("path"),
        "archive.path",
    )
    archive_sha256 = _parse_sha256(archive.get("sha256"), "archive.sha256")
    archive_size = _require_int(archive.get("size_bytes"), "archive.size_bytes")
    if archive_size <= 0:
        raise GuardError("archive.size_bytes must be positive.")
    if archive.get("ref_count") != len(candidates):
        raise GuardError("Archive ref count does not match the candidates.")
    if archive.get("ref_namespace") != "refs/heads/":
        raise GuardError("Archive must restore refs under refs/heads/.")
    if archive.get("complete_history") is not True:
        raise GuardError("Archive must record complete history.")
    if archive.get("prerequisites") != []:
        raise GuardError("Archive must be standalone and have no prerequisites.")
    if archive.get("object_hash_algorithm") != "sha1":
        raise GuardError("The audited archive must use this repository's SHA-1 format.")
    canonical_heads_sha256 = _parse_sha256(
        archive.get("canonical_heads_sha256"),
        "archive.canonical_heads_sha256",
    )
    observed_heads_sha256 = hashlib.sha256(_canonical_heads(candidates)).hexdigest()
    if canonical_heads_sha256 != observed_heads_sha256:
        raise GuardError("Archive head inventory digest does not match the candidates.")

    execution = _require_mapping(document.get("execution"), "execution")
    if execution.get("default_mode") != "dry-run":
        raise GuardError("The retirement default mode must remain dry-run.")
    if execution.get("atomic") is not True:
        raise GuardError("The retirement operation must remain atomic.")
    if execution.get("lease_per_ref") is not True:
        raise GuardError("Every deletion must retain an exact ref lease.")
    if execution.get("batching_fallback") is not False:
        raise GuardError("A batching or non-atomic fallback is forbidden.")
    confirmation_template = _require_string(
        execution.get("confirmation_template"),
        "execution.confirmation_template",
    )
    expected_template = (
        f"RETIRE {len(candidates)} MAINTENANCE BRANCHES AT MAIN "
        "{expected_main_sha} USING ARCHIVE "
        f"{archive_sha256}"
    )
    if confirmation_template != expected_template:
        raise GuardError("The exact confirmation template is inconsistent.")

    return Manifest(
        path=path.resolve(),
        repository=EXPECTED_REPOSITORY,
        cutoff=cutoff,
        candidates=tuple(candidates),
        exclusions=exclusions,
        archive_path=archive_path,
        archive_sha256=archive_sha256,
        archive_size=archive_size,
        canonical_heads_sha256=canonical_heads_sha256,
        confirmation_template=confirmation_template,
    )


def _default_runner(
    arguments: Sequence[str],
    *,
    cwd: Path,
    timeout: int = COMMAND_TIMEOUT_SECONDS,
) -> CommandResult:
    result = subprocess.run(
        list(arguments),
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )
    return CommandResult(result.returncode, result.stdout, result.stderr)


def _run_checked(
    arguments: Sequence[str],
    *,
    cwd: Path,
    label: str,
    runner: Runner = _default_runner,
    timeout: int = COMMAND_TIMEOUT_SECONDS,
) -> CommandResult:
    try:
        result = runner(arguments, cwd=cwd, timeout=timeout)
    except (OSError, subprocess.SubprocessError, TimeoutError) as error:
        raise GuardError(f"{label} could not run: {type(error).__name__}: {error}") from error
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        if len(detail) > 1_000:
            detail = f"{detail[:1_000]}…"
        raise GuardError(f"{label} failed: {detail or 'no diagnostic output'}")
    return result


def _bundle_has_prerequisites(path: Path) -> bool:
    try:
        with path.open("rb") as handle:
            signature = handle.readline().rstrip(b"\r\n")
            if signature not in (b"# v2 git bundle", b"# v3 git bundle"):
                raise GuardError("Recovery archive is not a supported Git bundle.")
            for raw_line in handle:
                line = raw_line.rstrip(b"\r\n")
                if not line:
                    return False
                if line.startswith(b"-"):
                    return True
    except OSError as error:
        raise GuardError(f"Cannot read recovery archive header: {error}") from error
    raise GuardError("Recovery archive has no bundle header terminator.")


def _parse_bundle_heads(output: str) -> dict[str, str]:
    heads: dict[str, str] = {}
    for line in output.splitlines():
        fields = line.split(" ", 1)
        if len(fields) != 2:
            raise GuardError("Recovery archive emitted an invalid head record.")
        sha, ref = fields
        if not SHA1_PATTERN.fullmatch(sha) or not ref.startswith("refs/heads/"):
            raise GuardError(f"Recovery archive contains invalid head {line!r}.")
        branch = ref.removeprefix("refs/heads/")
        if branch in heads:
            raise GuardError(f"Recovery archive contains duplicate head {branch}.")
        heads[branch] = sha
    return heads


def verify_archive(
    manifest: Manifest,
    *,
    repository_root: Path = REPOSITORY_ROOT,
    runner: Runner = _default_runner,
) -> None:
    """Verify bytes, refs, dates, trees, standalone restore, and object graph."""

    path = manifest.archive_path
    try:
        file_stat = path.lstat()
        if not stat.S_ISREG(file_stat.st_mode) or path.is_symlink():
            raise GuardError("Recovery archive must be a regular, non-symlink file.")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as error:
        raise GuardError(f"Cannot read versioned recovery archive: {error}") from error
    if file_stat.st_size != manifest.archive_size:
        raise GuardError("Recovery archive size differs from the manifest.")
    if digest != manifest.archive_sha256:
        raise GuardError("Recovery archive SHA-256 differs from the manifest.")
    if _bundle_has_prerequisites(path):
        raise GuardError("Recovery archive is thin; standalone history is required.")

    _run_checked(
        ["git", "bundle", "verify", str(path)],
        cwd=repository_root,
        label="git bundle verify",
        runner=runner,
    )
    list_result = _run_checked(
        ["git", "bundle", "list-heads", str(path)],
        cwd=repository_root,
        label="git bundle list-heads",
        runner=runner,
    )
    heads = _parse_bundle_heads(list_result.stdout)
    if heads != manifest.candidate_refs:
        raise GuardError("Recovery archive refs or SHAs differ from the manifest.")
    canonical = hashlib.sha256(_canonical_heads(manifest.candidates)).hexdigest()
    if canonical != manifest.canonical_heads_sha256:
        raise GuardError("Recovery archive canonical head digest changed.")

    with tempfile.TemporaryDirectory(prefix="hub-optimus-branch-recovery-") as temporary:
        bare = Path(temporary) / "restored.git"
        _run_checked(
            ["git", "init", "--bare", "-q", str(bare)],
            cwd=repository_root,
            label="initialize archive restore",
            runner=runner,
        )
        _run_checked(
            [
                "git",
                f"--git-dir={bare}",
                "fetch",
                "--quiet",
                str(path),
                "refs/heads/*:refs/heads/*",
            ],
            cwd=repository_root,
            label="restore archive",
            runner=runner,
        )
        refs_result = _run_checked(
            [
                "git",
                f"--git-dir={bare}",
                "for-each-ref",
                (
                    "--format=%(refname)%09%(objectname)%09%(tree)"
                    "%09%(committerdate:unix)"
                ),
                "refs/heads",
            ],
            cwd=repository_root,
            label="inspect restored archive",
            runner=runner,
        )
        restored: dict[str, tuple[str, str, int]] = {}
        for line in refs_result.stdout.splitlines():
            fields = line.split("\t")
            if len(fields) != 4:
                raise GuardError("Restored archive emitted invalid ref metadata.")
            ref, sha, tree_sha, timestamp_text = fields
            if not ref.startswith("refs/heads/"):
                raise GuardError(f"Restored archive contains non-head ref {ref}.")
            branch = ref.removeprefix("refs/heads/")
            try:
                timestamp = int(timestamp_text)
            except ValueError as error:
                raise GuardError(
                    f"Restored archive has invalid commit time for {branch}."
                ) from error
            restored[branch] = (sha, tree_sha, timestamp)
        if set(restored) != set(manifest.candidate_refs):
            raise GuardError("Standalone restore contains an unexpected ref set.")
        for candidate in manifest.candidates:
            sha, tree_sha, timestamp = restored[candidate.branch]
            if sha != candidate.tip_sha or tree_sha != candidate.tree_sha:
                raise GuardError(
                    f"Standalone restore metadata changed for {candidate.branch}."
                )
            committed_at = dt.datetime.fromtimestamp(timestamp, tz=dt.timezone.utc)
            if committed_at != candidate.tip_committed_at:
                raise GuardError(
                    f"Standalone restore commit time changed for {candidate.branch}."
                )
            if committed_at >= manifest.cutoff:
                raise GuardError(
                    f"Standalone restore crossed the cutoff at {candidate.branch}."
                )
        _run_checked(
            [
                "git",
                f"--git-dir={bare}",
                "fsck",
                "--full",
                "--strict",
                "--no-dangling",
            ],
            cwd=repository_root,
            label="git fsck restored archive",
            runner=runner,
        )


def _api_page(url: str, token: str | None) -> list[Any]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "HUB-Optimus-issue-1788-retirement",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = response.read()
    except (urllib.error.URLError, TimeoutError) as error:
        raise GuardError(f"GitHub API read failed for {url}: {error}") from error
    try:
        parsed = json.loads(payload)
    except (UnicodeError, json.JSONDecodeError) as error:
        raise GuardError(f"GitHub API returned invalid JSON for {url}.") from error
    if not isinstance(parsed, list):
        raise GuardError(f"GitHub API returned a non-list response for {url}.")
    return parsed


def _read_all_pages(
    endpoint: str,
    token: str | None,
    *,
    reader: ApiPageReader = _api_page,
) -> list[Any]:
    records: list[Any] = []
    separator = "&" if "?" in endpoint else "?"
    for page in range(1, MAX_API_PAGES + 1):
        url = (
            f"https://api.github.com{endpoint}{separator}"
            f"per_page={API_PAGE_SIZE}&page={page}"
        )
        batch = reader(url, token)
        records.extend(batch)
        if len(batch) < API_PAGE_SIZE:
            return records
    raise GuardError("GitHub API pagination exceeded the explicit safety ceiling.")


def _parse_ls_remote(output: str) -> dict[str, str]:
    refs: dict[str, str] = {}
    for line in output.splitlines():
        fields = line.split("\t")
        if len(fields) != 2:
            raise GuardError("git ls-remote returned an invalid record.")
        sha, ref = fields
        if not SHA1_PATTERN.fullmatch(sha) or not ref.startswith("refs/heads/"):
            raise GuardError(f"git ls-remote returned invalid head {line!r}.")
        branch = ref.removeprefix("refs/heads/")
        if branch in refs:
            raise GuardError(f"git ls-remote returned duplicate head {branch}.")
        refs[branch] = sha
    if not refs:
        raise GuardError("git ls-remote returned no branches.")
    return refs


def collect_live_state(
    manifest: Manifest,
    *,
    remote_url: str,
    token: str | None,
    repository_root: Path = REPOSITORY_ROOT,
    runner: Runner = _default_runner,
    api_reader: ApiPageReader = _api_page,
) -> LiveState:
    """Read all branches twice (REST and Git) plus every open pull request."""

    repository = urllib.parse.quote(manifest.repository, safe="/")
    branch_records = _read_all_pages(
        f"/repos/{repository}/branches",
        token,
        reader=api_reader,
    )
    protected: dict[str, bool] = {}
    api_refs: dict[str, str] = {}
    for index, raw in enumerate(branch_records):
        record = _require_mapping(raw, f"GitHub branch response[{index}]")
        name = _require_string(record.get("name"), f"GitHub branch[{index}].name")
        commit = _require_mapping(
            record.get("commit"),
            f"GitHub branch[{index}].commit",
        )
        sha = _parse_sha1(commit.get("sha"), f"GitHub branch[{index}].commit.sha")
        protected_value = record.get("protected")
        if not isinstance(protected_value, bool):
            raise GuardError(f"GitHub branch {name} has invalid protected state.")
        if name in api_refs:
            raise GuardError(f"GitHub API returned duplicate branch {name}.")
        api_refs[name] = sha
        protected[name] = protected_value

    pull_records = _read_all_pages(
        f"/repos/{repository}/pulls?state=open",
        token,
        reader=api_reader,
    )
    pulls: list[PullRequest] = []
    for index, raw in enumerate(pull_records):
        record = _require_mapping(raw, f"GitHub pull response[{index}]")
        number = _require_int(
            record.get("number"),
            f"GitHub pull[{index}].number",
        )
        head = _require_mapping(record.get("head"), f"GitHub pull[{index}].head")
        branch = _require_string(
            head.get("ref"),
            f"GitHub pull[{index}].head.ref",
        )
        pulls.append(PullRequest(number=number, head_branch=branch))

    ls_remote = _run_checked(
        ["git", "ls-remote", "--heads", "--", remote_url],
        cwd=repository_root,
        label="git ls-remote",
        runner=runner,
    )
    git_refs = _parse_ls_remote(ls_remote.stdout)
    if api_refs != git_refs:
        raise GuardError(
            "GitHub REST and Git branch inventories differ; retry a fresh audit."
        )
    return LiveState(
        refs=git_refs,
        protected=protected,
        open_pull_requests=tuple(pulls),
    )


def validate_live_state(
    manifest: Manifest,
    state: LiveState,
    expected_main_sha: str,
) -> None:
    """Require the live maintenance namespace to equal the audited universe."""

    if not SHA1_PATTERN.fullmatch(expected_main_sha):
        raise GuardError("Expected main SHA must be a full lowercase SHA-1.")
    if state.refs.get("main") != expected_main_sha:
        raise GuardError("Live main does not match the explicitly approved SHA.")

    expected_maintenance = set(manifest.candidate_refs) | set(manifest.exclusions)
    live_maintenance = {
        branch for branch in state.refs if branch.startswith(EXPECTED_PREFIX)
    }
    if live_maintenance != expected_maintenance:
        missing = sorted(expected_maintenance - live_maintenance)
        added = sorted(live_maintenance - expected_maintenance)
        raise GuardError(
            "Live maintenance namespace changed "
            f"(missing={missing[:5]}, added={added[:5]})."
        )

    for branch, expected_sha in manifest.candidate_refs.items():
        live_sha = state.refs.get(branch)
        if live_sha != expected_sha:
            raise GuardError(
                f"Candidate {branch} moved or disappeared "
                f"(expected {expected_sha}, observed {live_sha})."
            )
        if state.protected.get(branch) is not False:
            raise GuardError(f"Candidate {branch} is protected or protection is unknown.")

    blocked_prs: dict[str, list[int]] = {}
    for pull in state.open_pull_requests:
        if pull.head_branch in manifest.candidate_refs:
            blocked_prs.setdefault(pull.head_branch, []).append(pull.number)
    if blocked_prs:
        branch = sorted(blocked_prs)[0]
        raise GuardError(
            f"Candidate {branch} belongs to open pull request(s) "
            f"{blocked_prs[branch]}."
        )

    for branch, expected_sha in manifest.exclusions.items():
        live_sha = state.refs.get(branch)
        if live_sha != expected_sha:
            raise GuardError(
                f"Semantic exclusion {branch} moved or disappeared; re-audit required."
            )


def _git_output(
    arguments: Sequence[str],
    *,
    repository_root: Path,
    runner: Runner,
    label: str,
) -> str:
    return _run_checked(
        ["git", *arguments],
        cwd=repository_root,
        label=label,
        runner=runner,
    ).stdout.strip()


def _validate_remote_url(url: str, manifest: Manifest) -> None:
    parsed = urllib.parse.urlsplit(url)
    expected_path = f"/{manifest.repository}"
    if (
        parsed.scheme != "https"
        or parsed.hostname != "github.com"
        or parsed.port is not None
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
        or parsed.path.removesuffix(".git") != expected_path
        or url != CANONICAL_GITHUB_URL
    ):
        raise GuardError(
            "Push URL must be the exact HTTPS GitHub repository from the manifest."
        )


def _configured_remote_urls(
    remote: str,
    *,
    repository_root: Path,
    runner: Runner,
) -> tuple[str, str]:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", remote):
        raise GuardError("Remote name contains unsupported characters.")
    fetch_urls = _git_output(
        ["remote", "get-url", "--all", remote],
        repository_root=repository_root,
        runner=runner,
        label="read fetch URL",
    ).splitlines()
    push_urls = _git_output(
        ["remote", "get-url", "--push", "--all", remote],
        repository_root=repository_root,
        runner=runner,
        label="read push URL",
    ).splitlines()
    if len(fetch_urls) != 1 or len(push_urls) != 1:
        raise GuardError("Remote must have exactly one fetch URL and one push URL.")
    return fetch_urls[0], push_urls[0]


def _reject_git_url_rewrites(
    *,
    repository_root: Path,
    runner: Runner,
) -> None:
    try:
        result = runner(
            [
                "git",
                "config",
                "--show-origin",
                "--get-regexp",
                r"^url\..*\.(insteadof|pushinsteadof)$",
            ],
            cwd=repository_root,
            timeout=COMMAND_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.SubprocessError, TimeoutError) as error:
        raise GuardError(
            f"Cannot inspect Git URL rewrite configuration: {type(error).__name__}: {error}"
        ) from error
    if result.returncode not in (0, 1):
        detail = (result.stderr or result.stdout).strip()
        raise GuardError(f"Cannot inspect Git URL rewrite configuration: {detail}")
    if result.stdout.strip():
        raise GuardError("Git URL insteadOf/pushInsteadOf rewrites are forbidden.")


def validate_checkout(
    manifest: Manifest,
    expected_main_sha: str,
    *,
    remote: str,
    repository_root: Path = REPOSITORY_ROOT,
    runner: Runner = _default_runner,
    environment: Mapping[str, str] | None = None,
) -> None:
    """Require a clean, trusted, versioned checkout and exact push destination."""

    environment = os.environ if environment is None else environment
    unsafe_git_environment = sorted(
        key
        for key in environment
        if key.startswith("GIT_CONFIG_")
        or key
        in {
            "GIT_CONFIG",
            "GIT_CONFIG_GLOBAL",
            "GIT_CONFIG_SYSTEM",
            "GIT_DIR",
            "GIT_WORK_TREE",
            "GIT_COMMON_DIR",
            "GIT_INDEX_FILE",
            "GIT_NAMESPACE",
            "GIT_OBJECT_DIRECTORY",
            "GIT_ALTERNATE_OBJECT_DIRECTORIES",
            "GIT_SSH",
            "GIT_SSH_COMMAND",
        }
    )
    if unsafe_git_environment:
        raise GuardError(
            f"Unsafe Git environment override(s): {unsafe_git_environment}."
        )
    if not SHA1_PATTERN.fullmatch(expected_main_sha):
        raise GuardError("Expected main SHA must be a full lowercase SHA-1.")
    head = _git_output(
        ["rev-parse", "HEAD"],
        repository_root=repository_root,
        runner=runner,
        label="read checked-out commit",
    )
    if head != expected_main_sha:
        raise GuardError("Checked-out commit does not match the approved main SHA.")
    status = _git_output(
        ["status", "--porcelain=v1", "--untracked-files=all"],
        repository_root=repository_root,
        runner=runner,
        label="inspect checkout status",
    )
    if status:
        raise GuardError("Checkout is not clean; retirement stopped fail-closed.")

    for path in (manifest.path, manifest.archive_path):
        try:
            relative = path.resolve().relative_to(repository_root.resolve()).as_posix()
        except ValueError as error:
            raise GuardError("Versioned evidence escaped the checkout.") from error
        _run_checked(
            ["git", "ls-files", "--error-unmatch", "--", relative],
            cwd=repository_root,
            label=f"verify tracked evidence {relative}",
            runner=runner,
        )
        _run_checked(
            ["git", "diff", "--quiet", "--no-ext-diff", "HEAD", "--", relative],
            cwd=repository_root,
            label=f"verify committed evidence {relative}",
            runner=runner,
        )
        stage = _git_output(
            ["ls-files", "--stage", "--", relative],
            repository_root=repository_root,
            runner=runner,
            label=f"verify evidence mode {relative}",
        )
        if not stage.startswith("100644 ") or not stage.endswith(f"\t{relative}"):
            raise GuardError(f"Versioned evidence {relative} must be a 100644 file.")

    fetch_url, push_url = _configured_remote_urls(
        remote,
        repository_root=repository_root,
        runner=runner,
    )
    _validate_remote_url(fetch_url, manifest)
    _validate_remote_url(push_url, manifest)
    if fetch_url.removesuffix(".git") != push_url.removesuffix(".git"):
        raise GuardError("Fetch and push URLs resolve to different repositories.")
    _reject_git_url_rewrites(repository_root=repository_root, runner=runner)

    if environment.get("GITHUB_ACTIONS") == "true":
        if environment.get("GITHUB_EVENT_NAME") != "workflow_dispatch":
            raise GuardError("GitHub Actions execution must be a manual workflow_dispatch.")
        if environment.get("GITHUB_REF") != "refs/heads/main":
            raise GuardError("GitHub Actions execution must be dispatched from main.")
        if environment.get("GITHUB_SHA") != expected_main_sha:
            raise GuardError("Dispatch SHA does not match the approved main SHA.")
        if environment.get("GITHUB_REPOSITORY") != EXPECTED_REPOSITORY:
            raise GuardError("Workflow repository does not match the manifest.")


def build_push_command(
    manifest: Manifest,
    *,
    remote_url: str = CANONICAL_GITHUB_URL,
    dry_run: bool,
) -> list[str]:
    """Build one atomic deletion command with an explicit lease per ref."""

    arguments = [
        "git",
        "push",
        "--atomic",
        "--porcelain",
        "--no-follow-tags",
        "--no-verify",
    ]
    if dry_run:
        arguments.append("--dry-run")
    arguments.extend(
        f"--force-with-lease={candidate.full_ref}:{candidate.tip_sha}"
        for candidate in manifest.candidates
    )
    _validate_remote_url(remote_url, manifest)
    arguments.extend(["--", remote_url])
    arguments.extend(f":{candidate.full_ref}" for candidate in manifest.candidates)
    return arguments


def _command_fingerprint(arguments: Sequence[str]) -> str:
    return hashlib.sha256(
        "\0".join(arguments).encode("utf-8", errors="strict")
    ).hexdigest()


def validate_post_state(
    manifest: Manifest,
    before: LiveState,
    after: LiveState,
) -> tuple[bool, str]:
    """Classify the observed post-push state without masking partial mutation."""

    remaining_candidates = sorted(set(manifest.candidate_refs) & set(after.refs))
    missing_existing_non_candidates = sorted(
        branch
        for branch, sha in before.refs.items()
        if branch not in manifest.candidate_refs and after.refs.get(branch) != sha
    )
    new_maintenance = sorted(
        branch
        for branch in after.refs
        if branch.startswith(EXPECTED_PREFIX)
        and branch not in manifest.exclusions
    )
    postflight_open_candidate_prs = sorted(
        (pull.number, pull.head_branch)
        for pull in after.open_pull_requests
        if pull.head_branch in manifest.candidate_refs
    )
    if (
        not remaining_candidates
        and not missing_existing_non_candidates
        and not new_maintenance
        and not postflight_open_candidate_prs
    ):
        return True, "All audited candidates are absent and prior non-candidates are intact."
    detail = (
        f"remaining_candidates={remaining_candidates[:5]}, "
        f"changed_or_missing_non_candidates={missing_existing_non_candidates[:5]}, "
        f"new_maintenance={new_maintenance[:5]}, "
        f"postflight_open_candidate_prs={postflight_open_candidate_prs[:5]}"
    )
    return False, detail


def _state_counts(state: LiveState) -> dict[str, int]:
    return {
        "total_branches": state.total_branches,
        "maintenance_branches": state.maintenance_branches,
    }


def _render_markdown(report: Mapping[str, Any]) -> str:
    lines = [
        "## Audited maintenance branch retirement",
        "",
        f"- Mode: `{report['mode']}`",
        f"- Status: **{report['status']}**",
        f"- Detail: {report['detail']}",
        f"- Approved main: `{report['expected_main_sha']}`",
        f"- Recovery archive: `{report['archive_sha256']}`",
        f"- Audited candidates: `{report['candidate_count']}`",
    ]
    pre_counts = report.get("pre_counts")
    if pre_counts:
        lines.extend(
            [
                f"- Preflight branches: `{pre_counts['total_branches']}` total, "
                f"`{pre_counts['maintenance_branches']}` maintenance",
            ]
        )
    post_counts = report.get("post_counts")
    if post_counts:
        lines.extend(
            [
                f"- Postflight branches: `{post_counts['total_branches']}` total, "
                f"`{post_counts['maintenance_branches']}` maintenance",
            ]
        )
    lines.extend(
        [
            f"- Atomic push plan SHA-256: `{report['push_plan_sha256']}`",
            "",
            "The recovery bundle and exact tip manifest are versioned under "
            "`docs/maintenance/issue-1788/`.",
        ]
    )
    if report["mode"] == "dry-run" and report["status"] == "ready":
        lines.extend(
            [
                "",
                "Execution requires this exact confirmation:",
                "",
                f"`{report['required_confirmation']}`",
            ]
        )
    return "\n".join(lines) + "\n"


def _publish_report(
    report: Mapping[str, Any],
    *,
    json_path: Path | None,
    markdown_path: Path | None,
) -> None:
    markdown = _render_markdown(report)
    json_text = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    if json_path:
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(json_text, encoding="utf-8", newline="\n")
    if markdown_path:
        markdown_path.parent.mkdir(parents=True, exist_ok=True)
        markdown_path.write_text(markdown, encoding="utf-8", newline="\n")
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a", encoding="utf-8", newline="\n") as handle:
            handle.write(markdown)
    print(markdown, end="")


def _base_report(
    manifest: Manifest,
    *,
    mode: str,
    expected_main_sha: str,
    push_command: Sequence[str],
) -> dict[str, Any]:
    return {
        "format_version": 1,
        "issue": EXPECTED_ISSUE,
        "mode": mode,
        "status": "checking",
        "detail": "Safety checks are in progress.",
        "expected_main_sha": expected_main_sha,
        "archive_sha256": manifest.archive_sha256,
        "candidate_count": len(manifest.candidates),
        "push_plan_sha256": _command_fingerprint(push_command),
        "required_confirmation": manifest.expected_confirmation(expected_main_sha),
        "pre_counts": None,
        "post_counts": None,
        "push_returncode": None,
    }


def run_retirement(
    *,
    mode: str,
    expected_main_sha: str,
    confirmation: str,
    manifest_path: Path,
    remote: str,
    repository_root: Path = REPOSITORY_ROOT,
    runner: Runner = _default_runner,
    api_reader: ApiPageReader = _api_page,
    token: str | None = None,
    environment: Mapping[str, str] | None = None,
) -> tuple[int, dict[str, Any]]:
    """Run the guarded dry-run or execute path and return a report."""

    if mode not in {"dry-run", "execute"}:
        raise GuardError("Mode must be exactly dry-run or execute.")
    manifest = load_manifest(manifest_path, repository_root)
    push_command = build_push_command(manifest, dry_run=False)
    report = _base_report(
        manifest,
        mode=mode,
        expected_main_sha=expected_main_sha,
        push_command=push_command,
    )

    try:
        verify_archive(manifest, repository_root=repository_root, runner=runner)
        validate_checkout(
            manifest,
            expected_main_sha,
            remote=remote,
            repository_root=repository_root,
            runner=runner,
            environment=environment,
        )
        before = collect_live_state(
            manifest,
            remote_url=CANONICAL_GITHUB_URL,
            token=token,
            repository_root=repository_root,
            runner=runner,
            api_reader=api_reader,
        )
        validate_live_state(manifest, before, expected_main_sha)
        report["pre_counts"] = _state_counts(before)

        if mode == "dry-run":
            report["status"] = "ready"
            report["detail"] = (
                "All local, archive, REST, PR, protection, ref, and cutoff "
                "checks passed. No receive-pack command was invoked."
            )
            return 0, report

        required_confirmation = manifest.expected_confirmation(expected_main_sha)
        if confirmation != required_confirmation:
            raise GuardError("Exact retirement confirmation was not supplied.")

        dry_run_command = build_push_command(
            manifest,
            dry_run=True,
        )
        _run_checked(
            dry_run_command,
            cwd=repository_root,
            label="atomic Git push dry-run",
            runner=runner,
        )

        immediately_before = collect_live_state(
            manifest,
            remote_url=CANONICAL_GITHUB_URL,
            token=token,
            repository_root=repository_root,
            runner=runner,
            api_reader=api_reader,
        )
        validate_live_state(manifest, immediately_before, expected_main_sha)

        push_error = ""
        try:
            push_result = runner(
                push_command,
                cwd=repository_root,
                timeout=COMMAND_TIMEOUT_SECONDS,
            )
            report["push_returncode"] = push_result.returncode
        except (OSError, subprocess.SubprocessError, TimeoutError) as error:
            # Once subprocess invocation begins, an exception cannot prove
            # whether the remote committed the atomic update before an ACK was
            # lost.  Postflight remains authoritative.
            push_result = CommandResult(-1, "", "")
            push_error = f"{type(error).__name__}: {error}"

        # Always query after the real push.  A transport error may happen after
        # the server committed the atomic update, so returncode alone is not
        # authoritative.
        try:
            after = collect_live_state(
                manifest,
                remote_url=CANONICAL_GITHUB_URL,
                token=token,
                repository_root=repository_root,
                runner=runner,
                api_reader=api_reader,
            )
        except (GuardError, OSError, subprocess.SubprocessError, TimeoutError) as error:
            report["status"] = "indeterminate"
            report["detail"] = (
                "A real atomic push was attempted, but postflight could not "
                f"establish remote state: {type(error).__name__}: {error}"
            )
            if push_error:
                report["detail"] += f"; push transport: {push_error}"
            return 3, report
        report["post_counts"] = _state_counts(after)
        complete, detail = validate_post_state(manifest, immediately_before, after)
        if complete:
            report["status"] = "completed"
            if push_result.returncode == 0:
                report["detail"] = detail
            else:
                report["detail"] = (
                    "The push transport returned non-zero, but a fresh REST/Git "
                    f"postflight proves the atomic deletion completed. {detail}"
                )
                if push_error:
                    report["detail"] += f" Transport diagnostic: {push_error}"
            return 0, report

        all_candidates_unchanged = all(
            after.refs.get(branch) == sha
            for branch, sha in manifest.candidate_refs.items()
        )
        all_existing_non_candidates_unchanged = all(
            after.refs.get(branch) == sha
            for branch, sha in immediately_before.refs.items()
            if branch not in manifest.candidate_refs
        )
        no_unexpected_maintenance = all(
            not branch.startswith(EXPECTED_PREFIX)
            or branch in manifest.candidate_refs
            or branch in manifest.exclusions
            for branch in after.refs
        )
        no_postflight_candidate_pr = all(
            pull.head_branch not in manifest.candidate_refs
            for pull in after.open_pull_requests
        )
        if (
            push_result.returncode != 0
            and all_candidates_unchanged
            and all_existing_non_candidates_unchanged
            and no_unexpected_maintenance
            and no_postflight_candidate_pr
        ):
            report["status"] = "blocked"
            report["detail"] = (
                "Git rejected or did not apply the atomic deletion; all audited "
                "candidate refs remain at their leased SHAs and prior "
                "non-candidate refs remain intact."
            )
            return 2, report

        report["status"] = "inconsistent"
        report["detail"] = (
            "Postflight does not match either a complete atomic deletion or a "
            f"fully unchanged candidate set. Recovery review required: {detail}"
        )
        return 3, report
    except GuardError as error:
        report["status"] = "blocked"
        report["detail"] = str(error)
        return 2, report


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Dry-run or atomically retire only the 881 maintenance refs "
            "versioned for issue #1788."
        )
    )
    parser.add_argument(
        "--mode",
        choices=("dry-run", "execute"),
        default="dry-run",
        help="Default: dry-run. Execute still requires exact confirmation.",
    )
    parser.add_argument(
        "--expected-main-sha",
        required=True,
        help="Exact live main SHA approved for this invocation.",
    )
    parser.add_argument(
        "--confirmation",
        default="",
        help="Exact manifest-derived sentence required only in execute mode.",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_MANIFEST,
        help="Versioned issue #1788 manifest.",
    )
    parser.add_argument("--remote", default="origin")
    parser.add_argument("--report-json", type=Path)
    parser.add_argument("--report-markdown", type=Path)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    arguments = parse_args(argv)
    try:
        code, report = run_retirement(
            mode=arguments.mode,
            expected_main_sha=arguments.expected_main_sha,
            confirmation=arguments.confirmation,
            manifest_path=arguments.manifest,
            remote=arguments.remote,
            token=os.environ.get("GITHUB_TOKEN"),
        )
    except GuardError as error:
        # Manifest errors happen before enough trusted data exists to build the
        # structured operational report.
        print(f"Retirement blocked: {error}", file=sys.stderr)
        return 2
    _publish_report(
        report,
        json_path=arguments.report_json,
        markdown_path=arguments.report_markdown,
    )
    return code


if __name__ == "__main__":
    raise SystemExit(main())
