#!/usr/bin/env bash
# Core runner; the workflow supplies the network namespace. Direct local use
# does not certify network isolation. Only the standalone Brave module is built.
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
    project=tests/Optimus.Search.Brave.Tests/Optimus.Search.Brave.Tests.csproj
    # A cold restore with no sources must fail if a package is introduced.
    "$sdk" restore "$project" --configfile "$state/NuGet.Config" \
      --no-cache --force -p:NuGetAudit=false -p:RestoreIgnoreFailedSources=false \
      -p:RestoreFallbackFolders= -p:RestoreAdditionalProjectSources=
    python3 - <<PY
import json
from pathlib import Path
for path in (Path("src/Optimus.Search.Brave/obj/project.assets.json"),
             Path("tests/Optimus.Search.Brave.Tests/obj/project.assets.json")):
    data = json.loads(path.read_text())
    if any(item["type"] != "project" for item in data["libraries"].values()):
        raise SystemExit("Unexpected package dependency: " + str(path))
    if data["project"]["restore"].get("sources", {}):
        raise SystemExit("Unexpected NuGet source: " + str(path))
print("Verified: two assets files, zero package dependencies, zero NuGet sources")
PY
    "$sdk" build "$project" -c Release --no-restore --no-incremental -m:1 \
      -p:ContinuousIntegrationBuild=true -p:UseSharedCompilation=false
    "$sdk" run --project "$project" -c Release --no-build --no-restore
  ' _ "$module" "$dotnet" "$state"
