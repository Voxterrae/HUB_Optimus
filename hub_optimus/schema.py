import re

# Claves canónicas que el motor espera
REQUIRED_KEYS = [
    "context",
    "incentives",
    "systemic_impact",
    "classification",
]
OPTIONAL_KEYS = ["trigger"]

# Mapeo: clave canónica → posibles títulos reales en escenarios
ALIASES = {
    "context": {
        "context",
        "contexto",
        "structural context",
        "background",
        "situation",
    },
    "trigger": {"trigger"},
    "incentives": {
        "incentives",
        "incentivos",
        "incentive analysis (layer 2)",
        "incentive analysis",
        "drivers",
        "motivation",
    },
    "verification": {
        "verification",
        "verification & monitoring",
        "monitoring",
        "enforcement",
        "compliance",
        "verification mechanism",
        "verificación",
        "verificacion",
    },
    "systemic_impact": {
        "systemic impact",
        "systemic impacts",
        "systemic evaluation (layer 3)",
        "systemic evaluation",
        "impacto sistemico",
        "impacto sistémico",
        "second-order effects",
        "2nd order effects",
    },
    "classification": {
        "classification",
        "final classification",
        "resultado",
        "assessment",
        "verdict",
        "clasificación",
        "clasificacion",
    },
}


def _norm(s: str) -> str:
    s = s.strip().lower()
    s = s.replace("—", "-").replace("–", "-")
    s = re.sub(r"[\t\r\n]+", " ", s)
    s = re.sub(r"\s+", " ", s)
    s = s.replace(":", "")

    # Quitar prefijos tipo "2) "
    s = re.sub(r"^\d+\)\s*", "", s)

    # Quitar prefijos tipo "2. " o "2 - "
    s = re.sub(r"^\d+[\.\-]\s*", "", s)

    return s.strip()


def normalize_sections(raw_sections: dict) -> dict:
    alias_map = {}

    # Construir mapa normalizado alias → canonical
    for canonical, names in ALIASES.items():
        for name in names:
            alias_map[_norm(name)] = canonical

    out = {}
    for k, v in raw_sections.items():
        nk = _norm(k)
        canonical = alias_map.get(nk, nk)
        if canonical in out:
            out[canonical] = out[canonical].rstrip() + "\n\n---\n\n" + v.lstrip()
        else:
            out[canonical] = v

    return out


def validate_sections(sections: dict) -> list[str]:
    errors = []
    keys = set(sections.keys())

    for k in REQUIRED_KEYS:
        if k not in keys:
            errors.append(f"Missing required section: '{k}'")

    return errors

CRITICAL_KEYS = ["verification"]
