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
- POST /intake/url
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

The EC2 release environment is installed from separate runtime and validation
locks under `ops/ec2`. Both contain exact versions and reviewed wheel hashes for
the Linux x86_64 CPython 3.12 deployment ABI. Deployment rejects ambient
`PIP_*` settings, removes the former pip self-upgrade, uses only the fixed
PyPI simple index with `--require-hashes --no-deps --only-binary`, and runs
`pip check`. It then removes the bootstrap installer and requires the installed
name/version inventory and the virtual-environment base interpreter to match
the reviewed locks exactly, both before and after validation. Pip consumes a
single sealed Linux `memfd` assembled from the same no-follow lock snapshot that
produces the evidence digest; path identity tokens also reject temporary atomic
replacement followed by restoration. The combined lock digest is checked again
after validation and recorded with the selected tier and lock path in
`RELEASE_STATE`. The root requirement files remain the portable authoring tiers;
they are not the EC2 deployment lock.

The release state also records the SHA-256 of the selected `hub-api.sh`
launcher, the reviewed source-tree digest, and the complete venv-manifest
digest. Before changing operational state, deployment validates that the
current release is a managed, usable rollback target whose HEAD, source bytes,
and venv still match that state, then stages all replacement artifacts. If any
later step fails, an exit handler restores the exact previous
`current` symlink, shared launcher, shared release state, current-release
marker, previous-release pointer, and any transactionally completed legacy
release state. The failed candidate retains its validation log,
`pre-deploy-state` snapshot, and `recovery.log`; recovery does not depend on an
external or temporary checkout. Restoration is attempted even when the
recovery log cannot be opened or written; that condition is reported as a
failed recovery outcome rather than a false success.

The script fixes and records the selected source revision; it does not itself
prove that a commit or tag was reviewed or signed. GitHub review records and the
human deploy decision remain the authority for that claim.

Before switching, deployment preserves provenance for the current release.
`rollback-current` rejects duplicate target-state identity keys and verifies
the recorded commit, path, release, launcher hash, source tree, and venv for
both the current release and rollback target. It repeats mutable HEAD, source,
and venv checks immediately before mutation, then snapshots and stages its own
complete transition. Any injected or ordinary failure after rollback
mutation begins restores the exact pre-rollback symlink, launcher, release
state, rollback state, current marker, and prior transition marker. A successful
rollback publishes a separate `ROLLBACK_STATE`. Deploy and rollback share a
non-blocking host lock so they cannot mutate release state concurrently.

Neither operation silently restarts the running API service. After a deploy or
rollback, an operator must review the recorded state and explicitly restart the
service when the process should load the restored launcher.

The API launcher, core launcher, and systemd unit disable Python bytecode writes
inside a release. `hub-core test` also disables pytest's cache provider, so
normal `analyze` and test operations do not invalidate source authority.

At launcher start, the API captures the full commit of the resolved running
release and the SHA-256 of the launcher that started it. `/status` reports those
immutable process-bound values as `running_release`, `running_commit`, and
`running_launcher_sha256`. It reports the mutable symlink separately as
`configured_current_release` and `configured_current_commit`. Moving `current`
without restarting therefore cannot make an old process claim the new running
identity.

## Issue #1831 host safeguards

[`adopt-legacy-current.sh`](adopt-legacy-current.sh) is the one-time,
idempotent migration boundary for the confirmed pre-#1832 current release. It
requires the operator to supply that checkout's full commit SHA, then validates
the managed symlink, exact repository origin, clean checkout, marker, and
byte-identical versioned/shared launcher. It does not trust the legacy short
commit or validation-count claim as authority. The original six-field state is
retained byte-for-byte as mode-`0400` `LEGACY_RELEASE_STATE`; its SHA-256 and
short prefix are linked from the new full-SHA state. The v2 adoption state also
records source-tree and venv authority captured with reviewed helpers. HEAD,
source, and venv are checked at baseline, immediately before mutation, and
after publication. The shared/per-release states are postvalidated before
success. Any post-mutation failure restores the exact snapshot, and an exact
completed adoption can be rerun without change.

[`preflight-deploy.sh`](preflight-deploy.sh) is the read-only, fail-closed host
gate for the exact-SHA localhost intake operation. It checks rollback release
identity and launcher provenance, requires the shared launcher and shared
release state to match the configured current release exactly, checks
non-interactive sudo, required tooling, GitHub/reference-URL egress, and
explicit t3.small resource floors before a deploy is attempted. A historical
`previous_release` without per-release state is inventoried as unattested but
is not trusted as the next deployment's rollback target; the fully adopted
current release becomes that target when the deploy switches.

[`intake-smoke-evidence.py`](intake-smoke-evidence.py) renders only the reviewed
evidence allowlist from a retained localhost response. It never reproduces the
fetched text or passes through unknown response fields, and success requires
both curl transport success and HTTP 200. The complete repinning, attestation,
and failure boundary is documented in
[`ISSUE_1831_RUNBOOK.md`](ISSUE_1831_RUNBOOK.md). That template requires a new
exact merged SHA before host execution and does not itself authorize a deploy.

## Controlled URL intake network boundary

The repository launcher source also defines `POST /intake/url`. This records the
reviewed code boundary; it is not evidence that any particular host or public
endpoint is currently deployed.

The versioned application request/success/error payload contract is
[`controlled_url_intake.v1.schema.json`](controlled_url_intake.v1.schema.json).
The endpoint accepts `{"url": "..."}` as its only meaningful application field
and returns the schema's flat `status=ok` or `status=error` shape. HTTP framing
and malformed-body errors occur before that application contract. Executable
tests bind the schema to the launcher constants and the Operator request.

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

```bash
find ops/ec2 -maxdepth 1 -type f -name '*.sh' \
  ! -name 'hub-ops.sh' -exec bash -n '{}' +
python3 -m py_compile ops/ec2/hub-ops.sh ops/ec2/*.py
```

Runtime validation on EC2:

hub-product
hub-api-control status
curl -sS http://127.0.0.1:8080/health

Repository regression coverage:

```bash
python -m pytest -q \
  tests/test_ec2_run_identity_and_provenance.py \
  tests/test_ec2_deploy_hub_api_sync.py \
  tests/test_ec2_legacy_adoption.py \
  tests/test_ec2_preflight_and_evidence.py \
  tests/test_ec2_runbook_attestation.py
```
