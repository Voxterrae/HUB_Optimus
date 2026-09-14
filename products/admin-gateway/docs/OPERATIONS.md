# Operation lifecycle

```text
REQUESTED
  -> VALIDATED
  -> PLANNED
  -> APPROVAL_REQUIRED (mutation only)
  -> APPROVED
  -> QUEUED
  -> RUNNING
  -> SUCCEEDED | FAILED | CANCELLED
```

Read operations can pass directly from `PLANNED` to `QUEUED` once the tenant executor is configured. Mutation operations cannot do so without approval.

## Initial catalog

- `exchange.diagnose_mailbox`
- `exchange.get_mailbox_state`
- `exchange.get_mailbox_folder_health`
- `exchange.get_mailbox_permissions`
- `exchange.test_delegated_access`
- `exchange.grant_full_access`
- `exchange.revoke_full_access`
- `exchange.get_shared_mailbox_configuration`
- `exchange.check_forwarding`
- `exchange.verify_recipient_alignment`
- `powershell.get_job_status`
- `powershell.get_job_output`
- `powershell.cancel_job`

The catalog is data, but it is still version-controlled and reviewed. Adding a new operation requires code, tests and a catalog entry; changing the catalog alone cannot create arbitrary execution.
