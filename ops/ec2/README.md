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
