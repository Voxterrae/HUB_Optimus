# Azure deployment template boundary

This directory intentionally contains parameters and sequencing rather than a live tenant deployment. Resource IDs, domains, application IDs, certificates and connection strings belong in the private tenant overlay or deployment pipeline secret store.

PowerShell 7.4 is the target Azure Automation runtime. Pin the ExchangeOnlineManagement module to a version tested in the tenant before publishing runbooks.

Before exposing the API, replace every tenant and audience placeholder and map the tenant to the API's `OPTIMUS_ENTRA_TENANT_ID` application setting. EasyAuth must require authentication, return `401` for unauthenticated API calls, use the tenant-specific issuer, allow only the bound API audiences and prevent direct network access that bypasses EasyAuth. `/healthz` is the only public excluded path and must return no identity or tenant data. `/common` is not an accepted production issuer for this single-tenant deployment.
