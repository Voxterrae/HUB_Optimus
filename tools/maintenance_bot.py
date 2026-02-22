from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

LANGS = ["es", "de", "ca", "fr", "ru", "he", "zh"]
GOV_FILES = [
    "CHARTER.md",
    "KERNEL.md",
    "TRUST_LAYER.md",
    "LEGITIMACY_MODEL.md",
    "SCENARIO_SCHEMA.md",
    "EVALUATION_STANDARD.md",
    "CONSENSUS_PROCESS.md",
    "TRADEMARKS.md",
    "CUSTODIANSHIP.md",
    "CHANGE_REQUEST.md",
]

def write(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")

def ensure_docs_readme():
    p = REPO / "docs" / "README.md"
    if not p.exists():
        write(p, """# docs/

Start here:
- [00_start_here.md](00_start_here.md)
- [02_how_to_read_this_repo.md](02_how_to_read_this_repo.md)
- [03_try_a_scenario.md](03_try_a_scenario.md)
""")

def ensure_docs_v1_core_mirror():
    p = REPO / "docs" / "v1_core" / "workflow" / "README.md"
    if not p.exists():
        write(p, """# Workflow (mirror)

Canonical source:
- [../../../v1_core/workflow/README.md](../../../v1_core/workflow/README.md)
""")

def ensure_governance_mirrors():
    gov = REPO / "docs" / "governance"
    if not gov.exists():
        return
    for lang in LANGS:
        base = REPO / "docs" / lang / "governance"
        for f in GOV_FILES:
            canonical = gov / f
            if canonical.exists():
                target = base / f
                if not target.exists():
                    write(target, f"""# {f.replace('.md','')}

> Canonical source: ../../governance/{f}

Temporary mirror file to satisfy structure and link integrity.
Translation pending.
""")

def main():
    ensure_docs_readme()
    ensure_docs_v1_core_mirror()
    ensure_governance_mirrors()
    print("maintenance_bot OK")

if __name__ == "__main__":
    main()

