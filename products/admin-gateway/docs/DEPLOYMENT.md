# Deployment sequence

1. Create a non-production Power Platform environment.
2. Create a custom publisher and unmanaged Dataverse solution.
3. Deploy the Dataverse tables from the tenant-neutral schema.
4. Create the Entra application, bind the exact tenant ID and audience, and define separate `Optimus.Reader` and `Optimus.Mutator` roles.
5. Create Key Vault and upload only certificates/secrets required by the tenant.
6. Create the Azure Automation account and PowerShell 7.4 runtime.
7. Import the allowlisted runbooks and pin the ExchangeOnlineManagement module.
8. Deploy the API behind EasyAuth with authentication required, a tenant-specific issuer, an allowed-audience list, `401` for unauthenticated API calls and no direct backend bypass. Map the same tenant to `OPTIMUS_ENTRA_TENANT_ID`, set a reviewed `OPTIMUS_APPROVAL_MAX_AGE_SECONDS` from 1 to 86400 (900 seconds by default), synchronize the gateway and approval-service clocks, and exclude only the data-free `/healthz` probe.
9. Import the custom connector, replace its tenant, application and host placeholders, and verify that neither OAuth endpoint uses `/common`.
10. Import or build the approval flow using the supplied blueprint. Capture `approved_at` from the UTC approval-decision time, sign the complete receipt material and dispatch immediately rather than treating queue time as fresh authorization.
11. Create Copilot Studio agents and add only the intended connector actions.
12. Validate the private tenant overlay, including tenant ID, allowed audiences and both application-role names, then publish it to the client control area.
13. Run read-only acceptance tests.
14. Verify that a current approval is accepted through the configured freshness boundary and that a stale approval is rejected, then run a DryRun mutation acceptance test.
15. Execute the first real mutation only after explicit owner approval.

Deployment remains blocked while a placeholder survives, the connector and EasyAuth bindings disagree, or the backend is reachable without the EasyAuth trust boundary.
