# GitHub Wiki source

This directory is the reviewed source for the HUB_Optimus GitHub Wiki. The Wiki
is a navigation layer, not an independent source of truth.

## Publishing contract

- Review changes here through the normal pull-request workflow.
- Enable the repository Wiki only with **Restrict editing to collaborators only**
  selected. Direct edits in the published Wiki are not an authoring path; make
  every durable change here first and review it in a pull request.
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

## One-way publication procedure

Publish from a clean, reviewed `main` checkout. The following procedure mirrors
only `docs/wiki/*.md` into a disposable clone of the Wiki repository; never run
the removal step in the source repository or an unverified directory.

```bash
repo_root="$(git rev-parse --show-toplevel)"
test -z "$(git -C "$repo_root" status --porcelain)"
source_sha="$(git -C "$repo_root" rev-parse HEAD)"
wiki_parent="$(mktemp -d)"
wiki_checkout="$wiki_parent/HUB_Optimus.wiki"
git clone git@github.com:Voxterrae/HUB_Optimus.wiki.git "$wiki_checkout"
test "$(git -C "$wiki_checkout" remote get-url origin)" = \
  "git@github.com:Voxterrae/HUB_Optimus.wiki.git"
git -C "$wiki_checkout" rm -f --ignore-unmatch -- '*.md'
cp "$repo_root"/docs/wiki/*.md "$wiki_checkout"/
git -C "$wiki_checkout" add -- '*.md'
git -C "$wiki_checkout" diff --cached --check
git -C "$wiki_checkout" diff --cached --name-status
git -C "$wiki_checkout" commit -m "docs(wiki): sync from main $source_sha"
git -C "$wiki_checkout" push origin HEAD
```

Before pushing, a reviewer must confirm that the staged paths are only the
expected root-level Markdown pages. After pushing, fetch the Wiki again and
compare the source and published file sets and hashes:

```bash
git -C "$wiki_checkout" fetch origin
git -C "$wiki_checkout" reset --hard '@{upstream}'
(cd "$repo_root/docs/wiki" && sha256sum -- *.md | sort) > "$wiki_parent/source.sha256"
(cd "$wiki_checkout" && sha256sum -- *.md | sort) > "$wiki_parent/published.sha256"
diff -u "$wiki_parent/source.sha256" "$wiki_parent/published.sha256"
```

The final `diff` must be empty. If it is not, stop publication and reconcile the
drift through a new source pull request; do not repair the Wiki directly.
