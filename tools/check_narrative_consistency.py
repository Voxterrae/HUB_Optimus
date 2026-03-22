from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any


REQUIRED_STRING_FIELDS = (
    "claim_id", "claim_text", "source_shown", "source_type", "approx_date",
    "risk_domain", "verification_status", "evidence_tier", "jurisdiction", "notes",
)

SOURCE_EVIDENCE_RULES: dict[str, set[str]] = {
    "unknown": {"unknown", "advocacy"},
    "advocacy": {"advocacy", "unknown"},
    "reputable_press": {"reputable_press", "official_secondary"},
    "tech_press": {"reputable_press", "official_secondary"},
    "official": {"official_secondary"},
    "primary": {"primary"},
}

DOMAIN_KEYWORDS: dict[str, tuple[str, ...]] = {
    "privacy": ("privacy", "consent", "identity", "data selling", "scrapes your data"),
    "biometrics": ("biometric", "biometrics", "selfie", "face", "facial", "persona"),
    "surveillance": ("surveillance", "watchlist", "fincen", "tracking", "track", "airport", "911", "migrant"),
    "browser_security": ("chrome", "browser", "extension", "gemini", "cve-", "webcam", "microphone", "screenshots", "local files"),
    "copyright": ("copyright", "books", "films", "movies", "marvel", "star wars", "disney", "mediaset", "seedance", "intellectual property"),
    "defense": ("department of defense", "dod", "pentagon", "weapons", "military", "nuclear", "autonomous weapons"),
    "labor": ("lay off", "laid off", "entry-level", "workers", "manual coding", "labor", "jobs"),
    "environment": ("co2", "water", "emissions", "e-waste", "planet", "climate"),
    "hardware": ("dram", "ram", "laptop", "laptops", "smartphone", "smartphones", "console", "consoles", "pc"),
    "local_vs_cloud": ("local ai", "cloud ai", "no cloud", "on your device", "no internet"),
}

SEVERITY_ORDER = {"error": 0, "warning": 1, "info": 2}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check internal consistency of the narrative-risk seed corpus.")
    parser.add_argument("--input", required=True, help="Path to seed_claims.json")
    parser.add_argument("--taxonomy", required=True, help="Path to taxonomy.json")
    parser.add_argument("--report", required=True, help="Path to JSON report output")
    parser.add_argument("--summary-file", help="Optional Markdown summary output for GITHUB_STEP_SUMMARY")
    return parser.parse_args()


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _is_non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _claim_ref(record: dict[str, Any], index: int) -> str:
    claim_id = record.get("claim_id")
    return str(claim_id) if _is_non_empty_string(claim_id) else f"<row-{index + 1}>"


def _issue(claim_id: str, issue_type: str, severity: str, message: str) -> dict[str, str]:
    return {"claim_id": claim_id, "type": issue_type, "severity": severity, "message": message}


def _matched_domains(text: str) -> set[str]:
    lowered = text.lower()
    return {
        domain
        for domain, keywords in DOMAIN_KEYWORDS.items()
        if any(keyword in lowered for keyword in keywords)
    }


def build_report(records: Any, taxonomy: Any) -> dict[str, Any]:
    issues: list[dict[str, str]] = []
    if not isinstance(taxonomy, dict) or not isinstance(taxonomy.get("risk_domains"), list):
        return _finalize_report(0, [_issue("<dataset>", "invalid_taxonomy", "error", "taxonomy.json must contain a risk_domains list")])
    if not isinstance(records, list):
        return _finalize_report(0, [_issue("<dataset>", "invalid_dataset", "error", "input dataset must be a JSON array of claim records")])

    valid_domains = {str(domain) for domain in taxonomy["risk_domains"]}
    duplicates: dict[str, list[str]] = defaultdict(list)

    for index, record in enumerate(records):
        if not isinstance(record, dict):
            issues.append(_issue(f"<row-{index + 1}>", "invalid_record", "error", "claim record must be a JSON object"))
            continue

        claim_id = _claim_ref(record, index)
        for field in REQUIRED_STRING_FIELDS:
            if not _is_non_empty_string(record.get(field)):
                issues.append(_issue(claim_id, "missing_required_field", "error", f"{field} must be present and non-empty"))

        claim_text = record.get("claim_text")
        if _is_non_empty_string(claim_text):
            duplicates[hashlib.sha256(claim_text.encode("utf-8")).hexdigest()].append(claim_id)

        risk_domain = record.get("risk_domain")
        if _is_non_empty_string(risk_domain) and risk_domain not in valid_domains:
            issues.append(_issue(claim_id, "invalid_risk_domain", "error", f"risk_domain '{risk_domain}' is not defined in taxonomy.json"))

        source_type = record.get("source_type")
        evidence_tier = record.get("evidence_tier")
        allowed_evidence = SOURCE_EVIDENCE_RULES.get(str(source_type))
        if _is_non_empty_string(source_type) and _is_non_empty_string(evidence_tier) and allowed_evidence and evidence_tier not in allowed_evidence:
            allowed_text = ", ".join(sorted(allowed_evidence))
            issues.append(_issue(claim_id, "source_evidence_mismatch", "warning", f"source_type '{source_type}' should use evidence_tier in {{{allowed_text}}}, got '{evidence_tier}'"))

        if record.get("verification_status") == "verified" and evidence_tier in {"unknown", "advocacy"}:
            issues.append(_issue(claim_id, "invalid_promotion", "warning", "verification_status cannot be 'verified' with unknown or advocacy evidence_tier"))

        if _is_non_empty_string(claim_text) and _is_non_empty_string(risk_domain):
            matched_domains = _matched_domains(claim_text)
            if matched_domains and risk_domain not in matched_domains:
                expected = ", ".join(sorted(matched_domains))
                issues.append(_issue(claim_id, "domain_heuristic_mismatch", "info", f"claim_text keywords suggest {{{expected}}}, got '{risk_domain}'"))

    for claim_ids in duplicates.values():
        if len(claim_ids) > 1:
            issues.append(_issue(", ".join(claim_ids), "duplicate_claim_text", "info", "claim_text hash is repeated across multiple records"))

    return _finalize_report(len(records), issues)


def _finalize_report(total_claims: int, issues: list[dict[str, str]]) -> dict[str, Any]:
    ordered = sorted(issues, key=lambda item: (SEVERITY_ORDER[item["severity"]], item["claim_id"], item["type"]))
    summary = {"errors": 0, "warnings": 0, "info": 0}
    for issue in ordered:
        if issue["severity"] == "error":
            summary["errors"] += 1
        elif issue["severity"] == "warning":
            summary["warnings"] += 1
        else:
            summary["info"] += 1
    return {"total_claims": total_claims, "issues": ordered, "summary": summary}


def render_summary(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "## Narrative Consistency",
        "",
        f"- Claims: {report['total_claims']}",
        f"- Errors: {summary['errors']}",
        f"- Warnings: {summary['warnings']}",
        f"- Info: {summary['info']}",
        "",
    ]
    if not report["issues"]:
        lines.append("No issues found.")
        return "\n".join(lines) + "\n"

    lines.extend(["| Claim | Severity | Type | Message |", "| --- | --- | --- | --- |"])
    for issue in report["issues"]:
        message = issue["message"].replace("|", "\\|")
        lines.append(f"| {issue['claim_id']} | {issue['severity']} | {issue['type']} | {message} |")
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    try:
        records = _load_json(Path(args.input))
        taxonomy = _load_json(Path(args.taxonomy))
    except FileNotFoundError as exc:
        print(f"Missing file: {exc.filename}", file=sys.stderr)
        return 1
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON: {exc}", file=sys.stderr)
        return 1

    report = build_report(records, taxonomy)
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    if args.summary_file:
        summary_path = Path(args.summary_file)
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        with summary_path.open("a", encoding="utf-8") as handle:
            handle.write(render_summary(report))

    print(
        "Narrative consistency:",
        f"errors={report['summary']['errors']}",
        f"warnings={report['summary']['warnings']}",
        f"info={report['summary']['info']}",
    )
    return 1 if report["summary"]["errors"] > 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
