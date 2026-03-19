"""Tests for the mojibake detection guard (tools/check_mojibake.py)."""
from __future__ import annotations

import subprocess
import sys
import textwrap
from pathlib import Path

TOOL = Path(__file__).resolve().parent.parent / "tools" / "check_mojibake.py"


def _run_guard(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(TOOL), *args],
        capture_output=True,
        text=True,
        cwd=cwd,
    )


class TestCleanFiles:
    """Guard must pass on files without mojibake."""

    def test_clean_markdown(self, tmp_path: Path) -> None:
        f = tmp_path / "clean.md"
        f.write_text("# Title\n\nNormal content with accents: é à ü ñ ö\n", encoding="utf-8")
        result = _run_guard(".", cwd=tmp_path)
        assert result.returncode == 0
        assert "passed" in result.stdout.lower()

    def test_empty_file(self, tmp_path: Path) -> None:
        f = tmp_path / "empty.md"
        f.write_text("", encoding="utf-8")
        result = _run_guard(".", cwd=tmp_path)
        assert result.returncode == 0

    def test_non_markdown_ignored(self, tmp_path: Path) -> None:
        f = tmp_path / "data.json"
        f.write_text('{"key": "Ã¤"}', encoding="utf-8")
        result = _run_guard(".", cwd=tmp_path)
        assert result.returncode == 0  # .json not scanned


class TestMojibakeDetection:
    """Guard must detect known mojibake signatures."""

    def test_replacement_char(self, tmp_path: Path) -> None:
        f = tmp_path / "bad.md"
        f.write_text("Some text with \uFFFD replacement\n", encoding="utf-8")
        result = _run_guard(".", cwd=tmp_path)
        assert result.returncode == 1
        assert "replacement_char" in result.stderr

    def test_double_utf8_a_tilde(self, tmp_path: Path) -> None:
        f = tmp_path / "bad.md"
        f.write_text("Badly encoded: Ã¤\n", encoding="utf-8")
        result = _run_guard(".", cwd=tmp_path)
        assert result.returncode == 1
        assert "double_utf8_A_tilde" in result.stderr

    def test_smart_punct_mojibake(self, tmp_path: Path) -> None:
        f = tmp_path / "bad.md"
        f.write_text("Broken quotes: â??helloâ?\x9d\n", encoding="utf-8")
        result = _run_guard(".", cwd=tmp_path)
        assert result.returncode == 1
        assert "smart_punct_mojibake" in result.stderr


class TestDirectoryScan:
    """Guard must recurse into directories."""

    def test_finds_mojibake_in_subdirectory(self, tmp_path: Path) -> None:
        subdir = tmp_path / "nested" / "deep"
        subdir.mkdir(parents=True)
        clean = tmp_path / "ok.md"
        clean.write_text("# Fine\n", encoding="utf-8")
        bad = subdir / "corrupt.md"
        bad.write_text("Double encoded: Â\u00A0\n", encoding="utf-8")
        result = _run_guard(".", cwd=tmp_path)
        assert result.returncode == 1
        assert "corrupt.md" in result.stderr

    def test_nonexistent_target(self, tmp_path: Path) -> None:
        result = _run_guard(str(tmp_path / "does_not_exist"), cwd=tmp_path)
        assert result.returncode == 0  # no files found, no errors
