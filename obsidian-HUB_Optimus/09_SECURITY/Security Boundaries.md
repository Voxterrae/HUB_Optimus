---
type: "security"
status: "partial"
evidence: "CONFIRMED"
analysis_commit: "30e985226347b4bc59b0e187b96633a09647ca42"
tags:
  - "security"
  - "boundaries"
  - "risk"
---

# Security Boundaries

## Governance Security

- Owner identity and authority are explicit.
- Every path requires owner review.
- AI/contributors cannot self-ratify or merge protected work.
- Source of truth and history verification prevent ambiguous authorization.

## Input Security

### Scenario and Semantic JSON

- strict UTF-8/JSON;
- non-standard numeric constants rejected;
- unknown fields rejected;
- identity/reference invariants;
- controlled error output.

### Controlled URL Intake

- HTTP(S) only, default ports;
- no credentials in URL;
- public IP validation for each redirect;
- pinned numeric connection;
- proxies disabled;
- timeout, redirects, bytes and extracted text capped;
- no cookies/auth/browser automation;
- content remains unreviewed.

Residuals: resolver, routing, NAT, firewall, remote content and host configuration remain external.

## Service Security

- API binds `127.0.0.1:8080`.
- No authentication is implemented.
- Nginx source allowlists only `/health` and `/intake/url`.
- CORS/rate limiting do not replace authentication.
- `/status` and `/analyze` must remain non-public under current design.

## Data Security

- hub-core uses `umask 077`.
- API temp input is mode `0600` and deleted.
- Operator learning data is local IndexedDB, not managed secure storage.
- No secrets are copied into this model.

## Supply Chain

- Actions are pinned by SHA.
- Python dependencies have bounded major versions.
- No new frontend dependency is required for the explorer.

## Highest Priority Risks

Véase [[Risk Register]].

## Related

- [[Limitations]]
- [[Infrastructure Boundary]]
- [[Controlled URL Intake]]
- [[Local HTTP API]]
