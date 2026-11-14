# Product catalogue

Reviewed source snapshot: [main@7ca513eb](https://github.com/Voxterrae/HUB_Optimus/commit/7ca513eb16d12d77ba5f017c63109dab937c12b2), 8 November 2026 (Europe/Madrid).
The [capability registry](../site/data/capability-registry.v1.json) records the
reviewed source and execution boundaries. This catalogue and the public cards
are static, reviewed views; they do not monitor releases or deployments.

Source integration proves that the linked assets are in the repository. A
usable local prototype, a public static web pilot, a supported product release
and a deployed production service are separate claims. No commercial release,
service-level commitment or current-HEAD native acceptance follows from a card.
All components retain zero production writes and no deployed production-service
claim in this reviewed registry.

The existing methodology/prototype entries retain their older, explicitly
versioned public-document evidence baseline. New product entries link their own
immutable source snapshot. Historical tests apply only to the exact source they
executed; see the relevant PR, run and dated validation guide for acceptance.

## Existing methodology and prototype surfaces

| Component ID | Evidence / entry point | Source status | Lifecycle |
| --- | --- | --- | --- |
| `core` | [HUB_Optimus Core](https://github.com/Voxterrae/HUB_Optimus/tree/8426b08e5f88b650c4d79e41d3ce3afd7d42746b/v1_core/languages/es) | `merged` | `active-methodology` |
| `simulator` | [Deterministic Scenario Simulator](https://github.com/Voxterrae/HUB_Optimus/blob/8426b08e5f88b650c4d79e41d3ce3afd7d42746b/SIMULATION_README.md) | `merged` | `working-deterministic-prototype` |
| `semantic-engine` | [Semantic Engine Contracts and CLI](https://github.com/Voxterrae/HUB_Optimus/tree/8426b08e5f88b650c4d79e41d3ce3afd7d42746b/semantic_engine) | `merged` | `early-implementation` |
| `operator` | [HUB_Optimus Operator](https://github.com/Voxterrae/HUB_Optimus/tree/8426b08e5f88b650c4d79e41d3ce3afd7d42746b/site/operator) | `merged` | `browser-prototype` |
| `controlled-url-intake` | [Controlled URL Intake](https://github.com/Voxterrae/HUB_Optimus/blob/8426b08e5f88b650c4d79e41d3ce3afd7d42746b/docs/rfc/operator_controlled_url_intake.md) | `merged` | `implementation-present-deployment-unverified` |
| `research` | [Scenario and Narrative Research](https://github.com/Voxterrae/HUB_Optimus/blob/8426b08e5f88b650c4d79e41d3ce3afd7d42746b/docs/lab_state.md) | `merged` | `experimental-tooling` |
| `governance-intelligence` | [Governance Intelligence](https://github.com/Voxterrae/HUB_Optimus/blob/8426b08e5f88b650c4d79e41d3ce3afd7d42746b/docs/governance/GOVERNANCE_INTELLIGENCE.md) | `merged` | `active-ratified-protocol` |
| `labs` | [HUB-Optimus Labs](https://github.com/Voxterrae/HUB_Optimus/blob/8426b08e5f88b650c4d79e41d3ce3afd7d42746b/site/index.html) | `merged` | `documented-incubation-surface` |

## In development

These source records do not claim a released native product or a production
service. A static description can be public while execution remains disabled.
The separate web pilot is an explicitly labelled browser prototype.

| Component ID | Evidence / entry point | Source status | Lifecycle |
| --- | --- | --- | --- |
| `admin-gateway` | [Optimus Admin Gateway](https://github.com/Voxterrae/HUB_Optimus/tree/c7a67a7af9e5067e27518d3a9bd8b56f99767acf/products/admin-gateway/src/optimus_admin_gateway) | `merged` | `implementation-present-deployment-unverified` |
| `evidence-lab` | [Optimus Evidence Lab](https://github.com/Voxterrae/HUB_Optimus/tree/51327282170b9c0a6f769b8bd5ddc5c39572d6a4/products/evidence-lab) | `merged` | `implementation-present-deployment-unverified` |
| `connect-xai-x` | [HUB_Optimus Connect — xAI and X Foundation](https://github.com/Voxterrae/HUB_Optimus/tree/bd7cfd3cf39e36d7a9f9c215cd5d47635d63cf41/hub_optimus/connect) | `merged` | `early-implementation` |
| `global-graph` | [Optimus Global Graph](https://github.com/Voxterrae/HUB_Optimus/issues/1880) | `open-issue` | `issue-only` |
| `browser-windows` | [Optimus Browser — Windows](https://github.com/Voxterrae/HUB_Optimus/tree/7ca513eb16d12d77ba5f017c63109dab937c12b2/products/browser/windows) | `merged` | `early-implementation` |
| `browser-web-pilot` | [Optimus Browser — Web Pilot](https://github.com/Voxterrae/HUB_Optimus/tree/7ca513eb16d12d77ba5f017c63109dab937c12b2/site/browser) | `merged` | `browser-prototype` |
| `browser-linux` | [Optimus Browser — Linux](https://github.com/Voxterrae/HUB_Optimus/issues/2021) | `open-issue` | `issue-only` |
| `search` | [Optimus Search](https://github.com/Voxterrae/HUB_Optimus/tree/7ca513eb16d12d77ba5f017c63109dab937c12b2/products/browser/search) | `merged` | `implementation-present-deployment-unverified` |
| `device-bridge` | [Device Bridge / HUB_Relay](https://github.com/Voxterrae/HUB_Optimus/tree/7ca513eb16d12d77ba5f017c63109dab937c12b2/products/device-bridge) | `merged` | `experimental-tooling` |

## Product boundaries and next acceptance gates

| Area | Available source / prototype scope | Separate acceptance or activation gate |
| --- | --- | --- |
| Operator | [Browser-local draft preparation](../site/operator/); supplied text and source attribution are not verified evidence. | Private URL intake is disabled in the public runtime configuration. A local draft is not a Semantic Engine execution. |
| Browser / Windows | [WPF/WebView2 alpha](browser/windows/README.md), shared local Search and reversible session-only pilot catalogue selection. | Current-source native execution, physical Windows, spoken assistive-technology acceptance, signing and distribution need their own dated evidence. |
| Browser / web | [Separate static web pilot](browser/web/README.md) with six interface languages, explicit Wikipedia submission and optional device-local preferences; local voice depends on browser support. | It is not the native browser, a general-Web search engine or an offline guarantee. Requests to Wikipedia occur only after explicit user submission. |
| Browser / Linux | [Coordination issue #2021](https://github.com/Voxterrae/HUB_Optimus/issues/2021) records a declared local PySide6/Qt WebEngine prototype. | No Linux Browser source is merged at this snapshot. A contributor report or shared Search contract is not client acceptance. |
| Search / catalogue | [Device-local HTTPS host](browser/search/README.md), finite index and a separate [eight-summary Spanish pilot catalogue](browser/search/docs/PUBLIC_PILOT.md). | The catalogue is not a crawler or general Internet coverage. Its checksums do not establish a deployed Azure service. |
| Search / Web | Source includes an operator-configured SearXNG adapter and an explicit Wikipedia source. | A production provider is not configured by this catalogue. General-Web relevance remains a separate acceptance gate; proposed Brave/gateway adapters are not part of the reviewed merged source. |
| Device Bridge / HUB_Relay | [Compatibility records](device-bridge/README.md), [protocol-verification library](device-bridge/common/native-protocol/README.md), offline fixtures and a fixed-route [Windows diagnostic candidate](device-bridge/windows/bootstrap-inventory/README.md). | Relay activation remains blocked. Diagnostic receipts do not establish loaded-image provenance, biometric enforcement or an unattended management service. |
| Admin Gateway | [Tenant-neutral reference API](admin-gateway/README.md), allowlisted runbooks and connector/schema/deployment assets. | The reference executor rejects live execution. Source publication does not authorize tenant operations, installation or production writes. |
| Evidence Lab | [Dataverse package](evidence-lab/README.md), governed schema/aggregate seed plans and offline dry-run evidence. | Live metadata application, business-data seeding and deployment retain separate gates. |
| Connect | [xAI/X provider foundation](../docs/architecture/xai_x_signal_bridge.md) with injected, disabled-by-default adapters and local publication planning. | No bundled live transport, credentials, automatic social publication or partnership claim is established. |
| Global Graph | [Issue-only foundation #1880](https://github.com/Voxterrae/HUB_Optimus/issues/1880). | No implemented graph, public-globe integration, API or Dataverse mutation is represented by this record. |

## How to use the evidence

- Use the immutable links above for source evidence and the child guides for navigation.
- Read `source_status` together with `lifecycle_state` and the runtime/deployment fields; `merged` alone is not an activation signal.
- Keep catalogue, Web-provider and platform acceptance separate. A passing fixture or cross-compilation is not a native or real-Web test.
- Consult the [public-surface synchronization contract](../docs/architecture/public_surface_sync.md) and [issue #1888](https://github.com/Voxterrae/HUB_Optimus/issues/1888) for Pages/Sites receipts. The private Sites mirror is a separately synchronized presentation surface.
- Use [IP_NOTICE.md](../IP_NOTICE.md) for rights and permitted use. This catalogue does not create a commercial license, pricing, support contract or third-party endorsement.

All new public interface translations remain assisted drafts requiring qualified
human review. The canonical language and governance policies remain unchanged.
