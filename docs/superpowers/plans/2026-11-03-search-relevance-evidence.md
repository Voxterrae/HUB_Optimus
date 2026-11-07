# Search relevance evidence implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans. Follow RED/GREEN and retain the protected integration boundary.

**Goal:** Distinguish official destination evidence, title-topic evidence and a same-result match without changing Web acceptance.

**Architecture:** The C# probe emits independent existing domain/topic fields and a new pairedMatch boolean. The Python supervisor accepts only internally consistent evidence; a passing query still requires a same-result domain-and-topic match, an error-free typed response and nonempty all-SearXNG results.

**Tech Stack:** .NET10.0.403, existing Core, Python3, pytest.

**Spec:** Existing governance issue2062 and products/browser/search/docs/REAL_WEB_SMOKE_2062.md. The owner's continuation authorizes repair/testing; Microsoft-first deployment remains a separate proposal with no resource activation.

## Global constraints

- Product literal pin0790e0977c170ff8507bb73e0ec7b6e166755892 remains unchanged.
- No new upstream query, fallback, retry, criterion relaxation, endpoint, credential or cloud resource.
- No raw title, URL, query log, error text or private value in reports.
- Preserve local loopback TLS/HMAC; Azure hosting is not a drop-in replacement for that boundary.
- Historical run41363931459 stays blocked and cannot gain information retroactively.

## Review focus

- Domain-only result reports the allowed domain and false topic/paired/pass.
- Topic-only off-domain result reports topic but null domain/false paired/pass.
- Domain and topic in different results never pass.
- True paired evidence with absent domain/topic, or claimed pass with false paired evidence, is rejected even in a blocked outer report.
- Unknown/extra diagnostic fields and missing pairedMatch remain rejected.
- Report-domain labels cannot carry raw URLs or arbitrary upstream subdomain text; proper official subdomains retain the original qualification semantics.

## Task1: C# predicate evidence

Files: products/browser/search/tools/RealWebSmoke/Program.cs.

- [x] Add synthetic self-checks for domain-only, topic-only, split candidates and valid pair. Run --self-test and observe a diagnostic failure against the old combined evidence.
- [x] Compute domain and topic independently; add bool PairedMatch to QueryEvidence; keep Passed dependent on the original conjunction in one result.
- [x] Build with explicit product root whose21Core files match current main. Run all probe self-checks; no network.

## Task2: Supervisor contract and handoff

Files: products/browser/search/tools/real_web_smoke.py; tests/test_optimus_real_web_smoke.py; products/browser/search/docs/REAL_WEB_SMOKE_2062.md; docs/context/AI_HANDOFF.md.

- [x] Add literal blocked-domain-only/topic-only/split fixtures and contradictory paired/pass evidence. Observe RED before accepting the new field.
- [x] Validate exact field set and boolean pairing invariants, keeping existing global pass and cleanup checks.
- [x] Run the complete focused Python suite and C# self-test; inspect outputs. Fresh whole-branch review before normal protected integration.
- [x] Append diagnosis semantics and current evidence; document that this does not improve provider coverage or deploy Azure.

## Integration

- [ ] Six scoped files including this plan; owner Verified commits, current-base seven publisher-bound required checks, all CodeQL configurations plus aggregate success, zero unresolved threads.
- [ ] Record the Microsoft-first cloud direction separately in issue2021: lab now, shared Azure service/catalog later, own index/ranking and local privacy retained. No costs or subscriptions activated.
