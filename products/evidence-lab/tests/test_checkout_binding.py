from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

SOURCE = Path(__file__).parents[1] / "scripts" / "apply-dataverse-schema.py"
SPEC = importlib.util.spec_from_file_location("evidence_dataverse_binding_regressions", SOURCE)
assert SPEC and SPEC.loader
app = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = app
SPEC.loader.exec_module(app)
CONTRACT, PLAN = app.load_public_artifacts()


@pytest.fixture
def squashed_checkout(tmp_path, monkeypatch):
    source = tmp_path / "source"
    source.mkdir()
    env = {k: v for k, v in os.environ.items() if not k.upper().startswith("GIT_")}
    env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull)
    def git(*args, cwd=source, check=True):
        return subprocess.run(
            ["git", "-c", "user.name=Synthetic Test", "-c", "user.email=owner" + "@" + "example.com",
             "-c", "commit.gpgsign=false", "-c", "core.autocrlf=false", *args],
            cwd=cwd, env=env, check=check, capture_output=True,
        )
    git("init", "-b", "main")
    (source / "README.md").write_text("Synthetic protected baseline\n")
    git("add", ".")
    git("commit", "-m", "baseline")
    anchor = git("rev-parse", "HEAD").stdout.decode().strip()
    git("checkout", "-b", "old-proposal")
    package = source / "products" / "evidence-lab"
    relative = [
        Path("contract/optimus-evidence-lab.dataverse.json"),
        Path("plans/optimus-evidence-lab.schema-plan.json"),
        Path("scripts/apply-dataverse-schema.py"),
    ]
    contents = [json.dumps(CONTRACT), json.dumps(PLAN), "synthetic source\n"]
    for path, content in zip(relative, contents):
        target = package / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8", newline="\n")
    git("add", ".")
    git("commit", "-m", "old branch-only candidate")
    old = git("rev-parse", "HEAD").stdout.decode().strip()
    git("checkout", "main")
    git("merge", "--squash", "old-proposal")
    git("commit", "-m", "protected squash result")
    clone = tmp_path / "canonical"
    git("clone", "--single-branch", "--no-local", str(source), str(clone))
    assert git("merge-base", "--is-ancestor", old, "HEAD", cwd=clone, check=False).returncode != 0
    package = clone / "products" / "evidence-lab"
    monkeypatch.setattr(app, "PACKAGE_ROOT", package)
    monkeypatch.setattr(app, "CONTRACT_PATH", package / relative[0])
    monkeypatch.setattr(app, "PLAN_PATH", package / relative[1])
    monkeypatch.setattr(app, "__file__", str(package / relative[2]))
    monkeypatch.setattr(app, "PROTECTED_MAIN_ANCHOR", anchor, raising=False)
    def clone_git(*args, **kwargs):
        return git(*args, cwd=clone, **kwargs)
    return clone, relative, clone_git


def test_fresh_squash_clone_binds_without_old_branch_history(squashed_checkout):
    _clone, _paths, git = squashed_checkout
    expected = git("rev-parse", "HEAD").stdout.decode().strip()
    assert app.verify_public_artifacts(CONTRACT, PLAN, require_git_binding=True) == expected


@pytest.mark.parametrize("index", [0, 1, 2])
def test_hidden_worktree_edits_are_rejected(squashed_checkout, index):
    clone, paths, git = squashed_checkout
    relative = Path("products/evidence-lab") / paths[index]
    git("update-index", "--skip-worktree", relative.as_posix())
    with (clone / relative).open("a", encoding="utf-8") as stream:
        stream.write("\nchanged source\n")
    assert not git("diff", "--name-only").stdout.strip()
    with pytest.raises(app.ApplicatorError, match="bytes differ"):
        app.verify_public_artifacts(CONTRACT, PLAN, require_git_binding=True)


def test_staged_edit_with_restored_worktree_is_rejected(squashed_checkout):
    clone, paths, git = squashed_checkout
    relative = Path("products/evidence-lab") / paths[2]
    target = clone / relative
    original = target.read_bytes()
    target.write_bytes(original + b"staged alteration\n")
    git("add", relative.as_posix())
    target.write_bytes(original)
    with pytest.raises(app.ApplicatorError, match="bytes differ"):
        app.verify_public_artifacts(CONTRACT, PLAN, require_git_binding=True)


def test_unrelated_anchor_fails_closed(squashed_checkout, monkeypatch):
    monkeypatch.setattr(app, "PROTECTED_MAIN_ANCHOR", "0" * 40, raising=False)
    with pytest.raises(app.ApplicatorError, match="protected main anchor"):
        app.verify_public_artifacts(CONTRACT, PLAN, require_git_binding=True)


def test_ambient_git_redirection_cannot_select_another_checkout(squashed_checkout, monkeypatch):
    _clone, _paths, git = squashed_checkout
    monkeypatch.setenv("GIT_DIR", "does-not-exist")
    monkeypatch.setenv("GIT_WORK_TREE", "does-not-exist")
    monkeypatch.setenv("GIT_CONFIG_COUNT", "1")
    monkeypatch.setenv("GIT_CONFIG_KEY_0", "core.repositoryformatversion")
    monkeypatch.setenv("GIT_CONFIG_VALUE_0", "999")
    expected = git("rev-parse", "HEAD").stdout.decode().strip()
    assert app.verify_public_artifacts(CONTRACT, PLAN, require_git_binding=True) == expected


def test_contract_and_plan_content_pins_still_fail_closed():
    changed = dict(CONTRACT, schemaVersion="tampered")
    with pytest.raises(app.ApplicatorError, match="Contract hash drift"):
        app.verify_public_artifacts(changed, PLAN, require_git_binding=False)
    changed_plan = dict(PLAN, mode="APPLY")
    with pytest.raises(app.ApplicatorError, match="self-hash"):
        app.verify_public_artifacts(CONTRACT, changed_plan, require_git_binding=False)


