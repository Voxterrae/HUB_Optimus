---
type: "infrastructure"
status: "partial"
evidence: "CONFIRMED"
analysis_commit: "30e985226347b4bc59b0e187b96633a09647ca42"
tags:
  - "infrastructure"
  - "boundary"
  - "external-state"
---

# Infrastructure Boundary

## Confirmed Repository Infrastructure Source

- GitHub Actions workflows.
- GitHub Pages upload/deploy workflow.
- Linux/EC2 operational scripts.
- systemd unit and control wrapper.
- Nginx allowlisted proxy configuration.
- preflight, adoption, smoke evidence and runbooks.

## Not Confirmed by the Repository Alone

- Actual EC2 instance, size, IP or health.
- DNS resolution.
- TLS certificate.
- Firewall, NAT, routing and resolver configuration.
- Installed files/service state.
- Current `main` deployment.
- GitHub Pages settings and bytes served.
- Secrets, credentials or cloud permissions.

## Two Delivery Planes

### Static plane

GitHub → Pages workflow → `site/` artifact → browser.

### Managed host plane

Explicit ref → preflight → release directory → `current` symlink → explicit service restart → loopback API; optional Nginx allowlist.

## Infrastructure-as-Code Status

No Terraform/CloudFormation/Bicep deployment is established for the host. Scripts are manual operations with strong provenance, not full environment provisioning.

## Related

- [[Deployment Architecture]]
- [[EC2 Release Operations]]
- [[GitHub Pages Pipeline]]
- [[Security Boundaries]]
