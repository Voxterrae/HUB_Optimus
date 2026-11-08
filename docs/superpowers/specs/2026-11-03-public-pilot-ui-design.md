# Windows public pilot selection — approved increment2083

The owner approved implementing the proposed Windows pilot action and cloud acceptance after PR2082. Goal: use the real eight-reference public catalog from the native browser without manual file copying, and restore the habitual index. Microsoft/Azure remains the target infrastructure; this increment creates no Azure resource, account, credential, public endpoint or cost.

## Approach and bounded choices

Use two fixed bundled public files from Search/catalog (catalog and provenance), pin their reviewed canonical UTF-8/LF hashes, and import via the existing real .NET CLI. Do not add an arbitrary file picker/download/remote API, reimplement ranking, or overwrite the frozen three-help index. Embedded data would complicate honest corrupted-asset GUI acceptance; fixed files permit that fixture in the disposable publication. Generic user-catalog import and remote authentication are later projects.

Activation is explicit and session-only. Label the Index surface `Piloto público · 8 documentos` and state that it lasts the session; show `Cargar catálogo piloto` and `Restaurar catálogo anterior`. It applies to the application's search surfaces, including private tabs without exposing normal bookmarks. Default source selection, Web/Wikipedia settings and browser profile persistence remain unchanged. Re-loading the same pilot remains available for repair/error testing.

A newly owned temporary workspace holds normalized public input and imported index. No existing profile index is copied/replaced. Validate assets before any owned host reconfiguration. Import is bounded, cancellation-aware and sanitized. Select the new index only after the authenticated owned host restarts successfully. The launcher serializes selection/connect, refuses a healthy independent host, preserves previous index selection on import/startup/cancellation/normal-shutdown failure, and never stops independent processes. Dispose host before deleting only known owned temporary files; retain if owned-host cleanup is unconfirmed. Existing per-device token and TLS/HMAC boundary are unchanged.

All stale search results are cancelled/cleared across tabs before and after a switch. Search eligibility blocks while switching. UI controls use native accessible names, large buttons and existing responsive styling; no product QA switches or test-only event endpoints.

## Acceptance and cloud evidence

Portable behavioral tests first reproduce missing selection, malformed assets, import failure, cancellation, rollback, concurrent connect and independent-host refusal; original suites remain green. Build WPF and helper with SDK10.0.403.

The original malformed-byte GUI fixture is replaced by unavailable-asset failure so a caller-supplied publication is never modified; malformed-byte rejection remains proven with the real importer in portable tests. Within one disposable Windows GUI session: baseline three-help query; invoke pilot; verify visible finite scope and actual topic results plus genuine unrelated empty; hold a read-only exclusive lease on the fixed public catalog after valid activation, invoke the real reload action, verify generic unavailable-asset failure and prior pilot results, then release the lease without modifying publication bytes; restore habitual index and find original help. Prove result-click/render separately through an ordinary loopback bookmark made via the existing local guide. Do not describe that as fetching public pilot articles offline or as general-Web acceptance. Keep normal owned-process exit, TLS provenance and cleanup checks.

Cloud source identity is a literal earlier owner Verified product/helper SHA, committed before its workflow pin. Keep historical native0790 and Web0790 workflows unchanged; add a separate manual pilot workflow with the same owner/public/main/contents-read/no-artifact/no-cache gates, source provenance and standard runner. No provider query/retry/fallback. Native acceptance must be observed after protected integration; unavailable GUI is blocked, never green by inference.

Runtime source/data and helper commit precede the literal workflow pin; no runtime edit after that pin without a fresh reviewed product SHA. Current main handoff is preserved as an exact prefix before append. Owner authority/protections and unrelated work remain unchanged.
