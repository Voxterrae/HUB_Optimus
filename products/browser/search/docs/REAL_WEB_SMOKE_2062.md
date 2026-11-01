# Isolated real-Web acceptance proposal — issue2062

This manual QA tool tests two fixed public queries through the real product
client and an operator-owned temporary SearXNG process. It does not configure
the application, change ranking, or deploy a persistent/public service.
Authority and scope: [issue2062](https://github.com/Voxterrae/HUB_Optimus/issues/2062).
The separate ranking correction remains under issue2061.

## Plan and trust boundaries

1. An owner-only `workflow_dispatch` on protected main checks repository name,
   immutable repository/user IDs, owner login and public visibility. The standard
   Ubuntu24.04 job has `contents:read` and a 15-minute limit. Its sole input is a
   complete lowercase 40-hex product SHA that only confirms the literal reviewed
   source pin. Every other commit, even a well-formed SHA, is rejected before
   checkout. Executable source is never selected by a dispatch input.
2. Check out the harness at `github.workflow_sha`, the product at the literal reviewed SHA,
   and official SearXNG at `8b35dcd2e312d1d30fcfcbf6a9d01bda6fc52192`
   separately. Build the host from the product and the probe against the product's
   public Core project through mandatory `OptimusProductRoot`. Both builds carry
   the product SourceRevisionId; the probe checks its own, Core and host versions.
3. Install upstream `requirements.txt` in a temporary venv with no pip cache.
   Record the requirements blob/hash, direct pins, installed package versions and
   pip install report hash. Direct requirements are pinned; transitive resolution,
   runner image and package availability are not hermetically locked. Do not infer
   source provenance from SearXNG's version Git URL, which can reflect Actions env.
4. Generate a private temporary config, an ephemeral unprinted server secret and
   temporary cache directory. Start `python -m searx.webapp` bound only to
   `127.0.0.1:18888`, with JSON, only Mwmbl enabled, no autocomplete/plugins/metrics,
   no Valkey/Redis, no image proxy, timeout8s and configured retries0. Readiness
   polls only `/healthz`, requires its exact `OK` body and rejects redirects;
   it never sends a search before the probe.
5. The .NET probe owns the real SearchHost at `https://127.0.0.1:17831` with a new
   token/profile and `--owner-stdin true`. Health checks use public
   LocalSearchTransport TLS/HMAC plus the nonce proof. Two typed
   OptimusSearchService Web calls use empty bookmarks, no raw search prefetch and
   no fallback. The typed client checks the Optimus v1/scope protocol; no second
   raw request is issued to capture HTTP metadata. Successful source/domain/topic
   checks on this configured real backend establish the narrow acceptance.
6. Preserve the venv interpreter path without resolving its symlink, so the
   upstream sees the installed environment. SIGINT/SIGTERM of the Python supervisor
   cancel and join the exact probe before stopping the temporary upstream.
   Close the exact owned host's stdin and require normal exit0 and profile removal.
   Terminate/wait for only the exact temporary SearXNG process. A forced cleanup,
   nonzero host exit, missing evidence or timeout cannot produce green. Reports
   contain allowlisted stages, booleans, official result domains and provenance;
   no raw host/upstream logs, tokens, result text, query logs or screenshots.

| Fixed logical query | Required destination | Required title topic |
|---|---|---|
| `Python programming` | `python.org` including proper subdomains such as `docs.python.org` | Python |
| `Mozilla Firefox` | `mozilla.org` or `firefox.com`, including proper subdomains | Firefox |

Destinations must be HTTPS with the default port, without credentials, query or
fragment. Each accepted result must have source `SearXNG`. HTTP200 alone, empty
results, irrelevant results, reported engine failures, rate limits and challenges
remain blocked. The second logical query follows a two-second pause and is not
sent if the first fails. There are no automatic logical resubmissions or provider
fallbacks. Unmodified upstream curl networking may internally reconnect after a
connection error even with configured retries0; this is not a guarantee of exactly
two TCP attempts. Mwmbl's ordinary adapter uses `/api/v1/search/`, not authenticated
supersearch. No account, API key, IP rotation or challenge bypass is introduced.

## Local verification and execution status

Local tests use synthetic loopback fixtures only. They cover full-SHA rejection,
workflow authorization, isolated config/environment, exact-PID cleanup, forced
cleanup failure, report sanitization and missing/irrelevant evidence. The source
guard regression first failed seven negative cases, then passed after validation.
The probe's self-tests cover protocol/domain/topic rejection, and its local
integration verifies component provenance and exercises the real host and typed
TLS client with a synthetic upstream. Those results are not real Mwmbl or SearXNG
relevance evidence.

Observed locally: 44 Python checks, 26 probe self-tests and six real-host synthetic
scenarios passed. The latter cover a relevant positive pair, deceptive domain,
empty results, unresponsive engine, HTTP429 and SIGTERM cancellation. Rejected
first results prevent the second logical query; all six confirmed normal owned
host exit0 and profile removal. Probe and host builds produced no warnings.
The readiness redirect regression first reached another synthetic loopback
endpoint and incorrectly accepted it; after the fix it fails closed with zero
contacts to that redirect target.

Fresh review exposed two startup/lifecycle defects before integration. A real
symlinked-venv regression first failed, then passed after preserving the
interpreter path. Sending SIGINT or SIGTERM to the actual wrapper first left its
children alive; both cases now verify probe shutdown before upstream shutdown
and a blocked cancellation report. These three regressions are included in the
initial41 Python checks. CodeQL then exposed the untrusted-source/main-cache
boundary: syntax validation did not authorize a commit. Three new regressions
first failed, then passed after both manual workflows pinned checkout and build
identity literally and treated the input only as confirmation. The final44
checks include an actual Bash rejection of a different valid40-hex SHA and
literal-source invariants for both workflows. New candidates require another
protected pin update; owner/main/public and other existing guards remain. Finer allowlisted preflight stage names remain a minor
diagnostic follow-up; generic execution-blocked still fails closed.

No local upstream installation or external search is part of this preparation.
Independent review, current required CI, protected integration and an exact-SHA
cloud execution remain separate steps. Both manual test workflows default to the native-accepted product
`0790e0977c170ff8507bb73e0ec7b6e166755892` (Windows run41359258852:182/182,
packaged service/GUI, normal cleanup). Both workflows now fix that source literally in checkout and build metadata;
the confirmation input cannot select another commit. All existing authorization,
runner, permission, timeout and profile safeguards remain. The six local
synthetic host scenarios above used historical product `cfaadf3c5267d046bb3c4a105e6ec0f8a7d7a907`;
they do not validate the new product or establish real-Web relevance.

## First cloud execution and diagnostic correction

PR2068 integrated the reviewed preparation as protected main
`3652228c1cbbc2155bc44ba5280a396ab71312f6`, with the same full tree as
reviewed head `27d70040dc334dbc0279b581c14476044c498355`. Its final CI observed
2654 passed tests and1661 passed subtests, seven required publisher-bound
checks, six CodeQL analyses and aggregate CodeQL success, with no open threads.

The first real run [41362456275](https://github.com/Voxterrae/HUB_Optimus/actions/runs/41362456275)
attempt1 checked out the exact workflow, product0790 and SearXNG8b35 sources,
verified SDK10.0.403, prepared dependencies, built both binaries and passed26
probe self-tests. Execution exited2. The Actions Bash invocation includes `-e`;
`set -uo pipefail` did not disable it, so the shell exited before publishing the
redirected curated JSON. This run does not establish which internal stage failed,
whether either search query was sent, or whether owned cleanup completed.
Do not attribute that result to a provider denial or present it as Web acceptance.

The diagnostic correction captures the Python exit code through an explicit OR
list, publishes its existing curated report and summary, then returns the same
code. A test using the actual Actions Bash `-e -o pipefail` invocation first failed
to publish a blocked fixture, then passed while retaining exit2. A closed
`qa_mode` choice now defaults to `startup-only`; unknown values fail before any
checkout. This diagnostic starts only SearXNG, polls the fixed query-free health
endpoint, stops its exact process and reports `startup-ready`, never Web `passed`.
It does not start the product/probe or issue a search. The separate `queries` mode
retains the two original fixed queries and all relevance and cleanup gates.
Internal fixed stage names, upstream readiness/exit code and whether the query
probe was attempted distinguish startup failure from later probe failure without
printing upstream logs or private values. Cleanup failure retains the primary
failure stage when one already exists. The final local suite passes53 checks,
including query-free healthy startup, early upstream exit3, actual shell report
publication for exit0/2, and mode rejection. External diagnosis remains a separate
protected-main execution; the initial failure is not silently retried.

## Limits

No cache/artifact upload, secrets import, personal profile, paid provisioning,
subscription, DNS or public endpoint is used. A disposable runner success would
accept only these two queries at that time. It would not establish general-Web
coverage, production availability, family-safe search, language/region guarantees,
physical Windows10/11, GUI/accessibility, code signing or distribution. Mwmbl
standard results may include Wikipedia and previously suggested documents; do not
describe them as exclusively its own crawled index. Shared runner IP quotas can
block this test; stop on that outcome rather than rotate identity or retry it.

Official recipe references:
[SearXNG source](https://github.com/searxng/searxng/tree/8b35dcd2e312d1d30fcfcbf6a9d01bda6fc52192),
[Mwmbl adapter](https://github.com/searxng/searxng/blob/8b35dcd2e312d1d30fcfcbf6a9d01bda6fc52192/searx/engines/mwmbl.py),
[Mwmbl API](https://developer.mwmbl.org/).
