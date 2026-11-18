#!/usr/bin/env bash
# Core runner; the workflow supplies the network namespace. Direct local use
# does not certify network isolation. Only the standalone Brave suites are built.
set -euo pipefail
[[ $# == 2 ]] || { echo 'Usage: build-test.sh BRAVE_MODULE ABSOLUTE_DOTNET' >&2; exit 2; }
module="$(realpath -- "$1")"
dotnet="$(realpath -- "$2")"
[[ -x "$dotnet" ]] || { echo 'SDK executable missing' >&2; exit 2; }
state="$(mktemp -d)"
trap 'rm -rf -- "$state"' EXIT
mkdir -p "$state/home" "$state/packages" "$state/http-cache"
cat > "$state/NuGet.Config" <<'XML'
<configuration>
  <packageSources><clear /></packageSources>
  <fallbackPackageFolders><clear /></fallbackPackageFolders>
</configuration>
XML
# No inherited credentials, proxy, MSBuild hooks or user NuGet configuration.
env -i \
  PATH="$(dirname -- "$dotnet"):/usr/bin:/bin" \
  HOME="$state/home" LANG=C.UTF-8 \
  DOTNET_ROOT="$(dirname -- "$dotnet")" DOTNET_CLI_HOME="$state/home" \
  DOTNET_CLI_TELEMETRY_OPTOUT=1 DOTNET_NOLOGO=1 \
  DOTNET_SKIP_FIRST_TIME_EXPERIENCE=1 DOTNET_CLI_WORKLOAD_UPDATE_NOTIFY_DISABLE=true \
  DOTNET_MULTILEVEL_LOOKUP=0 DOTNET_EnableDiagnostics=0 \
  NUGET_PACKAGES="$state/packages" NUGET_HTTP_CACHE_PATH="$state/http-cache" \
  /bin/bash -euo pipefail -c '
    cd -- "$1"
    sdk="$2"
    state="$3"
    actual="$("$sdk" --version)"
    [[ "$actual" == 10.0.403 ]] || { echo "Wrong SDK: $actual; expected 10.0.403" >&2; exit 1; }
    echo "SDK: $actual"
    adapter=tests/Optimus.Search.Brave.Tests/Optimus.Search.Brave.Tests.csproj
    gateway=gateway/tests/Optimus.Search.Brave.Gateway.Tests/Optimus.Search.Brave.Gateway.Tests.csproj
    has_gateway=0
    if [[ -e gateway ]]; then
      [[ -f "$gateway" ]] || { echo "Incomplete gateway candidate" >&2; exit 1; }
      has_gateway=1
    fi
    # A cold restore with no sources must fail if a package is introduced.
    restore_project() {
      "$sdk" restore "$1" --configfile "$state/NuGet.Config" \
      --no-cache --force -p:NuGetAudit=false -p:RestoreIgnoreFailedSources=false \
      -p:RestoreFallbackFolders= -p:RestoreAdditionalProjectSources=
    }
    restore_project "$adapter"
    if (( has_gateway )); then restore_project "$gateway"; fi
    python3 - "$has_gateway" <<PY
import json
import sys
from pathlib import Path
paths = [Path("src/Optimus.Search.Brave/obj/project.assets.json"),
         Path("tests/Optimus.Search.Brave.Tests/obj/project.assets.json")]
if sys.argv[1] == "1":
    paths += [Path("gateway/src/Optimus.Search.Brave.Gateway/obj/project.assets.json"),
              Path("gateway/tests/Optimus.Search.Brave.Gateway.Tests/obj/project.assets.json")]
for path in paths:
    data = json.loads(path.read_text())
    if any(item["type"] != "project" for item in data["libraries"].values()):
        raise SystemExit("Unexpected package dependency: " + str(path))
    if data["project"]["restore"].get("sources", {}):
        raise SystemExit("Unexpected NuGet source: " + str(path))
print(f"Verified: {len(paths)} assets files, zero package dependencies, zero NuGet sources")
PY
    run_suite() {
      label="$1"
      project="$2"
      expected="$3"
      "$sdk" build "$project" -c Release --no-restore --no-incremental -m:1 \
        -p:ContinuousIntegrationBuild=true -p:UseSharedCompilation=false
      "$sdk" run --project "$project" -c Release --no-build --no-restore | tee "$state/$label.log"
      python3 - "$label" "$expected" "$state/$label.log" <<PY
import re
import sys
from pathlib import Path
label, expected, log = sys.argv[1], int(sys.argv[2]), sys.argv[3]
lines = Path(log).read_text().splitlines()
passes = [line for line in lines if line.startswith("PASS ")]
summaries = [line for line in lines if re.fullmatch(r"[0-9]+/[0-9]+ passed", line)]
summary = f"{expected}/{expected} passed"
if (len(passes) != expected or len(set(passes)) != expected
        or any(line.startswith("FAIL ") for line in lines)
        or summaries != [summary] or not lines or lines[-1] != summary):
    raise SystemExit("Incomplete or failed " + label + " console suite")
print(f"Verified {label}: {expected}/{expected} complete console cases")
PY
    }
    run_suite adapter "$adapter" 59
    if (( has_gateway )); then
      run_suite gateway "$gateway" 39
    else
      echo "Gateway NOT RUN: historical adapter-only candidate"
    fi
  ' _ "$module" "$dotnet" "$state"
