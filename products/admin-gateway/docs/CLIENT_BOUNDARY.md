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

The deployment slice is planned to introduce a private tenant-overlay JSON
contract at `deployment/sharepoint/tenant-overlay.schema.json`; that schema is
not included in this foundation checkout. The intended overlay binds the
product to one customer without forking product code.
