from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
GENERATOR = REPO_ROOT / "tools" / "scenario_generator" / "generate_scenarios.py"
TELEMETRY = REPO_ROOT / "tools" / "scenario_telemetry.py"
MANIFEST_NAME = "generation_manifest.json"
FAMILIES = (
    "info_asymmetry",
    "resource_scarcity",
    "incentive_misalignment",
)


def _run_generator(output_dir: Path, count: int, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(GENERATOR),
            "--count",
            str(count),
            "--seed",
            "42",
            "--output-dir",
            str(output_dir),
            *extra,
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )


def _load_manifest(output_dir: Path) -> dict:
    return json.loads((output_dir / MANIFEST_NAME).read_text(encoding="utf-8"))


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _tree_snapshot(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def _owned_paths(output_dir: Path) -> set[str]:
    paths: set[str] = set()
    for family in FAMILIES:
        family_dir = output_dir / family
        if not family_dir.is_dir():
            continue
        pattern = re.compile(rf"{re.escape(family)}_\d+\.json")
        paths.update(
            path.relative_to(output_dir).as_posix()
            for path in family_dir.iterdir()
            if path.is_file() and pattern.fullmatch(path.name)
        )
    return paths


def test_manifest_selects_current_run_and_excludes_retained_stale_files(
    tmp_path: Path,
) -> None:
    scenario_dir = tmp_path / "generated"
    first = _run_generator(scenario_dir, 6)
    assert first.returncode == 0, first.stderr
    first_files = {entry["path"] for entry in _load_manifest(scenario_dir)["files"]}

    second = _run_generator(scenario_dir, 3)
    assert second.returncode == 0, second.stderr
    current_manifest = _load_manifest(scenario_dir)
    current_files = {entry["path"] for entry in current_manifest["files"]}
    stale = first_files - current_files

    assert len(current_files) == 3
    assert len(stale) == 5
    assert stale <= _owned_paths(scenario_dir)
    assert "Stale retained (not current in manifest) (5):" in second.stdout

    telemetry_dir = tmp_path / "telemetry"
    telemetry = subprocess.run(
        [
            sys.executable,
            str(TELEMETRY),
            "--scenario-dir",
            str(scenario_dir),
            "--output-dir",
            str(telemetry_dir),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    assert telemetry.returncode == 0, telemetry.stderr

    records = json.loads((telemetry_dir / "telemetry.json").read_text(encoding="utf-8"))
    index = json.loads((telemetry_dir / "index.json").read_text(encoding="utf-8"))
    assert len(records) == 3
    assert {record["generation_run_id"] for record in records} == {
        current_manifest["run_id"]
    }
    assert all(record["manifest_verified"] for record in records)
    assert index["total"] == 3
    assert index["generation"] == {
        "manifest_verified": True,
        "run_id": current_manifest["run_id"],
        "seed": 42,
    }


def test_clean_removes_only_stale_generator_owned_paths(tmp_path: Path) -> None:
    scenario_dir = tmp_path / "generated"
    first = _run_generator(scenario_dir, 6)
    assert first.returncode == 0, first.stderr

    family_note = scenario_dir / "info_asymmetry" / "research_notes.json"
    family_note.write_text('{"preserve": true}\n', encoding="utf-8")
    nested_note = scenario_dir / "info_asymmetry" / "archive" / "info_asymmetry_999.json"
    nested_note.parent.mkdir()
    nested_note.write_text('{"preserve": true}\n', encoding="utf-8")
    root_note = scenario_dir / "operator_input.json"
    root_note.write_text('{"preserve": true}\n', encoding="utf-8")

    second = _run_generator(scenario_dir, 3, "--clean")
    assert second.returncode == 0, second.stderr
    current_files = {entry["path"] for entry in _load_manifest(scenario_dir)["files"]}

    assert _owned_paths(scenario_dir) == current_files
    assert len(current_files) == 3
    assert family_note.read_text(encoding="utf-8") == '{"preserve": true}\n'
    assert nested_note.read_text(encoding="utf-8") == '{"preserve": true}\n'
    assert root_note.read_text(encoding="utf-8") == '{"preserve": true}\n'
    assert "Stale removed (5):" in second.stdout


def test_manifest_is_reproducible_for_same_seed_and_count(tmp_path: Path) -> None:
    first_dir = tmp_path / "first"
    second_dir = tmp_path / "second"
    first = _run_generator(first_dir, 7)
    second = _run_generator(second_dir, 7)
    assert first.returncode == 0, first.stderr
    assert second.returncode == 0, second.stderr

    first_manifest = (first_dir / MANIFEST_NAME).read_bytes()
    second_manifest = (second_dir / MANIFEST_NAME).read_bytes()
    assert first_manifest == second_manifest

    for entry in _load_manifest(first_dir)["files"]:
        first_bytes = (first_dir / entry["path"]).read_bytes()
        second_bytes = (second_dir / entry["path"]).read_bytes()
        assert first_bytes == second_bytes
        assert hashlib.sha256(first_bytes).hexdigest() == entry["sha256"]


def test_generated_benchmark_scan_excludes_manifest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    scenario_dir = tmp_path / "generated"
    generated = _run_generator(scenario_dir, 1)
    assert generated.returncode == 0, generated.stderr
    nested_manifest_scenario = (
        scenario_dir / "operator_cases" / MANIFEST_NAME
    )
    nested_manifest_scenario.parent.mkdir()
    nested_manifest_scenario.write_bytes(
        (REPO_ROOT / "example_scenario.json").read_bytes()
    )

    benchmark_path = REPO_ROOT / "benchmarks" / "run_benchmarks.py"
    module = _load_module(benchmark_path, "manifest_benchmark_test")

    empty_static = tmp_path / "static"
    empty_expected = tmp_path / "expected"
    empty_static.mkdir()
    empty_expected.mkdir()
    monkeypatch.setattr(module, "SCENARIOS_DIR", empty_static)
    monkeypatch.setattr(module, "EXPECTED_DIR", empty_expected)
    monkeypatch.setattr(module, "GENERATED_DIR", scenario_dir)
    monkeypatch.setattr(sys, "argv", ["run_benchmarks.py", "--include-generated"])

    assert module.main() == 0
    captured = capsys.readouterr()
    assert "2 passed, 0 failed, 2 total" in captured.out
    assert captured.out.count("generation_manifest") == 1


def test_telemetry_fails_closed_when_manifested_file_changes(tmp_path: Path) -> None:
    scenario_dir = tmp_path / "generated"
    generated = _run_generator(scenario_dir, 3)
    assert generated.returncode == 0, generated.stderr
    manifest = _load_manifest(scenario_dir)
    changed = scenario_dir / manifest["files"][0]["path"]
    changed.write_text(changed.read_text(encoding="utf-8") + "\n", encoding="utf-8")

    telemetry_dir = tmp_path / "telemetry"
    telemetry = subprocess.run(
        [
            sys.executable,
            str(TELEMETRY),
            "--manifest",
            str(scenario_dir / MANIFEST_NAME),
            "--output-dir",
            str(telemetry_dir),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )

    assert telemetry.returncode == 1
    assert "[manifest-error] manifest hash mismatch:" in telemetry.stderr
    assert not telemetry_dir.exists()


def test_manifested_telemetry_executes_the_exact_verified_bytes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scenario_dir = tmp_path / "generated"
    generated = _run_generator(scenario_dir, 1)
    assert generated.returncode == 0, generated.stderr

    telemetry = _load_module(TELEMETRY, "immutable_manifest_telemetry_test")
    real_load_manifest = telemetry.load_manifest
    changed_paths: list[Path] = []

    def load_then_replace_source(*args, **kwargs):
        selected, manifest = real_load_manifest(*args, **kwargs)
        for path, _file_hash, _verified_bytes in selected:
            path.write_bytes(b"{post-verification replacement")
            changed_paths.append(path)
        return selected, manifest

    monkeypatch.setattr(telemetry, "load_manifest", load_then_replace_source)

    records = telemetry.collect_all(
        scenario_dir,
        42,
        scenario_dir / MANIFEST_NAME,
    )

    assert changed_paths
    assert all(path.read_bytes() == b"{post-verification replacement" for path in changed_paths)
    assert len(records) == 1
    assert records[0]["processing_outcome"] in {"agreement", "no_agreement"}
    assert records[0]["manifest_verified"] is True
    assert records[0]["scenario_sha256"] == _load_manifest(
        scenario_dir
    )["files"][0]["sha256"]


def test_legacy_telemetry_skips_only_the_root_manifest(tmp_path: Path) -> None:
    scenario_dir = tmp_path / "generated"
    scenario_dir.mkdir()
    (scenario_dir / MANIFEST_NAME).write_text("{}\n", encoding="utf-8")
    nested_scenario = scenario_dir / "operator_cases" / MANIFEST_NAME
    nested_scenario.parent.mkdir()
    nested_scenario.write_bytes(
        (REPO_ROOT / "example_scenario.json").read_bytes()
    )
    telemetry = _load_module(TELEMETRY, "nested_manifest_telemetry_test")

    records = telemetry.collect_all(scenario_dir, 42)

    assert len(records) == 1
    assert records[0]["scenario_id"] == "generation_manifest"
    assert records[0]["manifest_verified"] is False
    assert records[0]["processing_outcome"] in {"agreement", "no_agreement"}


@pytest.mark.parametrize(
    ("helper_name", "failure_call"),
    (
        ("_write_staged_file", 2),
        ("_publish_staged_file", 2),
    ),
)
def test_generation_failure_restores_previous_set_and_manifest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    helper_name: str,
    failure_call: int,
) -> None:
    scenario_dir = tmp_path / "generated"
    generated = _run_generator(scenario_dir, 6)
    assert generated.returncode == 0, generated.stderr
    unrelated = scenario_dir / "operator_notes.json"
    unrelated.write_text('{"preserve": true}\n', encoding="utf-8")
    before = _tree_snapshot(scenario_dir)

    generator = _load_module(
        GENERATOR,
        f"transactional_generator_test_{helper_name}",
    )
    real_helper = getattr(generator, helper_name)
    calls = 0

    def fail_during_transaction(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == failure_call:
            raise OSError(f"injected {helper_name} failure")
        return real_helper(*args, **kwargs)

    monkeypatch.setattr(generator, helper_name, fail_during_transaction)

    with pytest.raises(OSError, match=f"injected {helper_name} failure"):
        generator.write_generation(
            generator.generate(3, 99),
            scenario_dir,
            seed=99,
            requested_count=3,
            clean=True,
        )

    assert calls >= failure_call
    assert _tree_snapshot(scenario_dir) == before
    assert not list(tmp_path.glob(".generated.generation-*"))


@pytest.mark.parametrize("count", (0, -1))
def test_non_positive_count_preserves_existing_output(
    tmp_path: Path,
    count: int,
) -> None:
    scenario_dir = tmp_path / "generated"
    generated = _run_generator(scenario_dir, 3)
    assert generated.returncode == 0, generated.stderr
    before = _tree_snapshot(scenario_dir)

    rejected = _run_generator(scenario_dir, count, "--clean")

    assert rejected.returncode == 2
    assert "[generator-error] --count must be greater than zero" in rejected.stderr
    assert _tree_snapshot(scenario_dir) == before


@pytest.mark.skipif(not hasattr(os, "symlink"), reason="symlinks unavailable")
def test_generator_rejects_symlink_output_directory(tmp_path: Path) -> None:
    actual_output = tmp_path / "actual"
    symlink_output = tmp_path / "generated"
    actual_output.mkdir()
    symlink_output.symlink_to(actual_output, target_is_directory=True)

    generated = _run_generator(symlink_output, 1, "--clean")

    assert generated.returncode == 1
    assert "[generator-error] refusing symlink output directory:" in generated.stderr
    assert list(actual_output.iterdir()) == []


@pytest.mark.skipif(not hasattr(os, "symlink"), reason="symlinks unavailable")
def test_generator_rejects_family_symlink_outside_output_root(tmp_path: Path) -> None:
    scenario_dir = tmp_path / "generated"
    outside = tmp_path / "outside"
    scenario_dir.mkdir()
    outside.mkdir()
    protected = outside / "info_asymmetry_001.json"
    protected.write_text('{"preserve": true}\n', encoding="utf-8")
    (scenario_dir / "info_asymmetry").symlink_to(outside, target_is_directory=True)

    generated = _run_generator(scenario_dir, 1, "--clean")

    assert generated.returncode == 1
    assert "[generator-error] refusing symlink output target:" in generated.stderr
    assert protected.read_text(encoding="utf-8") == '{"preserve": true}\n'
    assert not (scenario_dir / MANIFEST_NAME).exists()
