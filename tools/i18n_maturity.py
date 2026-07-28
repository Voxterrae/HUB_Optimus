"""Policy-aware translation maturity audit helpers.

The maturity manifest is deliberately descriptive: it records what each file is
today.  Passing this audit means that the declarations are honest and that the
files required by a locale's coverage tier exist.  It does not certify linguistic
quality.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Iterable


MANIFEST_VERSION = 1
REQUIRED_STATES = {
    "missing",
    "stub",
    "draft-machine",
    "review-needed",
    "reviewed",
    "canonical",
    "parity",
}
REVIEW_EVIDENCE_STATES = {"reviewed"}
BCP47_PATTERN = re.compile(
    r"^[A-Za-z]{2,3}(?:-[A-Za-z]{4})?(?:-(?:[A-Za-z]{2}|\d{3}))?"
    r"(?:-[A-Za-z0-9]{5,8})*$"
)
EXPLICIT_STUB_PATTERNS = (
    re.compile(r"^\s*<!--\s*TODO:\s*TRANSLATE\s*-->\s*$", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^\s*(?:>\s*)?Translation pending\.\s*$", re.IGNORECASE | re.MULTILINE),
    re.compile(r"\bTemporary mirror file\b.*\bTranslation pending\b", re.IGNORECASE),
    re.compile(r"\bcurrently (?:an? )?stub\b", re.IGNORECASE),
    re.compile(r"\bstub honn[eê]te\b", re.IGNORECASE),
)


class ManifestError(ValueError):
    """Raised when the maturity manifest is malformed."""


@dataclass(frozen=True)
class MaturityDeclaration:
    """Declared maturity and any human review evidence."""

    state: str
    reviewer: str | None = None
    evidence: str | None = None


@dataclass(frozen=True)
class FileObservation:
    """Observed state for one locale/surface/file tuple."""

    locale: str
    direction: str
    tier: str
    surface: str
    filename: str
    path: Path
    state: str
    required: bool
    exists: bool
    identical_to_source: bool


@dataclass
class AuditResult:
    """Complete audit result."""

    manifest: dict[str, Any]
    observations: list[FileObservation]
    errors: list[str]
    warnings: list[str]

    @property
    def ok(self) -> bool:
        return not self.errors


def load_manifest(path: Path) -> dict[str, Any]:
    """Load and validate the top-level shape of a maturity manifest."""

    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ManifestError(f"Maturity manifest not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ManifestError(f"Invalid JSON in maturity manifest {path}: {exc}") from exc

    if not isinstance(manifest, dict):
        raise ManifestError("Maturity manifest must be a JSON object")
    if manifest.get("manifest_version") != MANIFEST_VERSION:
        raise ManifestError(
            f"Unsupported manifest_version {manifest.get('manifest_version')!r}; "
            f"expected {MANIFEST_VERSION}"
        )

    for key in ("policy", "states", "tiers", "locales", "surfaces"):
        if not isinstance(manifest.get(key), dict) or not manifest[key]:
            raise ManifestError(f"Manifest field '{key}' must be a non-empty object")

    declared_states = set(manifest["states"])
    missing_states = REQUIRED_STATES - declared_states
    if missing_states:
        raise ManifestError(
            "Manifest does not define required maturity states: "
            + ", ".join(sorted(missing_states))
        )

    return manifest


def _safe_relative_path(value: Any, context: str) -> Path:
    if not isinstance(value, str) or not value:
        raise ManifestError(f"{context} must be a non-empty relative path")
    pure = PurePosixPath(value)
    if pure.is_absolute() or ".." in pure.parts:
        raise ManifestError(f"{context} must stay within docs/: {value!r}")
    return Path(*pure.parts)


def _parse_declaration(value: Any, context: str) -> MaturityDeclaration:
    if isinstance(value, str):
        declaration = MaturityDeclaration(state=value)
    elif isinstance(value, dict):
        declaration = MaturityDeclaration(
            state=value.get("state"),
            reviewer=value.get("reviewer"),
            evidence=value.get("evidence"),
        )
    else:
        raise ManifestError(f"{context} must be a state string or object")

    if declaration.state not in REQUIRED_STATES:
        raise ManifestError(f"{context} has unknown state {declaration.state!r}")

    if declaration.state in REVIEW_EVIDENCE_STATES:
        if (
            not isinstance(declaration.reviewer, str)
            or not declaration.reviewer.strip()
            or not isinstance(declaration.evidence, str)
            or not declaration.evidence.strip()
        ):
            raise ManifestError(
                f"{context} declares '{declaration.state}' without reviewer and evidence"
            )

    return declaration


def _declaration_for(
    maturity: dict[str, Any],
    locale: str,
    filename: str,
    surface: str,
) -> MaturityDeclaration:
    locale_config = maturity.get(locale)
    if not isinstance(locale_config, dict):
        raise ManifestError(
            f"Surface '{surface}' has no maturity declaration for locale '{locale}'"
        )
    overrides = locale_config.get("overrides", {})
    if not isinstance(overrides, dict):
        raise ManifestError(
            f"Surface '{surface}' locale '{locale}' overrides must be an object"
        )
    value = overrides.get(filename, locale_config.get("default"))
    if value is None:
        raise ManifestError(
            f"Surface '{surface}' locale '{locale}' has no state for '{filename}'"
        )
    return _parse_declaration(
        value,
        f"Surface '{surface}' locale '{locale}' file '{filename}'",
    )


def _required_files(
    manifest: dict[str, Any],
    locale: str,
    surface: str,
    files: list[str],
) -> set[str]:
    locale_config = manifest["locales"][locale]
    tier_name = locale_config.get("tier")
    tier = manifest["tiers"].get(tier_name)
    if not isinstance(tier, dict):
        raise ManifestError(f"Locale '{locale}' references unknown tier {tier_name!r}")
    requirements = tier.get("required")
    if not isinstance(requirements, dict):
        raise ManifestError(f"Tier '{tier_name}' must define a 'required' object")
    requirement = requirements.get(surface, [])
    if requirement == "all":
        return set(files)
    if not isinstance(requirement, list) or not all(
        isinstance(filename, str) for filename in requirement
    ):
        raise ManifestError(
            f"Tier '{tier_name}' requirement for '{surface}' must be 'all' or a list"
        )
    unknown = set(requirement) - set(files)
    if unknown:
        raise ManifestError(
            f"Tier '{tier_name}' requires unknown {surface} files: "
            + ", ".join(sorted(unknown))
        )
    return set(requirement)


def _contains_explicit_stub_marker(text: str) -> bool:
    return any(pattern.search(text) for pattern in EXPLICIT_STUB_PATTERNS)


def _validate_locale_metadata(manifest: dict[str, Any]) -> None:
    for locale, config in manifest["locales"].items():
        if not BCP47_PATTERN.fullmatch(locale):
            raise ManifestError(f"Locale key is not a supported BCP-47 tag: {locale!r}")
        if not isinstance(config, dict):
            raise ManifestError(f"Locale '{locale}' metadata must be an object")
        _safe_relative_path(config.get("path"), f"Locale '{locale}' path")
        if config.get("direction") not in {"ltr", "rtl"}:
            raise ManifestError(f"Locale '{locale}' direction must be 'ltr' or 'rtl'")
        if config.get("tier") not in manifest["tiers"]:
            raise ManifestError(
                f"Locale '{locale}' references unknown tier {config.get('tier')!r}"
            )


def audit_repository(
    repo_root: Path,
    *,
    docs_dir: Path | None = None,
    manifest_path: Path | None = None,
    surfaces: Iterable[str] | None = None,
) -> AuditResult:
    """Audit declared maturity against files on disk.

    A green result certifies only that:

    * the manifest is internally valid;
    * required files for each declared tier exist;
    * missing/stub/candidate/review states match observable facts; and
    * byte-identical source copies are never presented as translations.
    """

    repo_root = repo_root.resolve()
    docs_dir = (docs_dir or repo_root / "docs").resolve()
    manifest_path = (
        manifest_path or docs_dir / "i18n" / "maturity.v1.json"
    ).resolve()
    manifest = load_manifest(manifest_path)
    _validate_locale_metadata(manifest)

    selected = set(surfaces) if surfaces is not None else set(manifest["surfaces"])
    unknown_surfaces = selected - set(manifest["surfaces"])
    if unknown_surfaces:
        raise ManifestError(
            "Unknown manifest surfaces requested: " + ", ".join(sorted(unknown_surfaces))
        )

    observations: list[FileObservation] = []
    errors: list[str] = []
    warnings: list[str] = []

    for surface_name, surface in manifest["surfaces"].items():
        if surface_name not in selected:
            continue
        if not isinstance(surface, dict):
            raise ManifestError(f"Surface '{surface_name}' must be an object")

        source_locale = surface.get("source_locale")
        if source_locale not in manifest["locales"]:
            raise ManifestError(
                f"Surface '{surface_name}' has unknown source locale {source_locale!r}"
            )
        subdir = _safe_relative_path(
            surface.get("subdir"), f"Surface '{surface_name}' subdir"
        )
        files = surface.get("files")
        if not isinstance(files, list) or not files or not all(
            isinstance(filename, str) for filename in files
        ):
            raise ManifestError(
                f"Surface '{surface_name}' files must be a non-empty string list"
            )
        if len(files) != len(set(files)):
            raise ManifestError(f"Surface '{surface_name}' contains duplicate files")
        inventory = surface.get("inventory")
        if inventory not in {"complete", "selected"}:
            raise ManifestError(
                f"Surface '{surface_name}' inventory must be 'complete' or 'selected'"
            )
        for filename in files:
            _safe_relative_path(filename, f"Surface '{surface_name}' filename")

        maturity = surface.get("maturity")
        if not isinstance(maturity, dict):
            raise ManifestError(f"Surface '{surface_name}' maturity must be an object")

        source_config = manifest["locales"][source_locale]
        source_base = docs_dir / _safe_relative_path(
            source_config.get("path"), f"Locale '{source_locale}' path"
        ) / subdir
        declared_source_files = set(files)
        if inventory == "complete" and source_base.is_dir():
            actual_source_files = {
                str(path.relative_to(source_base).as_posix())
                for path in source_base.glob("*.md")
            }
            untracked = actual_source_files - declared_source_files
            if untracked:
                errors.append(
                    f"{surface_name}: source files absent from manifest: "
                    + ", ".join(sorted(untracked))
                )

        for locale, locale_config in manifest["locales"].items():
            locale_path = _safe_relative_path(
                locale_config.get("path"), f"Locale '{locale}' path"
            )
            target_base = docs_dir / locale_path / subdir
            required = _required_files(manifest, locale, surface_name, files)

            locale_maturity = maturity.get(locale)
            if not isinstance(locale_maturity, dict):
                raise ManifestError(
                    f"Surface '{surface_name}' has no maturity object for '{locale}'"
                )
            overrides = locale_maturity.get("overrides", {})
            if not isinstance(overrides, dict):
                raise ManifestError(
                    f"Surface '{surface_name}' locale '{locale}' overrides "
                    "must be an object"
                )
            unknown_overrides = set(overrides) - set(files)
            if unknown_overrides:
                raise ManifestError(
                    f"Surface '{surface_name}' locale '{locale}' overrides unknown files: "
                    + ", ".join(sorted(unknown_overrides))
                )

            for filename in files:
                declaration = _declaration_for(
                    maturity, locale, filename, surface_name
                )
                source_path = source_base / filename
                target_path = target_base / filename
                exists = target_path.is_file()
                source_exists = source_path.is_file()
                identical = (
                    locale != source_locale
                    and exists
                    and source_exists
                    and target_path.read_bytes() == source_path.read_bytes()
                )
                is_required = filename in required

                observations.append(
                    FileObservation(
                        locale=locale,
                        direction=locale_config["direction"],
                        tier=locale_config["tier"],
                        surface=surface_name,
                        filename=filename,
                        path=target_path,
                        state=declaration.state,
                        required=is_required,
                        exists=exists,
                        identical_to_source=identical,
                    )
                )

                label = f"{locale}/{surface_name}/{filename}"
                if not source_exists:
                    errors.append(f"{label}: source file is missing: {source_path}")
                    continue
                if is_required and declaration.state == "missing":
                    errors.append(
                        f"{label}: tier '{locale_config['tier']}' requires this file, "
                        "but it is declared missing"
                    )
                if declaration.state == "missing":
                    if exists:
                        errors.append(
                            f"{label}: declared missing but file exists at {target_path}"
                        )
                    continue
                if (
                    declaration.state == "parity"
                    and locale != source_locale
                    and (
                        not isinstance(declaration.reviewer, str)
                        or not declaration.reviewer.strip()
                        or not isinstance(declaration.evidence, str)
                        or not declaration.evidence.strip()
                    )
                ):
                    errors.append(
                        f"{label}: translated parity requires reviewer and evidence"
                    )
                if (
                    declaration.state == "canonical"
                    and locale != manifest["policy"].get("canonical_v1")
                ):
                    errors.append(
                        f"{label}: canonical state conflicts with canonical_v1="
                        f"{manifest['policy'].get('canonical_v1')!r}"
                    )
                if not exists:
                    errors.append(
                        f"{label}: declared '{declaration.state}' but file is missing"
                    )
                    continue
                if identical and declaration.state != "stub":
                    errors.append(
                        f"{label}: byte-identical to the {source_locale} source; "
                        "declare it as 'stub' instead of "
                        f"'{declaration.state}'"
                    )
                if locale != source_locale:
                    text = target_path.read_text(encoding="utf-8")
                    if (
                        _contains_explicit_stub_marker(text)
                        and declaration.state != "stub"
                    ):
                        errors.append(
                            f"{label}: contains an explicit translation-pending/stub "
                            f"marker but is declared '{declaration.state}'"
                        )

            if inventory == "complete" and target_base.is_dir():
                actual_target_files = {
                    str(path.relative_to(target_base).as_posix())
                    for path in target_base.glob("*.md")
                }
                extra = actual_target_files - set(files)
                if extra:
                    warnings.append(
                        f"{locale}/{surface_name}: files outside the manifest: "
                        + ", ".join(sorted(extra))
                    )

    return AuditResult(
        manifest=manifest,
        observations=observations,
        errors=errors,
        warnings=warnings,
    )


def state_counts(
    observations: Iterable[FileObservation],
) -> dict[str, dict[str, int]]:
    """Count declared states by locale."""

    counts: dict[str, dict[str, int]] = {}
    for observation in observations:
        locale_counts = counts.setdefault(observation.locale, {})
        locale_counts[observation.state] = locale_counts.get(observation.state, 0) + 1
    return counts
