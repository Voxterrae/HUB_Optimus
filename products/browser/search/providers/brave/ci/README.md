# Brave offline CI candidate

This directory contains the template for `.github/workflows/brave-offline.yml`,
registered under governance issue #2118. The protected integration candidate
reconstructs design #2109, inactive adapter #2111 and CI #2119 directly on main,
without inheriting their unsigned proposal commits. Registration in a candidate
does not by itself prove protected-main integration.
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

The working-session approval and reconstruction scope are recorded in #2118.
An identical template copy is registered at `.github/workflows/brave-offline.yml`.
The reviewed executable inputs are preserved from #2119 at
`45e5c2534d9ff8b1d84be13567dfdcccc1ac729b`; the fresh integration commit is based
directly on protected main. No old branch is force-pushed and no signature is
retroactively attributed to an unsigned proposal.

Historical [run 42423601228](https://github.com/Voxterrae/HUB_Optimus/actions/runs/42423601228)
passed on that #2119 head: SDK 10.0.403, verified archive hash, successful
loopback-only namespace, zero NuGet packages/sources, zero build warnings/errors,
and 59/59 console tests. This establishes the earlier candidate only. The new
protected candidate must repeat hosted validation on its own exact SHA; no
skipped/missing/neutral result substitutes for the console suite or main gates.

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

The original #2111 commit remains unsigned. Its historical stacked checks do not
establish protected-main readiness. The reconstruction carries the design and
adapter together to preserve their dependency, while leaving the five C#/project
files unchanged. Require fresh validation after every source, base or harness
change. GitHub server signing is not an enrolled hardware-key attestation.
Do not add this check to the required-check ruleset without a reviewed decision.

## Handoff

This scoped README carries the technical handoff. Protected
`docs/context/AI_HANDOFF.md` is unchanged because this is a scoped inactive-adapter
and CI integration candidate; authority controls are unchanged and no live
provider is enabled.
`docs/context/OWNER_AUTHORITY_HANDOFF.md` remains the controlling governance
handoff. Hosted results must be recorded separately after approved activation.
