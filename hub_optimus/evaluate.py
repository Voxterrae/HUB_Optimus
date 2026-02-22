from pathlib import Path

from .parser_md import read_text, extract_sections, extract_bullets
from .schema import validate_sections, normalize_sections, CRITICAL_KEYS
from .trust_layer import classify_claim_typed, evidence_required


def evaluate_scenario(path: Path) -> tuple[str, dict]:
    md = read_text(path)

    sections = normalize_sections(extract_sections(md))

    errors = validate_sections(sections)
    critical_missing = [k for k in CRITICAL_KEYS if k not in sections]

    if "verification" not in sections:
        trigger = sections.get("trigger", "")
        # If trigger text explicitly states no verification, treat as an evidence-gap claim.
        if "without" in trigger.lower() and "verification" in trigger.lower():
            claims = [
                "Ceasefire announced without independent verification mechanism (evidence gap)."
            ]
        else:
            claims = []
    else:
        verification = sections.get("verification", "")
        claims = extract_bullets(verification)

    classified = []
    for claim in claims:
        level, claim_type = classify_claim_typed(claim)
        classified.append(
            {
                "claim": claim,
                "level": level,
                "claim_type": claim_type,
                "evidence_required": evidence_required(level, claim_type),
            }
        )

    counts = {"A": 0, "B": 0, "C": 0}
    claim_type_counts = {
        "verification_mechanism": 0,
        "third_party_audit": 0,
        "metrics_reporting": 0,
        "declarative_only": 0,
    }
    for item in classified:
        counts[item["level"]] = counts.get(item["level"], 0) + 1
        claim_type_counts[item["claim_type"]] = claim_type_counts.get(item["claim_type"], 0) + 1

    total = sum(counts.values()) or 1
    dist = {k: round(v * 100.0 / total, 1) for k, v in counts.items()}

    total_types = sum(claim_type_counts.values()) or 1
    type_dist = {k: round(v * 100.0 / total_types, 1) for k, v in claim_type_counts.items()}

    flags = []
    if errors:
        flags.append("Schema incomplete")

    for key in critical_missing:
        flags.append(f"CRITICAL missing section: '{key}' (trustability degraded)")

    lines = []
    lines.append(f"# Scenario Evaluation Report: {path.name}")
    lines.append("")
    lines.append("## Schema validation")
    if errors:
        for err in errors:
            lines.append(f"- ❌ {err}")
    else:
        lines.append("- ✅ All required sections present")
    lines.append("")

    lines.append("## Trust Layer scan")
    if classified:
        for item in classified:
            lines.append(f"- [{item['level']}] ({item['claim_type']}) {item['claim']}")
    else:
        lines.append("- (none detected)")
    lines.append("")

    lines.append("## Trust distribution")
    lines.append(f"- A: {counts['A']} ({dist['A']}%)")
    lines.append(f"- B: {counts['B']} ({dist['B']}%)")
    lines.append(f"- C: {counts['C']} ({dist['C']}%)")
    lines.append(f"- verification_mechanism: {claim_type_counts['verification_mechanism']} ({type_dist['verification_mechanism']}%)")
    lines.append(f"- third_party_audit: {claim_type_counts['third_party_audit']} ({type_dist['third_party_audit']}%)")
    lines.append(f"- metrics_reporting: {claim_type_counts['metrics_reporting']} ({type_dist['metrics_reporting']}%)")
    lines.append(f"- declarative_only: {claim_type_counts['declarative_only']} ({type_dist['declarative_only']}%)")
    lines.append("")

    lines.append("## Evidence required")
    if classified:
        for item in classified:
            lines.append(f"- [{item['level']}] ({item['claim_type']}) {item['claim']}")
            for ev in item["evidence_required"]:
                lines.append(f"  - {ev}")
    else:
        lines.append("- (none)")
    lines.append("")

    lines.append("## Integrity flags")
    if flags:
        for flag in flags:
            lines.append(f"- ⚠️ {flag}")
    else:
        lines.append("- ✅ No flags")
    lines.append("")

    lines.append("## Classification (v0)")
    if any(item["level"] == "A" for item in classified):
        lines.append("- Likely higher structural robustness (A-class verifiability present).")
    elif any(item["level"] == "B" for item in classified):
        lines.append("- Medium robustness (measurable but weak independence).")
    else:
        lines.append("- High risk of false success (mostly C-class declarative commitments).")

    payload = {
        "scenario": path.name,
        "schema": {
            "missing": errors,
            "critical_missing": critical_missing,
        },
        "trust_layer": {
            "counts": counts,
            "distribution_pct": dist,
            "claim_type_counts": claim_type_counts,
            "claim_type_distribution_pct": type_dist,
            "claims": classified,
        },
        "flags": flags,
        "claims": classified,
    }

    return "\n".join(lines), payload
