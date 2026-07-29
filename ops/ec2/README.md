# EC2 local backend operations

This directory captures the manually validated EC2 backend v0.1 operational layer for HUB_Optimus.

## Scope

Included:

- release deployment helper
- rollback helper
- local backend command wrappers
- run registry helper
- local API launcher
- local API systemd control wrapper
- systemd unit for the local API

## Non-goals

This does not add:

- public API exposure
- nginx
- DNS/domain configuration
- Elastic IP configuration
- Terraform
- AWS automation
- frontend
- secrets handling

## Current validated shape

The local backend runs as:

- hub-ops: deploy, rollback and validation operations
- hub-core: backend execution commands
- hub-runs: run registry inspection
- hub-product: local product status
- hub-api: localhost API wrapper
- hub-api-control: systemd wrapper
- hub-api.service: local API service

## Local API

The API binds locally only:

127.0.0.1:8080

Validated endpoints:

- GET /health
- GET /status
- POST /analyze

POST /analyze returns direct JSON with:

- status
- run_id
- run_path
- analysis_result

Each request is written to its own mode-`0600` temporary JSON file and removed
after `hub-core` returns. The response uses the run ID emitted by that exact
`hub-core analyze` process; it does not discover or infer the latest run.

Run directories use UTC timestamps for readability plus an exclusive random
suffix, for example `20260729T153012Z.aB3dE9`. `RUN_STATE` records that exact
ID and the full release commit SHA.

## Reviewed deployment and rollback

Deployment has no implicit branch or repository-HEAD default:

```bash
deploy-current <full-commit-sha-or-tag>
# or
hub-ops deploy <full-commit-sha-or-tag>
```

A tag is resolved to its commit before checkout. Every successful release
records the requested ref, its resolved full commit SHA, the exact validation
command, its exit code, its final output line, and its validation log. Failed
validation leaves its candidate release and metadata for inspection but never
switches `current`.

The script fixes and records the selected source revision; it does not itself
prove that a commit or tag was reviewed or signed. GitHub review records and the
human deploy decision remain the authority for that claim.

Before switching, deployment preserves provenance for the current release.
`rollback-current` verifies that the recorded commit still matches the target,
switches explicitly to `previous_release`, restores that release's API launcher
and deployment state, and writes a separate `ROLLBACK_STATE` transition record.
Deploy and rollback share a non-blocking host lock so they cannot mutate release
state concurrently.

Neither operation silently restarts the running API service. After a deploy or
rollback, an operator must review the recorded state and explicitly restart the
service when the process should load the restored launcher.

## Controlled URL intake network boundary

The repository launcher source also defines `POST /intake/url`. This records the
reviewed code boundary; it is not evidence that any particular host or public
endpoint is currently deployed.

For each supplied URL and each permitted redirect hop, the launcher:

- accepts only an absolute ASCII HTTP/HTTPS URI with the matching default port;
- rejects raw spaces, control characters, and Unicode IRIs before DNS; callers
  must use an IDNA A-label (punycode) hostname and submit international
  path/query text as a correctly percent-encoded URI;
- resolves the hostname once and rejects the whole hop if any returned IPv4 or
  IPv6 address is non-global or multicast;
- rejects known IPv6 transition forms when their embedded IPv4 destination is
  non-global, including IPv4-compatible, mapped/translated, 6to4, ISATAP, and
  the `64:ff9b::/96` NAT64 well-known prefix;
- disables environment proxies, opens a family-specific numeric socket without
  a second hostname resolution, and verifies that the connected peer matches
  the validated IP;
- retains the original hostname for the HTTP `Host` header and for HTTPS SNI
  and certificate verification;
- validates every redirect before making the next connection and caps the
  chain at three redirects;
- uses one eight-second monotonic budget across candidate IP connections,
  redirect hops, TLS, headers, and body reading instead of restarting the
  timeout for each operation; the remaining connection budget is divided
  across remaining candidate IPs so one stalled address cannot consume it all;
- fetches no links, embedded resources, or related pages from the returned
  document;
- sends no cookies, credentials, authorization headers, or browser state.

The current launcher is a synchronous Linux `HTTPServer`. From its main thread,
`SIGALRM` enforces the application budget for Python-visible and socket
operations. The budget is checked immediately after the system resolver
returns, but interruption of a blocking libc `getaddrinfo()` call is
best-effort and is not a portable DNS cancellation guarantee. Calling intake
deadline enforcement from another thread returns a controlled service error.

This closes the application-level DNS validation/connection TOCTOU boundary.
It does not make fetched text trustworthy. The initial system resolver remains
a dependency, a globally routed server can still return misleading material,
and infrastructure-specific NAT64 or 6rd prefixes, external routing, NAT,
firewall, resolver, and host configuration remain outside this repository's
proof boundary. Successful output therefore retains the submitted URL,
redirect chain, retrieval metadata, and `verification_status=unreviewed`;
controlled failures retain the submitted URL and the same unreviewed status.

## Installation note

These scripts are documented from a validated EC2 instance. They are not automatically installed by this repository.

Manual installation targets:

- /opt/hub-optimus/shared/bin/
- /etc/systemd/system/hub-api.service

## Validation

Run from the repository root:

bash -n ops/ec2/*.sh

Runtime validation on EC2:

hub-product
hub-api-control status
curl -sS http://127.0.0.1:8080/health

Repository regression coverage:

```bash
python -m pytest -q tests/test_ec2_run_identity_and_provenance.py
```
