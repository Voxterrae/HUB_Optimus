# Governed schema applicator

## Bound state

- authorized base commit: `fc5939fe46152464378f4f09ae02824954970d83`;
- contract SHA-256: `912e762601fb3265627787dd57fb1f248929492a6bca3ba5c3d2cec5afe09e70`;
- schema plan SHA-256: `fd6751ff5fe42b0336bb3bc5b7da1d3854b78ec733afb76fc72a7f842005a981`;
- baseline B0 SHA-256: `3f141153424f178fae8007d0ac829932b8fff5ddecf21264c6c6b08714b0100b`.

## Apply order

1. six global choices;
2. five organization-owned table roots;
3. fifty scalar columns;
4. five alternate keys, waiting for Active;
5. four one-to-many relationships and their lookup columns;
6. one `PublishAllXml`;
7. exact verification and zero-row gate.

## Membership

A subcomponent is accepted only when it is either a direct solution component
or included through an exact target table root with
`RootComponentBehavior=0`. Missing direct membership plus missing qualifying
root membership is classified as orphan metadata and fails closed.

## Rollback

Rollback is reverse journal order, exact-journal-bound, zero-row-gated, one
publication maximum, no retry, and no automatic rollback.

## Global-choice metadata lookup

Dataverse does not support `$filter` on the `GlobalOptionSetDefinitions`
collection. The applicator retrieves a global choice through its metadata
alternate key instead:

```text
GlobalOptionSetDefinitions(Name='<escaped-name>')
```

Single quotes inside the OData string literal are doubled. A `404` is treated
as an absent choice during idempotent discovery; other HTTP failures, including
`405`, fail closed. After a successful `POST`, the applicator waits for the
created choice to become visible through the same alternate-key path before
recording its metadata ID. Rollback remains bound to the exact metadata-ID
delete path stored in the journal.

## Sanitized prewrite finding

The governed LCDH-OS DEV run `20260821T113235Z` stopped before the first
metadata write because the previous implementation used an unsupported
collection `$filter` for `GlobalOptionSetDefinitions`. The private result is
classified as `FAILED_PREWRITE_UNSUPPORTED_GLOBAL_OPTIONSET_FILTER`: zero
created components, zero reused components, final direct component count zero,
zero rows, zero publications, no rollback required, and the consumed
authorization is not reusable. No private tenant identifiers or evidence paths
are stored in this repository.
