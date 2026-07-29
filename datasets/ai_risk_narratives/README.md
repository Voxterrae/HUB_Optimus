# AI Risk Narratives

This lane stores screenshot and post claims as reviewable input, not as repo truth.

Operator rules:
- Treat screenshot text as dirty input that requires human review.
- Treat screenshots as claims, never as settled facts.
- Keep labels reviewable and reversible.
- Do not automate truth adjudication from the screenshot alone.
- Preserve exact screenshot wording in `claim_text`; only normalize line breaks needed for JSON serialization.

Current limitation:
- The screenshot files themselves are not stored in the repo. `seed_claims.json` is a literal transcription set derived from operator-supplied source images.
- The seed remains provisional until maintainers review every transcription and label against those source images.

Files:
- `claim_record.schema.json`: machine-validatable seed contract and the sole stored source for the closed risk-domain, verification-status, and evidence-tier vocabularies under `$defs`; the consistency checker reads those definitions directly.
- `narrative_report.schema.json`: output contract for structured narrative reports.
- `seed_claims.json`: initial claim corpus for manual review and benchmark wiring.
