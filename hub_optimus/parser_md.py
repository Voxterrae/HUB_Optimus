import re
from pathlib import Path

HEADER_RE = re.compile(r"^(#{1,6})\s+(.*)$", re.M)

def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")

def extract_sections(md: str) -> dict:
    matches = list(HEADER_RE.finditer(md))
    if not matches:
        return {"_full": md}

    sections = {}
    for i, m in enumerate(matches):
        title = m.group(2).strip()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(md)
        body = md[start:end].strip()
        sections[title.lower()] = body
    return sections

def extract_bullets(text: str) -> list[str]:
    out = []
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("- "):
            out.append(line[2:].strip())
        elif line.startswith(" "):
            out.append(line[2:].strip())
    return out
