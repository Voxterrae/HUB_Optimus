# Deployment sequence

1. Create a non-production Power Platform environment.
2. Create a custom publisher and unmanaged Dataverse solution.
3. Deploy the Dataverse tables from the tenant-neutral schema.
4. Create the Entra application and least-privilege roles.
5. Create Key Vault and upload only certificates/secrets required by the tenant.
6. Create the Azure Automation account and PowerShell 7.4 runtime.
7. Import the allowlisted runbooks and pin the ExchangeOnlineManagement module.
8. Deploy the API behind Entra authentication.
9. Import the custom connector and bind its OAuth settings.
10. Import or build the approval flow using the supplied blueprint.
11. Create Copilot Studio agents and add only the intended connector actions.
12. Publish the private tenant overlay to the client control area.
13. Run read-only acceptance tests.
14. Run a DryRun mutation acceptance test.
15. Execute the first real mutation only after explicit owner approval.
