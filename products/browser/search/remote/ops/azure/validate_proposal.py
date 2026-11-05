#!/usr/bin/env python3
"""Offline structural review of this inert proposal; never contacts Azure.

This is deliberately not a deployment tool or an ARM service/schema validator.
Passing means the checked files retain the proposal's narrow safety boundaries,
not that a subscription, permissions, runtime image or deployment is ready.
"""

import argparse
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CONDITION = "[parameters('deployEnabled')]"
ENVIRONMENT_TYPE = "Microsoft.App/managedEnvironments"
APP_TYPE = "Microsoft.App/containerApps"
IMAGE_PATTERN = re.compile(r"[^\s@]+@sha256:[0-9a-f]{64}\Z")


class ProposalError(ValueError):
    """A proposed change violates an inert-proposal boundary."""


def _require(test, description):
    if not test:
        raise ProposalError(description)


def _keys(value, allowed, description):
    _require(isinstance(value, dict), f"{description} must be an object")
    _require(set(value) <= set(allowed), f"{description} contains an unreviewed property")


def _no_duplicates(pairs):
    result = {}
    for key, value in pairs:
        _require(key not in result, f"duplicate JSON property: {key}")
        result[key] = value
    return result


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"), object_pairs_hook=_no_duplicates)


def validate(template, parameters, manifest):
    """Raise ProposalError on activation or a broadened resource/security boundary."""
    _keys(template, {"$schema", "contentVersion", "metadata", "parameters", "resources", "outputs"}, "template")
    definitions = template.get("parameters", {})
    expected_parameters = {"deployEnabled", "location", "environmentName", "containerAppName", "imageDigestRef"}
    _require(set(definitions) == expected_parameters, "template parameter set changed")
    gate = definitions["deployEnabled"]
    _require(gate.get("type") == "bool", "deployEnabled must be bool")
    _require(gate.get("defaultValue") is False, "deployEnabled default must be false")
    allowed = gate.get("allowedValues")
    _require(isinstance(allowed, list) and len(allowed) == 1 and allowed[0] is False, "deployEnabled must allow false only")
    _keys(parameters, {"$schema", "contentVersion", "parameters"}, "parameter file")
    supplied = parameters.get("parameters", {})
    _require(set(supplied) <= expected_parameters, "unrecognized activation or deployment parameter")
    for name, value in supplied.items():
        _require(isinstance(value, dict) and set(value) == {"value"}, f"{name} must use a literal value only")
        if name == "deployEnabled":
            _require(value["value"] is False, "activation parameters are rejected")
        else:
            _require(isinstance(value["value"], str), f"{name} must be string")
    image = supplied.get("imageDigestRef", {}).get("value", definitions["imageDigestRef"].get("defaultValue"))
    _require(isinstance(image, str) and IMAGE_PATTERN.fullmatch(image), "image must be immutable sha256 digest reference")

    resources = template.get("resources")
    _require(isinstance(resources, list) and len(resources) == 2, "exactly two proposed resources required")
    _require({r.get("type") for r in resources} == {ENVIRONMENT_TYPE, APP_TYPE}, "only ACA environment and container app resource types are permitted")
    for resource in resources:
        _keys(resource, {"condition", "type", "apiVersion", "name", "location", "dependsOn", "properties"}, "resource")
        _require(resource.get("condition") == CONDITION, "every resource must use the false-only condition")
        _require(resource.get("apiVersion") == "2025-01-01", "resource API version requires separate review")
        _require(resource.get("location") == "[parameters('location')]", "resource region must come from reviewed location parameter")

    environment = next(r for r in resources if r["type"] == ENVIRONMENT_TYPE)
    env_props = environment["properties"]
    _keys(env_props, {"appLogsConfiguration", "workloadProfiles"}, "environment properties")
    _require(env_props.get("appLogsConfiguration") == {"destination": "none"}, "saved application/system logs must be disabled")
    _require(env_props.get("workloadProfiles") == [{"name": "Consumption", "workloadProfileType": "Consumption"}], "only Consumption profile is proposed")

    app = next(r for r in resources if r["type"] == APP_TYPE)
    props = app["properties"]
    _keys(props, {"managedEnvironmentId", "workloadProfileName", "configuration", "template"}, "container app properties")
    environment_id = "[resourceId('Microsoft.App/managedEnvironments', parameters('environmentName'))]"
    _require(props.get("managedEnvironmentId") == environment_id and app.get("dependsOn") == [environment_id], "app must use only the proposed environment")
    _require(props.get("workloadProfileName") == "Consumption", "app must select Consumption")
    config = props["configuration"]
    _keys(config, {"activeRevisionsMode", "maxInactiveRevisions", "ingress"}, "app configuration")
    _require(config.get("activeRevisionsMode") == "Single" and config.get("maxInactiveRevisions") == 1, "single revision with bounded history required")
    _require(config.get("ingress") == {"external": False, "allowInsecure": False, "transport": "http", "targetPort": 8080}, "ingress must be private with HTTPS edge and container HTTP 8080")
    _require(config["ingress"].get("external") is False and config["ingress"].get("allowInsecure") is False, "ingress flags must be literal false booleans")

    workload = props["template"]
    _keys(workload, {"containers", "scale"}, "workload")
    _require(workload.get("scale") == {"minReplicas": 0, "maxReplicas": 1, "rules": [{"name": "bounded-http", "http": {"metadata": {"concurrentRequests": "4"}}}]}, "replica/HTTP scaling boundary changed")
    containers = workload.get("containers")
    _require(isinstance(containers, list) and len(containers) == 1, "only one container is proposed")
    container = containers[0]
    _keys(container, {"name", "image", "env", "resources", "probes"}, "container")
    _require(container.get("image") == "[parameters('imageDigestRef')]", "container must use reviewed digest parameter")
    _require(container.get("resources") == {"cpu": 0.25, "memory": "0.5Gi"}, "CPU/memory boundary changed")
    _require(container.get("env") == [
        {"name": "OPTIMUS_REMOTE_CONTAINER_HTTP", "value": "true"},
        {"name": "OPTIMUS_REMOTE_CREDENTIALS_FILE", "value": "/run/optimus-remote/credentials.json"},
    ], "only explicit private HTTP and external credentials path are proposed")
    probes = container.get("probes")
    _require(isinstance(probes, list) and len(probes) == 2, "bounded TCP probes required")
    _require({p.get("type") for p in probes} == {"Startup", "Liveness"}, "only startup/liveness probes proposed")
    for probe in probes:
        _keys(probe, {"type", "tcpSocket", "periodSeconds", "timeoutSeconds", "failureThreshold"}, "probe")
        _require(probe.get("tcpSocket") == {"port": 8080}, "probes must use private TCP 8080")
        _require(probe.get("timeoutSeconds") == 1, "probe timeout boundary changed")
        period, threshold = (3, 10) if probe["type"] == "Startup" else (10, 3)
        _require(type(probe.get("periodSeconds")) is int and probe["periodSeconds"] == period, "probe period boundary changed")
        _require(type(probe.get("failureThreshold")) is int and probe["failureThreshold"] == threshold, "probe failure threshold boundary changed")

    _require(manifest.get("status") == "BLOCKED_INERT_PROPOSAL" and manifest.get("deployEnabled") is False, "manifest cannot authorize activation")
    _require(all(value is None for value in manifest.get("scope", {}).values()) and bool(manifest.get("scope")), "draft must not infer actual scope identifiers")
    for gate_name in ("permissions", "economics", "release", "credentials", "networkAndPrivacy"):
        _require(manifest.get(gate_name, {}).get("approved") is False, f"{gate_name} remains an unresolved approval gate")
    _require(manifest["economics"].get("budgetIsHardCap") is False, "budgets must not be represented as hard caps")
    _require(manifest["networkAndPrivacy"].get("externalIngress") is False, "public ingress is not authorized")
    _require(manifest["credentials"].get("containsCredentialMaterial") is False, "credential material must remain outside source")
    _require(len(manifest.get("blockers", [])) >= 7, "promotion blockers must remain explicit")
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--parameters", type=Path, default=ROOT / "parameters.draft.json")
    args = parser.parse_args()
    try:
        validate(load_json(ROOT / "main.proposal.json"), load_json(args.parameters), load_json(ROOT / "promotion-manifest.draft.json"))
    except (ProposalError, OSError, ValueError, TypeError, KeyError) as error:
        parser.exit(1, f"PROPOSAL REJECTED: {error}\n")
    print("INERT PROPOSAL OK; activation remains blocked. No Azure service validation or deployment was performed.")


if __name__ == "__main__":
    main()
