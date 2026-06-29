#!/usr/bin/env bash
set -euo pipefail

APP_ROOT="/opt/hub-optimus"
RUN_ROOT="$APP_ROOT/shared/runs"

usage() {
  cat <<USAGE
HUB_Optimus core runner

Usage:
  hub-core status
  hub-core test
  hub-core benchmark
  hub-core narrative-benchmark
  hub-core semantic-smoke
  hub-core scenario-smoke
  hub-core analyze <case.json>

Commands:
  status               Show active release and available core commands.
  test                 Run full pytest suite on current release.
  benchmark            Run benchmark pack v0 and store output.
  narrative-benchmark  Run narrative benchmark pack and store output.
  semantic-smoke       Run Semantic Engine minimal case and store JSON result.
  scenario-smoke       Run example scenario and store JSON result.
  analyze              Analyze a provided Semantic Engine case JSON and store result.
USAGE
}

require_current() {
  if [ ! -L "$APP_ROOT/current" ]; then
    echo "[hub-core:error] current symlink does not exist."
    exit 1
  fi
  cd "$APP_ROOT/current"
}

activate_current() {
  require_current
  if [ ! -d ".venv" ]; then
    echo "[hub-core:error] .venv does not exist in current release."
    exit 1
  fi
  source .venv/bin/activate
}

new_run_dir() {
  local name="$1"
  local ts
  ts="$(date -u +%Y%m%dT%H%M%SZ)"
  local dir="$RUN_ROOT/$name/$ts"
  mkdir -p "$dir"
  echo "$dir"
}

write_run_meta() {
  local dir="$1"
  local command_name="$2"
  local input_path="${3:-}"
  local commit
  local release
  local current_path

  require_current
  commit="$(git rev-parse --short HEAD)"
  current_path="$(readlink -f "$APP_ROOT/current")"
  release="$(basename "$current_path")"

  cat > "$dir/RUN_STATE" <<STATE
command=$command_name
release=$release
commit=$commit
path=$current_path
input=$input_path
ran_at_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)
STATE
}

status_core() {
  require_current

  echo "[hub-core] HUB_Optimus core"
  echo

  echo "[hub-core] current:"
  readlink -f "$APP_ROOT/current"
  echo

  echo "[hub-core] release_state:"
  cat "$APP_ROOT/shared/RELEASE_STATE" 2>/dev/null || echo "none"
  echo

  echo "[hub-core] commit:"
  git rev-parse --short HEAD
  echo

  echo "[hub-core] available commands:"
  usage
}

run_tests() {
  activate_current

  local dir
  dir="$(new_run_dir test)"
  write_run_meta "$dir" "test"

  echo "[hub-core:test] Output dir: $dir"
  python -m pytest -q | tee "$dir/pytest.log"

  deactivate
  echo "[hub-core:test] Done"
}

run_benchmark() {
  activate_current

  local dir
  dir="$(new_run_dir benchmark)"
  write_run_meta "$dir" "benchmark"

  echo "[hub-core:benchmark] Output dir: $dir"
  python benchmarks/run_benchmarks.py --summary-file "$dir/benchmark_summary.md" | tee "$dir/benchmark.log"

  deactivate
  echo "[hub-core:benchmark] Done"
}

run_narrative_benchmark() {
  activate_current

  local dir
  dir="$(new_run_dir narrative-benchmark)"
  write_run_meta "$dir" "narrative-benchmark"

  echo "[hub-core:narrative-benchmark] Output dir: $dir"
  python benchmarks/run_narrative_benchmarks.py | tee "$dir/narrative_benchmark.log"

  deactivate
  echo "[hub-core:narrative-benchmark] Done"
}

run_semantic_smoke() {
  activate_current

  local dir
  dir="$(new_run_dir semantic-smoke)"
  write_run_meta "$dir" "semantic-smoke"

  echo "[hub-core:semantic-smoke] Output dir: $dir"
  python -m semantic_engine.cli analyze \
    examples/semantic_engine/case_minimal.json \
    --output "$dir/analysis_result.json"

  cp examples/semantic_engine/case_minimal.json "$dir/input_case.json"
  cat "$dir/analysis_result.json"

  deactivate
  echo "[hub-core:semantic-smoke] Done"
}

run_scenario_smoke() {
  activate_current

  local dir
  dir="$(new_run_dir scenario-smoke)"
  write_run_meta "$dir" "scenario-smoke"

  echo "[hub-core:scenario-smoke] Output dir: $dir"
  python run_scenario.py \
    --scenario example_scenario.json \
    --output "$dir/example_scenario.result.json" \
    --seed 42 | tee "$dir/scenario_stdout.json"

  cp example_scenario.json "$dir/input_scenario.json"

  deactivate
  echo "[hub-core:scenario-smoke] Done"
}

run_analyze() {
  local input="${1:-}"

  if [ -z "$input" ]; then
    echo "[hub-core:error] case JSON path required."
    echo
    usage
    exit 1
  fi

  if [ ! -f "$input" ]; then
    echo "[hub-core:error] case JSON not found: $input"
    exit 1
  fi

  activate_current

  local dir
  dir="$(new_run_dir analyze)"
  write_run_meta "$dir" "analyze" "$input"

  echo "[hub-core:analyze] Output dir: $dir"

  cp "$input" "$dir/input_case.json"

  python -m semantic_engine.cli analyze \
    "$dir/input_case.json" \
    --output "$dir/analysis_result.json"

  cat "$dir/analysis_result.json"

  deactivate
  echo "[hub-core:analyze] Done"
}

case "${1:-}" in
  status)
    status_core
    ;;
  test)
    run_tests
    ;;
  benchmark)
    run_benchmark
    ;;
  narrative-benchmark)
    run_narrative_benchmark
    ;;
  semantic-smoke)
    run_semantic_smoke
    ;;
  scenario-smoke)
    run_scenario_smoke
    ;;
  analyze)
    shift
    run_analyze "${1:-}"
    ;;
  ""|-h|--help|help)
    usage
    ;;
  *)
    echo "[hub-core:error] Unknown command: $1"
    echo
    usage
    exit 1
    ;;
esac
