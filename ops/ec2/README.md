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
