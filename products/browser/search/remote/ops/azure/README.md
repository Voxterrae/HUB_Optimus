# Inert Azure Container Apps proposal

No Azure deployment, public endpoint, provider registration, role assignment,
service activation or image build/push/pull is authorized by these files. They
contain no deployment workflow or Azure action script.

`main.proposal.json` is an ARM resource-group template using the documented
2025-01-01 API. Its `deployEnabled` parameter defaults to `false` and allows only
`false`; **every resource has that condition**. Passing `true` is invalid. A
parameter edit cannot promote it: promotion needs a separately reviewed template
change and operational authorization. Never submit this proposal to an existing
resource group, especially in complete deployment mode: false conditions are not
a stop/decommission mechanism and complete mode can delete existing resources.

| File | Review purpose |
| --- | --- |
| `parameters.draft.json` | False gate, unselected region, draft names and unpullable digest placeholder |
| `promotion-manifest.draft.json` | Missing exact scope, permissions, economics, release, credential and network evidence |
| `Dockerfile` | Separate .NET 10 API; only reviewed source/catalog paths copied; non-root runtime |
| `Dockerfile.dockerignore` | Minimal build-context allowlist; credentials are excluded |
| `validate_proposal.py` | Offline structural checks; no ARM service validation or deployment |

## Proposed boundary and promotion blockers

The only proposed resources are an ACA Consumption environment and container app.
The app uses one active revision, 0.25 vCPU, 0.5 GiB RAM, minimum zero and maximum
one replica per revision. These limits do not promise a global spending cap or
prevent temporary platform maintenance overlap. No ACR, storage, Log Analytics,
Application Insights, diagnostic settings, Dapr, HTTP access-log sink or role
assignment is provisioned. Platform-managed infrastructure and existing
subscription policies must still be inventoried and priced before promotion.

Ingress is **internal to the ACA environment** (`external: false`), with
`allowInsecure: false`, HTTP transport and target port 8080. The ingress edge
requires HTTPS; the edge-to-container hop is private HTTP. This is not an
internet-accessible pilot and does not assert a private VNet environment. Public
HTTPS promotion needs a reviewed ingress change, trusted certificate/hostname
checks, logging/privacy review and real native-client end-to-end acceptance.
TCP probes only test whether the process listens; they do not validate auth or
catalog readiness.

The process receives `OPTIMUS_REMOTE_CONTAINER_HTTP=true` explicitly from the
proposed template and reads
`OPTIMUS_REMOTE_CREDENTIALS_FILE=/run/optimus-remote/credentials.json`. **No
credential volume or secret is supplied. Startup must fail closed without that
external registry.** Promotion must select and validate an ACA secret-volume
mechanism, verify read-only mounting and UID/GID 1654 access, review secret-read
RBAC, and prove expiry/revocation through a complete revision restart. Keep both
bearer secrets and hashed registry contents outside source, image, build arguments,
plain template parameters, logs and command history. Updating an ACA secret alone
does not restart a revision or prove revocation. This draft is deliberately not
deploy-ready.

The environment sets application log destination to `none`. Azure still permits
live log streaming, so the API must not write queries, tokens, credentials or IPs
to stdout/stderr. No claim is made that Azure retains no operational metadata;
review Activity Log, platform telemetry, inherited policy/diagnostic settings and
access/retention permissions before promotion.

Exact tenant, subscription, resource group/disposition, region, deploying
principal and effective scoped permissions are all unset in the manifest. Do not
infer them from a signed-in account. Registration, resource-group creation and
permission grants require separate review when needed. Economics must identify
the billing offer, remaining free grant, credits/expiry, traffic/active-time and
egress assumptions, registry/platform costs, monthly amount, alert owner and stop
trigger. See the [cost worksheet](../../docs/AZURE_COSTS.md). Budget alerts are
**not hard caps**.

## Offline checks

From the repository root:

```sh
python3 products/browser/search/remote/ops/azure/validate_proposal.py
python3 -m unittest discover -s products/browser/search/remote/ops -p 'test_*.py' -v
```

The validator accepts an optional `--parameters PATH` to reject activation
parameters offline. A pass means the proposal remains inert; it does not validate
Azure policy, quota, permissions, pricing, schema service acceptance or runtime
behavior. No Azure CLI is invoked. The Dockerfile build context is
`products/browser/search`. Both base-image defaults are unpullable placeholders;
approved .NET 10 Linux SDK and ASP.NET runtime digests and a verified build are
still required. No image was fetched or built for this proposal.

## Lifecycle after a separately authorized promotion

1. **Deploy:** Complete every manifest gate; review exact scope and effective
   permissions, economics and stop ownership. Produce a separate promotion diff
   covering the immutable release/base-image digests, registry pull path,
   credential mount and chosen HTTPS ingress. Validate that exact promoted
   template and review its what-if in the approved scope before an incremental
   deployment. Check synthetic auth/rejection, catalog hashes, bounds, privacy,
   cold start and HTTPS from the intended client. Invite clients only after
   acceptance; native-client integration is still future work.
2. **Update:** Build and review a new immutable image/catalog digest, retaining
   provenance and the previously accepted digest. Deploy a new single revision,
   verify health/auth/catalog/limits/privacy and record acceptance. Single mode
   and max-one settings do not eliminate brief update/maintenance overlap.
3. **Rollback:** Redeploy the previous accepted digest with its matching catalog
   and reviewed configuration. Revalidate credentials, expiry, hashes and HTTPS.
   Application-scoped secrets are not restored by changing the image digest;
   never restore a revoked credential registry as part of rollback.
4. **Stop:** An idle zero-replica app can restart on traffic. For an operational
   stop, block/disable ingress and explicitly stop/deactivate every serving
   revision using the approved procedure, then verify it is unreachable and has
   no active replicas. Track the remaining environment, registry, egress and
   other resource costs. Merely setting minimum replicas to zero is not shutoff.
5. **Decommission:** After inventory/dependency and ownership review, revoke
   credentials, remove the app and environment and separately remove only owned
   ancillary resources/artifacts. Verify residual managed resources, role grants,
   stored secrets, retention obligations and billing; delete a resource group
   only if it is dedicated and its complete inventory is authorized for removal.

## Primary references checked 2026-11-04

- [ACA containerApps ARM API 2025-01-01](https://learn.microsoft.com/en-us/azure/templates/microsoft.app/2025-01-01/containerapps)
- [ACA managedEnvironments ARM API 2025-01-01](https://learn.microsoft.com/en-us/azure/templates/microsoft.app/2025-01-01/managedenvironments)
- [Ingress configuration and HTTPS target port](https://learn.microsoft.com/en-us/azure/container-apps/ingress-how-to)
- [Scaling and temporary maintenance replicas](https://learn.microsoft.com/en-us/azure/container-apps/scale-app)
- [Log destinations and live streaming](https://learn.microsoft.com/en-us/azure/container-apps/log-options)
- [Application-scoped secrets and restart behavior](https://learn.microsoft.com/en-us/azure/container-apps/manage-secrets)
