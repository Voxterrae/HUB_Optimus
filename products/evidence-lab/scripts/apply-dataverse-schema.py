from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Protocol

PACKAGE_ROOT = Path(__file__).parents[1]
CONTRACT_PATH = PACKAGE_ROOT / "contract" / "optimus-evidence-lab.dataverse.json"
PLAN_PATH = PACKAGE_ROOT / "plans" / "optimus-evidence-lab.schema-plan.json"

AUTHORIZED_BASE_COMMIT = "fc5939fe46152464378f4f09ae02824954970d83"
AUTHORIZED_CONTRACT_SHA256 = "912e762601fb3265627787dd57fb1f248929492a6bca3ba5c3d2cec5afe09e70"
AUTHORIZED_PLAN_SHA256 = "fd6751ff5fe42b0336bb3bc5b7da1d3854b78ec733afb76fc72a7f842005a981"
AUTHORIZED_BASELINE_B0_SHA256 = "3f141153424f178fae8007d0ac829932b8fff5ddecf21264c6c6b08714b0100b"
AUTHORIZED_SOLUTION = "OptimusEvidenceLab"
AUTHORIZED_PUBLISHER = "HUB_Optimus"
AUTHORIZED_PREFIX = "opt"
AUTHORIZED_VERSION = "0.1.0.0"
EXPECTED_INITIAL_COMPONENT_COUNT = 0
EXPECTED_FINAL_DIRECT_COMPONENT_COUNT = 11
EXPECTED_GLOBAL_CHOICES = 6
EXPECTED_TABLE_ROOTS = 5
EXPECTED_SCALAR_COLUMNS = 50
EXPECTED_LOOKUPS = 4
EXPECTED_ALTERNATE_KEYS = 5
EXPECTED_RELATIONSHIPS = 4
EXPECTED_ROWS = 0
BASE_LANGUAGE = 1033
SOLUTION_HEADER = "MSCRM.SolutionUniqueName"
SAFE_GUID = re.compile(r"[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}")
CONTROL_CHARACTER = re.compile(r"[\x00-\x1f\x7f]")
COMPONENT_TYPES = {
    "Table": 1,
    "Column": 2,
    "GlobalChoice": 9,
    "Relationship": 10,
    "AlternateKey": 14,
}
KEY_STATUS_NAMES = {0: "Pending", 1: "InProgress", 2: "Active", 3: "Failed"}
AUTHORIZATION_MAX_VALIDITY = timedelta(minutes=90)
AUTHORIZATION_CLOCK_SKEW = timedelta(minutes=5)
ODATA_PATH_SAFE = "/()',$=-._~:@%"
ODATA_QUERY_SAFE = "$&'()*+,-./:;=@_~%"

ROLLBACK_PATH_PATTERNS = {
    "GlobalChoice": re.compile(r"^GlobalOptionSetDefinitions\(([0-9a-fA-F-]{36})\)$"),
    "Table": re.compile(r"^EntityDefinitions\(([0-9a-fA-F-]{36})\)$"),
    "Column": re.compile(r"^EntityDefinitions\(LogicalName='[A-Za-z0-9_]+'\)/Attributes\(([0-9a-fA-F-]{36})\)$"),
    "AlternateKey": re.compile(r"^EntityDefinitions\(LogicalName='[A-Za-z0-9_]+'\)/Keys\(([0-9a-fA-F-]{36})\)$"),
    "Relationship": re.compile(r"^RelationshipDefinitions\(([0-9a-fA-F-]{36})\)$"),
}


class ApplicatorError(RuntimeError):
    pass


def canonical_bytes(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def canonical_sha256(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def label(text: str) -> dict[str, Any]:
    return {
        "@odata.type": "Microsoft.Dynamics.CRM.Label",
        "LocalizedLabels": [
            {
                "@odata.type": "Microsoft.Dynamics.CRM.LocalizedLabel",
                "Label": text,
                "LanguageCode": BASE_LANGUAGE,
            }
        ],
    }


def managed_bool(value: bool) -> dict[str, bool]:
    return {"Value": bool(value)}


def required_level(value: str) -> dict[str, Any]:
    return {
        "Value": value,
        "CanBeChanged": True,
        "ManagedPropertyLogicalName": "canmodifyrequirementlevelsettings",
    }


def parse_entity_id(headers: dict[str, str]) -> str | None:
    for name in ("OData-EntityId", "odata-entityid", "Location", "location"):
        raw = headers.get(name)
        if raw:
            match = SAFE_GUID.search(raw)
            if match:
                return match.group(0).lower()
    return None


def normalize_environment_url(value: str) -> str:
    parsed = urllib.parse.urlparse(value.strip())
    host = (parsed.hostname or "").lower()
    if (
        parsed.scheme.lower() != "https"
        or not host.endswith(".dynamics.com")
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
        or parsed.path not in {"", "/"}
    ):
        raise ApplicatorError("Environment URL must be a bare HTTPS Dataverse dynamics.com origin.")
    port = f":{parsed.port}" if parsed.port is not None else ""
    return urllib.parse.urlunsplit(("https", f"{host}{port}", "/", "", ""))


def odata_string_literal(value: str) -> str:
    if not isinstance(value, str) or not value:
        raise ApplicatorError("OData string literal must be a non-empty string.")
    if CONTROL_CHARACTER.search(value):
        raise ApplicatorError("OData string literal contains a control character.")
    return value.replace("'", "''")


def encode_odata_relative_path(path: str) -> str:
    if not isinstance(path, str) or not path:
        raise ApplicatorError("Dataverse request path must be a non-empty string.")
    if CONTROL_CHARACTER.search(path):
        raise ApplicatorError("Dataverse request path contains a control character.")
    if "\\" in path:
        raise ApplicatorError("Dataverse request path must not contain backslashes.")
    parsed = urllib.parse.urlsplit(path)
    if parsed.scheme or parsed.netloc:
        raise ApplicatorError("Dataverse request path must remain relative to the approved environment.")
    if parsed.fragment:
        raise ApplicatorError("Dataverse request path must not contain a URL fragment.")
    if any(segment == ".." for segment in parsed.path.split("/")):
        raise ApplicatorError("Dataverse request path must not traverse outside the API root.")
    encoded_path = urllib.parse.quote(parsed.path.lstrip("/"), safe=ODATA_PATH_SAFE)
    encoded_query = urllib.parse.quote(parsed.query, safe=ODATA_QUERY_SAFE)
    return urllib.parse.urlunsplit(("", "", encoded_path, encoded_query, ""))


@dataclass(frozen=True)
class Response:
    status: int
    headers: dict[str, str]
    body: Any


class Transport(Protocol):
    def request(
        self,
        method: str,
        path: str,
        *,
        body: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> Response: ...


class UrllibTransport:
    def __init__(self, environment_url: str, access_token: str, *, timeout: int = 90):
        token = access_token.strip()
        if not token:
            raise ApplicatorError("The Dataverse access token is empty.")
        self.base_url = normalize_environment_url(environment_url).rstrip("/") + "/api/data/v9.2/"
        self.access_token = token
        self.timeout = timeout

    def request(
        self,
        method: str,
        path: str,
        *,
        body: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> Response:
        url = urllib.parse.urljoin(self.base_url, encode_odata_relative_path(path))
        payload = None if body is None else json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        request_headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Accept": "application/json",
            "OData-MaxVersion": "4.0",
            "OData-Version": "4.0",
        }
        if payload is not None:
            request_headers["Content-Type"] = "application/json; charset=utf-8"
        if headers:
            request_headers.update(headers)
        request = urllib.request.Request(url, data=payload, headers=request_headers, method=method.upper())
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                raw = response.read()
                parsed = json.loads(raw.decode("utf-8")) if raw else None
                return Response(response.status, dict(response.headers.items()), parsed)
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            try:
                parsed: Any = json.loads(raw) if raw else None
            except json.JSONDecodeError:
                parsed = raw
            return Response(exc.code, dict(exc.headers.items()), parsed)


class EvidenceJournal:
    def __init__(self, output_directory: Path, *, mode: str, target: dict[str, Any]):
        self.output_directory = output_directory
        self.output_directory.mkdir(parents=True, exist_ok=True)
        self.path = self.output_directory / "metadata-apply-journal.json"
        self.data: dict[str, Any] = {
            "schemaVersion": "1.0",
            "mode": mode,
            "startedAtUtc": utc_now(),
            "target": target,
            "authorizedBaseCommit": AUTHORIZED_BASE_COMMIT,
            "contractSha256": AUTHORIZED_CONTRACT_SHA256,
            "planSha256": AUTHORIZED_PLAN_SHA256,
            "baselineB0Sha256": AUTHORIZED_BASELINE_B0_SHA256,
            "status": "STARTED",
            "created": [],
            "reused": [],
            "checks": [],
            "containsSecrets": False,
        }
        self.save()

    def check(self, name: str, result: str, details: dict[str, Any] | None = None) -> None:
        entry: dict[str, Any] = {"atUtc": utc_now(), "name": name, "result": result}
        if details:
            entry["details"] = details
        self.data["checks"].append(entry)
        self.save()

    def created(self, entry: dict[str, Any]) -> None:
        safe = {key: value for key, value in entry.items() if key not in {"accessToken", "authorization"}}
        safe["atUtc"] = utc_now()
        self.data["created"].append(safe)
        self.save()

    def reused(self, entry: dict[str, Any]) -> None:
        safe = dict(entry)
        safe["atUtc"] = utc_now()
        self.data["reused"].append(safe)
        self.save()

    def complete(self, status: str, **extra: Any) -> None:
        self.data["status"] = status
        self.data["completedAtUtc"] = utc_now()
        self.data.update(extra)
        self.save()

    def save(self) -> None:
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps(self.data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        temporary.replace(self.path)


def load_public_artifacts() -> tuple[dict[str, Any], dict[str, Any]]:
    return (
        json.loads(CONTRACT_PATH.read_text(encoding="utf-8")),
        json.loads(PLAN_PATH.read_text(encoding="utf-8")),
    )


def verify_public_artifacts(contract: dict[str, Any], plan: dict[str, Any], *, require_git_binding: bool) -> str | None:
    if canonical_sha256(contract) != AUTHORIZED_CONTRACT_SHA256:
        raise ApplicatorError("Contract hash drift.")
    if plan.get("planHash") != AUTHORIZED_PLAN_SHA256:
        raise ApplicatorError("Plan hash drift.")
    unsigned = dict(plan)
    embedded = unsigned.pop("planHash", None)
    if embedded != canonical_sha256(unsigned):
        raise ApplicatorError("The deterministic plan self-hash is invalid.")
    if plan.get("contractSha256") != AUTHORIZED_CONTRACT_SHA256:
        raise ApplicatorError("The plan is not bound to the authorized contract.")
    if plan.get("apply") is not False:
        raise ApplicatorError("The public source plan must remain non-applying.")
    solution = contract.get("solution", {})
    expected = {
        "uniqueName": AUTHORIZED_SOLUTION,
        "publisher": AUTHORIZED_PUBLISHER,
        "prefix": AUTHORIZED_PREFIX,
        "version": AUTHORIZED_VERSION,
    }
    for name, value in expected.items():
        if solution.get(name) != value:
            raise ApplicatorError(f"Solution contract drift for {name}.")
    if not require_git_binding:
        return None
    repo_root = PACKAGE_ROOT.parents[1]
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo_root, capture_output=True, text=True)
    current_head = head.stdout.strip() if head.returncode == 0 else ""
    if not re.fullmatch(r"[0-9a-f]{40}", current_head):
        raise ApplicatorError("Could not resolve the applicator Git commit.")
    critical = [CONTRACT_PATH, PLAN_PATH, Path(__file__).resolve()]
    relative = [str(path.relative_to(repo_root)) for path in critical]
    for path in relative:
        tracked = subprocess.run(["git", "ls-files", "--error-unmatch", "--", path], cwd=repo_root)
        if tracked.returncode != 0:
            raise ApplicatorError(f"Critical source is not tracked: {path}")
    for args in (("diff", "--quiet", "HEAD"), ("diff", "--cached", "--quiet", "HEAD")):
        clean = subprocess.run(["git", *args, "--", *relative], cwd=repo_root)
        if clean.returncode != 0:
            raise ApplicatorError("Critical bytes differ from the Git commit.")
    ancestor = subprocess.run(["git", "merge-base", "--is-ancestor", AUTHORIZED_BASE_COMMIT, current_head], cwd=repo_root)
    if ancestor.returncode != 0:
        raise ApplicatorError("The authorized base commit is not an ancestor of the applicator commit.")
    unchanged = subprocess.run(
        ["git", "diff", "--quiet", AUTHORIZED_BASE_COMMIT, current_head, "--", str(CONTRACT_PATH.relative_to(repo_root)), str(PLAN_PATH.relative_to(repo_root))],
        cwd=repo_root,
    )
    if unchanged.returncode != 0:
        raise ApplicatorError("The contract or plan changed after the authorized base commit.")
    return current_head


def _private_path(path: Path, *, must_exist: bool) -> Path:
    repo_root = PACKAGE_ROOT.parents[1].resolve()
    resolved = path.expanduser().resolve(strict=must_exist)
    try:
        resolved.relative_to(repo_root)
    except ValueError:
        return resolved
    raise ApplicatorError("Private authorizations and evidence must remain outside the repository.")


def _parse_time(value: Any, name: str) -> datetime:
    if not isinstance(value, str):
        raise ApplicatorError(f"Authorization requires {name}.")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ApplicatorError(f"Authorization {name} must include a timezone.")
    return parsed.astimezone(timezone.utc)


def load_authorization(
    path: Path,
    environment_url: str,
    environment_id: str,
    expected_component_count: int,
    applicator_commit: str,
    *,
    expected_mode: str,
    rollback_journal: Path | None = None,
) -> dict[str, Any]:
    path = _private_path(path, must_exist=True)
    authorization = json.loads(path.read_text(encoding="utf-8"))
    required = {
        "mode": expected_mode,
        "authorizedBaseCommit": AUTHORIZED_BASE_COMMIT,
        "contractSha256": AUTHORIZED_CONTRACT_SHA256,
        "planSha256": AUTHORIZED_PLAN_SHA256,
        "baselineB0Sha256": AUTHORIZED_BASELINE_B0_SHA256,
        "solutionUniqueName": AUTHORIZED_SOLUTION,
        "rollbackDecision": "DELETE_ONLY_CREATED_COMPONENTS_IN_REVERSE_ORDER_IF_ALL_TARGET_TABLES_HAVE_ZERO_ROWS",
        "afterBusinessRows": "NO_AUTOMATIC_METADATA_DELETION",
    }
    for key, expected in required.items():
        if authorization.get(key) != expected:
            raise ApplicatorError(f"Authorization mismatch for {key}.")
    authorization_id = str(authorization.get("authorizationId", ""))
    if not SAFE_GUID.fullmatch(authorization_id):
        raise ApplicatorError("Authorization requires a valid GUID.")
    if authorization.get("environmentUrl", "").rstrip("/") != environment_url.rstrip("/"):
        raise ApplicatorError("Authorization environment URL mismatch.")
    if authorization.get("environmentId") != environment_id:
        raise ApplicatorError("Authorization environment ID mismatch.")
    if authorization.get("applicatorCommit") != applicator_commit:
        raise ApplicatorError("Authorization applicator commit mismatch.")
    if authorization.get("expectedCurrentComponentCount") != expected_component_count:
        raise ApplicatorError("Authorization component-count mismatch.")
    now = datetime.now(timezone.utc)
    approved = _parse_time(authorization.get("approvedAtUtc"), "approvedAtUtc")
    expires = _parse_time(authorization.get("expiresAtUtc"), "expiresAtUtc")
    if approved > now + AUTHORIZATION_CLOCK_SKEW or expires <= now:
        raise ApplicatorError("Authorization timing is invalid or expired.")
    if expires <= approved or expires - approved > AUTHORIZATION_MAX_VALIDITY:
        raise ApplicatorError("Authorization validity must be no longer than 90 minutes.")
    if expected_mode == "ROLLBACK_METADATA":
        if rollback_journal is None:
            raise ApplicatorError("Rollback requires an exact journal.")
        rollback_journal = _private_path(rollback_journal, must_exist=True)
        if authorization.get("journalSha256") != hashlib.sha256(rollback_journal.read_bytes()).hexdigest():
            raise ApplicatorError("Rollback journal SHA-256 mismatch.")
    elif "journalSha256" in authorization:
        raise ApplicatorError("Apply authorization must not contain journalSha256.")
    return authorization


def string_format_name(value: str) -> str:
    return {"Text": "Text", "TextArea": "TextArea", "Url": "Url"}.get(value, "Text")


def primary_attribute_payload(table: dict[str, Any]) -> dict[str, Any]:
    item = table["primaryName"]
    return {
        "@odata.type": "Microsoft.Dynamics.CRM.StringAttributeMetadata",
        "SchemaName": item["schemaName"],
        "DisplayName": label(item["displayName"]),
        "Description": label(f"Primary name for {table['displayName']}"),
        "RequiredLevel": required_level(item["requiredLevel"]),
        "MaxLength": int(item["maxLength"]),
        "FormatName": {"Value": "Text"},
        "IsAuditEnabled": managed_bool(bool(item.get("auditEnabled", True))),
    }


def column_payload(column: dict[str, Any], choice_ids: dict[str, str]) -> dict[str, Any]:
    common: dict[str, Any] = {
        "SchemaName": column["schemaName"],
        "DisplayName": label(column["displayName"]),
        "Description": label(column["displayName"]),
        "RequiredLevel": required_level(column.get("requiredLevel", "None")),
        "IsAuditEnabled": managed_bool(bool(column.get("auditEnabled", False))),
    }
    kind = column["type"]
    if kind == "String":
        return {
            "@odata.type": "Microsoft.Dynamics.CRM.StringAttributeMetadata",
            **common,
            "MaxLength": int(column["maxLength"]),
            "FormatName": {"Value": string_format_name(column.get("format", "Text"))},
        }
    if kind == "Memo":
        return {
            "@odata.type": "Microsoft.Dynamics.CRM.MemoAttributeMetadata",
            **common,
            "MaxLength": int(column["maxLength"]),
        }
    if kind == "Boolean":
        return {
            "@odata.type": "Microsoft.Dynamics.CRM.BooleanAttributeMetadata",
            **common,
            "DefaultValue": bool(column.get("default", False)),
            "OptionSet": {
                "@odata.type": "Microsoft.Dynamics.CRM.BooleanOptionSetMetadata",
                "TrueOption": {"Value": 1, "Label": label("Yes")},
                "FalseOption": {"Value": 0, "Label": label("No")},
            },
        }
    if kind == "DateTime":
        return {
            "@odata.type": "Microsoft.Dynamics.CRM.DateTimeAttributeMetadata",
            **common,
            "Format": column.get("format", "DateOnly"),
            "DateTimeBehavior": {"Value": column.get("behavior", "DateOnly")},
        }
    if kind == "Integer":
        return {
            "@odata.type": "Microsoft.Dynamics.CRM.IntegerAttributeMetadata",
            **common,
            "MinValue": int(column["minValue"]),
            "MaxValue": int(column["maxValue"]),
            "Format": "None",
        }
    if kind == "Decimal":
        return {
            "@odata.type": "Microsoft.Dynamics.CRM.DecimalAttributeMetadata",
            **common,
            "MinValue": float(column["minValue"]),
            "MaxValue": float(column["maxValue"]),
            "Precision": int(column["precision"]),
        }
    if kind == "Choice":
        choice_name = column["globalChoice"]
        metadata_id = choice_ids.get(choice_name)
        if not metadata_id:
            raise ApplicatorError(f"Global choice metadata ID unavailable: {choice_name}")
        return {
            "@odata.type": "Microsoft.Dynamics.CRM.PicklistAttributeMetadata",
            **common,
            "GlobalOptionSet@odata.bind": f"/GlobalOptionSetDefinitions({metadata_id})",
        }
    raise ApplicatorError(f"Unsupported column type: {kind}")


def global_choice_payload(choice: dict[str, Any]) -> dict[str, Any]:
    return {
        "@odata.type": "Microsoft.Dynamics.CRM.OptionSetMetadata",
        "Name": choice["logicalName"],
        "DisplayName": label(choice["displayName"]),
        "Description": label(choice["description"]),
        "IsGlobal": True,
        "OptionSetType": "Picklist",
        "Options": [
            {
                "Value": int(option["value"]),
                "Label": label(option["label"]),
                "Description": label(option["label"]),
            }
            for option in choice["options"]
        ],
    }


def table_payload(table: dict[str, Any]) -> dict[str, Any]:
    return {
        "@odata.type": "Microsoft.Dynamics.CRM.EntityMetadata",
        "SchemaName": table["schemaName"],
        "DisplayName": label(table["displayName"]),
        "DisplayCollectionName": label(table["displayCollectionName"]),
        "Description": label(table["description"]),
        "OwnershipType": table["ownershipType"],
        "IsActivity": False,
        "HasActivities": bool(table.get("hasActivities", False)),
        "HasNotes": bool(table.get("hasNotes", False)),
        "IsAuditEnabled": managed_bool(bool(table.get("auditEnabled", True))),
        "ChangeTrackingEnabled": bool(table.get("changeTrackingEnabled", True)),
        "PrimaryAttribute": primary_attribute_payload(table),
    }


def relationship_payload(relationship: dict[str, Any]) -> dict[str, Any]:
    lookup = relationship["lookup"]
    return {
        "@odata.type": "Microsoft.Dynamics.CRM.OneToManyRelationshipMetadata",
        "SchemaName": relationship["schemaName"],
        "ReferencedEntity": relationship["referencedTable"],
        "ReferencedAttribute": relationship["referencedPrimaryKey"],
        "ReferencingEntity": relationship["referencingTable"],
        "CascadeConfiguration": {
            "Assign": "NoCascade",
            "Share": "NoCascade",
            "Unshare": "NoCascade",
            "Reparent": "NoCascade",
            "Delete": "Restrict",
            "Merge": "NoCascade",
        },
        "Lookup": {
            "@odata.type": "Microsoft.Dynamics.CRM.LookupAttributeMetadata",
            "SchemaName": lookup["schemaName"],
            "DisplayName": label(lookup["displayName"]),
            "Description": label(lookup["displayName"]),
            "RequiredLevel": required_level(lookup["requiredLevel"]),
        },
    }


class SchemaApplicator:
    def __init__(
        self,
        contract: dict[str, Any],
        plan: dict[str, Any],
        transport: Transport,
        journal: EvidenceJournal,
        *,
        apply: bool,
        expected_component_count: int = EXPECTED_INITIAL_COMPONENT_COUNT,
    ):
        self.contract = contract
        self.plan = plan
        self.transport = transport
        self.journal = journal
        self.apply = apply
        self.expected_component_count = expected_component_count
        self.solution_id: str | None = None
        self.choice_ids: dict[str, str] = {}
        self.table_ids: dict[str, str] = {}
        self.table_entity_sets: dict[str, str] = {}
        self.publication_count = 0

    def request(
        self,
        method: str,
        path: str,
        *,
        body: dict[str, Any] | None = None,
        solution_component: bool = False,
        headers: dict[str, str] | None = None,
        allowed: set[int] | None = None,
    ) -> Response:
        request_headers = dict(headers or {})
        if solution_component:
            request_headers[SOLUTION_HEADER] = AUTHORIZED_SOLUTION
        response = self.transport.request(method, path, body=body, headers=request_headers)
        accepted = allowed or ({200} if method.upper() == "GET" else {200, 201, 204})
        if response.status not in accepted:
            raise ApplicatorError(f"Dataverse {method} {path} returned {response.status}: {response.body}")
        return response

    def query_single(self, path: str, *, optional: bool = False) -> dict[str, Any] | None:
        response = self.transport.request("GET", path)
        if optional and response.status == 404:
            return None
        if response.status != 200:
            raise ApplicatorError(f"Dataverse GET {path} returned {response.status}: {response.body}")
        body = response.body or {}
        if isinstance(body, dict) and isinstance(body.get("value"), list):
            values = body["value"]
            if len(values) > 1:
                raise ApplicatorError(f"Expected one item, found {len(values)}: {path}")
            return values[0] if values else None
        if isinstance(body, dict):
            return body
        raise ApplicatorError(f"Unexpected response shape: {path}")

    def wait_for_single(
        self,
        path: str,
        *,
        description: str,
        timeout_seconds: float = 90,
        interval_seconds: float = 2,
    ) -> dict[str, Any]:
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            item = self.query_single(path, optional=True)
            if item is not None:
                return item
            time.sleep(interval_seconds)
        raise ApplicatorError(f"Timed out waiting for {description}.")

    def solution_component_records(self, metadata_id: str, component_type: int) -> list[dict[str, Any]]:
        if self.solution_id is None:
            raise ApplicatorError("Solution ID unavailable.")
        path = (
            "solutioncomponents?$select=solutioncomponentid,objectid,componenttype,"
            "rootcomponentbehavior,rootsolutioncomponentid&$top=2"
            f"&$filter=_solutionid_value eq {self.solution_id} and objectid eq {metadata_id} "
            f"and componenttype eq {component_type}"
        )
        response = self.request("GET", path, headers={"Consistency": "Strong"})
        values = (response.body or {}).get("value", [])
        if not isinstance(values, list) or len(values) > 1:
            raise ApplicatorError("Unexpected or duplicate solution-component membership.")
        return values

    @staticmethod
    def normalize_root_behavior(value: Any) -> int | None:
        if isinstance(value, dict):
            value = value.get("Value")
        if value is None:
            return None
        return int(value)

    def table_root_membership(self, table_name: str) -> dict[str, Any]:
        metadata_id = self.table_ids.get(table_name)
        if not metadata_id:
            return {"table": table_name, "included": False, "rootComponentBehavior": None}
        records = self.solution_component_records(metadata_id, COMPONENT_TYPES["Table"])
        if not records:
            return {"table": table_name, "included": False, "rootComponentBehavior": None}
        behavior = self.normalize_root_behavior(records[0].get("rootcomponentbehavior"))
        return {
            "table": table_name,
            "metadataId": metadata_id,
            "included": behavior == 0,
            "rootComponentBehavior": behavior,
        }

    def require_effective_membership(
        self,
        metadata_id: str,
        kind: str,
        description: str,
        *,
        parent_tables: tuple[str, ...] = (),
    ) -> dict[str, Any]:
        direct = self.solution_component_records(metadata_id, COMPONENT_TYPES[kind])
        if direct:
            details = {
                "kind": kind,
                "description": description,
                "metadataId": metadata_id,
                "mode": "DIRECT_SOLUTION_COMPONENT",
                "rootTable": None,
                "rootComponentBehavior": self.normalize_root_behavior(direct[0].get("rootcomponentbehavior")),
            }
            self.journal.check("Effective solution membership", "PASS", details)
            return details
        parent_states = []
        for table_name in dict.fromkeys(parent_tables):
            state = self.table_root_membership(table_name)
            parent_states.append(state)
            if state.get("included"):
                details = {
                    "kind": kind,
                    "description": description,
                    "metadataId": metadata_id,
                    "mode": "INCLUDED_VIA_TABLE_ROOT",
                    "rootTable": table_name,
                    "rootMetadataId": state.get("metadataId"),
                    "rootComponentBehavior": 0,
                }
                self.journal.check("Effective solution membership", "PASS", details)
                return details
        self.journal.check(
            "Effective solution membership",
            "FAIL",
            {
                "kind": kind,
                "description": description,
                "metadataId": metadata_id,
                "mode": "ORPHAN_METADATA",
                "parentTableStates": parent_states,
            },
        )
        raise ApplicatorError(f"Metadata is orphaned from solution {AUTHORIZED_SOLUTION}: {description}")

    def count_direct_components(self) -> int:
        if self.solution_id is None:
            raise ApplicatorError("Solution ID unavailable.")
        path = f"solutioncomponents?$select=solutioncomponentid&$filter=_solutionid_value eq {self.solution_id}"
        response = self.request("GET", path, headers={"Consistency": "Strong"})
        return len((response.body or {}).get("value", []))

    def verify_target(self) -> None:
        solution_path = (
            "solutions?$select=solutionid,uniquename,friendlyname,version,ismanaged&$top=2"
            "&$filter=uniquename eq 'OptimusEvidenceLab'"
            "&$expand=publisherid($select=uniquename,customizationprefix,customizationoptionvalueprefix)"
        )
        solution = self.query_single(solution_path)
        if solution is None:
            raise ApplicatorError("OptimusEvidenceLab solution does not exist.")
        publisher = solution.get("publisherid") or {}
        if (
            solution.get("uniquename") != AUTHORIZED_SOLUTION
            or solution.get("version") != AUTHORIZED_VERSION
            or solution.get("ismanaged") is not False
            or publisher.get("uniquename") != AUTHORIZED_PUBLISHER
            or publisher.get("customizationprefix") != AUTHORIZED_PREFIX
            or int(publisher.get("customizationoptionvalueprefix", -1)) != 88483
        ):
            raise ApplicatorError("Target solution or publisher boundary mismatch.")
        self.solution_id = str(solution["solutionid"]).lower()
        count = self.count_direct_components()
        if count != self.expected_component_count:
            raise ApplicatorError(f"Direct component-count drift: expected {self.expected_component_count}, actual {count}.")
        self.journal.check("Target solution boundary", "PASS", {"directComponents": count})

    def choice_query(self, name: str) -> str:
        literal = odata_string_literal(name)
        return (
            f"GlobalOptionSetDefinitions(Name='{literal}')"
            "?$select=MetadataId,Name,IsGlobal,OptionSetType"
        )

    def table_query(self, name: str) -> str:
        return (
            "EntityDefinitions?$select=MetadataId,LogicalName,SchemaName,EntitySetName,OwnershipType&$top=2"
            f"&$filter=LogicalName eq '{name}'"
        )

    def column_query(self, table: str, name: str) -> str:
        return (
            f"EntityDefinitions(LogicalName='{table}')/Attributes?"
            "$select=MetadataId,LogicalName,SchemaName,AttributeType&$top=2"
            f"&$filter=LogicalName eq '{name}'"
        )

    def key_query(self, table: str, schema_name: str) -> str:
        return (
            f"EntityDefinitions(LogicalName='{table}')/Keys?"
            "$select=MetadataId,SchemaName,KeyAttributes,EntityKeyIndexStatus&$top=2"
            f"&$filter=SchemaName eq '{schema_name}'"
        )

    def relationship_query(self, schema_name: str) -> str:
        return (
            "RelationshipDefinitions?$select=MetadataId,SchemaName,RelationshipType&$top=2"
            f"&$filter=SchemaName eq '{schema_name}'"
        )

    def ensure_choices(self) -> None:
        for choice in self.contract["globalChoices"]:
            name = choice["logicalName"]
            query_path = self.choice_query(name)
            existing = self.query_single(query_path, optional=True)
            if existing is None:
                if not self.apply:
                    raise ApplicatorError(f"Dry-run discovered missing global choice: {name}")
                response = self.request(
                    "POST",
                    "GlobalOptionSetDefinitions",
                    body=global_choice_payload(choice),
                    solution_component=True,
                )
                response_metadata_id = parse_entity_id(response.headers)
                created = self.wait_for_single(
                    query_path,
                    description=f"global choice {name}",
                )
                metadata_id = str(created.get("MetadataId", "")).lower()
                if (
                    response_metadata_id
                    and metadata_id
                    and response_metadata_id != metadata_id
                ):
                    raise ApplicatorError(
                        f"Created global choice metadata ID mismatch: {name}"
                    )
                if not SAFE_GUID.fullmatch(metadata_id or ""):
                    raise ApplicatorError(f"Could not resolve created global choice: {name}")
                self.journal.created({
                    "kind": "GlobalChoice",
                    "name": name,
                    "metadataId": metadata_id,
                    "deletePath": f"GlobalOptionSetDefinitions({metadata_id})",
                    "parentTables": [],
                })
            else:
                metadata_id = str(existing["MetadataId"]).lower()
                self.journal.reused({"kind": "GlobalChoice", "name": name, "metadataId": metadata_id})
            self.choice_ids[name] = metadata_id
            self.require_effective_membership(metadata_id, "GlobalChoice", name)

    def ensure_tables(self) -> None:
        for table in self.contract["tables"]:
            name = table["logicalName"]
            existing = self.query_single(self.table_query(name))
            if existing is None:
                if not self.apply:
                    raise ApplicatorError(f"Dry-run discovered missing table: {name}")
                response = self.request(
                    "POST",
                    "EntityDefinitions",
                    body=table_payload(table),
                    solution_component=True,
                )
                metadata_id = parse_entity_id(response.headers)
                if not metadata_id:
                    created = self.query_single(self.table_query(name))
                    metadata_id = str((created or {}).get("MetadataId", "")).lower()
                    existing = created
                if not SAFE_GUID.fullmatch(metadata_id or ""):
                    raise ApplicatorError(f"Could not resolve created table: {name}")
                self.journal.created({
                    "kind": "Table",
                    "name": name,
                    "metadataId": metadata_id,
                    "deletePath": f"EntityDefinitions({metadata_id})",
                    "parentTables": [name],
                })
            else:
                metadata_id = str(existing["MetadataId"]).lower()
                self.journal.reused({"kind": "Table", "name": name, "metadataId": metadata_id})
            self.table_ids[name] = metadata_id
            refreshed = self.query_single(self.table_query(name)) or existing or {}
            entity_set = str(refreshed.get("EntitySetName", ""))
            if entity_set:
                self.table_entity_sets[name] = entity_set
            membership = self.require_effective_membership(metadata_id, "Table", name)
            if membership.get("rootComponentBehavior") != 0:
                raise ApplicatorError(f"Table root must use RootComponentBehavior=0: {name}")

    def ensure_columns(self) -> None:
        for table in self.contract["tables"]:
            table_name = table["logicalName"]
            for column in table["columns"]:
                name = column["logicalName"]
                existing = self.query_single(self.column_query(table_name, name))
                if existing is None:
                    if not self.apply:
                        raise ApplicatorError(f"Dry-run discovered missing column: {table_name}.{name}")
                    response = self.request(
                        "POST",
                        f"EntityDefinitions(LogicalName='{table_name}')/Attributes",
                        body=column_payload(column, self.choice_ids),
                        solution_component=True,
                    )
                    metadata_id = parse_entity_id(response.headers)
                    if not metadata_id:
                        created = self.query_single(self.column_query(table_name, name))
                        metadata_id = str((created or {}).get("MetadataId", "")).lower()
                    if not SAFE_GUID.fullmatch(metadata_id or ""):
                        raise ApplicatorError(f"Could not resolve created column: {table_name}.{name}")
                    self.journal.created({
                        "kind": "Column",
                        "name": f"{table_name}.{name}",
                        "metadataId": metadata_id,
                        "deletePath": f"EntityDefinitions(LogicalName='{table_name}')/Attributes({metadata_id})",
                        "parentTables": [table_name],
                    })
                else:
                    metadata_id = str(existing["MetadataId"]).lower()
                    self.journal.reused({"kind": "Column", "name": f"{table_name}.{name}", "metadataId": metadata_id})
                self.require_effective_membership(metadata_id, "Column", f"{table_name}.{name}", parent_tables=(table_name,))

    def ensure_keys(self) -> None:
        for table in self.contract["tables"]:
            table_name = table["logicalName"]
            for key in table["alternateKeys"]:
                schema_name = key["schemaName"]
                existing = self.query_single(self.key_query(table_name, schema_name))
                if existing is None:
                    if not self.apply:
                        raise ApplicatorError(f"Dry-run discovered missing alternate key: {schema_name}")
                    response = self.request(
                        "POST",
                        f"EntityDefinitions(LogicalName='{table_name}')/Keys",
                        body={"SchemaName": schema_name, "KeyAttributes": key["columns"]},
                        solution_component=True,
                    )
                    metadata_id = parse_entity_id(response.headers)
                    if not metadata_id:
                        created = self.query_single(self.key_query(table_name, schema_name))
                        metadata_id = str((created or {}).get("MetadataId", "")).lower()
                    if not SAFE_GUID.fullmatch(metadata_id or ""):
                        raise ApplicatorError(f"Could not resolve alternate key: {schema_name}")
                    self.journal.created({
                        "kind": "AlternateKey",
                        "name": schema_name,
                        "metadataId": metadata_id,
                        "deletePath": f"EntityDefinitions(LogicalName='{table_name}')/Keys({metadata_id})",
                        "parentTables": [table_name],
                    })
                else:
                    metadata_id = str(existing["MetadataId"]).lower()
                    self.journal.reused({"kind": "AlternateKey", "name": schema_name, "metadataId": metadata_id})
                self.wait_key_active(table_name, schema_name)
                self.require_effective_membership(metadata_id, "AlternateKey", schema_name, parent_tables=(table_name,))

    def wait_key_active(self, table_name: str, schema_name: str, timeout_seconds: int = 600) -> None:
        deadline = time.monotonic() + timeout_seconds
        last = None
        while time.monotonic() < deadline:
            item = self.query_single(self.key_query(table_name, schema_name))
            if item is None:
                time.sleep(5)
                continue
            status = item.get("EntityKeyIndexStatus")
            if isinstance(status, dict):
                status = status.get("Value")
            if isinstance(status, int):
                status = KEY_STATUS_NAMES.get(status)
            last = status
            if status == "Active":
                self.journal.check("Alternate key active", "PASS", {"key": schema_name})
                return
            if status == "Failed":
                raise ApplicatorError(f"Alternate key activation failed: {schema_name}")
            time.sleep(5)
        raise ApplicatorError(f"Timed out waiting for alternate key {schema_name}; last status={last!r}")

    def ensure_relationships(self) -> None:
        for relationship in self.contract["relationships"]:
            schema_name = relationship["schemaName"]
            existing = self.query_single(self.relationship_query(schema_name))
            if existing is None:
                if not self.apply:
                    raise ApplicatorError(f"Dry-run discovered missing relationship: {schema_name}")
                response = self.request(
                    "POST",
                    "RelationshipDefinitions",
                    body=relationship_payload(relationship),
                    solution_component=True,
                )
                metadata_id = parse_entity_id(response.headers)
                if not metadata_id:
                    created = self.query_single(self.relationship_query(schema_name))
                    metadata_id = str((created or {}).get("MetadataId", "")).lower()
                if not SAFE_GUID.fullmatch(metadata_id or ""):
                    raise ApplicatorError(f"Could not resolve relationship: {schema_name}")
                self.journal.created({
                    "kind": "Relationship",
                    "name": schema_name,
                    "metadataId": metadata_id,
                    "deletePath": f"RelationshipDefinitions({metadata_id})",
                    "parentTables": [relationship["referencedTable"], relationship["referencingTable"]],
                })
            else:
                metadata_id = str(existing["MetadataId"]).lower()
                self.journal.reused({"kind": "Relationship", "name": schema_name, "metadataId": metadata_id})
            self.require_effective_membership(
                metadata_id,
                "Relationship",
                schema_name,
                parent_tables=(relationship["referencedTable"], relationship["referencingTable"]),
            )
            lookup_name = relationship["lookup"]["logicalName"]
            lookup = self.query_single(self.column_query(relationship["referencingTable"], lookup_name))
            if lookup is None:
                raise ApplicatorError(f"Relationship lookup is missing: {lookup_name}")
            lookup_id = str(lookup["MetadataId"]).lower()
            self.require_effective_membership(
                lookup_id,
                "Column",
                f"{relationship['referencingTable']}.{lookup_name}",
                parent_tables=(relationship["referencingTable"],),
            )

    def verify_zero_rows(self) -> None:
        for table in self.contract["tables"]:
            table_name = table["logicalName"]
            entity_set = self.table_entity_sets.get(table_name)
            if not entity_set:
                refreshed = self.query_single(self.table_query(table_name)) or {}
                entity_set = str(refreshed.get("EntitySetName", ""))
            if not entity_set:
                raise ApplicatorError(f"EntitySetName unavailable: {table_name}")
            primary_id = f"{table_name}id"
            response = self.request("GET", f"{entity_set}?$select={primary_id}&$top=1")
            if len((response.body or {}).get("value", [])) != 0:
                raise ApplicatorError(f"Target table contains rows: {table_name}")
        self.journal.check("Target rows", "PASS", {"rows": 0})

    def publish_once(self) -> None:
        if self.publication_count != 0:
            raise ApplicatorError("Publication has already been executed.")
        if not self.apply:
            raise ApplicatorError("Publish is forbidden in non-apply mode.")
        self.request("POST", "PublishAllXml", body={})
        self.publication_count += 1
        self.journal.check("PublishAllXml", "PASS", {"count": 1})

    def verify_exact_schema(self) -> None:
        self.ensure_choices()
        self.ensure_tables()
        self.ensure_columns()
        self.ensure_keys()
        self.ensure_relationships()
        self.verify_zero_rows()
        count = self.count_direct_components()
        if count != EXPECTED_FINAL_DIRECT_COMPONENT_COUNT:
            raise ApplicatorError(
                f"Expected {EXPECTED_FINAL_DIRECT_COMPONENT_COUNT} direct components, found {count}."
            )
        self.journal.check("Final direct component count", "PASS", {"count": count})

    def run(self) -> dict[str, Any]:
        self.verify_target()
        if not self.apply:
            return {
                "schemaVersion": "1.0",
                "mode": "READ_ONLY_INSPECTION",
                "status": "PASS",
                "currentDirectComponents": self.expected_component_count,
                "plannedGlobalChoices": EXPECTED_GLOBAL_CHOICES,
                "plannedTableRoots": EXPECTED_TABLE_ROOTS,
                "plannedScalarColumns": EXPECTED_SCALAR_COLUMNS,
                "plannedLookups": EXPECTED_LOOKUPS,
                "plannedAlternateKeys": EXPECTED_ALTERNATE_KEYS,
                "plannedRelationships": EXPECTED_RELATIONSHIPS,
                "expectedFinalDirectComponents": EXPECTED_FINAL_DIRECT_COMPONENT_COUNT,
                "rowsWritten": 0,
                "metadataWritesExecuted": 0,
            }
        self.ensure_choices()
        self.ensure_tables()
        self.ensure_columns()
        self.ensure_keys()
        self.ensure_relationships()
        self.verify_zero_rows()
        self.publish_once()
        self.verify_exact_schema()
        created_count = len(self.journal.data["created"])
        reused_count = len(self.journal.data["reused"])
        self.journal.complete(
            "PASS",
            result={
                "createdCount": created_count,
                "reusedCount": reused_count,
                "directComponents": self.count_direct_components(),
                "rowsCreated": 0,
                "publicationCount": self.publication_count,
            },
        )
        return self.journal.data["result"]


def table_is_absent(transport: Transport, table_name: str) -> bool:
    response = transport.request("GET", f"EntityDefinitions(LogicalName='{table_name}')?$select=MetadataId")
    return response.status == 404


def rollback_from_journal(
    transport: Transport,
    journal_path: Path,
    output_directory: Path,
) -> dict[str, Any]:
    journal_path = _private_path(journal_path, must_exist=True)
    journal = json.loads(journal_path.read_text(encoding="utf-8"))
    if journal.get("contractSha256") != AUTHORIZED_CONTRACT_SHA256 or journal.get("planSha256") != AUTHORIZED_PLAN_SHA256:
        raise ApplicatorError("Rollback journal is not bound to the authorized contract and plan.")
    created = journal.get("created")
    if not isinstance(created, list):
        raise ApplicatorError("Rollback journal has no created component list.")
    contract, _ = load_public_artifacts()
    # Zero-row gate before any delete.
    for table in contract["tables"]:
        name = table["logicalName"]
        response = transport.request("GET", f"EntityDefinitions(LogicalName='{name}')?$select=EntitySetName")
        if response.status == 404:
            continue
        if response.status != 200:
            raise ApplicatorError(f"Could not verify rows for {name}.")
        entity_set = str((response.body or {}).get("EntitySetName", ""))
        if not entity_set:
            raise ApplicatorError(f"EntitySetName unavailable for {name}.")
        rows = transport.request("GET", f"{entity_set}?$top=1")
        if rows.status != 200 or len((rows.body or {}).get("value", [])) != 0:
            raise ApplicatorError(f"Rollback blocked because {name} contains rows or cannot be verified.")
    output_directory = _private_path(output_directory, must_exist=False)
    output_directory.mkdir(parents=True, exist_ok=True)
    deleted: list[dict[str, Any]] = []
    publication_needed = False
    for entry in reversed(created):
        kind = str(entry.get("kind", ""))
        name = str(entry.get("name", ""))
        path = str(entry.get("deletePath", ""))
        parents = tuple(str(value) for value in entry.get("parentTables", []))
        pattern = ROLLBACK_PATH_PATTERNS.get(kind)
        if kind not in COMPONENT_TYPES or not path or pattern is None or pattern.fullmatch(path) is None:
            raise ApplicatorError(f"Unsafe rollback journal entry: {entry}")
        response = transport.request("DELETE", path)
        if response.status in {200, 204}:
            status = "DELETED"
            publication_needed = True
        elif response.status == 404 and parents and any(table_is_absent(transport, parent) for parent in parents):
            status = "ALREADY_ABSENT_VIA_PARENT_TABLE_ROOT"
        else:
            raise ApplicatorError(f"Rollback DELETE failed for {kind} {name}: {response.status}")
        deleted.append({"atUtc": utc_now(), "kind": kind, "name": name, "status": status})
    publication_count = 0
    if publication_needed:
        response = transport.request("POST", "PublishAllXml", body={})
        if response.status not in {200, 204}:
            raise ApplicatorError("Rollback publication failed.")
        publication_count = 1
    result = {
        "schemaVersion": "1.0",
        "mode": "ROLLBACK_METADATA",
        "status": "PASS",
        "completedAtUtc": utc_now(),
        "zeroRowsVerified": True,
        "deleted": deleted,
        "publicationCount": publication_count,
        "rowsDeleted": 0,
        "retry": False,
        "automaticRollback": False,
    }
    (output_directory / "metadata-rollback-result.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return result


def offline_review(contract: dict[str, Any], plan: dict[str, Any]) -> dict[str, Any]:
    verify_public_artifacts(contract, plan, require_git_binding=False)
    counts = plan["counts"]
    expected = {
        "globalChoices": EXPECTED_GLOBAL_CHOICES,
        "tables": EXPECTED_TABLE_ROOTS,
        "scalarColumns": EXPECTED_SCALAR_COLUMNS,
        "lookupColumns": EXPECTED_LOOKUPS,
        "alternateKeys": EXPECTED_ALTERNATE_KEYS,
        "relationships": EXPECTED_RELATIONSHIPS,
    }
    for key, value in expected.items():
        if int(counts.get(key, -1)) != value:
            raise ApplicatorError(f"Plan count mismatch for {key}.")
    return {
        "schemaVersion": "1.0",
        "mode": "OFFLINE_REVIEW",
        "status": "PASS",
        "authorizedBaseCommit": AUTHORIZED_BASE_COMMIT,
        "contractSha256": AUTHORIZED_CONTRACT_SHA256,
        "planSha256": AUTHORIZED_PLAN_SHA256,
        "baselineB0Sha256": AUTHORIZED_BASELINE_B0_SHA256,
        "counts": {
            **expected,
            "expectedFinalDirectComponents": EXPECTED_FINAL_DIRECT_COMPONENT_COUNT,
            "rows": EXPECTED_ROWS,
        },
        "apply": False,
        "metadataWritesExecuted": 0,
        "rowsWritten": 0,
        "merge": False,
        "deployment": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--environment-url")
    parser.add_argument("--environment-id")
    parser.add_argument("--access-token-file")
    parser.add_argument("--output-directory")
    parser.add_argument("--expected-component-count", type=int, default=EXPECTED_INITIAL_COMPONENT_COUNT)
    parser.add_argument("--authorization-file")
    parser.add_argument("--rollback-journal")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--rollback", action="store_true")
    parser.add_argument("--inspect", action="store_true")
    args = parser.parse_args()

    contract, plan = load_public_artifacts()
    if not any((args.apply, args.rollback, args.inspect)):
        print(json.dumps(offline_review(contract, plan), indent=2))
        return 0

    required = [args.environment_url, args.environment_id, args.access_token_file, args.output_directory]
    if not all(required):
        raise ApplicatorError("Live modes require environment, token and output arguments.")
    environment_url = normalize_environment_url(args.environment_url)
    token_path = _private_path(Path(args.access_token_file), must_exist=True)
    output_directory = _private_path(Path(args.output_directory), must_exist=False)
    output_directory.mkdir(parents=True, exist_ok=True)
    transport = UrllibTransport(environment_url, token_path.read_text(encoding="utf-8"))
    applicator_commit = verify_public_artifacts(contract, plan, require_git_binding=True)

    if args.rollback:
        if not args.authorization_file or not args.rollback_journal:
            raise ApplicatorError("Rollback requires authorization and journal.")
        load_authorization(
            Path(args.authorization_file),
            environment_url,
            args.environment_id,
            args.expected_component_count,
            applicator_commit or "",
            expected_mode="ROLLBACK_METADATA",
            rollback_journal=Path(args.rollback_journal),
        )
        result = rollback_from_journal(transport, Path(args.rollback_journal), output_directory)
        print(json.dumps(result, indent=2))
        return 0

    if args.apply:
        if not args.authorization_file:
            raise ApplicatorError("Apply requires a private authorization file.")
        load_authorization(
            Path(args.authorization_file),
            environment_url,
            args.environment_id,
            args.expected_component_count,
            applicator_commit or "",
            expected_mode="APPLY_METADATA",
        )

    journal = EvidenceJournal(
        output_directory,
        mode="APPLY_METADATA" if args.apply else "READ_ONLY_INSPECTION",
        target={
            "environmentUrl": environment_url,
            "environmentId": args.environment_id,
            "solution": AUTHORIZED_SOLUTION,
            "applicatorCommit": applicator_commit,
        },
    )
    applicator = SchemaApplicator(
        contract,
        plan,
        transport,
        journal,
        apply=args.apply,
        expected_component_count=args.expected_component_count,
    )
    result = applicator.run()
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
