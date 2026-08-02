# GitHub Wiki source

This directory is the reviewed source for the HUB_Optimus GitHub Wiki. The Wiki
is a navigation layer, not an independent source of truth.

## Publishing contract

- Review changes here through the normal pull-request workflow.
- Publish only the Markdown files in this directory to
  `Voxterrae/HUB_Optimus.wiki.git`.
- Keep `_Sidebar.md` and `_Footer.md` synchronized with the published pages.
- Every status page must name its observation date and audited repository SHA.
- Immutable specifications should link to a commit-pinned path. Mutable PR,
  Issue, Actions, and deployment state should link to the live GitHub object.
- Never add credentials, tokens, cookies, tenant/client secrets, private keys,
  internal capabilities, or live secret values.

If a Wiki statement conflicts with an applicable contract, `main`, or a live
GitHub object, the narrower authoritative source wins.
