"""Render per-family behavior aggregates from scenario telemetry.

The report consumes the ``telemetry.json`` written by
``tools/scenario_telemetry.py``. Behavioral failures (``no_agreement``) and
processing errors remain separate so malformed inputs are not presented as
simulation outcomes.
"""

from __future__ import annotations

import argparse
import json
import os
import secrets
import sys
import tempfile
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_TELEMETRY = REPO_ROOT / "scenarios" / "telemetry.json"
AGREEMENT = "agreement"
NO_AGREEMENT = "no_agreement"
ERROR_OUTCOMES = frozenset({"parse_error", "schema_error", "runtime_error"})
KNOWN_OUTCOMES = frozenset({AGREEMENT, NO_AGREEMENT}) | ERROR_OUTCOMES


class ReportInputError(ValueError):
    """Raised when telemetry cannot define a trustworthy behavior report."""


@dataclass(frozen=True)
class OutputTarget:
    """One validated output name anchored to its parent directory identity."""

    parent: Path
    name: str
    parent_device: int
    parent_inode: int
    source_name: str

    @property
    def path(self) -> Path:
        return self.parent / self.name


@dataclass
class FamilyStats:
    """Mutable aggregate for one telemetry family."""

    scenarios: int = 0
    agreements: int = 0
    failures: int = 0
    errors: int = 0
    convergence_rounds: list[int] = field(default_factory=list)

    @property
    def completed(self) -> int:
        return self.agreements + self.failures

    @property
    def agreement_rate(self) -> float | None:
        if self.completed == 0:
            return None
        return self.agreements * 100 / self.completed

    @property
    def average_round(self) -> float | None:
        if not self.convergence_rounds:
            return None
        return sum(self.convergence_rounds) / len(self.convergence_rounds)


def load_telemetry(path: Path) -> list[dict[str, Any]]:
    """Load and strictly validate current telemetry records."""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ReportInputError(f"telemetry file not found: {path}") from exc
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ReportInputError(f"cannot read telemetry file {path}: {exc}") from exc

    if not isinstance(payload, list):
        raise ReportInputError("telemetry root must be a JSON array")
    if not payload:
        raise ReportInputError("telemetry contains no scenario records")

    records: list[dict[str, Any]] = []
    for index, record in enumerate(payload):
        if not isinstance(record, dict):
            raise ReportInputError(f"telemetry[{index}] must be a JSON object")

        family = record.get("family")
        if not isinstance(family, str) or not family.strip():
            raise ReportInputError(
                f"telemetry[{index}].family must be a non-empty string"
            )
        if family != family.strip() or not family.isprintable():
            raise ReportInputError(
                f"telemetry[{index}].family must be printable and have no "
                "surrounding whitespace"
            )

        outcome = record.get("processing_outcome")
        if not isinstance(outcome, str) or outcome not in KNOWN_OUTCOMES:
            raise ReportInputError(
                f"telemetry[{index}].processing_outcome must be one of "
                f"{sorted(KNOWN_OUTCOMES)}"
            )

        result_status = record.get("result_status")
        if (
            not isinstance(result_status, str)
            or result_status not in {"success", "failure", "error"}
        ):
            raise ReportInputError(
                f"telemetry[{index}].result_status must be success, failure, or error"
            )

        rounds_used = record.get("rounds_used")
        max_rounds = record.get("max_rounds")
        for field_name, value in (
            ("rounds_used", rounds_used),
            ("max_rounds", max_rounds),
        ):
            if (
                not isinstance(value, int)
                or isinstance(value, bool)
                or value < 0
            ):
                raise ReportInputError(
                    f"telemetry[{index}].{field_name} must be a non-negative integer"
                )
        if rounds_used > max_rounds:
            raise ReportInputError(
                f"telemetry[{index}].rounds_used must not exceed max_rounds"
            )

        schema_valid = record.get("schema_valid")
        runtime_error = record.get("runtime_error")
        if not isinstance(schema_valid, bool) or not isinstance(runtime_error, bool):
            raise ReportInputError(
                f"telemetry[{index}] requires boolean schema_valid and runtime_error"
            )

        convergence_round = record.get("convergence_round")
        error_code = record.get("error_code")
        if outcome == AGREEMENT:
            if (
                not isinstance(convergence_round, int)
                or isinstance(convergence_round, bool)
                or convergence_round < 1
            ):
                raise ReportInputError(
                    f"telemetry[{index}].convergence_round must be a positive "
                    "integer for an agreement"
                )
            if (
                result_status != "success"
                or rounds_used != convergence_round
                or not schema_valid
                or runtime_error
                or error_code is not None
            ):
                raise ReportInputError(
                    f"telemetry[{index}] agreement fields contradict the "
                    "current telemetry contract"
                )
        elif outcome == NO_AGREEMENT:
            if (
                result_status != "failure"
                or convergence_round is not None
                or max_rounds < 1
                or rounds_used != max_rounds
                or not schema_valid
                or runtime_error
                or error_code is not None
            ):
                raise ReportInputError(
                    f"telemetry[{index}] no_agreement fields contradict the "
                    "current telemetry contract"
                )
        else:
            if (
                result_status != "error"
                or rounds_used != 0
                or convergence_round is not None
                or not isinstance(error_code, str)
                or not error_code
            ):
                raise ReportInputError(
                    f"telemetry[{index}] error fields contradict the current "
                    "telemetry contract"
                )
            if outcome in {"parse_error", "schema_error"} and (
                schema_valid or runtime_error or max_rounds != 0
            ):
                raise ReportInputError(
                    f"telemetry[{index}] {outcome} fields contradict the "
                    "current telemetry contract"
                )
            if outcome == "runtime_error":
                invalid_runtime_shape = (
                    not runtime_error
                    or (schema_valid and max_rounds < 1)
                    or (not schema_valid and max_rounds != 0)
                )
                if invalid_runtime_shape:
                    raise ReportInputError(
                        f"telemetry[{index}] runtime_error fields contradict the "
                        "current telemetry contract"
                    )

        records.append(record)
    return records


def aggregate_by_family(
    records: Sequence[dict[str, Any]],
) -> dict[str, FamilyStats]:
    """Aggregate current processing outcomes by family."""
    families: dict[str, FamilyStats] = {}
    for record in records:
        family = record["family"]
        stats = families.setdefault(family, FamilyStats())
        stats.scenarios += 1

        outcome = record["processing_outcome"]
        if outcome == AGREEMENT:
            stats.agreements += 1
            stats.convergence_rounds.append(record["convergence_round"])
        elif outcome == NO_AGREEMENT:
            stats.failures += 1
        else:
            stats.errors += 1
    return families


def _format_number(value: float | None, *, suffix: str = "") -> str:
    if value is None:
        return "-"
    rendered = f"{value:.2f}".rstrip("0").rstrip(".")
    return f"{rendered}{suffix}"


def _rows(families: dict[str, FamilyStats]) -> list[list[str]]:
    rows: list[list[str]] = []
    for family, stats in sorted(families.items()):
        rows.append(
            [
                family,
                str(stats.scenarios),
                str(stats.completed),
                _format_number(stats.agreement_rate, suffix="%"),
                _format_number(stats.average_round),
                str(stats.failures),
                str(stats.errors),
            ]
        )
    return rows


def render_text(families: dict[str, FamilyStats]) -> str:
    """Render a fixed-width plain-text table."""
    headers = [
        "Family",
        "Scenarios",
        "Completed",
        "Agreement % (completed)",
        "Avg Rounds (agreements)",
        "Failures",
        "Errors",
    ]
    rows = _rows(families)
    widths = [
        max(len(headers[index]), *(len(row[index]) for row in rows))
        for index in range(len(headers))
    ]

    def render_row(row: Sequence[str]) -> str:
        return "  ".join(
            value.ljust(widths[index]) for index, value in enumerate(row)
        ).rstrip()

    separator = "  ".join("-" * width for width in widths)
    return "\n".join([render_row(headers), separator, *(render_row(row) for row in rows)])


def render_markdown(families: dict[str, FamilyStats]) -> str:
    """Render a GitHub-flavored Markdown table."""
    headers = [
        "Family",
        "Scenarios",
        "Completed",
        "Agreement % (completed)",
        "Avg Rounds (agreements)",
        "Failures",
        "Errors",
    ]

    def escape(value: str) -> str:
        return value.replace("\\", "\\\\").replace("|", "\\|")

    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    lines.extend(
        "| " + " | ".join(escape(value) for value in row) + " |"
        for row in _rows(families)
    )
    return "\n".join(lines)


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render per-family aggregates from scenario telemetry."
    )
    parser.add_argument(
        "telemetry",
        nargs="?",
        type=Path,
        default=DEFAULT_TELEMETRY,
        help=f"Telemetry JSON file (default: {DEFAULT_TELEMETRY}).",
    )
    parser.add_argument(
        "--markdown",
        action="store_true",
        help="Render a Markdown table instead of fixed-width text.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Write the report to this file instead of stdout.",
    )
    return parser.parse_args(argv)


def _validate_output_target(telemetry: Path, output: Path) -> OutputTarget:
    """Resolve a stable parent and reject the telemetry source as output."""
    try:
        telemetry_path = telemetry.resolve(strict=True)
        output_parent = output.parent.resolve(strict=True)
        if not output_parent.is_dir():
            raise ReportInputError(f"output parent is not a directory: {output_parent}")
        if output.name in {"", ".", ".."}:
            raise ReportInputError("output file name is invalid")
        target = output_parent / output.name
        same_resolved_path = telemetry_path == target.resolve(strict=False)
        same_existing_file = target.exists() and telemetry_path.samefile(target)
        parent_stat = output_parent.stat()
    except (OSError, RuntimeError) as exc:
        raise ReportInputError(f"cannot validate output path {output}: {exc}") from exc
    if same_resolved_path or same_existing_file:
        raise ReportInputError("output file must not replace the telemetry input")
    return OutputTarget(
        parent=output_parent,
        name=output.name,
        parent_device=parent_stat.st_dev,
        parent_inode=parent_stat.st_ino,
        source_name=telemetry_path.name,
    )


def _secure_dir_fd_available() -> bool:
    return (
        hasattr(os, "O_DIRECTORY")
        and hasattr(os, "O_NOFOLLOW")
        and os.open in os.supports_dir_fd
        and os.rename in os.supports_dir_fd
        and os.unlink in os.supports_dir_fd
    )


def _write_report_with_dir_fd(target: OutputTarget, report: str) -> None:
    """Publish relative to an inode-checked directory descriptor."""
    directory_fd = -1
    descriptor = -1
    temporary_name: str | None = None
    try:
        flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
        if hasattr(os, "O_CLOEXEC"):
            flags |= os.O_CLOEXEC
        directory_fd = os.open(target.parent, flags)
        directory_stat = os.fstat(directory_fd)
        if (
            directory_stat.st_dev != target.parent_device
            or directory_stat.st_ino != target.parent_inode
        ):
            raise ReportInputError(
                "output parent changed after validation; report was not written"
            )

        create_flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
        if hasattr(os, "O_CLOEXEC"):
            create_flags |= os.O_CLOEXEC
        for _ in range(100):
            candidate = f".{target.name}.{secrets.token_hex(12)}.tmp"
            try:
                descriptor = os.open(
                    candidate,
                    create_flags,
                    0o600,
                    dir_fd=directory_fd,
                )
            except FileExistsError:
                continue
            temporary_name = candidate
            break
        if temporary_name is None:
            raise ReportInputError("cannot allocate a unique temporary report file")

        with os.fdopen(
            descriptor,
            "w",
            encoding="utf-8",
            newline="\n",
        ) as handle:
            descriptor = -1
            handle.write(report)
            handle.flush()
            os.fsync(handle.fileno())
        os.rename(
            temporary_name,
            target.name,
            src_dir_fd=directory_fd,
            dst_dir_fd=directory_fd,
        )
        temporary_name = None
        os.fsync(directory_fd)
    except OSError as exc:
        raise ReportInputError(f"cannot write report {target.path}: {exc}") from exc
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        if temporary_name is not None and directory_fd >= 0:
            try:
                os.unlink(temporary_name, dir_fd=directory_fd)
            except FileNotFoundError:
                pass
        if directory_fd >= 0:
            os.close(directory_fd)


def _write_report_path_fallback(target: OutputTarget, report: str) -> None:
    """Portable fallback with a source-name guard and parent revalidation."""
    if os.path.normcase(target.name) == os.path.normcase(target.source_name):
        raise ReportInputError(
            "this platform cannot safely publish a source-named report file"
        )
    temporary: Path | None = None
    descriptor = -1
    try:
        current_parent = target.parent.stat()
        if (
            current_parent.st_dev != target.parent_device
            or current_parent.st_ino != target.parent_inode
        ):
            raise ReportInputError(
                "output parent changed after validation; report was not written"
            )
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{target.name}.",
            suffix=".tmp",
            dir=target.parent,
            text=True,
        )
        temporary = Path(temporary_name)
        with os.fdopen(
            descriptor,
            "w",
            encoding="utf-8",
            newline="\n",
        ) as handle:
            descriptor = -1
            handle.write(report)
            handle.flush()
            os.fsync(handle.fileno())
        current_parent = target.parent.stat()
        if (
            current_parent.st_dev != target.parent_device
            or current_parent.st_ino != target.parent_inode
        ):
            raise ReportInputError(
                "output parent changed during publication; report was not written"
            )
        os.replace(temporary, target.path)
        temporary = None
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _write_report_atomically(target: OutputTarget, report: str) -> None:
    """Replace one report entry without following a swapped target or parent."""
    if _secure_dir_fd_available():
        _write_report_with_dir_fd(target, report)
    else:
        _write_report_path_fallback(target, report)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        records = load_telemetry(args.telemetry)
        families = aggregate_by_family(records)
        report = (
            render_markdown(families)
            if args.markdown
            else render_text(families)
        ) + "\n"
        if args.output is None:
            sys.stdout.write(report)
        else:
            target = _validate_output_target(args.telemetry, args.output)
            _write_report_atomically(target, report)
    except (ReportInputError, OSError) as exc:
        print(f"scenario-report: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
