# AWS Dev Runtime

## Status

Development-runtime setup guide for running HUB_Optimus Semantic Engine CLI on an AWS EC2 instance.

This is not production deployment. It does not implement HERMES, API, S3 persistence, vector search, workers, dashboards, or model-based judging.

## Purpose

The AWS Dev Runtime is the external execution container for the current Semantic Engine CLI.

It exists to run the same contract-first command already validated locally:

```bash
python -m semantic_engine.cli analyze inputs/case.json --output outputs/analysis_result.json
```

AWS does not define semantic authority. GitHub remains the source of truth.

## Recommended instance shape

Start simple:

```text
OS: Ubuntu LTS with Python >= 3.11 available
CPU/RAM: development-sized EC2 instance
Disk: enough for repo, inputs, outputs, logs, and future artifacts
Access: SSH with key pair
Inbound: SSH only at first
```

Do not expose HTTP ports until API or HERMES exist.

## Runtime layout

Recommended path:

```text
/opt/hub-optimus/
  repo/
  inputs/
  outputs/
  logs/
  runs/
```

Meaning:

- `repo/` contains the cloned `Voxterrae/HUB_Optimus` repository.
- `inputs/` contains case input JSON files copied or generated for runtime tests.
- `outputs/` contains CLI output JSON files.
- `logs/` contains manual or scripted runtime logs.
- `runs/` is reserved for the later archive-layout hito.

## Bootstrap

After provisioning the EC2 instance and connecting through SSH, run:

```bash
sudo bash scripts/infra/bootstrap_aws_dev_runtime.sh
```

The script installs the minimum system packages, verifies Python `>=3.11`, creates `/opt/hub-optimus`, clones the repo if missing, creates a virtual environment, installs dependencies from `requirements-dev.txt`, and runs a CLI smoke test.

The script must be launched with `sudo` because it installs packages and prepares `/opt/hub-optimus`. After root-only setup is done, repository operations, Python dependency installation, and CLI execution run as the invoking non-root user.

## Smoke test

Expected command:

```bash
cd /opt/hub-optimus/repo
python -m semantic_engine.cli analyze examples/semantic_engine/case_minimal.json \
  --output /opt/hub-optimus/outputs/analysis_result.json
```

Expected result:

- exit code `0`;
- stdout empty because `--output` is used;
- `/opt/hub-optimus/outputs/analysis_result.json` exists;
- output JSON contains `case_id`, `core_version_ref`, `input_summary`, and draft decomposition fields.

## Out of scope

- HERMES PWA
- API
- S3 sync or bucket creation
- AWS IAM automation
- public HTTP exposure
- reverse proxy
- TLS
- systemd services
- workers or queues
- vector DB
- scoring
- normalizers/evaluators beyond current CLI validation

## Gate to next hito

Move to S3/archive work only when:

- AWS instance can run the CLI smoke command;
- local output file is created successfully;
- runtime folders exist;
- no secrets are committed to the repo;
- no public service is exposed unnecessarily.
