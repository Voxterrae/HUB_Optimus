# Canary OIDC role boundary

These policies are review inputs, not an automatic IAM deployment. They pin the
three GitHub Environments used by the canary to three non-interchangeable roles:

| Environment | Role | Only mutation allowed |
| --- | --- | --- |
| `operator-private-canary-prepare` | `HUBOptimusOperatorPrepare` | upload one CDK asset and create a CloudFormation change set |
| `operator-private-canary-execute` | `HUBOptimusOperatorExecute` | execute an already prepared `operator-*` change set |
| `operator-private-canary-stop` | `HUBOptimusOperatorStop` | set concurrency to zero on one fixed Lambda |

The Prepare policy explicitly denies `ExecuteChangeSet`; the Execute policy
explicitly denies creating change sets or direct stack updates. Neither role may
assume the bootstrap deploy, lookup, image-publishing, or CloudFormation execution
roles. Prepare may assume only the exact bootstrap file-publishing role for the
single content-addressed Lambda asset and may pass only the fixed CloudFormation
execution role to the CloudFormation service.
The 15-minute file-publishing session carries an inline session policy that
intersects the bootstrap role down to bucket-versioning read, one exact
content-addressed object, and only the KMS data-key operations needed by that
object. It cannot list or delete bootstrap assets.

Before enabling a workflow, verify read-only that:

1. the GitHub OIDC provider is exactly
   `token.actions.githubusercontent.com` with audience `sts.amazonaws.com`;
2. each trust policy uses the exact Environment `sub` shown here;
3. the attached permissions match these files byte-for-byte;
4. the bootstrap CloudFormation execution role trusts only CloudFormation, not
   GitHub or either OIDC role;
5. the bootstrap asset bucket has versioning enabled and its file-publishing role
   can upload and read only the expected content-addressed object versions;
6. the stop Environment is limited to `main` and has no economic or deployment
   gate that could delay an emergency stop;
7. `HUBOptimusOperatorStop` has `MaxSessionDuration` of at least 10,800 seconds,
   matching the protected stop and containment workflows' three-hour session.

No permanent AWS access key is used or stored.
