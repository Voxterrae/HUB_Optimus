### Canonical languages policy (v1)

Language folders currently present in the repository:
- `v1_core/languages/`: `es`, `en`
- `docs/`: `ca`, `de`, `es`, `fr`, `he`, `ru`, `zh` (English lives in root `docs/` files, not `docs/en/`)

Translation tiers:
- Tier 0 (canonical): `es`
  - Source of truth for normative content in `v1_core/`.
- Tier 1 (required parity): `en`
  - Must stay semantically aligned with `es`.
  - On conflict, `es` wins.
- Tier 2 (additional languages): `ca`, `de`, `fr`, `he`, `ru`, `zh`
  - Structural paths and links are guaranteed.
  - Content can be partial unless a language is explicitly promoted.

Source-of-truth rule:
- If repository docs conflict, this file wins.

## Next steps
- [ ] Decidir si REPO_TREE.txt y SNAPSHOT.txt van a git (sí/no) y actuar en consecuencia
- [ ] Validar/finalizar tools/fix_encoding_docs.ps1 (y documentar uso en WORKFLOWS.md)
- [ ] Ejecutar link-check (Lychee) localmente o vía GitHub Actions y corregir rotos
