# GitHub Copilot Instructions for HUB_Optimus

## Project Overview
HUB_Optimus is an integrity-first diplomatic simulation framework designed for evaluation, preventive mediation, and systemic learning. It helps institutions avoid repeating historical failure patterns and prioritizes medium/long-term stability over short-term optics.

**Core Purpose:** Improve diplomatic outcomes through structured evaluation of incentives, verification mechanisms, and sequencing of decisions.

**What it is NOT:**
- Not an authority or decision-maker
- Not a prediction engine
- Not a replacement for diplomacy
- Not a propaganda tool
- Not a coercive enforcement mechanism

## Immutable Principles (Layer 0 - Kernel)

When contributing to this codebase, you MUST respect these non-negotiable principles:

### 1. Stability Over Optics
Medium/long-term systemic stability is the supreme criterion. Any "success" that increases long-term instability is a false success and must be rejected.

### 2. Integrity First
Influence over the core is earned through ethical coherence and sustained integrity, not credentials or position.

### 3. Evaluation Over Narrative
Outcomes are assessed structurally (incentives, verification, sequencing), not rhetorically or through narratives.

### 4. Prevention Over Reaction
Early, discreet mediation is preferred to public escalation.

### 5. Non-Coercion
HUB_Optimus does not coerce, enforce, punish, or compel. It evaluates structure; it does not execute power.

### 6. Neutrality
The system must remain outcome-neutral. It does not assign moral blame or political legitimacy. It clarifies consequences and structural risk.

### 7. Systemic Error Framing
Errors are treated as systemic (incentives, structures, feedback loops), never as personal defects. No scapegoating.

### 8. Incentives First
The primary driver of recurring crises is misaligned incentives. Always prioritize detecting and correcting incentive structures.

### 9. Verifiability First
Claims and commitments are evaluated by verifiability. Narrative strength, authority, urgency, or moral framing do not increase trust classification.

### 10. Anti-Capture
No individual—including the originator—has special privileges. Authorship does not confer authority. All changes must go through transparent review processes.

## Repository Structure

### Critical Paths
- `v1_core/` — Active Kernel and simulator (HIGH SCRUTINY required for changes - see "D) Kernel Changes" section below)
  - `v1_core/languages/en/` — English reference for structure and validation
  - `v1_core/languages/es/` — Spanish translations
  - `v1_core/workflow/` — Scenario simulator templates and examples
- `docs/` — Onboarding and reading paths (multilingual)
- `docs/governance/` — Governance documents (Charter, Kernel, Consensus Process, etc.)
- `legacy/` — Historical v0 materials (DO NOT rewrite or modernize)

### File Naming Convention
- Folder structure and filenames MUST remain consistent across all languages
- English (`en`) is the reference language for structural validation
- All translations must preserve meaning without conceptual drift

## Contribution Guidelines

### A) Documentation Improvements (Low Risk)
**Allowed:**
- Typo fixes
- Formatting improvements
- Readability enhancements (without meaning drift)
- Broken link fixes

**Process:**
- Make focused, minimal changes
- Preserve existing structure and tone
- Do not introduce new concepts without justification

### B) Scenario Contributions (Recommended)
**Location:** `v1_core/workflow/`

**Template:** Use `v1_core/workflow/04_scenario_template.md`

**Required Elements:**
- Trigger and structural context
- Incentive analysis
- Systemic evaluation
- Historical contrast
- Kernel coherence check
- Final classification
- Memory integration notes

### C) Meta-Learning Updates (Medium Risk)
**Location:** `v1_core/workflow/05_meta_learning.md`

**Requirements:**
- Reference which scenario(s) justify the new rule
- Explain what failure/success pattern it prevents or reinforces
- Maintain integrity-first framing

### D) Kernel Changes (High Risk)
**Files:**
- `v1_core/languages/en/01_base_declaracion.md`
- `v1_core/languages/en/02_arquitectura_base.md`
- `v1_core/languages/en/03_flujo_operativo.md`

**Requirements:**
- Explicit justification aligned with Layer 0 principles
- Impact analysis
- Integrity-first review
- Synchronized language updates across ALL translations

**DO NOT:**
- Weaken Kernel integrity protections
- Introduce coercive enforcement concepts
- Add personal scapegoating as analysis
- Present short-term "wins" as success while increasing long-term instability
- Introduce narrative manipulation

### E) Legacy Materials
**Location:** `legacy/`

**Rules:**
- DO NOT rewrite or "modernize" legacy documents
- Corrections should be added as v1 notes, not retroactively edited
- Preserve for transparency and historical reference

## Language Policy

### Translation Requirements
1. **Structural Consistency:** All languages mirror the same file set, order, and structure
2. **Reference Language:** English (`en`) is the reference for validation
3. **Meaning Preservation:** Translations must preserve intent and definitions precisely
4. **No Conceptual Drift:** Language must not introduce new interpretations or concepts
5. **Synchronized Updates:** Kernel changes must be reflected in ALL language versions

### Supported Languages
- English (`en`) — Reference language
- Spanish (`es`) — Parallel documentation
- German (`de`) — Onboarding materials
- Catalan (`ca`) — Onboarding materials
- French (`fr`) — Onboarding materials
- Russian (`ru`) — Onboarding materials

## Code and Documentation Standards

### Writing Style
- **Clarity over volume:** Be precise and concise
- **Structural reasoning over rhetoric:** Focus on systemic analysis
- **Prevention over escalation:** Frame solutions proactively
- **Integrity and coherence:** Maintain consistency with Layer 0 principles
- **Verifiable improvement:** Changes must demonstrate measurable value

### What to Avoid
- Verbose explanations that obscure meaning
- Personal opinions presented as facts
- Blame-oriented language
- Short-term optimization that increases long-term risk
- Propaganda or narrative manipulation
- Introducing dependencies on external authorities

### Comments and Documentation
- Include comments when explaining complex incentive structures
- Document systemic relationships and feedback loops
- Explain evaluation criteria and stability metrics
- Reference historical patterns when relevant
- Keep inline comments minimal; prefer external documentation

## Git Workflow

### Branch Naming
- `feat/<short-name>` — New features or scenarios
- `chore/<short-name>` — Maintenance, documentation, tooling
- `fix/<short-name>` — Bug fixes

### Commit Messages
- Use clear, descriptive messages
- Reference affected areas: `docs:`, `kernel:`, `scenario:`, `workflow:`
- Example: `docs: fix broken links in governance section`
- Example: `scenario: add SCN-003 verified monitoring protocol`
- Example: `kernel: clarify incentive evaluation criteria`

### Pull Request Requirements
1. Clear summary of changes
2. Rationale aligned with Layer 0 principles
3. List of affected files
4. Scenario links (if applicable)
5. Risks and mitigations (if kernel-adjacent)
6. Impact on other language versions (if applicable)

## Quality Standards

### Before Submitting Changes
- [ ] Changes preserve Kernel integrity
- [ ] No weakening of evaluation standards
- [ ] No introduction of coercive mechanisms
- [ ] Language is clear and precise
- [ ] Systemic framing (not personal blame)
- [ ] Medium/long-term stability prioritized
- [ ] All relevant translations updated
- [ ] Links validated (Lychee enforced via CI)

### Review Criteria
Contributions are reviewed for:
- Coherence with Layer 0 principles
- Systemic framing (not personal blame)
- Incentive awareness
- Prevention posture
- Clarity and traceability
- Integrity-first alignment

## Security and Sensitive Information

### DO NOT Commit
- Personal data
- Banking or financial documents
- Credentials, API keys, passwords
- Private agreements
- Sensitive diplomatic information
- Real names or identifying information from scenarios (use anonymized examples)

### If Sensitive Data is Accidentally Committed
1. Report immediately
2. Do not attempt to fix by deleting only
3. History rewriting may be required

## Testing and Validation

### Link Checking
- All documentation links are checked via GitHub Actions using Lychee
- Configuration: `.github/lychee.toml`
- Broken links will fail CI checks

### Scenario Validation
When adding or modifying scenarios:
1. Verify all required sections are present per template
2. Check incentive analysis is structural (not rhetorical)
3. Ensure historical contrasts are accurate and relevant
4. Validate Kernel coherence check references Layer 0 principles
5. Confirm meta-learning integration is specified

### Multi-Language Validation
When updating Kernel documents:
1. Update English version first
2. Synchronize all language versions
3. Verify structural consistency across languages
4. Check that translations preserve meaning
5. Validate file naming and structure match exactly

## Common Tasks

### Adding a New Scenario
1. Copy `v1_core/workflow/04_scenario_template.md`
2. Name it `scenario_XXX_descriptive_name.md`
3. Fill all required sections
4. Include incentive analysis (structural, not rhetorical)
5. Add historical contrast
6. Perform Kernel coherence check
7. Update meta-learning if introducing new pattern
8. Submit PR with clear rationale

### Fixing Documentation Typos
1. Make minimal, focused changes
2. Preserve existing structure and tone
3. If in Kernel files, update ALL language versions
4. Verify links still work
5. Submit with clear commit message

### Updating Governance Documents
1. Reference Layer 0 principles in justification
2. Provide impact analysis
3. Ensure systemic framing (not personal)
4. Get integrity-first review
5. Synchronize across languages if applicable

## Working with GitHub Copilot

### Prompts That Align With Project Values
✅ "Add a scenario evaluating incentive misalignment in ceasefire negotiations"
✅ "Document the systemic factors that lead to verification failures"
✅ "Translate this Kernel section to Spanish, preserving exact meaning"
✅ "Fix broken links in the governance documentation"
✅ "Add meta-learning rule about short-term optics vs long-term stability"

### Prompts to Avoid
❌ "Add enforcement mechanisms for compliance"
❌ "Create blame-assignment framework"
❌ "Optimize for short-term visibility"
❌ "Add predictive analytics for outcomes"
❌ "Introduce authority-based decision making"

## Additional Resources

- Main README: `/README.md`
- Contributing Guide: `/CONTRIBUTING.md`
- Start Here: `/docs/00_start_here.md`
- Workflow Overview: `/v1_core/workflow/README.md`
- Base Declaration (Kernel): `/v1_core/languages/en/01_base_declaracion.md`
- Architecture: `/v1_core/languages/en/02_arquitectura_base.md`
- Operational Flow: `/v1_core/languages/en/03_flujo_operativo.md`
- Governance Documents: `/docs/governance/`

## Questions or Uncertainty?

When in doubt:
1. Prioritize stability over optics
2. Frame systemically, not personally
3. Focus on incentives and verification
4. Preserve Kernel integrity
5. Ask for clarification via issue or PR discussion

Remember: HUB_Optimus is a tool for better judgment, not a replacement for human diplomatic wisdom. Contributions should enhance evaluation capacity while maintaining integrity-first principles.
