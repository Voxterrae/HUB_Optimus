# AGENTS.md

## Read Order
1. `AGENTS.md`
2. `docs/context/hub_optimus_checkpoint.md`
3. `docs/context/AI_CONTEXT.md`
4. `docs/context/STATUS.md`
5. `docs/context/PROJECT_OVERVIEW.md`
6. `docs/context/TRACEABILITY.md`

## Non-Negotiables
- Ship small, reversible PRs with one objective each.
- GitHub Issues and PRs are the source of truth for roadmap and task state.
- If repository docs conflict, `docs/context/STATUS.md` wins.
- Do not change runtime, CI, contracts, or governance without explicit approval.
- Preserve backward compatibility unless an approved RFC says otherwise.

## Validation Commands
- `python tools/check_mojibake.py v1_core docs README.md CONTRIBUTING.md`
- `python -m pytest -q`
- `python run_scenario.py example_scenario.json --output out/example.result.json`

## Traceability Rule
- If `tools/trace_repo.py` exists, run:
  `python tools/trace_repo.py --output-md docs/context/TRACEABILITY_SNAPSHOT.md --output-json docs/context/TRACEABILITY_SNAPSHOT.json`
- Otherwise use:
  `powershell -ExecutionPolicy Bypass -File tools/trace_repo.ps1`
- Read `docs/context/TRACEABILITY_SNAPSHOT.md` before merge or deploy guidance.

## Working Mode
- Use repo evidence, current git state, and reproducible checks.
- If scope grows, split it into a follow-up issue or PR.
- Keep docs and comments minimal, concrete, and traceable.
