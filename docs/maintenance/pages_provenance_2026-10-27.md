# Pages source, artifact and served-byte receipt — 2026-10-27 UTC

Tracking: #1743. This is a dated, non-normative maintenance receipt for one
existing Pages deployment. It changes no policy, authority, setting, workflow
or served file and grants no merge or deployment permission.

## Bound source and deployment

- Observation interval: **2026-10-27 15:27:31 UTC to 2026-10-27 15:27:55 UTC**.
- Source: `main@ae16798e440d906c3736929856331e3777c2dbd9`.
- Exact `site/` tree: `67e832e3e6f5e7f0258d5bb58df5383bf8aa7677`.
- [Pages run 40528939132](https://github.com/Voxterrae/HUB_Optimus/actions/runs/40528939132): attempt 1, `push/main`, completed `success`.
- Deployment `7362333529`: latest status `20735765521` was `success` before and after the comparisons.
- [Deployment log](https://github.com/Voxterrae/HUB_Optimus/actions/runs/40528939132/job/122276083034); environment URL: [huboptimus.dev](https://huboptimus.dev/).
- Artifact `github-pages`, ID `12745880389`: `1217195` ZIP bytes.
- API-reported ZIP digest, independently matched after download: `sha256:84b51d778c39f8eed1ba44835087ce82049199ae7ec175d177eba309cb33c3bc`.
- Artifact expiry reported by GitHub: `2026-10-28T15:14:18Z`; the hash inventory below remains a durable observation after expiry.

Current main and the latest Pages deployment ID/source/status were read again
at the end of the observation interval and matched the start. The workflow
uploads `site/` directly; no new workflow or deployment was invoked here.

## Method and result

The exact tracked source set contained **72 regular files, 3,153,469 bytes**.
The downloaded ZIP digest matched its GitHub artifact metadata. Its TAR file
set equalled the tracked source set, with no additional or missing files;
each artifact file was byte-identical to its Git blob.

Credential-free HTTPS GETs used `Accept-Encoding: identity`, refused redirects
and compared response bodies directly with source bytes as well as SHA-256.
All **72/72 listed routes returned HTTP 200 and exact bytes**, with zero
redirects, retries, mismatches or failed requests. Each `index.html` source was
requested through its directory route, as listed below; explicit index-file
aliases were not separately checked. The direct `/404.html` file returned 200;
unknown-route error handling was not tested.

Source/API reads used:

```text
git ls-tree -rz ae16798e440d906c3736929856331e3777c2dbd9 -- site/
git cat-file blob <blob returned by ls-tree>
gh api repos/Voxterrae/HUB_Optimus/actions/runs/40528939132
gh api repos/Voxterrae/HUB_Optimus/actions/artifacts/12745880389
gh api repos/Voxterrae/HUB_Optimus/actions/artifacts/12745880389/zip
gh api repos/Voxterrae/HUB_Optimus/deployments/7362333529/statuses
```

Inventory checksum: SHA-256 of sorted UTF-8/LF rows, with the site/ prefix included in source_path
`source_path<TAB>byte_count<TAB>sha256<LF>`:
`a79390dd7aaa2d45255750874642deb31a9f712c8cd728aa5610c2cde0482019`.

## Complete tracked-file inventory

The byte count and hash in each row matched Git, the artifact and the served
response. HTTPS paths below are relative to `https://huboptimus.dev`.

| Source below `site/` | HTTPS path checked | Bytes | Matching SHA-256 |
| --- | --- | ---: | --- |
| `404.html` | `/404.html` | 4296 | `2df0e9a8c55c6af8dd685b2a60530905377d9d2956343b26fef9b9956d3ccebf` |
| `404.js` | `/404.js` | 8417 | `e63019f50c037f19d01063485be9d8bef98d7b73bfec7e43e464a15d531bd866` |
| `app.js` | `/app.js` | 95179 | `5acdee749c16a30c0f8f3a4d340ab757b46f0062d4b14f374bbb8194a053e6bb` |
| `assets/brand/hub-optimus-hero.jpg` | `/assets/brand/hub-optimus-hero.jpg` | 162276 | `3c0bffc56bf43e05c6cc2c0fb43ffaafed2c8b2d01bff07d380745f53242b7d3` |
| `assets/brand/hub-optimus-logo-lockup.png` | `/assets/brand/hub-optimus-logo-lockup.png` | 543194 | `a9828f39b04389ca2efc276e2411e8a6d580b722a29be8fd19f7f0072e016bb4` |
| `assets/geo/README.md` | `/assets/geo/README.md` | 1061 | `4e4690dc45b36a5fd4d576cb7329108d5ea30c183f1ada0a0caaa1894c568c34` |
| `assets/geo/land-110m.geojson` | `/assets/geo/land-110m.geojson` | 202230 | `837db91532bb2f632eb822ad1159dbe687316d1e63e931327adcdd0a558f8db6` |
| `assets/geo/land-110m.geojson.sha256` | `/assets/geo/land-110m.geojson.sha256` | 84 | `0c862f196f606c5c1d911cee6982a35a23cb9b865f1e7ab6c515b7e13799b8dd` |
| `assets/huboptimus_signature_mark.png` | `/assets/huboptimus_signature_mark.png` | 3940 | `d3ea1ea7b9549e40c9d47687fe9cf85e33491887df4e13231fc772d24e426b24` |
| `data/capability-registry.v1.json` | `/data/capability-registry.v1.json` | 12660 | `335a29681a64efbadf48a7bd65234fbd4376cd58d34a16eef3e6213641c9ace4` |
| `data/capability-registry.v1.schema.json` | `/data/capability-registry.v1.schema.json` | 16516 | `696f9e26b5d6c74b72a5551ef890a2b83c6893e770ce512982548714ed6e391c` |
| `globe.js` | `/globe.js` | 18069 | `4cf4dc4b2e9e66a04c8b13031b8ba96cd8f23b9dbc0323de14e8cc16896f1dc8` |
| `i18n/README.md` | `/i18n/README.md` | 6487 | `292711292415bc76c15be0cd3060bf7ec49c0dd205d54bb7b1c69557662add0b` |
| `i18n/document-routes.v1.js` | `/i18n/document-routes.v1.js` | 3337 | `8054ab54e4209d0c385127f707194470c4774d34576bc588042f0e49386744ab` |
| `i18n/locale-metadata.v1.json` | `/i18n/locale-metadata.v1.json` | 9266 | `586e11cc5948ab5dd88e0625915b9cb5570567e9d6567bfe0053cffebf152576` |
| `i18n/termbase.v1.json` | `/i18n/termbase.v1.json` | 5311 | `87b2e87ec9511e203c43ae0b034bd2785f1757dd5006353fe3961197cfb31fa4` |
| `index.html` | `/` | 30943 | `a49bbed7f526a40c46b4dd3e83ffbd8e0d209d5a827d77741ca9154062e30be8` |
| `obsidian-HUB_Optimus-v1.0/app-graph.js` | `/obsidian-HUB_Optimus-v1.0/app-graph.js` | 15131 | `7840c4285607bd5110ee71c43c129bdd86e46850bbd4c9c2d611247d0aa6002e` |
| `obsidian-HUB_Optimus-v1.0/app.js` | `/obsidian-HUB_Optimus-v1.0/app.js` | 12651 | `7b52a2ab0dbe171153defb61f0a3ad209a2b351a5b7a8cae5565926309dcfeb4` |
| `obsidian-HUB_Optimus-v1.0/index.html` | `/obsidian-HUB_Optimus-v1.0/` | 15174 | `c2112ff72199911871bc7207a720b6d127a7ce001d52f210f0807d3f94066d02` |
| `obsidian-HUB_Optimus-v1.0/styles-content.css` | `/obsidian-HUB_Optimus-v1.0/styles-content.css` | 8199 | `0e9fea75fd4d84d94ede09cbf953d5c8b2e4035b2101775dcadde77e52d894c7` |
| `obsidian-HUB_Optimus-v1.0/styles-explorer.css` | `/obsidian-HUB_Optimus-v1.0/styles-explorer.css` | 9495 | `68fabef774cdc1674baa93881787c8b59707e8d31dc9538eb9b1d8d6f018897f` |
| `obsidian-HUB_Optimus-v1.0/styles.css` | `/obsidian-HUB_Optimus-v1.0/styles.css` | 11553 | `dff21227eb3a2996228b142dc851a5a11b08d5f0a7e2bb87858f545d0493deee` |
| `obsidian-HUB_Optimus-v1.0/system.json` | `/obsidian-HUB_Optimus-v1.0/system.json` | 14297 | `a880812439e96cb0cddbacb28d28eb5ae61cc3bd50bbb30d6a6a46c56760d2f1` |
| `obsidian-HUB_Optimus-v1.0/system.runtime.json` | `/obsidian-HUB_Optimus-v1.0/system.runtime.json` | 13865 | `ed71759923487b584cc7c074ce5c7e6cd06a47a99b380482ad07fb09f74b4706` |
| `obsidian-HUB_Optimus-v1.1/app-graph.js` | `/obsidian-HUB_Optimus-v1.1/app-graph.js` | 15131 | `7840c4285607bd5110ee71c43c129bdd86e46850bbd4c9c2d611247d0aa6002e` |
| `obsidian-HUB_Optimus-v1.1/app-v11.js` | `/obsidian-HUB_Optimus-v1.1/app-v11.js` | 20641 | `bcefd454517586990b9c5abaefecee3ff421f62cfb97ad562e18424f986053cc` |
| `obsidian-HUB_Optimus-v1.1/app.js` | `/obsidian-HUB_Optimus-v1.1/app.js` | 12651 | `7b52a2ab0dbe171153defb61f0a3ad209a2b351a5b7a8cae5565926309dcfeb4` |
| `obsidian-HUB_Optimus-v1.1/index.html` | `/obsidian-HUB_Optimus-v1.1/` | 15269 | `72c8357cd17025c01603ea65c6bb929df16ef39de199bd29d768ab17661ef983` |
| `obsidian-HUB_Optimus-v1.1/styles-content.css` | `/obsidian-HUB_Optimus-v1.1/styles-content.css` | 8199 | `0e9fea75fd4d84d94ede09cbf953d5c8b2e4035b2101775dcadde77e52d894c7` |
| `obsidian-HUB_Optimus-v1.1/styles-explorer.css` | `/obsidian-HUB_Optimus-v1.1/styles-explorer.css` | 9495 | `68fabef774cdc1674baa93881787c8b59707e8d31dc9538eb9b1d8d6f018897f` |
| `obsidian-HUB_Optimus-v1.1/styles-v11.css` | `/obsidian-HUB_Optimus-v1.1/styles-v11.css` | 5714 | `a3b682a29b0bf6b2ab88174e2332fec953a3935d64f85f2ed919884adcd2cdeb` |
| `obsidian-HUB_Optimus-v1.1/styles.css` | `/obsidian-HUB_Optimus-v1.1/styles.css` | 11553 | `dff21227eb3a2996228b142dc851a5a11b08d5f0a7e2bb87858f545d0493deee` |
| `obsidian-HUB_Optimus-v1.1/system.delta.json` | `/obsidian-HUB_Optimus-v1.1/system.delta.json` | 72064 | `0039afa60c9c5622ca6d5ea65c39638b80587e4bda10ed6d62c7535022a1eeda` |
| `obsidian-HUB_Optimus-v1.1/system.inventory.json` | `/obsidian-HUB_Optimus-v1.1/system.inventory.json` | 338905 | `19f3f26e6ac452611f480b67f98c8c46c5b1988c7bc37c677c7b0edaba71c71c` |
| `obsidian-HUB_Optimus-v1.1/system.json` | `/obsidian-HUB_Optimus-v1.1/system.json` | 14297 | `a880812439e96cb0cddbacb28d28eb5ae61cc3bd50bbb30d6a6a46c56760d2f1` |
| `obsidian-HUB_Optimus-v1.1/system.learning.json` | `/obsidian-HUB_Optimus-v1.1/system.learning.json` | 5436 | `13c1050deae615f520ba45cfa6739f291b571a0a0ffc865c2b3dbde851f4c096` |
| `obsidian-HUB_Optimus-v1.1/system.runtime.json` | `/obsidian-HUB_Optimus-v1.1/system.runtime.json` | 13944 | `7f176e6d9ce98180512c7bbe68b47f2b5fc210459094f70c94a6bcef4491bec3` |
| `obsidian-HUB_Optimus/app-graph.js` | `/obsidian-HUB_Optimus/app-graph.js` | 15131 | `7840c4285607bd5110ee71c43c129bdd86e46850bbd4c9c2d611247d0aa6002e` |
| `obsidian-HUB_Optimus/app-v11.js` | `/obsidian-HUB_Optimus/app-v11.js` | 20641 | `bcefd454517586990b9c5abaefecee3ff421f62cfb97ad562e18424f986053cc` |
| `obsidian-HUB_Optimus/app.js` | `/obsidian-HUB_Optimus/app.js` | 12651 | `7b52a2ab0dbe171153defb61f0a3ad209a2b351a5b7a8cae5565926309dcfeb4` |
| `obsidian-HUB_Optimus/index.html` | `/obsidian-HUB_Optimus/` | 15269 | `72c8357cd17025c01603ea65c6bb929df16ef39de199bd29d768ab17661ef983` |
| `obsidian-HUB_Optimus/styles-content.css` | `/obsidian-HUB_Optimus/styles-content.css` | 8199 | `0e9fea75fd4d84d94ede09cbf953d5c8b2e4035b2101775dcadde77e52d894c7` |
| `obsidian-HUB_Optimus/styles-explorer.css` | `/obsidian-HUB_Optimus/styles-explorer.css` | 9495 | `68fabef774cdc1674baa93881787c8b59707e8d31dc9538eb9b1d8d6f018897f` |
| `obsidian-HUB_Optimus/styles-v11.css` | `/obsidian-HUB_Optimus/styles-v11.css` | 5714 | `a3b682a29b0bf6b2ab88174e2332fec953a3935d64f85f2ed919884adcd2cdeb` |
| `obsidian-HUB_Optimus/styles.css` | `/obsidian-HUB_Optimus/styles.css` | 11553 | `dff21227eb3a2996228b142dc851a5a11b08d5f0a7e2bb87858f545d0493deee` |
| `obsidian-HUB_Optimus/system.delta.json` | `/obsidian-HUB_Optimus/system.delta.json` | 72064 | `0039afa60c9c5622ca6d5ea65c39638b80587e4bda10ed6d62c7535022a1eeda` |
| `obsidian-HUB_Optimus/system.inventory.json` | `/obsidian-HUB_Optimus/system.inventory.json` | 338905 | `19f3f26e6ac452611f480b67f98c8c46c5b1988c7bc37c677c7b0edaba71c71c` |
| `obsidian-HUB_Optimus/system.json` | `/obsidian-HUB_Optimus/system.json` | 14297 | `a880812439e96cb0cddbacb28d28eb5ae61cc3bd50bbb30d6a6a46c56760d2f1` |
| `obsidian-HUB_Optimus/system.learning.json` | `/obsidian-HUB_Optimus/system.learning.json` | 5436 | `13c1050deae615f520ba45cfa6739f291b571a0a0ffc865c2b3dbde851f4c096` |
| `obsidian-HUB_Optimus/system.runtime.json` | `/obsidian-HUB_Optimus/system.runtime.json` | 13944 | `7f176e6d9ce98180512c7bbe68b47f2b5fc210459094f70c94a6bcef4491bec3` |
| `obsidian-release-channels.v1.json` | `/obsidian-release-channels.v1.json` | 1059 | `4459580eb1a825865ab102a0ba76b6105c340144458bbf7035a35cc59872f0de` |
| `operator/auth.v1.js` | `/operator/auth.v1.js` | 19121 | `5c85ddd085c70ad882ba33a66ba5c6b494126b051a9d0d80950025f071721966` |
| `operator/claim-decomposition.v1.js` | `/operator/claim-decomposition.v1.js` | 37996 | `48ab631d6f8c1a5ada6f7ee39973de83d55df864a6c29492396cdd90a8d26c05` |
| `operator/i18n.v1.js` | `/operator/i18n.v1.js` | 327845 | `6a1e7091c12587b3b764cd369d1af4e45adc6e92d5d0d2c579416aee188c1069` |
| `operator/icon.svg` | `/operator/icon.svg` | 2126 | `3e2ed8dc33417ec4e280439021253d5e706b4cf8b0eada2f3fd6873a31aeb67f` |
| `operator/index.html` | `/operator/` | 316829 | `e7c5c892383fd723d6702a6f57d0b5cc853a10fc1c9e30d448129074b81fa29b` |
| `operator/learning-candidate.v1.js` | `/operator/learning-candidate.v1.js` | 56973 | `2d3fb269d5cbd2fffc7fc2d40734f33a55462f31dd15e70d644e91a9ab12aa37` |
| `operator/learning-store.v1.js` | `/operator/learning-store.v1.js` | 27395 | `d42b84765ec3194b34e12c22ff5a629dede5cbdbe235b778f32fc6ff92943a89` |
| `operator/manifest.de.webmanifest` | `/operator/manifest.de.webmanifest` | 484 | `94da0ba9a4755e7bb1dccc82794508bea09d751a0908b78e578ff28fcee470a2` |
| `operator/manifest.en.webmanifest` | `/operator/manifest.en.webmanifest` | 467 | `4c915876381e6b8fcc797cabec0976894830ca0d3ea1848a34d8c78ac7720d2d` |
| `operator/manifest.es.webmanifest` | `/operator/manifest.es.webmanifest` | 492 | `fdf8b5b1f50f8a2ca40c523a5f50d3b2a0d704b81045d38cf0cf8c7bf4310dca` |
| `operator/manifest.he.webmanifest` | `/operator/manifest.he.webmanifest` | 497 | `1d2046371bf93c2fd848ca5a84651e412108c1102d2bfe302d9941445cfdc824` |
| `operator/manifest.ru.webmanifest` | `/operator/manifest.ru.webmanifest` | 568 | `cfca36dfd5a7735fb2bbfd7c4346313f5e972759c60a9b15e04a8b58909969c3` |
| `operator/manifest.webmanifest` | `/operator/manifest.webmanifest` | 503 | `1c9b29309c2955ebce884858e0d4993771abb6f3d79771200bfaa3379855ab27` |
| `operator/manifest.zh-Hans.webmanifest` | `/operator/manifest.zh-Hans.webmanifest` | 476 | `2722074c5592e2451301da68741ce6675132f0c1d139083e5db9e375982675ad` |
| `operator/og.svg` | `/operator/og.svg` | 2421 | `30a01496a9ff44faae820d7e7b3cc5df6d25827f020b52320725b29ac254845f` |
| `operator/runtime-config.v1.js` | `/operator/runtime-config.v1.js` | 916 | `c90285fa6c0629696c1b4f2dede20eeb40566ba1d880ddba7d915a03043c1ec2` |
| `operator/schemas/operator_learning_candidate.v1.schema.json` | `/operator/schemas/operator_learning_candidate.v1.schema.json` | 13346 | `4b6b72b1ac3b00edffe7d7b501f5b098cf0d644804f255b078457e74acaf610a` |
| `operator/sw.js` | `/operator/sw.js` | 3431 | `bab4cd5ff73ff29581bb06c2a2d6868a5dd162314a13af912b9edc9aa2ed8a40` |
| `robots.txt` | `/robots.txt` | 23 | `16ceb5ee3e0dc13aa9adf31a3ebbe45a1d965b8c2b9f72eaf84e5911e140ed95` |
| `styles.css` | `/styles.css` | 30272 | `b47057ad7da5023d05ce33babdc1aec87219fdccced3ba516678456710c05ea6` |

## Remaining boundaries

This extends the [three-HTML receipt](github_settings_audit_2026-10-27.md) for
this exact deployment to every tracked file in its `site/` tree. It is not an
inventory of every possible URL, third-party resource, browser/service-worker
state, backend or AWS deployment, and it does not certify future publication.

Keep #1743 open for human Environment-review design, complete installed-App
coverage and physical owner-key enrollment. Related #1906 and #1974 retain
their own acceptance work. No key, fingerprint, ratification, App permission
or ownership assertion follows from these technical comparisons.

The protected [Settings Protection Checklist](../governance/GITHUB_SETTINGS_PROTECTION_CHECKLIST.md),
Kernel, owner-authority records, workflows and settings are unchanged.
