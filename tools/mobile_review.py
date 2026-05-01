from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from collections import Counter
from dataclasses import dataclass
from pathlib import Path


DEFAULT_INPUT_PATH = Path(__file__).resolve().parent.parent / "mobile_ingest.jsonl"
ERROR_PREFIX = "[mobile_review:error]"
SHORT_CLAIM_THRESHOLD = 10

WORD_RE = re.compile(r"[^\W_]+(?:['-][^\W_]+)?", re.UNICODE)

VAGUE_MARKERS = {
    ".",
    "..",
    "...",
    "\u2026",
    "lo que detectes",
    "lo que veas interesante",
    "claim que quieras guardar",
}

SHORT_MEANINGFUL_TERMS = {
    "eeuu",
    "gaza",
    "iran",
    "israel",
    "trump",
    "tiktok",
}

STOPWORDS = {
    "a",
    "al",
    "algo",
    "an",
    "and",
    "ante",
    "are",
    "as",
    "at",
    "be",
    "by",
    "con",
    "como",
    "cu\u00e1l",
    "cual",
    "de",
    "del",
    "desde",
    "donde",
    "el",
    "ella",
    "en",
    "es",
    "esa",
    "ese",
    "eso",
    "esta",
    "este",
    "esto",
    "for",
    "from",
    "hay",
    "in",
    "is",
    "la",
    "las",
    "le",
    "lo",
    "los",
    "m\u00e1s",
    "mas",
    "mi",
    "mis",
    "no",
    "of",
    "on",
    "or",
    "para",
    "pero",
    "por",
    "que",
    "qu\u00e9",
    "se",
    "si",
    "sin",
    "sobre",
    "su",
    "sus",
    "te",
    "that",
    "the",
    "this",
    "to",
    "tu",
    "un",
    "una",
    "uno",
    "with",
    "y",
    "ya",
}

TOPIC_PATTERNS = {
    "espa\u00f1a": (r"\bespana\b", r"\bspain\b"),
    "ia / deepfake": (
        r"\bai\b",
        r"\bia\b",
        r"\bdeepfake\b",
        r"\bdeepfakes\b",
        r"\bartificial intelligence\b",
        r"\binteligencia artificial\b",
    ),
    "iran": (r"\biran\b", r"\biranian\b"),
    "israel": (r"\bisrael\b", r"\bisraeli\b"),
    "netanyahu": (r"\bnetanyahu\b",),
    "tel aviv": (r"\btel aviv\b",),
    "tiktok": (r"\btiktok\b",),
    "trump": (r"\btrump\b",),
    "x": (
        r"\bpost viral en x\b",
        r"\bpost en x\b",
        r"\bx\.com\b",
        r"\btwitter\b",
    ),
}

TOPIC_REGEXES = {
    topic: tuple(re.compile(pattern) for pattern in patterns)
    for topic, patterns in TOPIC_PATTERNS.items()
}


class MobileReviewError(Exception):
    """Raised for deterministic user-facing review errors."""


class MobileReviewArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        self.exit(2, f"{ERROR_PREFIX} {message}\n")


@dataclass(frozen=True)
class ClaimRecord:
    line_number: int
    claim: str
    timestamp: str
    source: str
    status: str


def _positive_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("expected a positive integer") from exc
    if parsed <= 0:
        raise argparse.ArgumentTypeError("expected a positive integer")
    return parsed


def build_parser() -> MobileReviewArgumentParser:
    parser = MobileReviewArgumentParser(
        description="Review raw mobile claims stored in mobile_ingest.jsonl."
    )
    parser.add_argument(
        "--input",
        default=str(DEFAULT_INPUT_PATH),
        help="Path to the mobile_ingest.jsonl dataset.",
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Show total claims and dataset time range.",
    )
    parser.add_argument(
        "--latest",
        type=_positive_int,
        metavar="N",
        help="Show the latest N claims in readable form.",
    )
    parser.add_argument(
        "--duplicates",
        action="store_true",
        help="Show exact duplicate claim texts with counts.",
    )
    parser.add_argument(
        "--flag-vague",
        action="store_true",
        help="Show vague or underspecified claims.",
    )
    parser.add_argument(
        "--keywords",
        action="store_true",
        help="Show keyword frequency over claim text.",
    )
    parser.add_argument(
        "--topics",
        action="store_true",
        help="Show simple topic-family counts.",
    )
    return parser


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = build_parser()
    return parser.parse_args(argv)


def _has_selected_action(args: argparse.Namespace) -> bool:
    return any(
        (
            args.summary,
            args.latest is not None,
            args.duplicates,
            args.flag_vague,
            args.keywords,
            args.topics,
        )
    )


def _coerce_text(value: object) -> str:
    if isinstance(value, str):
        return value.strip()
    if value is None:
        return ""
    return str(value).strip()


def load_records(path: Path) -> list[ClaimRecord]:
    if not path.exists() or not path.is_file():
        raise MobileReviewError(f"input file not found: {path}")

    records: list[ClaimRecord] = []
    try:
        with path.open("r", encoding="utf-8") as handle:
            for line_number, raw_line in enumerate(handle, start=1):
                if not raw_line.strip():
                    continue
                try:
                    payload = json.loads(raw_line)
                except json.JSONDecodeError as exc:
                    raise MobileReviewError(
                        f"invalid JSON on line {line_number}: {exc.msg}"
                    ) from exc
                if not isinstance(payload, dict):
                    raise MobileReviewError(
                        f"line {line_number} must contain a JSON object"
                    )
                records.append(
                    ClaimRecord(
                        line_number=line_number,
                        claim=_coerce_text(payload.get("claim")),
                        timestamp=_coerce_text(payload.get("timestamp")),
                        source=_coerce_text(payload.get("source")),
                        status=_coerce_text(payload.get("status")),
                    )
                )
    except OSError as exc:
        raise MobileReviewError(str(exc)) from exc

    return records


def summarize_records(records: list[ClaimRecord]) -> list[str]:
    first_timestamp = records[0].timestamp if records else "-"
    last_timestamp = records[-1].timestamp if records else "-"
    return [
        "Summary",
        f"- Total claims: {len(records)}",
        f"- First timestamp: {first_timestamp or '-'}",
        f"- Last timestamp: {last_timestamp or '-'}",
    ]


def select_latest_records(records: list[ClaimRecord], limit: int) -> list[ClaimRecord]:
    return list(reversed(records[-limit:]))


def format_latest_records(records: list[ClaimRecord], limit: int) -> list[str]:
    selected = select_latest_records(records, limit)
    lines = [f"Latest {limit} Claims"]
    if not selected:
        lines.append("(no claims found)")
        return lines

    for index, record in enumerate(selected, start=1):
        metadata = " | ".join(
            part
            for part in (
                f"line {record.line_number}",
                record.timestamp or "-",
                record.source or "-",
                record.status or "-",
            )
        )
        lines.append(f"{index}. {metadata}")
        lines.append(f"   {record.claim or '(empty claim)'}")
    return lines


def find_duplicate_claims(records: list[ClaimRecord]) -> list[tuple[str, int]]:
    counts = Counter(record.claim for record in records)
    duplicates = [
        (claim, count)
        for claim, count in counts.items()
        if count > 1
    ]
    return sorted(duplicates, key=lambda item: (-item[1], item[0].casefold(), item[0]))


def format_duplicate_claims(records: list[ClaimRecord]) -> list[str]:
    duplicates = find_duplicate_claims(records)
    lines = ["Duplicate Claims"]
    if not duplicates:
        lines.append("(no exact duplicates found)")
        return lines
    for claim, count in duplicates:
        lines.append(f"- {count}x | {claim or '(empty claim)'}")
    return lines


def _normalize_text(text: str) -> str:
    return " ".join(text.casefold().split())


def _fold_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text.casefold())
    return "".join(char for char in normalized if not unicodedata.combining(char))


def _looks_meaningful_short_claim(normalized_text: str) -> bool:
    tokens = WORD_RE.findall(normalized_text)
    if not tokens:
        return False
    if any(token.isdigit() for token in tokens):
        return True
    if len(tokens) >= 2:
        return True
    return tokens[0] in SHORT_MEANINGFUL_TERMS


def classify_vague_claim(record: ClaimRecord) -> str | None:
    normalized = _normalize_text(record.claim)
    if not normalized:
        return "empty claim"
    if normalized in VAGUE_MARKERS:
        return "generic marker"
    if not re.search(r"\w", normalized, re.UNICODE):
        return "punctuation only"

    compact = normalized.replace(" ", "")
    if len(compact) < SHORT_CLAIM_THRESHOLD and not _looks_meaningful_short_claim(normalized):
        return f"short claim (<{SHORT_CLAIM_THRESHOLD} chars)"
    return None


def find_vague_claims(records: list[ClaimRecord]) -> list[tuple[ClaimRecord, str]]:
    flagged: list[tuple[ClaimRecord, str]] = []
    for record in records:
        reason = classify_vague_claim(record)
        if reason:
            flagged.append((record, reason))
    return flagged


def format_vague_claims(records: list[ClaimRecord]) -> list[str]:
    flagged = find_vague_claims(records)
    lines = ["Vague Claims"]
    if not flagged:
        lines.append("(no vague claims found)")
        return lines
    for record, reason in flagged:
        lines.append(
            f"- line {record.line_number} | {reason} | {record.claim or '(empty claim)'}"
        )
    return lines


def tokenize_claim_text(text: str) -> list[str]:
    tokens = WORD_RE.findall(_fold_text(text))
    kept: list[str] = []
    for token in tokens:
        if token.isdigit():
            continue
        if len(token) == 1 and token != "x":
            continue
        if token in STOPWORDS:
            continue
        kept.append(token)
    return kept


def count_keywords(records: list[ClaimRecord]) -> list[tuple[str, int]]:
    counts: Counter[str] = Counter()
    for record in records:
        counts.update(tokenize_claim_text(record.claim))
    return sorted(counts.items(), key=lambda item: (-item[1], item[0]))


def format_keywords(records: list[ClaimRecord]) -> list[str]:
    keywords = count_keywords(records)
    lines = ["Keyword Frequency"]
    if not keywords:
        lines.append("(no keywords found)")
        return lines
    for keyword, count in keywords:
        lines.append(f"- {keyword}: {count}")
    return lines


def count_topic_families(records: list[ClaimRecord]) -> list[tuple[str, int]]:
    counts = {topic: 0 for topic in TOPIC_PATTERNS}
    for record in records:
        folded = _fold_text(record.claim)
        for topic, regexes in TOPIC_REGEXES.items():
            if any(regex.search(folded) for regex in regexes):
                counts[topic] += 1
    return sorted(counts.items(), key=lambda item: (-item[1], item[0]))


def format_topic_families(records: list[ClaimRecord]) -> list[str]:
    topics = count_topic_families(records)
    lines = ["Topic Families"]
    for topic, count in topics:
        lines.append(f"- {topic}: {count}")
    return lines


def _print_sections(sections: list[list[str]]) -> None:
    for index, lines in enumerate(sections):
        if index:
            print()
        for line in lines:
            print(line)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not _has_selected_action(args):
        parser.print_help()
        return 0

    try:
        records = load_records(Path(args.input))
    except MobileReviewError as exc:
        print(f"{ERROR_PREFIX} {exc}", file=sys.stderr)
        return 1

    sections: list[list[str]] = []
    if args.summary:
        sections.append(summarize_records(records))
    if args.latest is not None:
        sections.append(format_latest_records(records, args.latest))
    if args.duplicates:
        sections.append(format_duplicate_claims(records))
    if args.flag_vague:
        sections.append(format_vague_claims(records))
    if args.keywords:
        sections.append(format_keywords(records))
    if args.topics:
        sections.append(format_topic_families(records))

    _print_sections(sections)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
