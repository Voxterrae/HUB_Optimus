# Product and client boundary

## Correct separation

```text
HUB_Optimus
  └── Optimus Admin Gateway (commercial product module)
        ├── generic API and validation
        ├── generic runbooks
        ├── operation catalog
        ├── connector and agent templates
        └── deployable package

Client deployment
  └── Customer operating environment
        ├── tenant-specific identities
        ├── mailbox targets
        ├── approval owners
        ├── Power Platform connection references
        ├── Dataverse rows and audit events
        ├── SharePoint evidence
        └── pilot acceptance records
```

A customer operating environment is not the parent platform. It consumes Optimus modules through a private tenant overlay.

## Public repository rule

The public product repository may contain:

- generic source code;
- schemas and templates;
- placeholder domains and identifiers;
- synthetic test data;
- security and deployment documentation.

It must not contain:

- real tenant, organization, environment or object identifiers;
- mailbox addresses;
- application IDs, secrets, certificates or thumbprints;
- SharePoint URLs or document paths containing customer data;
- real approval receipts or execution output;
- customer accounting or personnel material.

## Tenant overlay

A tenant overlay is a private JSON document conforming to
`deployment/sharepoint/tenant-overlay.schema.json`. It binds the product to one
customer without forking product code.
