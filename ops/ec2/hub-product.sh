#!/usr/bin/env bash
set -euo pipefail

APP_ROOT="/opt/hub-optimus"

api_active="$(systemctl is-active hub-api 2>/dev/null || echo not_configured)"
api_enabled="$(systemctl is-enabled hub-api 2>/dev/null || echo not_configured)"

echo "HUB_Optimus backend v0.1"
echo

echo "[core]"
echo "current=$(readlink -f "$APP_ROOT/current" 2>/dev/null || echo none)"
echo "release=$(cat "$APP_ROOT/shared/current_release" 2>/dev/null || echo none)"
echo "commit=$(
  if [ -L "$APP_ROOT/current" ]; then
    cd "$APP_ROOT/current"
    git rev-parse --short HEAD
  else
    echo none
  fi
)"
echo "status=$(grep '^status=' "$APP_ROOT/shared/RELEASE_STATE" 2>/dev/null | cut -d= -f2- || echo unknown)"
echo

echo "[capabilities]"
command -v hub-ops >/dev/null && echo "hub-ops=active" || echo "hub-ops=missing"
command -v hub-core >/dev/null && echo "hub-core=active" || echo "hub-core=missing"
command -v hub-runs >/dev/null && echo "hub-runs=active" || echo "hub-runs=missing"
command -v hub-api-control >/dev/null && echo "hub-api-control=active" || echo "hub-api-control=missing"

echo "semantic_analyze=active"
echo "scenario_runner=active"
echo "deploy_rollback=active"
echo "runs_registry=active"
echo "local_api=$api_active"
echo "systemd_service=$api_enabled"
echo "api_bind=127.0.0.1:8080"
echo "api_contract=direct_json"
echo

echo "[not_configured]"
echo "public_api=not_configured"
echo "frontend=not_configured"
echo "nginx=not_configured"
echo "elastic_ip=deferred"
echo "ami=deferred"
echo "domain=deferred"
echo "typescript_artifact=not_present"
echo

echo "[latest_runs]"
if [ -d "$APP_ROOT/shared/runs" ]; then
  find "$APP_ROOT/shared/runs" -mindepth 2 -maxdepth 2 -type d \
    | sed "s#$APP_ROOT/shared/runs/##" \
    | sort \
    | tail -n 10
else
  echo "none"
fi
