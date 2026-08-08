# Azure deployment template boundary

This directory intentionally contains parameters and sequencing rather than a live tenant deployment. Resource IDs, domains, application IDs, certificates and connection strings belong in the private tenant overlay or deployment pipeline secret store.

PowerShell 7.4 is the target Azure Automation runtime. Pin the ExchangeOnlineManagement module to a version tested in the tenant before publishing runbooks.
