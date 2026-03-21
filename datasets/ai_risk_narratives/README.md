# AI Risk Narratives

This lane stores screenshot and post claims as reviewable input, not as repo truth.

Operator rules:
- Treat screenshots as claims, never as settled facts.
- Keep labels reviewable and reversible.
- Do not automate truth adjudication from the screenshot alone.
- Replace paraphrased seed wording with exact screenshot wording when the source corpus is attached.

Current limitation:
- The seed dataset in this branch is a provisional paraphrase set derived from the operator brief because the underlying screenshot files are not stored in the repo.

Files:
- `taxonomy.json`: closed vocabularies for risk domains, verification labels, and evidence tiers.
- `claim_record.schema.json`: machine-validatable schema for the seed corpus.
- `narrative_report.schema.json`: output contract for structured narrative reports.
- `seed_claims.json`: initial claim corpus for manual review and benchmark wiring.
