# Optimus Admin Gateway architecture

```text
Copilot Studio / Teams / mobile / Power App
                    |
                    v
Power Platform custom connector (OAuth 2.0 / Entra ID)
                    |
                    v
Optimus Admin Gateway API
  - principal and role boundary
  - allowlisted operation catalog
  - typed parameter validation
  - deterministic plan hash
  - DryRun default
  - approval receipt validation
  - idempotency and audit envelope
                    |
          +---------+---------+
          |                   |
          v                   v
Exchange Online         Approved PowerShell 7
API / PowerShell         Azure Automation runbooks
          |                   |
          +---------+---------+
                    v
Dataverse audit, approvals and job state
SharePoint evidence and deployment records
```

## Control planes

1. **Product control plane** — versioned in HUB_Optimus.
2. **Tenant configuration plane** — private client overlay.
3. **Execution plane** — Azure-hosted API and Automation account.
4. **Evidence plane** — Dataverse state plus SharePoint evidence.
5. **Human authority plane** — explicit owner approval for mutation.

## Trust boundaries

- The agent is not an administrator. It can only request catalog operations.
- The connector is not an executor. It transports authenticated requests.
- The API does not accept raw PowerShell.
- The runbook dispatcher accepts only `ValidateSet` operation identifiers.
- A mutation is rejected unless its approval receipt binds to the exact plan hash.
- The deployment executor is disabled until configured by the client tenant.
