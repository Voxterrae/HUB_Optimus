# Canonical Spanish ↔ English core parity matrix

This is an evidence artifact for [issue #1749](https://github.com/Voxterrae/HUB_Optimus/issues/1749). It prepares section-level human review; it does **not** amend the canonical Spanish core, resolve any disposition, establish English parity, or authorize Russian, Hebrew, or Chinese kernel translations.

## Baseline and authority

| Field | Value |
| --- | --- |
| Artifact version | 1 |
| Comparison date | 2026-07-28 |
| Git baseline | `3ef199305c2d2d114f88aceb97b65a08b9f91b4a` |
| Canonical source | Spanish, per [`docs/context/STATUS.md`](../context/STATUS.md) |
| Parity target | English, unresolved |
| Human dispositions | 51 of 51 `UNRESOLVED` |

Compared pairs:

- [`v1_core/languages/es/01_base_declaracion.md`](../../v1_core/languages/es/01_base_declaracion.md) ↔ [`v1_core/languages/en/01_base_declaracion.md`](../../v1_core/languages/en/01_base_declaracion.md)
- [`v1_core/languages/es/02_arquitectura_base.md`](../../v1_core/languages/es/02_arquitectura_base.md) ↔ [`v1_core/languages/en/02_arquitectura_base.md`](../../v1_core/languages/en/02_arquitectura_base.md)
- [`v1_core/languages/es/03_flujo_operativo.md`](../../v1_core/languages/es/03_flujo_operativo.md) ↔ [`v1_core/languages/en/03_flujo_operativo.md`](../../v1_core/languages/en/03_flujo_operativo.md)

## Method

1. Extract every ATX Markdown heading matching `^#{1,6} ` from the six baseline files, preserving file order and exact heading text.
2. Pair files by their shared repository filename.
3. Compare the content governed by each heading. Map headings only when they address the same apparent subject; a matrix item may cite several headings when one language splits a subject that the other keeps together.
4. Require every source heading to occur exactly once in the matrix. Do not infer equivalence from numbering or order alone.
5. Assign one evidence classification:
   - `translation equivalent`: the scoped propositions appear equivalent; human confirmation is still required.
   - `ES-only`: no scoped English section carries the Spanish section's subject.
   - `EN-only`: no scoped Spanish section carries the English section's subject.
   - `semantic conflict`: scopes, definitions, requirements, or normative status differ materially. This label does not decide which text should prevail.
   - `editorial/order difference`: the apparent proposition is substantially shared but split, expanded, or ordered differently, without an identified direct contradiction.
   - `unknown`: the repository evidence is insufficient to classify more precisely without human interpretation.
6. Leave every human disposition `UNRESOLVED`. The only permitted future disposition values are `Spanish canonical wins`, `separate governance RFC`, and `English explanatory non-canonical`; this artifact chooses none.

Reproduce the structural audit with:

```bash
python -m pytest -q tests/test_core_es_en_parity_matrix.py
python tools/check_mojibake.py docs/i18n/core_es_en_parity_matrix.md tests/test_core_es_en_parity_matrix.py
git diff --check
```

## Divergence summary

| Pair | Matrix items | Translation equivalent | ES-only | EN-only | Semantic conflict | Editorial/order difference | Unknown |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Declaration | 16 | 1 | 4 | 6 | 5 | 0 | 0 |
| Architecture | 16 | 1 | 3 | 2 | 6 | 3 | 1 |
| Operational flow | 19 | 0 | 5 | 7 | 5 | 2 | 0 |
| **Total** | **51** | **2** | **12** | **15** | **16** | **5** | **1** |

The largest unresolved differences are:

- the English declaration assigns immutability and change-policy status that the Spanish declaration does not state in corresponding sections;
- the architecture pair gives materially different definitions to Layers 0, 2, and 5 and supplies different I/O, constraints, and repository mappings;
- the Spanish operational file describes scenario preparation and a three-round exercise, while the English file defines an eight-step signal-processing protocol;
- English-only language about Kernel integrity, active memory, and protocol invariants cannot be imported into canonical Spanish by this audit;
- Spanish-only priority, outcome-taxonomy, red-flag, preparation, and round-execution sections cannot be dropped merely to make the file shapes match.

These are observations about the versioned text, not governance decisions.

## Machine-readable section matrix

The JSON block below is the authoritative data within this artifact. Tests bind it to every baseline heading and file hash.

```json
{
  "schema_version": 1,
  "baseline_commit": "3ef199305c2d2d114f88aceb97b65a08b9f91b4a",
  "baseline_date": "2026-07-28",
  "canonical_language": "es",
  "parity_target": "en",
  "source_files": [
    {
      "pair_id": "declaration",
      "language": "es",
      "path": "v1_core/languages/es/01_base_declaracion.md",
      "sha256": "1bd43c7575dab98a4a8f318d49b17ab50c869247530505b282dd8d9ecca491f8"
    },
    {
      "pair_id": "declaration",
      "language": "en",
      "path": "v1_core/languages/en/01_base_declaracion.md",
      "sha256": "d5ac98438cf614d31a2b1a7568af95131f6ffac04b77b713d204cdf322bceeb7"
    },
    {
      "pair_id": "architecture",
      "language": "es",
      "path": "v1_core/languages/es/02_arquitectura_base.md",
      "sha256": "5b5315c09561b3892d4c4bd424048ad2d55f70e5553450043794c41035079b3b"
    },
    {
      "pair_id": "architecture",
      "language": "en",
      "path": "v1_core/languages/en/02_arquitectura_base.md",
      "sha256": "63def121910bf9738e1002ae082f7dd0f6f368b95089dec208c67880e13161bc"
    },
    {
      "pair_id": "operational_flow",
      "language": "es",
      "path": "v1_core/languages/es/03_flujo_operativo.md",
      "sha256": "9837cadd8c3b4d9277a5f5dbca5725217d4e7be819785ccf0e9944ab6f1c76db"
    },
    {
      "pair_id": "operational_flow",
      "language": "en",
      "path": "v1_core/languages/en/03_flujo_operativo.md",
      "sha256": "5f2c3c5f6c0b763e88eff04fcaa06811c54d602e5723726e910abf26cad22878"
    }
  ],
  "allowed_classifications": [
    "translation equivalent",
    "ES-only",
    "EN-only",
    "semantic conflict",
    "editorial/order difference",
    "unknown"
  ],
  "allowed_human_dispositions": [
    "Spanish canonical wins",
    "separate governance RFC",
    "English explanatory non-canonical"
  ],
  "entries": [
    {
      "id": "declaration-01",
      "pair_id": "declaration",
      "classification": "semantic conflict",
      "es": [{"path": "v1_core/languages/es/01_base_declaracion.md", "heading": "# Declaración base (ES)"}],
      "en": [{"path": "v1_core/languages/en/01_base_declaracion.md", "heading": "# 01 — Base Declaration (Immutable Core)"}],
      "evidence": "Both title the declaration, but only the English title assigns Immutable Core status.",
      "human_disposition": {
        "status": "UNRESOLVED",
        "allowed_options": ["Spanish canonical wins", "separate governance RFC", "English explanatory non-canonical"]
      }
    },
    {
      "id": "declaration-02",
      "pair_id": "declaration",
      "classification": "semantic conflict",
      "es": [{"path": "v1_core/languages/es/01_base_declaracion.md", "heading": "## 1) Propósito"}],
      "en": [{"path": "v1_core/languages/en/01_base_declaracion.md", "heading": "## 1) Purpose"}],
      "evidence": "Spanish defines reproducible scenario analysis, relief-versus-stability distinction, and meta-learning; English defines ethical peacebuilding, future-conflict reduction, incentive correction, and legitimacy through results.",
      "human_disposition": {
        "status": "UNRESOLVED",
        "allowed_options": ["Spanish canonical wins", "separate governance RFC", "English explanatory non-canonical"]
      }
    },
    {
      "id": "declaration-03",
      "pair_id": "declaration",
      "classification": "semantic conflict",
      "es": [{"path": "v1_core/languages/es/01_base_declaracion.md", "heading": "## 2) Qué hace HUB_Optimus"}],
      "en": [{"path": "v1_core/languages/en/01_base_declaracion.md", "heading": "## 2) What HUB_Optimus is"}],
      "evidence": "Spanish describes case-structuring and verification behavior; English describes system identity, preventive mediation, and active historical memory.",
      "human_disposition": {
        "status": "UNRESOLVED",
        "allowed_options": ["Spanish canonical wins", "separate governance RFC", "English explanatory non-canonical"]
      }
    },
    {
      "id": "declaration-04",
      "pair_id": "declaration",
      "classification": "EN-only",
      "es": [],
      "en": [{"path": "v1_core/languages/en/01_base_declaracion.md", "heading": "## 3) What HUB_Optimus is not"}],
      "evidence": "The Spanish declaration has no corresponding exclusion section for party, tribunal, coercive authority, or human-judgment replacement.",
      "human_disposition": {
        "status": "UNRESOLVED",
        "allowed_options": ["Spanish canonical wins", "separate governance RFC", "English explanatory non-canonical"]
      }
    },
    {
      "id": "declaration-05",
      "pair_id": "declaration",
      "classification": "semantic conflict",
      "es": [{"path": "v1_core/languages/es/01_base_declaracion.md", "heading": "## 3) Principios operativos"}],
      "en": [
        {"path": "v1_core/languages/en/01_base_declaracion.md", "heading": "## 4) Non-negotiable principles (Layer 0)"},
        {"path": "v1_core/languages/en/01_base_declaracion.md", "heading": "### 4.4 Incentives first"},
        {"path": "v1_core/languages/en/01_base_declaracion.md", "heading": "### 4.5 Evaluation over narrative"}
      ],
      "evidence": "The lists overlap on incentives and narrative, but Spanish also defines verification, sequence, clarity, and iteration while English assigns Layer 0 and non-negotiable status and omits those three Spanish principles.",
      "human_disposition": {
        "status": "UNRESOLVED",
        "allowed_options": ["Spanish canonical wins", "separate governance RFC", "English explanatory non-canonical"]
      }
    },
    {
      "id": "declaration-06",
      "pair_id": "declaration",
      "classification": "translation equivalent",
      "es": [{"path": "v1_core/languages/es/01_base_declaracion.md", "heading": "## 4) Criterio supremo"}],
      "en": [{"path": "v1_core/languages/en/01_base_declaracion.md", "heading": "### 4.2 Supreme criterion"}],
      "evidence": "Both make medium/long-term stability and reduced future risk the supreme criterion and reject apparent success that increases later instability.",
      "human_disposition": {
        "status": "UNRESOLVED",
        "allowed_options": ["Spanish canonical wins", "separate governance RFC", "English explanatory non-canonical"]
      }
    },
    {
      "id": "declaration-07",
      "pair_id": "declaration",
      "classification": "ES-only",
      "es": [{"path": "v1_core/languages/es/01_base_declaracion.md", "heading": "## 5) Modelo de prioridad D + A (definición operativa)"}],
      "en": [],
      "evidence": "The English declaration has no corresponding Durability plus immediate Relief/Assistance priority model.",
      "human_disposition": {
        "status": "UNRESOLVED",
        "allowed_options": ["Spanish canonical wins", "separate governance RFC", "English explanatory non-canonical"]
      }
    },
    {
      "id": "declaration-08",
      "pair_id": "declaration",
      "classification": "ES-only",
      "es": [{"path": "v1_core/languages/es/01_base_declaracion.md", "heading": "## 6) Resultados típicos (tipología)"}],
      "en": [],
      "evidence": "The four-part outcome typology is absent from the English declaration.",
      "human_disposition": {
        "status": "UNRESOLVED",
        "allowed_options": ["Spanish canonical wins", "separate governance RFC", "English explanatory non-canonical"]
      }
    },
    {
      "id": "declaration-09",
      "pair_id": "declaration",
      "classification": "ES-only",
      "es": [{"path": "v1_core/languages/es/01_base_declaracion.md", "heading": "## 7) Señales de alerta temprana (red flags)"}],
      "en": [],
      "evidence": "The English declaration has no corresponding checklist of verification, timing, incentive, consequence, and celebratory-language red flags.",
      "human_disposition": {
        "status": "UNRESOLVED",
        "allowed_options": ["Spanish canonical wins", "separate governance RFC", "English explanatory non-canonical"]
      }
    },
    {
      "id": "declaration-10",
      "pair_id": "declaration",
      "classification": "semantic conflict",
      "es": [{"path": "v1_core/languages/es/01_base_declaracion.md", "heading": "## 8) Qué se considera “éxito” aquí"}],
      "en": [{"path": "v1_core/languages/en/01_base_declaracion.md", "heading": "### 4.1 Success definition"}],
      "evidence": "Spanish defines success through an agreement's clarity, verification, sequencing, and compliance incentives; English defines it as measurable reduction of future risk.",
      "human_disposition": {
        "status": "UNRESOLVED",
        "allowed_options": ["Spanish canonical wins", "separate governance RFC", "English explanatory non-canonical"]
      }
    },
    {
      "id": "declaration-11",
      "pair_id": "declaration",
      "classification": "EN-only",
      "es": [],
      "en": [{"path": "v1_core/languages/en/01_base_declaracion.md", "heading": "### 4.3 Systemic error framing"}],
      "evidence": "The Spanish declaration does not state a corresponding systemic-error and no-scapegoating principle.",
      "human_disposition": {
        "status": "UNRESOLVED",
        "allowed_options": ["Spanish canonical wins", "separate governance RFC", "English explanatory non-canonical"]
      }
    },
    {
      "id": "declaration-12",
      "pair_id": "declaration",
      "classification": "EN-only",
      "es": [],
      "en": [{"path": "v1_core/languages/en/01_base_declaracion.md", "heading": "### 4.6 Integrity as the entry filter"}],
      "evidence": "The Spanish declaration does not state a corresponding rule for access to Kernel influence.",
      "human_disposition": {
        "status": "UNRESOLVED",
        "allowed_options": ["Spanish canonical wins", "separate governance RFC", "English explanatory non-canonical"]
      }
    },
    {
      "id": "declaration-13",
      "pair_id": "declaration",
      "classification": "EN-only",
      "es": [],
      "en": [{"path": "v1_core/languages/en/01_base_declaracion.md", "heading": "## 5) Operating posture"}],
      "evidence": "The Spanish declaration has no corresponding preference list for discreet mediation, parallel action and analysis, and transparent criteria.",
      "human_disposition": {
        "status": "UNRESOLVED",
        "allowed_options": ["Spanish canonical wins", "separate governance RFC", "English explanatory non-canonical"]
      }
    },
    {
      "id": "declaration-14",
      "pair_id": "declaration",
      "classification": "EN-only",
      "es": [],
      "en": [{"path": "v1_core/languages/en/01_base_declaracion.md", "heading": "## 6) Translation policy (single core, multiple languages)"}],
      "evidence": "The Spanish declaration contains a navigation label calling English a source, but no section that defines this English translation-policy rule.",
      "human_disposition": {
        "status": "UNRESOLVED",
        "allowed_options": ["Spanish canonical wins", "separate governance RFC", "English explanatory non-canonical"]
      }
    },
    {
      "id": "declaration-15",
      "pair_id": "declaration",
      "classification": "ES-only",
      "es": [{"path": "v1_core/languages/es/01_base_declaracion.md", "heading": "## 9) Enlaces internos"}],
      "en": [],
      "evidence": "Only the Spanish declaration provides an internal-links section.",
      "human_disposition": {
        "status": "UNRESOLVED",
        "allowed_options": ["Spanish canonical wins", "separate governance RFC", "English explanatory non-canonical"]
      }
    },
    {
      "id": "declaration-16",
      "pair_id": "declaration",
      "classification": "EN-only",
      "es": [],
      "en": [{"path": "v1_core/languages/en/01_base_declaracion.md", "heading": "## 7) Change policy"}],
      "evidence": "Only English declares this file immutable and requires Kernel review and language synchronization for changes.",
      "human_disposition": {
        "status": "UNRESOLVED",
        "allowed_options": ["Spanish canonical wins", "separate governance RFC", "English explanatory non-canonical"]
      }
    },
    {
      "id": "architecture-01",
      "pair_id": "architecture",
      "classification": "editorial/order difference",
      "es": [{"path": "v1_core/languages/es/02_arquitectura_base.md", "heading": "# Arquitectura base (ES)"}],
      "en": [{"path": "v1_core/languages/en/02_arquitectura_base.md", "heading": "# 02 — Architecture Baseline (Layers 0–5)"}],
      "evidence": "Both title an architecture baseline; English adds the layer range and file number.",
      "human_disposition": {
        "status": "UNRESOLVED",
        "allowed_options": ["Spanish canonical wins", "separate governance RFC", "English explanatory non-canonical"]
      }
    },
    {
      "id": "architecture-02",
      "pair_id": "architecture",
      "classification": "semantic conflict",
      "es": [{"path": "v1_core/languages/es/02_arquitectura_base.md", "heading": "## 1) Visión general"}],
      "en": [{"path": "v1_core/languages/en/02_arquitectura_base.md", "heading": "## 1) Core design statement"}],
      "evidence": "Spanish frames layers as questions that reduce negotiation errors; English defines non-coercive, integrity-first, anti-cycle, and human-compatible architectural properties.",
      "human_disposition": {
        "status": "UNRESOLVED",
        "allowed_options": ["Spanish canonical wins", "separate governance RFC", "English explanatory non-canonical"]
      }
    },
    {
      "id": "architecture-03",
      "pair_id": "architecture",
      "classification": "translation equivalent",
      "es": [{"path": "v1_core/languages/es/02_arquitectura_base.md", "heading": "## 2) Capas (Layers) y función"}],
      "en": [{"path": "v1_core/languages/en/02_arquitectura_base.md", "heading": "## 2) Layer model (0–5)"}],
      "evidence": "Both headings introduce the six-layer model; individual layer definitions are classified separately.",
      "human_disposition": {
        "status": "UNRESOLVED",
        "allowed_options": ["Spanish canonical wins", "separate governance RFC", "English explanatory non-canonical"]
      }
    },
    {
      "id": "architecture-04",
      "pair_id": "architecture",
      "classification": "semantic conflict",
      "es": [{"path": "v1_core/languages/es/02_arquitectura_base.md", "heading": "### Capa 0 — Coherencia del núcleo (Kernel)"}],
      "en": [{"path": "v1_core/languages/en/02_arquitectura_base.md", "heading": "### Layer 0 — Immutable Ethical–Rational Kernel (INMUTABLE)"}],
      "evidence": "Spanish checks the supreme stability criterion; English adds constitutional, capture-prevention, integrity, systemic-error, immutability, input, output, and change requirements.",
      "human_disposition": {
        "status": "UNRESOLVED",
        "allowed_options": ["Spanish canonical wins", "separate governance RFC", "English explanatory non-canonical"]
      }
    },
    {
      "id": "architecture-05",
      "pair_id": "architecture",
      "classification": "unknown",
      "es": [{"path": "v1_core/languages/es/02_arquitectura_base.md", "heading": "### Capa 1 — Calibración humana"}],
      "en": [{"path": "v1_core/languages/en/02_arquitectura_base.md", "heading": "### Layer 1 — Human Model (Interpretative)"}],
      "evidence": "Both concern human calibration and framing, but only English states that the interface adapts rather than core truth; repository text alone does not establish whether that is intended as explanation or an added rule.",
      "human_disposition": {
        "status": "UNRESOLVED",
        "allowed_options": ["Spanish canonical wins", "separate governance RFC", "English explanatory non-canonical"]
      }
    },
    {
      "id": "architecture-06",
      "pair_id": "architecture",
      "classification": "semantic conflict",
      "es": [{"path": "v1_core/languages/es/02_arquitectura_base.md", "heading": "### Capa 2 — Incentivos"}],
      "en": [{"path": "v1_core/languages/en/02_arquitectura_base.md", "heading": "### Layer 2 — Observation & Detection (Optimus)"}],
      "evidence": "Spanish defines an incentive question and map; English expands Layer 2 into observation and detection with feedback loops, historical recurrence, dependency, and a no-policy-imposition rule.",
      "human_disposition": {
        "status": "UNRESOLVED",
        "allowed_options": ["Spanish canonical wins", "separate governance RFC", "English explanatory non-canonical"]
      }
    },
    {
      "id": "architecture-07",
      "pair_id": "architecture",
      "classification": "editorial/order difference",
      "es": [{"path": "v1_core/languages/es/02_arquitectura_base.md", "heading": "### Capa 3 — Evaluación sistémica"}],
      "en": [{"path": "v1_core/languages/en/02_arquitectura_base.md", "heading": "### Layer 3 — Systemic Evaluation (Operational Core)"}],
      "evidence": "Both evaluate medium/long-term stability and output risk classification plus a correction or intervention signal; English expands the questions and names this the operational core.",
      "human_disposition": {
        "status": "UNRESOLVED",
        "allowed_options": ["Spanish canonical wins", "separate governance RFC", "English explanatory non-canonical"]
      }
    },
    {
      "id": "architecture-08",
      "pair_id": "architecture",
      "classification": "editorial/order difference",
      "es": [{"path": "v1_core/languages/es/02_arquitectura_base.md", "heading": "### Capa 4 — Mediación preventiva"}],
      "en": [{"path": "v1_core/languages/en/02_arquitectura_base.md", "heading": "### Layer 4 — Preventive Mediation (Discrete Intervention)"}],
      "evidence": "Both define minimal preventive interventions using framing, incentives, and sequencing or timing; English expands activation inputs and discreet-output constraints.",
      "human_disposition": {
        "status": "UNRESOLVED",
        "allowed_options": ["Spanish canonical wins", "separate governance RFC", "English explanatory non-canonical"]
      }
    },
    {
      "id": "architecture-09",
      "pair_id": "architecture",
      "classification": "semantic conflict",
      "es": [{"path": "v1_core/languages/es/02_arquitectura_base.md", "heading": "### Capa 5 — Patrón histórico"}],
      "en": [{"path": "v1_core/languages/en/02_arquitectura_base.md", "heading": "### Layer 5 — Active Memory (Anti-cycle)"}],
      "evidence": "Spanish asks for historical precedent and divergence conditions; English defines an active memory subsystem with inputs, outputs, alerts, guidance, and a non-archival rule.",
      "human_disposition": {
        "status": "UNRESOLVED",
        "allowed_options": ["Spanish canonical wins", "separate governance RFC", "English explanatory non-canonical"]
      }
    },
    {
      "id": "architecture-10",
      "pair_id": "architecture",
      "classification": "ES-only",
      "es": [
        {"path": "v1_core/languages/es/02_arquitectura_base.md", "heading": "## 3) Entradas y salidas del sistema (I/O)"},
        {"path": "v1_core/languages/es/02_arquitectura_base.md", "heading": "### Entrada típica (input)"},
        {"path": "v1_core/languages/es/02_arquitectura_base.md", "heading": "### Salida típica (output)"}
      ],
      "en": [],
      "evidence": "English distributes some per-layer inputs and outputs but has no corresponding system-level scenario input and output contract with the Spanish lists.",
      "human_disposition": {
        "status": "UNRESOLVED",
        "allowed_options": ["Spanish canonical wins", "separate governance RFC", "English explanatory non-canonical"]
      }
    },
    {
      "id": "architecture-11",
      "pair_id": "architecture",
      "classification": "EN-only",
      "es": [],
      "en": [{"path": "v1_core/languages/en/02_arquitectura_base.md", "heading": "## 3) Cross-layer flow (canonical)"}],
      "evidence": "Spanish architecture has no corresponding canonical eight-step cross-layer flow section.",
      "human_disposition": {
        "status": "UNRESOLVED",
        "allowed_options": ["Spanish canonical wins", "separate governance RFC", "English explanatory non-canonical"]
      }
    },
    {
      "id": "architecture-12",
      "pair_id": "architecture",
      "classification": "semantic conflict",
      "es": [{"path": "v1_core/languages/es/02_arquitectura_base.md", "heading": "## 4) Principales modos de fallo que la arquitectura intenta evitar"}],
      "en": [{"path": "v1_core/languages/en/02_arquitectura_base.md", "heading": "## 4) Hard constraints (what the architecture forbids)"}],
      "evidence": "Spanish lists implementation failure modes; English declares prohibitions. They overlap on false success but differ on verification, ambiguity, sequence, history, scapegoating, Kernel change, language drift, and coercion.",
      "human_disposition": {
        "status": "UNRESOLVED",
        "allowed_options": ["Spanish canonical wins", "separate governance RFC", "English explanatory non-canonical"]
      }
    },
    {
      "id": "architecture-13",
      "pair_id": "architecture",
      "classification": "semantic conflict",
      "es": [{"path": "v1_core/languages/es/02_arquitectura_base.md", "heading": "## 5) Artefactos del repositorio y dónde viven"}],
      "en": [{"path": "v1_core/languages/en/02_arquitectura_base.md", "heading": "## 5) Repository mapping (where each layer lives)"}],
      "evidence": "Spanish maps general inputs, workflow, and conceptual bases; English maps individual layers and identifies future implementation, playbook, and memory locations.",
      "human_disposition": {
        "status": "UNRESOLVED",
        "allowed_options": ["Spanish canonical wins", "separate governance RFC", "English explanatory non-canonical"]
      }
    },
    {
      "id": "architecture-14",
      "pair_id": "architecture",
      "classification": "ES-only",
      "es": [{"path": "v1_core/languages/es/02_arquitectura_base.md", "heading": "## 6) Estándar mínimo de un documento “usable”"}],
      "en": [],
      "evidence": "English has no corresponding document-readiness standard for links, definitions, criteria, contradictions, and reproducibility.",
      "human_disposition": {
        "status": "UNRESOLVED",
        "allowed_options": ["Spanish canonical wins", "separate governance RFC", "English explanatory non-canonical"]
      }
    },
    {
      "id": "architecture-15",
      "pair_id": "architecture",
      "classification": "EN-only",
      "es": [],
      "en": [{"path": "v1_core/languages/en/02_arquitectura_base.md", "heading": "## 6) Versioning"}],
      "evidence": "Spanish architecture has no corresponding Kernel-baseline versioning and cross-language synchronization section.",
      "human_disposition": {
        "status": "UNRESOLVED",
        "allowed_options": ["Spanish canonical wins", "separate governance RFC", "English explanatory non-canonical"]
      }
    },
    {
      "id": "architecture-16",
      "pair_id": "architecture",
      "classification": "ES-only",
      "es": [{"path": "v1_core/languages/es/02_arquitectura_base.md", "heading": "## 7) Enlaces internos"}],
      "en": [],
      "evidence": "Only Spanish provides a dedicated internal-links section.",
      "human_disposition": {
        "status": "UNRESOLVED",
        "allowed_options": ["Spanish canonical wins", "separate governance RFC", "English explanatory non-canonical"]
      }
    },
    {
      "id": "operational-flow-01",
      "pair_id": "operational_flow",
      "classification": "semantic conflict",
      "es": [{"path": "v1_core/languages/es/03_flujo_operativo.md", "heading": "# Flujo operativo (ES)"}],
      "en": [{"path": "v1_core/languages/en/03_flujo_operativo.md", "heading": "# 03 — Operational Flow (Protocol 1–8)"}],
      "evidence": "Both title an operational flow, but English assigns an eight-step protocol identity while Spanish organizes preparation and a three-round exercise.",
      "human_disposition": {
        "status": "UNRESOLVED",
        "allowed_options": ["Spanish canonical wins", "separate governance RFC", "English explanatory non-canonical"]
      }
    },
    {
      "id": "operational-flow-02",
      "pair_id": "operational_flow",
      "classification": "semantic conflict",
      "es": [{"path": "v1_core/languages/es/03_flujo_operativo.md", "heading": "## 1) Objetivo del flujo"}],
      "en": [{"path": "v1_core/languages/en/03_flujo_operativo.md", "heading": "## 1) Purpose of the operational flow"}],
      "evidence": "Spanish defines a negotiation/simulation exercise and reusable learning; English defines canonical signal processing under time, information, political, and power constraints.",
      "human_disposition": {
        "status": "UNRESOLVED",
        "allowed_options": ["Spanish canonical wins", "separate governance RFC", "English explanatory non-canonical"]
      }
    },
    {
      "id": "operational-flow-03",
      "pair_id": "operational_flow",
      "classification": "ES-only",
      "es": [
        {"path": "v1_core/languages/es/03_flujo_operativo.md", "heading": "## 2) Preparación (2–10 minutos)"},
        {"path": "v1_core/languages/es/03_flujo_operativo.md", "heading": "### 2.1 Elegir un escenario"},
        {"path": "v1_core/languages/es/03_flujo_operativo.md", "heading": "### 2.2 Definir roles y límites"},
        {"path": "v1_core/languages/es/03_flujo_operativo.md", "heading": "### 2.3 Definir “éxito mínimo”"}
      ],
      "en": [],
      "evidence": "English has no corresponding timed scenario-selection, role-boundary, and minimum-success preparation section.",
      "human_disposition": {
        "status": "UNRESOLVED",
        "allowed_options": ["Spanish canonical wins", "separate governance RFC", "English explanatory non-canonical"]
      }
    },
    {
      "id": "operational-flow-04",
      "pair_id": "operational_flow",
      "classification": "EN-only",
      "es": [],
      "en": [{"path": "v1_core/languages/en/03_flujo_operativo.md", "heading": "## 2) Entry conditions (what can trigger the flow)"}],
      "evidence": "Spanish has no corresponding trigger taxonomy for decisions, events, memory recurrence, and incentive shifts.",
      "human_disposition": {
        "status": "UNRESOLVED",
        "allowed_options": ["Spanish canonical wins", "separate governance RFC", "English explanatory non-canonical"]
      }
    },
    {
      "id": "operational-flow-05",
      "pair_id": "operational_flow",
      "classification": "semantic conflict",
      "es": [{"path": "v1_core/languages/es/03_flujo_operativo.md", "heading": "## 3) Ejecución (3 rondas recomendadas)"}],
      "en": [{"path": "v1_core/languages/en/03_flujo_operativo.md", "heading": "## 3) Protocol steps (1–8)"}],
      "evidence": "Spanish specifies three negotiation rounds; English specifies eight detection, evaluation, mediation, and memory protocol steps.",
      "human_disposition": {
        "status": "UNRESOLVED",
        "allowed_options": ["Spanish canonical wins", "separate governance RFC", "English explanatory non-canonical"]
      }
    },
    {
      "id": "operational-flow-06",
      "pair_id": "operational_flow",
      "classification": "ES-only",
      "es": [{"path": "v1_core/languages/es/03_flujo_operativo.md", "heading": "### Ronda 1 — Propuesta inicial"}],
      "en": [],
      "evidence": "English has no corresponding initial-proposal negotiation round.",
      "human_disposition": {
        "status": "UNRESOLVED",
        "allowed_options": ["Spanish canonical wins", "separate governance RFC", "English explanatory non-canonical"]
      }
    },
    {
      "id": "operational-flow-07",
      "pair_id": "operational_flow",
      "classification": "ES-only",
      "es": [{"path": "v1_core/languages/es/03_flujo_operativo.md", "heading": "### Ronda 2 — Ajuste estructural"}],
      "en": [],
      "evidence": "English has no corresponding verification, sequencing, incentive, and consequence adjustment round.",
      "human_disposition": {
        "status": "UNRESOLVED",
        "allowed_options": ["Spanish canonical wins", "separate governance RFC", "English explanatory non-canonical"]
      }
    },
    {
      "id": "operational-flow-08",
      "pair_id": "operational_flow",
      "classification": "ES-only",
      "es": [{"path": "v1_core/languages/es/03_flujo_operativo.md", "heading": "### Ronda 3 — Cierre"}],
      "en": [],
      "evidence": "English has no corresponding agreement-draft and next-step closing round.",
      "human_disposition": {
        "status": "UNRESOLVED",
        "allowed_options": ["Spanish canonical wins", "separate governance RFC", "English explanatory non-canonical"]
      }
    },
    {
      "id": "operational-flow-09",
      "pair_id": "operational_flow",
      "classification": "EN-only",
      "es": [],
      "en": [{"path": "v1_core/languages/en/03_flujo_operativo.md", "heading": "### Step 1 — Trigger registration"}],
      "evidence": "Spanish has no corresponding neutral trigger-registration step and output record.",
      "human_disposition": {
        "status": "UNRESOLVED",
        "allowed_options": ["Spanish canonical wins", "separate governance RFC", "English explanatory non-canonical"]
      }
    },
    {
      "id": "operational-flow-10",
      "pair_id": "operational_flow",
      "classification": "semantic conflict",
      "es": [{"path": "v1_core/languages/es/03_flujo_operativo.md", "heading": "## 4) Evaluación (post-ronda)"}],
      "en": [{"path": "v1_core/languages/en/03_flujo_operativo.md", "heading": "### Step 4 — Systemic evaluation"}],
      "evidence": "Spanish scores five criteria from 0–5 after a round and emits a four-part typology; English evaluates four Kernel questions and emits a risk classification.",
      "human_disposition": {
        "status": "UNRESOLVED",
        "allowed_options": ["Spanish canonical wins", "separate governance RFC", "English explanatory non-canonical"]
      }
    },
    {
      "id": "operational-flow-11",
      "pair_id": "operational_flow",
      "classification": "editorial/order difference",
      "es": [{"path": "v1_core/languages/es/03_flujo_operativo.md", "heading": "## 5) Aplicación de capas (cómo usar la arquitectura en la práctica)"}],
      "en": [
        {"path": "v1_core/languages/en/03_flujo_operativo.md", "heading": "### Step 2 — Incentive and signal detection"},
        {"path": "v1_core/languages/en/03_flujo_operativo.md", "heading": "### Step 3 — Human calibration"},
        {"path": "v1_core/languages/en/03_flujo_operativo.md", "heading": "### Step 5 — Historical contrast"},
        {"path": "v1_core/languages/en/03_flujo_operativo.md", "heading": "### Step 6 — Kernel coherence check"}
      ],
      "evidence": "Both invoke Layers 2, 1, 5, and 0 for incentives, human calibration, history, and Kernel coherence, but Spanish presents checkpoints and also includes Layers 3 and 4 while English splits the operations into ordered protocol steps.",
      "human_disposition": {
        "status": "UNRESOLVED",
        "allowed_options": ["Spanish canonical wins", "separate governance RFC", "English explanatory non-canonical"]
      }
    },
    {
      "id": "operational-flow-12",
      "pair_id": "operational_flow",
      "classification": "editorial/order difference",
      "es": [{"path": "v1_core/languages/es/03_flujo_operativo.md", "heading": "## 6) Meta-learning (iteración)"}],
      "en": [{"path": "v1_core/languages/en/03_flujo_operativo.md", "heading": "### Step 8 — Feedback and memory update"}],
      "evidence": "Both feed outcomes into future learning; Spanish specifies minimal patches and reruns, while English specifies recording and Active Memory reinforcement.",
      "human_disposition": {
        "status": "UNRESOLVED",
        "allowed_options": ["Spanish canonical wins", "separate governance RFC", "English explanatory non-canonical"]
      }
    },
    {
      "id": "operational-flow-13",
      "pair_id": "operational_flow",
      "classification": "EN-only",
      "es": [],
      "en": [{"path": "v1_core/languages/en/03_flujo_operativo.md", "heading": "### Step 7 — Preventive mediation activation (conditional)"}],
      "evidence": "Spanish applies a preventive-layer checkpoint but has no corresponding conditional activation step, three-condition gate, action set, and mediation package output.",
      "human_disposition": {
        "status": "UNRESOLVED",
        "allowed_options": ["Spanish canonical wins", "separate governance RFC", "English explanatory non-canonical"]
      }
    },
    {
      "id": "operational-flow-14",
      "pair_id": "operational_flow",
      "classification": "EN-only",
      "es": [],
      "en": [{"path": "v1_core/languages/en/03_flujo_operativo.md", "heading": "## 4) Failure handling"}],
      "evidence": "Spanish has no corresponding blockage recording, structural-cause capture, future-pattern preservation, and no-forced-intervention section.",
      "human_disposition": {
        "status": "UNRESOLVED",
        "allowed_options": ["Spanish canonical wins", "separate governance RFC", "English explanatory non-canonical"]
      }
    },
    {
      "id": "operational-flow-15",
      "pair_id": "operational_flow",
      "classification": "EN-only",
      "es": [],
      "en": [{"path": "v1_core/languages/en/03_flujo_operativo.md", "heading": "## 5) Time-critical mode"}],
      "evidence": "Spanish gives preparation and round timing but has no corresponding parallel-step and dominant-human-calibration emergency mode.",
      "human_disposition": {
        "status": "UNRESOLVED",
        "allowed_options": ["Spanish canonical wins", "separate governance RFC", "English explanatory non-canonical"]
      }
    },
    {
      "id": "operational-flow-16",
      "pair_id": "operational_flow",
      "classification": "semantic conflict",
      "es": [{"path": "v1_core/languages/es/03_flujo_operativo.md", "heading": "## 7) Artefactos de salida (qué guardar)"}],
      "en": [{"path": "v1_core/languages/en/03_flujo_operativo.md", "heading": "## 6) Output types"}],
      "evidence": "Spanish stores agreement drafts, open points, evidence-backed metrics, recommended changes, and scenario versions; English outputs evaluations, risk classifications, options, and warnings while expressly excluding decisions, mandates, and coercion.",
      "human_disposition": {
        "status": "UNRESOLVED",
        "allowed_options": ["Spanish canonical wins", "separate governance RFC", "English explanatory non-canonical"]
      }
    },
    {
      "id": "operational-flow-17",
      "pair_id": "operational_flow",
      "classification": "EN-only",
      "es": [],
      "en": [{"path": "v1_core/languages/en/03_flujo_operativo.md", "heading": "## 7) Invariants"}],
      "evidence": "Spanish has no corresponding operational invariants section for Layer 0 integrity, systemic error framing, de-escalation, and prevention.",
      "human_disposition": {
        "status": "UNRESOLVED",
        "allowed_options": ["Spanish canonical wins", "separate governance RFC", "English explanatory non-canonical"]
      }
    },
    {
      "id": "operational-flow-18",
      "pair_id": "operational_flow",
      "classification": "EN-only",
      "es": [],
      "en": [{"path": "v1_core/languages/en/03_flujo_operativo.md", "heading": "## 8) Versioning"}],
      "evidence": "Spanish has no corresponding statement that the protocol is part of the Kernel and requires architectural justification and Kernel review.",
      "human_disposition": {
        "status": "UNRESOLVED",
        "allowed_options": ["Spanish canonical wins", "separate governance RFC", "English explanatory non-canonical"]
      }
    },
    {
      "id": "operational-flow-19",
      "pair_id": "operational_flow",
      "classification": "ES-only",
      "es": [{"path": "v1_core/languages/es/03_flujo_operativo.md", "heading": "## 8) Enlaces internos"}],
      "en": [],
      "evidence": "Only Spanish provides a dedicated internal-links section.",
      "human_disposition": {
        "status": "UNRESOLVED",
        "allowed_options": ["Spanish canonical wins", "separate governance RFC", "English explanatory non-canonical"]
      }
    }
  ]
}
```

## Human review gate

For every item, a qualified maintainer must record one allowed disposition in a later, GitHub-traceable review. Items classified `unknown` require clarification before disposition. Any proposed addition to canonical Spanish that changes governance, Kernel authority, immutability, or protocol status belongs in a separate governance RFC rather than a translation patch.

Until those records exist and English is regenerated or revised from the resulting canonical source:

- English parity is not established;
- no Russian, Hebrew, or Chinese Kernel-readiness claim is valid;
- this matrix must not be treated as ratification, translation, or permission to modify protected paths.
