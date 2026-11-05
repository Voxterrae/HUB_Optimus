# Remote pilot API implementation plan

Goal: implement the design in DESIGN.md as a reviewable offline-tested candidate.

- [x] API: write failing behavior/integration tests; implement separate credential, catalog, resource guard and host modules using existing ranking types; run all remote tests.
- [x] Azure: prepare an inert Consumption deployment template with explicit false-only promotion gate, small replica/resource limits, no query logging, no registry/log/storage resource provisioning; validate locally.
- [x] Compatibility: document portable HTTP/JSON and credential storage boundaries for Windows/Linux/Android; preserve current native paths.
- [x] Verify: run baseline backend, public pilot Python tests, remote/infrastructure tests; independently review security and deployment boundaries; fix reproduced findings.
- [x] Deliver: source snapshot, apply-ready patch against the pinned commit, checksummed evidence and exact decisions required for a first shared Azure service.

Review focus: spoofed proxy headers cannot bypass auth; chunked/duplicate JSON cannot bypass limits; source corruption fails before startup; malicious inputs cannot enter logs; template defaults or partial parameter changes cannot activate resources.
