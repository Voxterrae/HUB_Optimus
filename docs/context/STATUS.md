### Canonical languages policy (v1)

**v1_core/** (normative spec):
- **Canonical (source of truth): es**
- **Reference translation / parity target: en** (kept close, but es wins on conflicts)

**docs/** (onboarding & navigation):
- Priority languages: **es, de, en**
- Additional languages: ca, fr, ru (structure complete; translation progressive)
- Stub languages: **zh, he** (directory + governance stub only; full translation pending)

**Source-of-truth rule:**
- If repository docs conflict, this file wins.

**Planned switch (later, not now):**
- Once en reaches stable parity, we may declare **en as canonical** for a future version (v1.1 or v2).

## Next steps
- [ ] Decidir si REPO_TREE.txt y SNAPSHOT.txt van a git (sí/no) y actuar en consecuencia
- [ ] Validar/finalizar tools/fix_encoding_docs.ps1 (y documentar uso en WORKFLOWS.md)
- [ ] Ejecutar link-check (Lychee) localmente o vía GitHub Actions y corregir rotos
