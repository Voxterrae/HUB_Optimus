# Brave offline CI candidate

This directory contains the template for `.github/workflows/brave-offline.yml`,
registered only on the stacked CI candidate under governance issue #2118.
This is not evidence of protected-main integration.
Nothing here connects the adapter to the own index, SearchHost, Windows, Azure
or a remote API. No Brave account, key, service or billing is configured.

## Reproducible boundary

The proposed workflow checks out the harness and the source candidate separately.
It validates a full 40-character SHA and verifies the candidate checkout HEAD.
For pull requests it tests the PR head, not an implicit merge commit. Manual
dispatch can validate the original #2111 candidate
`75e34382ded37d37f52f2970bfa04760badc9ef8`, even though that commit has no CI script.
Both source and harness SHAs are written to the run summary. A manual run is
associated with the dispatch ref; it does not retroactively attach a PR check
to the separately checked-out historical candidate. Use the summary SHA as its
source evidence, and require a PR-triggered check on any final integration head.

GitHub checkout and fixed SDK acquisition are preparatory network operations.
The SDK is the official Linux x64 .NET 10.0.403 archive, checked against its
reviewed SHA512 from [Microsoft release metadata](https://builds.dotnet.microsoft.com/dotnet/release-metadata/10.0/releases.json).
No new action, floating SDK version, installer script or package cache is used.
Ubuntu runner image/system libraries remain managed inputs; this does not claim
a bit-for-bit reproducible operating system or deterministic binary comparison.

Restore, compilation and tests run as the runner user with no new privileges in a new Linux network
namespace, with only loopback up. There is no external interface or route.
Namespace failure fails the job; there is no unisolated fallback. Loopback is
required by the suite's owned-listener HTTP/redirect/proxy checks.

`build-test.sh` clears the inherited environment, uses fresh home/package/cache
directories, clears NuGet sources/fallback folders and disables audit, telemetry,
diagnostics and workload-update notification. It rejects an SDK other than
10.0.403 and any resolved package dependency or feed. The only dependency is the
test project's reference to the adapter library; framework packs come from the
fixed SDK. Build uses `--no-restore`; run uses `--no-build --no-restore`.
The executable console suite's exit status is authoritative, not `dotnet test`
discovery. No continue-on-error, result persistence or provider requests are used.

Direct local reproduction of the core commands, after preparing that SDK:

```sh
bash products/browser/search/providers/brave/ci/build-test.sh \
  "$PWD/products/browser/search/providers/brave" /absolute/sdk/dotnet
```

Direct use does not establish network isolation. Use the workflow's namespace
wrapper on a host that permits it. Never treat a blocked isolation attempt as
offline certification.

## Activation and signature review

Human approval to prepare registration was given in the working session and
recorded in #2118. An identical copy of the template is registered at
`.github/workflows/brave-offline.yml` on the stacked CI branch. Main currently
lacks the adapter; this candidate targets the #2111 branch and does not bypass
the signed-ancestor/main-authority gates. Do not change required checks.
The first hosted run must exercise the namespace boundary and all 59 console
cases on the exact candidate, with no skipped/missing/neutral substitute.

Read current `AGENTS.md`, CODEOWNERS and live protections again. `.github/` is a
protected surface and workflow registration is HIGH risk. The protected change
needs owner-authored, verified commits (including every stacked commit), an
owner-authored issue labelled `governance`, and a PR-body line `Related to #N`
or `Governance issue #N` pointing to that actual issue. Do not invent an issue
number, sign as the owner, or infer a formal GitHub approval from a chat message.

Ruleset 11665521 currently requires verified signatures, linear history,
squash-only merge, resolved discussions and all seven strict contexts:
`founder-authority-bootstrap`, `pytest`, `PowerShell tooling`, `guard`,
`Risk classification`, `lychee` (Actions App 15368), and `founder-authority`
(App 4705710). No bypass is available. Native approval count is zero and native
CODEOWNER review is disabled under the owner-only model; owner authority is
enforced separately. Recheck rules and candidate head immediately before review.

The original #2111 commit is unsigned. Its stacked checks do not establish
protected-main readiness. Preserve #2109 -> #2111 ordering and require a new
validation after any source or harness change. Do not add the new check to the
required-check ruleset without a separately reviewed decision.

## Handoff

This scoped README carries the technical handoff. Protected
`docs/context/AI_HANDOFF.md` is unchanged because this is a scoped stacked CI
candidate; no protected-main integration or authority change has occurred.
`docs/context/OWNER_AUTHORITY_HANDOFF.md` remains the controlling governance
handoff. Hosted results must be recorded separately after approved activation.
