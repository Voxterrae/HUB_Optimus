# Authenticated Web gateway (inactive local candidate)

Second increment of the
[hybrid design](../../../../../../docs/superpowers/specs/2026-11-07-search-hybrid-brave-design.md),
tracked in [issue2113](https://github.com/Voxterrae/HUB_Optimus/issues/2113).
See [protocol v1](PROTOCOL.md).

The candidate is a server library with explicit loopback startup and offline
console acceptance. It has no production executable, Azure resource, ingress,
real Brave key, paid request, Windows wiring or runtime/CI registration.
Do not interpret its HTTP fixture as a deployed remote HTTPS gateway.

## Validation

SDK10.0.403, framework-only net10.0, no new packages. From products/browser/search:

```sh
dotnet build providers/brave/gateway/tests/Optimus.Search.Brave.Gateway.Tests -c Release -m:1 -nr:false -p:UseSharedCompilation=false
dotnet run --project providers/brave/gateway/tests/Optimus.Search.Brave.Gateway.Tests -c Release --no-build
dotnet run --project providers/brave/tests/Optimus.Search.Brave.Tests -c Release
```

Fixtures use synthetic tokens and provider results, temporary local files and
owned loopback HTTP sockets. Child processes test exclusive state leasing and
abrupt process death after provider entry; cleanup targets only those children.
No external provider request occurs. Test diagnostics print case names and
exception type only; HTTP hosts clear logging and use Production environment.

Initial compiling stubs failed28/28; implementation passed28/28. Additional
tests reproduced provider-error misclassification and noncooperative timeout
(35/38), then passed38/38 after correction. A further real process-kill test
failed because the original reservation lacked a pending marker; the durable
pending-before-forward change passes the expanded39/39 suite. Release build
has0 warnings/errors. These are local candidate results, not production or
full-repository CI acceptance.

## Guarantees within the candidate

- Hash-only bearer registry with expiry and per-request revocation lookup.
- Strict bounded POST; hostile Origin/Host/method and malformed input do not
  reach the provider or consume budget.
- One active admitted call,100 durable total reservations, no retries/refunds.
- Lifetime exclusive quota lease; pending marker flushed before provider entry.
- Missing/corrupt/uncertain state blocks; restart never silently resets budget.
- Generic JSON errors, no query echo or result persistence, no-store responses.

## Remaining activation work

Production host with reviewed HTTPS ingress, mounted server-only provider key,
operator-owned persistent volume and registry permissions, binding the pilot
ledger to the actual provider/account/key, provider-side spend limits, logging
and platform retention inspection, shutdown/revocation runbook, live relevance,
terms/use rights and exact cost approval. The Windows client needs its own
reviewed HTTPS configuration/credential storage and explicit external-source
notice. The original SearXNG acceptance #2062 and finite-catalog #2098 remain
separate. Commit signatures, applicable checks and human integration gates
remain required; this code enables no external service.

Filesystem state is trusted operator state and can be rolled back by an
administrator/snapshot. One delegate invocation is not a certified billable
transport count. No forensic memory erasure or perfect family protection is
claimed. If state is pending/blocked, investigate; do not reset it to continue
calls under the same purported100-attempt pilot.
