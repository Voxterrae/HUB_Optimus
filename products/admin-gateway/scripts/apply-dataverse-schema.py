from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Protocol

PACKAGE_ROOT = Path(__file__).parents[1]
CONTRACT_PATH = PACKAGE_ROOT / "dataverse" / "schema" / "optimus-admin-gateway.dataverse.json"
PLAN_PATH = PACKAGE_ROOT / "dataverse" / "plans" / "optimus-admin-gateway.schema-plan.json"

AUTHORIZED_BASE_COMMIT = "4aab546e503e7bb2fda253eb0b20741b25b13a47"
AUTHORIZED_CONTRACT_SHA256 = "ad0275c652f8877c2fc091dcdf66c8ab5fea6db3b2d4b64e847e17716c549d1d"
AUTHORIZED_PLAN_SHA256 = "dd1a4c4d2ab24f224172bb8f87f6c89d89f09e86ea36cc3886e8551d12751a06"
AUTHORIZED_SOLUTION = "OptimusAdminGateway"
AUTHORIZED_PUBLISHER = "HUB_Optimus"
AUTHORIZED_PREFIX = "opt"
AUTHORIZED_VERSION = "0.1.0.0"
EXPECTED_INITIAL_COMPONENT_COUNT = 0
BASE_LANGUAGE = 1033
SOLUTION_HEADER = "MSCRM.SolutionUniqueName"
SAFE_GUID = re.compile(r"[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}")
TRANSIENT_CODES = ("0x80040216", "0x80060891")
COMPONENT_TYPES = {
    "Table": 1,
    "Column": 2,
    "GlobalChoice": 9,
    "Relationship": 10,
    "AlternateKey": 14,
}
KEY_STATUS_NAMES = {0: "Pending", 1: "InProgress", 2: "Active", 3: "Failed"}
MAX_AUTHORIZATION_VALIDITY = timedelta(hours=4)
AUTHORIZATION_CLOCK_SKEW = timedelta(minutes=5)
ROLLBACK_PATH_PATTERNS = {
    "GlobalChoice": re.compile(r"^GlobalOptionSetDefinitions\(([0-9a-fA-F-]{36})\)$"),
    "Table": re.compile(r"^EntityDefinitions\(([0-9a-fA-F-]{36})\)$"),
    "Column": re.compile(
        r"^EntityDefinitions\(LogicalName='[A-Za-z0-9_]+'\)/Attributes\(([0-9a-fA-F-]{36})\)$"
    ),
    "AlternateKey": re.compile(
        r"^EntityDefinitions\(LogicalName='[A-Za-z0-9_]+'\)/Keys\(([0-9a-fA-F-]{36})\)$"
    ),
    "Relationship": re.compile(r"^RelationshipDefinitions\(([0-9a-fA-F-]{36})\)$"),
}


def canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def canonical_sha256(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def label(text: str, language_code: int = BASE_LANGUAGE) -> dict[str, Any]:
    return {
        "@odata.type": "Microsoft.Dynamics.CRM.Label",
        "LocalizedLabels": [
            {
                "@odata.type": "Microsoft.Dynamics.CRM.LocalizedLabel",
                "Label": text,
                "LanguageCode": language_code,
            }
        ],
    }


def managed_bool(value: bool) -> dict[str, bool]:
    return {"Value": bool(value)}


def required_level(value: str) -> dict[str, str]:
    return {"Value": value}


def normalize_managed_bool(value: Any) -> bool:
    if isinstance(value, dict):
        return bool(value.get("Value"))
    return bool(value)




def localized_label_text(value: Any, language_code: int = BASE_LANGUAGE) -> str | None:
    if not isinstance(value, dict):
        return None
    for item in value.get("LocalizedLabels", []):
        if int(item.get("LanguageCode", -1)) == language_code:
            return item.get("Label")
    user = value.get("UserLocalizedLabel")
    if isinstance(user, dict):
        return user.get("Label")
    return None


def normalize_required_level(value: Any) -> str | None:
    if isinstance(value, dict):
        return value.get("Value")
    return value if isinstance(value, str) else None


def normalize_named_value(value: Any) -> str | None:
    if isinstance(value, dict):
        return value.get("Value")
    return value if isinstance(value, str) else None


def normalize_key_index_status(value: Any) -> str | None:
    if isinstance(value, str):
        return value
    if isinstance(value, int):
        return KEY_STATUS_NAMES.get(value)
    return None


def parse_entity_id(headers: dict[str, str]) -> str | None:
    for name in ("OData-EntityId", "odata-entityid", "Location", "location"):
        raw = headers.get(name)
        if raw:
            match = SAFE_GUID.search(raw)
            if match:
                return match.group(0).lower()
    return None


def escape_odata_string(value: str) -> str:
    return value.replace("'", "''")


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


class ApplicatorError(RuntimeError):
    pass


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
    def __init__(self, environment_url: str, access_token: str, *, timeout: int = 90, max_attempts: int = 6):
        token = access_token.strip()
        if not token:
            raise ApplicatorError("The Dataverse access token is empty.")
        self.base_url = environment_url.rstrip("/") + "/api/data/v9.2/"
        self.access_token = token
        self.timeout = timeout
        self.max_attempts = max_attempts

    def request(
        self,
        method: str,
        path: str,
        *,
        body: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> Response:
        url = urllib.parse.urljoin(self.base_url, path.lstrip("/"))
        payload = None if body is None else json.dumps(body, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
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

        last_error: Exception | None = None
        for attempt in range(1, self.max_attempts + 1):
            request = urllib.request.Request(url, data=payload, headers=request_headers, method=method.upper())
            try:
                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    raw = response.read()
                    parsed: Any = None
                    if raw:
                        parsed = json.loads(raw.decode("utf-8"))
                    return Response(response.status, dict(response.headers.items()), parsed)
            except urllib.error.HTTPError as exc:
                raw = exc.read().decode("utf-8", errors="replace")
                parsed: Any = raw
                try:
                    parsed = json.loads(raw) if raw else None
                except json.JSONDecodeError:
                    pass
                text = raw.lower()
                retry_after = exc.headers.get("Retry-After")
                transient = exc.code in {429, 502, 503, 504} or any(code.lower() in text for code in TRANSIENT_CODES)
                if transient and attempt < self.max_attempts:
                    delay = int(retry_after) if retry_after and retry_after.isdigit() else min(2**attempt, 20)
                    time.sleep(delay)
                    continue
                return Response(exc.code, dict(exc.headers.items()), parsed)
            except (urllib.error.URLError, TimeoutError) as exc:
                last_error = exc
                if attempt < self.max_attempts:
                    time.sleep(min(2**attempt, 20))
                    continue
                break
        raise ApplicatorError(f"Dataverse request failed after retries: {method} {path}: {last_error}")


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
        safe_entry = {key: value for key, value in entry.items() if key not in {"accessToken", "authorization"}}
        safe_entry["atUtc"] = utc_now()
        self.data["created"].append(safe_entry)
        self.save()

    def reused(self, entry: dict[str, Any]) -> None:
        safe_entry = dict(entry)
        safe_entry["atUtc"] = utc_now()
        self.data["reused"].append(safe_entry)
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
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    plan = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
    return contract, plan


def verify_public_artifacts(
    contract: dict[str, Any], plan: dict[str, Any], *, require_git_binding: bool
) -> str | None:
    actual_contract_hash = canonical_sha256(contract)
    if actual_contract_hash != AUTHORIZED_CONTRACT_SHA256:
        raise ApplicatorError(
            f"Contract hash drift. Expected {AUTHORIZED_CONTRACT_SHA256}, actual {actual_contract_hash}."
        )
    if plan.get("planHash") != AUTHORIZED_PLAN_SHA256:
        raise ApplicatorError(
            f"Plan hash drift. Expected {AUTHORIZED_PLAN_SHA256}, actual {plan.get('planHash')}."
        )
    unsigned_plan = dict(plan)
    embedded_plan_hash = unsigned_plan.pop("planHash", None)
    if embedded_plan_hash != canonical_sha256(unsigned_plan):
        raise ApplicatorError("The deterministic plan self-hash is invalid.")
    if plan.get("contractSha256") != AUTHORIZED_CONTRACT_SHA256:
        raise ApplicatorError("The plan is not bound to the authorized contract hash.")
    if plan.get("apply") is not False or plan.get("mode") != "DRY_RUN":
        raise ApplicatorError("The source plan must remain a non-applying DRY_RUN artifact.")
    solution = contract.get("solution", {})
    expected_solution = {
        "uniqueName": AUTHORIZED_SOLUTION,
        "publisher": AUTHORIZED_PUBLISHER,
        "prefix": AUTHORIZED_PREFIX,
        "version": AUTHORIZED_VERSION,
    }
    for key, expected in expected_solution.items():
        if solution.get(key) != expected:
            raise ApplicatorError(f"Solution contract drift for {key}: {solution.get(key)!r}")
    if not require_git_binding:
        return None
    repo_root = PACKAGE_ROOT.parents[1]
    head_result = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo_root, capture_output=True, text=True
    )
    current_head = head_result.stdout.strip() if head_result.returncode == 0 else ""
    if not re.fullmatch(r"[0-9a-f]{40}", current_head):
        raise ApplicatorError("Could not resolve the applicator Git commit.")
    critical_paths = [CONTRACT_PATH, PLAN_PATH, Path(__file__).resolve()]
    relative_critical_paths = [str(path.relative_to(repo_root)) for path in critical_paths]
    for relative_path in relative_critical_paths:
        tracked = subprocess.run(
            ["git", "ls-files", "--error-unmatch", "--", relative_path],
            cwd=repo_root,
            capture_output=True,
        )
        if tracked.returncode != 0:
            raise ApplicatorError(f"Critical applicator source is not tracked: {relative_path}")
    for diff_args in (("diff", "--quiet", "HEAD"), ("diff", "--cached", "--quiet", "HEAD")):
        clean = subprocess.run(
            ["git", *diff_args, "--", *relative_critical_paths],
            cwd=repo_root,
            capture_output=True,
        )
        if clean.returncode != 0:
            raise ApplicatorError("Critical applicator, contract or plan bytes differ from the authorized Git commit.")
    ancestor = subprocess.run(
        ["git", "merge-base", "--is-ancestor", AUTHORIZED_BASE_COMMIT, current_head],
        cwd=repo_root,
        capture_output=True,
    )
    if ancestor.returncode != 0:
        raise ApplicatorError("The authorized base commit is not an ancestor of the applicator commit.")
    unchanged = subprocess.run(
        [
            "git",
            "diff",
            "--quiet",
            AUTHORIZED_BASE_COMMIT,
            current_head,
            "--",
            str(CONTRACT_PATH.relative_to(repo_root)),
            str(PLAN_PATH.relative_to(repo_root)),
        ],
        cwd=repo_root,
    )
    if unchanged.returncode != 0:
        raise ApplicatorError("The contract or plan changed after the authorized base commit.")
    return current_head


def _require_private_path(path: Path, *, description: str, must_exist: bool) -> Path:
    repo_root = PACKAGE_ROOT.parents[1].resolve()
    resolved = path.expanduser().resolve(strict=must_exist)
    try:
        resolved.relative_to(repo_root)
    except ValueError:
        return resolved
    raise ApplicatorError(f"{description} must remain outside the repository: {resolved}")


def _parse_authorization_time(value: Any, *, name: str) -> datetime:
    if not isinstance(value, str):
        raise ApplicatorError(f"Authorization requires {name}.")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ApplicatorError(f"Authorization {name} is not a valid timestamp.") from exc
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
    path = _require_private_path(path, description="Authorization file", must_exist=True)
    authorization = json.loads(path.read_text(encoding="utf-8"))
    required = {
        "mode": expected_mode,
        "authorizedBaseCommit": AUTHORIZED_BASE_COMMIT,
        "contractSha256": AUTHORIZED_CONTRACT_SHA256,
        "planSha256": AUTHORIZED_PLAN_SHA256,
        "solutionUniqueName": AUTHORIZED_SOLUTION,
        "rollbackDecision": "DELETE_ONLY_CREATED_COMPONENTS_IN_REVERSE_ORDER_IF_ALL_TARGET_TABLES_HAVE_ZERO_ROWS",
        "afterBusinessRows": "NO_AUTOMATIC_METADATA_DELETION",
    }
    for key, expected in required.items():
        if authorization.get(key) != expected:
            raise ApplicatorError(f"Authorization mismatch for {key}.")
    authorization_id = str(authorization.get("authorizationId", ""))
    if not SAFE_GUID.fullmatch(authorization_id):
        raise ApplicatorError("Authorization requires a valid authorizationId GUID.")
    approved_by = authorization.get("approvedBy")
    if not isinstance(approved_by, str) or not approved_by.strip():
        raise ApplicatorError("Authorization requires approvedBy.")
    if authorization.get("environmentUrl", "").rstrip("/") != environment_url.rstrip("/"):
        raise ApplicatorError("Authorization environment URL mismatch.")
    if authorization.get("environmentId") != environment_id:
        raise ApplicatorError("Authorization environment ID mismatch.")
    if authorization.get("applicatorCommit") != applicator_commit:
        raise ApplicatorError("Authorization applicator-commit mismatch.")
    if authorization.get("expectedCurrentComponentCount") != expected_component_count:
        raise ApplicatorError("Authorization component-count boundary mismatch.")

    now = datetime.now(timezone.utc)
    approved_at = _parse_authorization_time(authorization.get("approvedAtUtc"), name="approvedAtUtc")
    expires = _parse_authorization_time(authorization.get("expiresAtUtc"), name="expiresAtUtc")
    if approved_at > now + AUTHORIZATION_CLOCK_SKEW:
        raise ApplicatorError("Authorization approval time is in the future.")
    if expires <= now:
        raise ApplicatorError("Authorization has expired.")
    if expires <= approved_at or expires - approved_at > MAX_AUTHORIZATION_VALIDITY:
        raise ApplicatorError("Authorization validity must be positive and no longer than four hours.")

    if expected_mode == "ROLLBACK_METADATA":
        if rollback_journal is None:
            raise ApplicatorError("Rollback authorization requires an exact journal path.")
        rollback_journal = _require_private_path(
            rollback_journal, description="Rollback journal", must_exist=True
        )
        journal_sha = hashlib.sha256(rollback_journal.read_bytes()).hexdigest()
        if authorization.get("journalSha256") != journal_sha:
            raise ApplicatorError("Rollback authorization journal SHA-256 mismatch.")
    elif "journalSha256" in authorization:
        raise ApplicatorError("Apply authorization must not contain journalSha256.")
    return authorization


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
        self.choice_metadata_ids: dict[str, str] = {}
        self.table_metadata_ids: dict[str, str] = {}
        self.missing_tables: set[str] = set()
        self.record_reuse = True
        self.require_present = False

    def _request(
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
        accepted = allowed or ({200, 201, 204} if method.upper() != "GET" else {200})
        if response.status not in accepted:
            detail = response.body
            raise ApplicatorError(f"Dataverse {method} {path} returned {response.status}: {detail}")
        return response

    def _query_single(self, path: str) -> dict[str, Any] | None:
        response = self._request("GET", path)
        body = response.body or {}
        if isinstance(body, dict) and isinstance(body.get("value"), list):
            values = body["value"]
            if len(values) > 1:
                raise ApplicatorError(f"Expected one metadata item, found {len(values)}: {path}")
            return values[0] if values else None
        if isinstance(body, dict):
            return body
        raise ApplicatorError(f"Unexpected Dataverse response shape: {path}")

    def _query_single_optional(self, path: str) -> dict[str, Any] | None:
        response = self.transport.request("GET", path)
        if response.status == 404:
            return None
        if response.status != 200:
            raise ApplicatorError(f"Dataverse GET {path} returned {response.status}: {response.body}")
        body = response.body or {}
        if isinstance(body, dict) and isinstance(body.get("value"), list):
            values = body["value"]
            if len(values) > 1:
                raise ApplicatorError(f"Expected one metadata item, found {len(values)}: {path}")
            return values[0] if values else None
        if isinstance(body, dict):
            return body
        raise ApplicatorError(f"Unexpected Dataverse response shape: {path}")

    def _wait_for_single(
        self, path: str, *, description: str, timeout_seconds: int = 180, interval_seconds: int = 5
    ) -> dict[str, Any]:
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            item = self._query_single_optional(path)
            if item is not None:
                return item
            time.sleep(interval_seconds)
        raise ApplicatorError(f"Timed out waiting for Dataverse metadata propagation: {description}")

    def _solution_component_query(self, metadata_id: str, component_type: int) -> str:
        if self.solution_id is None:
            raise ApplicatorError("Target solution ID is unavailable.")
        return (
            "solutioncomponents?$select=solutioncomponentid,objectid,componenttype&$top=2"
            f"&$filter=_solutionid_value eq {self.solution_id} "
            f"and objectid eq {metadata_id} and componenttype eq {component_type}"
        )

    def _require_solution_membership(
        self, metadata_id: str, kind: str, description: str, *, wait: bool = False
    ) -> None:
        component_type = COMPONENT_TYPES[kind]
        deadline = time.monotonic() + (180 if wait else 0)
        while True:
            response = self._request(
                "GET",
                self._solution_component_query(metadata_id, component_type),
                headers={"ConsistencyLevel": "eventual"},
            )
            values = (response.body or {}).get("value", [])
            if values:
                return
            if not wait or time.monotonic() >= deadline:
                raise ApplicatorError(
                    f"Existing {description} is not a component of solution {AUTHORIZED_SOLUTION}."
                )
            time.sleep(5)

    def _record_reused(self, entry: dict[str, Any]) -> None:
        if self.record_reuse:
            self.journal.reused(entry)

    def _missing(self, kind: str, name: str, *, details: dict[str, Any] | None = None) -> None:
        if self.require_present:
            raise ApplicatorError(f"Post-apply verification could not find {kind}: {name}")
        payload = {"name": name}
        if details:
            payload.update(details)
        self.journal.check(f"{kind} missing", "WOULD_CREATE", payload)

    def verify_target(self) -> None:
        solution_name = escape_odata_string(AUTHORIZED_SOLUTION)
        path = (
            "solutions?$select=solutionid,uniquename,friendlyname,version,ismanaged"
            f"&$filter=uniquename eq '{solution_name}'"
            "&$expand=publisherid($select=uniquename,customizationprefix,customizationoptionvalueprefix)"
        )
        solution = self._query_single(path)
        if solution is None:
            raise ApplicatorError("Authorized solution was not found.")
        publisher = solution.get("publisherid") or {}
        checks = {
            "uniquename": AUTHORIZED_SOLUTION,
            "version": AUTHORIZED_VERSION,
            "ismanaged": False,
        }
        for key, expected in checks.items():
            if solution.get(key) != expected:
                raise ApplicatorError(f"Target solution drift for {key}: {solution.get(key)!r}")
        if publisher.get("uniquename") != AUTHORIZED_PUBLISHER:
            raise ApplicatorError("Target publisher unique name drift.")
        if publisher.get("customizationprefix") != AUTHORIZED_PREFIX:
            raise ApplicatorError("Target publisher prefix drift.")
        if int(publisher.get("customizationoptionvalueprefix", -1)) != self.contract["solution"]["choiceValuePrefix"]:
            raise ApplicatorError("Target publisher choice-value prefix drift.")
        solution_id = str(solution.get("solutionid", "")).lower()
        if not SAFE_GUID.fullmatch(solution_id):
            raise ApplicatorError("Could not resolve the target solution ID.")
        self.solution_id = solution_id

        component_path = (
            "solutioncomponents?$select=solutioncomponentid&$count=true&$top=1"
            f"&$filter=_solutionid_value eq {solution_id}"
        )
        response = self._request("GET", component_path, headers={"ConsistencyLevel": "eventual"})
        body = response.body or {}
        count = int(body.get("@odata.count", len(body.get("value", []))))
        if count != self.expected_component_count:
            raise ApplicatorError(
                f"Solution component count drift. Expected {self.expected_component_count}, actual {count}."
            )
        self.journal.check(
            "Target solution and component boundary",
            "PASS",
            {
                "solution": AUTHORIZED_SOLUTION,
                "publisher": AUTHORIZED_PUBLISHER,
                "prefix": AUTHORIZED_PREFIX,
                "version": AUTHORIZED_VERSION,
                "currentComponentCount": count,
            },
        )

    def _global_choice_path(self, logical_name: str) -> str:
        name = escape_odata_string(logical_name)
        # GlobalOptionSetDefinitions does not support $filter. Retrieve the
        # exact choice through its documented Name alternate key. The direct
        # response includes the derived OptionSetMetadata properties, including
        # Options, and returns 404 when the named choice is absent.
        return f"GlobalOptionSetDefinitions(Name='{name}')"

    @staticmethod
    def _choice_payload(choice: dict[str, Any]) -> dict[str, Any]:
        return {
            "@odata.type": "Microsoft.Dynamics.CRM.OptionSetMetadata",
            "Name": choice["logicalName"],
            "DisplayName": label(choice["displayName"]),
            "Description": label(choice["description"]),
            "OptionSetType": "Picklist",
            "Options": [
                {
                    "Value": option["value"],
                    "Label": label(option["label"]),
                }
                for option in choice["options"]
            ],
        }

    def _validate_global_choice(self, choice: dict[str, Any], existing: dict[str, Any]) -> str:
        metadata_id = str(existing.get("MetadataId", "")).lower()
        if not SAFE_GUID.fullmatch(metadata_id):
            raise ApplicatorError(f"Global choice metadata ID missing: {choice['logicalName']}")
        if existing.get("Name") != choice["logicalName"] or existing.get("IsGlobal") is not True:
            raise ApplicatorError(f"Global choice drift: {choice['logicalName']}")
        actual_options = {
            int(option["Value"]): localized_label_text(option.get("Label"))
            for option in existing.get("Options", [])
        }
        expected_options = {int(option["value"]): option["label"] for option in choice["options"]}
        if actual_options != expected_options:
            raise ApplicatorError(f"Global choice option drift: {choice['logicalName']}")
        return metadata_id

    def ensure_global_choice(self, choice: dict[str, Any]) -> None:
        choice_path = self._global_choice_path(choice["logicalName"])
        lookup = self.transport.request("GET", choice_path)
        if lookup.status == 200:
            existing = lookup.body or {}
            metadata_id = self._validate_global_choice(choice, existing)
            self._require_solution_membership(
                metadata_id, "GlobalChoice", f"global choice {choice['logicalName']}"
            )
            self.choice_metadata_ids[choice["logicalName"]] = metadata_id
            self._record_reused(
                {"kind": "GlobalChoice", "name": choice["logicalName"], "metadataId": metadata_id}
            )
            return
        if lookup.status != 404:
            raise ApplicatorError(
                f"Global choice lookup failed: {choice['logicalName']}: {lookup.status} {lookup.body}"
            )
        if not self.apply:
            self._missing("Global choice", choice["logicalName"])
            return
        response = self._request(
            "POST",
            "GlobalOptionSetDefinitions",
            body=self._choice_payload(choice),
            solution_component=True,
        )
        metadata_id = parse_entity_id(response.headers)
        created = self._wait_for_single(choice_path, description=f"global choice {choice['logicalName']}")
        verified_id = self._validate_global_choice(choice, created)
        metadata_id = metadata_id or verified_id
        if metadata_id != verified_id:
            raise ApplicatorError(f"Global choice identity mismatch after create: {choice['logicalName']}")
        self._require_solution_membership(
            metadata_id, "GlobalChoice", f"global choice {choice['logicalName']}", wait=True
        )
        self.choice_metadata_ids[choice["logicalName"]] = metadata_id
        self.journal.created(
            {
                "kind": "GlobalChoice",
                "name": choice["logicalName"],
                "metadataId": metadata_id,
                "rollbackPath": f"GlobalOptionSetDefinitions({metadata_id})",
            }
        )

    @staticmethod
    def _primary_column_payload(primary: dict[str, Any]) -> dict[str, Any]:
        return {
            "@odata.type": "Microsoft.Dynamics.CRM.StringAttributeMetadata",
            "AttributeType": "String",
            "AttributeTypeName": {"Value": "StringType"},
            "SchemaName": primary["schemaName"],
            "DisplayName": label(primary["displayName"]),
            "RequiredLevel": required_level(primary["requiredLevel"]),
            "MaxLength": primary["maxLength"],
            "FormatName": {"Value": "Text"},
            "IsPrimaryName": True,
            "IsAuditEnabled": managed_bool(primary["auditEnabled"]),
        }

    @classmethod
    def _table_payload(cls, table: dict[str, Any]) -> dict[str, Any]:
        return {
            "@odata.type": "Microsoft.Dynamics.CRM.EntityMetadata",
            "SchemaName": table["schemaName"],
            "EntitySetName": table["entitySetName"],
            "DisplayName": label(table["displayName"]),
            "DisplayCollectionName": label(table["displayCollectionName"]),
            "Description": label(table["description"]),
            "OwnershipType": table["ownershipType"],
            "IsActivity": False,
            "HasActivities": table["hasActivities"],
            "HasNotes": table["hasNotes"],
            "IsAuditEnabled": managed_bool(table["auditEnabled"]),
            "ChangeTrackingEnabled": table["changeTrackingEnabled"],
            "Attributes": [cls._primary_column_payload(table["primaryName"])],
        }

    def _table_path(self, logical_name: str) -> str:
        escaped = escape_odata_string(logical_name)
        return (
            f"EntityDefinitions(LogicalName='{escaped}')"
            "?$select=MetadataId,LogicalName,SchemaName,EntitySetName,OwnershipType,PrimaryNameAttribute,"
            "IsAuditEnabled,ChangeTrackingEnabled,HasActivities,HasNotes"
        )

    def _validate_table(self, table: dict[str, Any], existing: dict[str, Any]) -> str:
        expected = {
            "LogicalName": table["logicalName"],
            "SchemaName": table["schemaName"],
            "EntitySetName": table["entitySetName"],
            "OwnershipType": table["ownershipType"],
            "PrimaryNameAttribute": table["primaryName"]["logicalName"],
            "HasActivities": table["hasActivities"],
            "HasNotes": table["hasNotes"],
            "ChangeTrackingEnabled": table["changeTrackingEnabled"],
        }
        for key, expected_value in expected.items():
            if existing.get(key) != expected_value:
                raise ApplicatorError(f"Table drift {table['logicalName']}.{key}: {existing.get(key)!r}")
        if normalize_managed_bool(existing.get("IsAuditEnabled")) != table["auditEnabled"]:
            raise ApplicatorError(f"Table audit drift: {table['logicalName']}")
        metadata_id = str(existing.get("MetadataId", "")).lower()
        if not SAFE_GUID.fullmatch(metadata_id):
            raise ApplicatorError(f"Table metadata ID missing: {table['logicalName']}")
        return metadata_id

    def ensure_table(self, table: dict[str, Any]) -> None:
        response = self.transport.request("GET", self._table_path(table["logicalName"]))
        if response.status == 200:
            existing = response.body or {}
            metadata_id = self._validate_table(table, existing)
            self._require_solution_membership(metadata_id, "Table", f"table {table['logicalName']}")
            self.table_metadata_ids[table["logicalName"]] = metadata_id
            self.missing_tables.discard(table["logicalName"])
            self._record_reused(
                {"kind": "Table", "name": table["logicalName"], "metadataId": metadata_id}
            )
            return
        if response.status != 404:
            raise ApplicatorError(f"Table lookup failed: {table['logicalName']}: {response.status} {response.body}")
        if not self.apply:
            self.missing_tables.add(table["logicalName"])
            self._missing("Table", table["logicalName"])
            return
        created_response = self._request(
            "POST", "EntityDefinitions", body=self._table_payload(table), solution_component=True
        )
        metadata_id = parse_entity_id(created_response.headers)
        verified = self._wait_for_single(
            self._table_path(table["logicalName"]), description=f"table {table['logicalName']}"
        )
        verified_id = self._validate_table(table, verified)
        metadata_id = metadata_id or verified_id
        if metadata_id != verified_id:
            raise ApplicatorError(f"Table identity mismatch after create: {table['logicalName']}")
        self._require_solution_membership(
            metadata_id, "Table", f"table {table['logicalName']}", wait=True
        )
        self.table_metadata_ids[table["logicalName"]] = metadata_id
        self.missing_tables.discard(table["logicalName"])
        self.journal.created(
            {
                "kind": "Table",
                "name": table["logicalName"],
                "metadataId": metadata_id,
                "rollbackPath": f"EntityDefinitions({metadata_id})",
            }
        )

    def verify_primary_column(self, table: dict[str, Any]) -> None:
        table_name = escape_odata_string(table["logicalName"])
        primary = table["primaryName"]
        column_name = escape_odata_string(primary["logicalName"])
        path = (
            f"EntityDefinitions(LogicalName='{table_name}')/Attributes(LogicalName='{column_name}')/"
            "Microsoft.Dynamics.CRM.StringAttributeMetadata"
            "?$select=MetadataId,LogicalName,SchemaName,RequiredLevel,MaxLength,FormatName,IsAuditEnabled,IsPrimaryName"
        )
        response = self._request("GET", path)
        existing = response.body or {}
        if existing.get("LogicalName") != primary["logicalName"]:
            raise ApplicatorError(f"Primary column logical-name drift: {table['logicalName']}")
        if existing.get("SchemaName") != primary["schemaName"]:
            raise ApplicatorError(f"Primary column schema-name drift: {table['logicalName']}")
        if normalize_required_level(existing.get("RequiredLevel")) != primary["requiredLevel"]:
            raise ApplicatorError(f"Primary column required-level drift: {table['logicalName']}")
        if int(existing.get("MaxLength", -1)) != primary["maxLength"]:
            raise ApplicatorError(f"Primary column length drift: {table['logicalName']}")
        if normalize_named_value(existing.get("FormatName")) != "Text":
            raise ApplicatorError(f"Primary column format drift: {table['logicalName']}")
        if normalize_managed_bool(existing.get("IsAuditEnabled")) != primary["auditEnabled"]:
            raise ApplicatorError(f"Primary column audit drift: {table['logicalName']}")
        if existing.get("IsPrimaryName") is not True:
            raise ApplicatorError(f"Primary column flag drift: {table['logicalName']}")
        self.journal.check("Primary column exact match", "PASS", {"table": table["logicalName"]})

    @staticmethod
    def _column_type_cast(column_type: str) -> str:
        return {
            "String": "Microsoft.Dynamics.CRM.StringAttributeMetadata",
            "Memo": "Microsoft.Dynamics.CRM.MemoAttributeMetadata",
            "Boolean": "Microsoft.Dynamics.CRM.BooleanAttributeMetadata",
            "Choice": "Microsoft.Dynamics.CRM.PicklistAttributeMetadata",
            "DateTime": "Microsoft.Dynamics.CRM.DateTimeAttributeMetadata",
        }[column_type]

    @staticmethod
    def _expected_attribute_type(column_type: str) -> str:
        return {
            "String": "String",
            "Memo": "Memo",
            "Boolean": "Boolean",
            "Choice": "Picklist",
            "DateTime": "DateTime",
        }[column_type]

    def _column_base_path(self, table: dict[str, Any], column: dict[str, Any]) -> str:
        table_name = escape_odata_string(table["logicalName"])
        column_name = escape_odata_string(column["logicalName"])
        return (
            f"EntityDefinitions(LogicalName='{table_name}')/Attributes(LogicalName='{column_name}')"
            "?$select=MetadataId,LogicalName,SchemaName,AttributeType"
        )

    def _column_path(self, table: dict[str, Any], column: dict[str, Any]) -> str:
        table_name = escape_odata_string(table["logicalName"])
        column_name = escape_odata_string(column["logicalName"])
        cast = self._column_type_cast(column["type"])
        select = "MetadataId,LogicalName,SchemaName,AttributeType,RequiredLevel,IsAuditEnabled"
        if column["type"] == "String":
            select += ",MaxLength,FormatName"
        if column["type"] == "Memo":
            select += ",MaxLength,Format"
        if column["type"] == "Boolean":
            select += ",DefaultValue"
        if column["type"] == "Choice":
            select += ",DefaultFormValue"
        if column["type"] == "DateTime":
            select += ",DateTimeBehavior,Format"
        path = (
            f"EntityDefinitions(LogicalName='{table_name}')/Attributes(LogicalName='{column_name}')/{cast}"
            f"?$select={select}"
        )
        if column["type"] == "Choice":
            path += "&$expand=GlobalOptionSet($select=MetadataId,Name)"
        return path

    def _column_payload(self, column: dict[str, Any]) -> dict[str, Any]:
        common: dict[str, Any] = {
            "@odata.type": self._column_type_cast(column["type"]),
            "SchemaName": column["schemaName"],
            "DisplayName": label(column["displayName"]),
            "RequiredLevel": required_level(column["requiredLevel"]),
            "IsAuditEnabled": managed_bool(column["auditEnabled"]),
        }
        column_type = column["type"]
        if column_type == "String":
            common["AttributeType"] = "String"
            common["AttributeTypeName"] = {"Value": "StringType"}
            common["MaxLength"] = column["maxLength"]
            common["FormatName"] = {"Value": column.get("format", "Text")}
        elif column_type == "Memo":
            common["AttributeType"] = "Memo"
            common["AttributeTypeName"] = {"Value": "MemoType"}
            common["MaxLength"] = column["maxLength"]
            common["Format"] = "TextArea"
        elif column_type == "Boolean":
            common["AttributeType"] = "Boolean"
            common["AttributeTypeName"] = {"Value": "BooleanType"}
            common["DefaultValue"] = bool(column.get("default", False))
            common["OptionSet"] = {
                "TrueOption": {"Value": 1, "Label": label("Yes")},
                "FalseOption": {"Value": 0, "Label": label("No")},
                "OptionSetType": "Boolean",
            }
        elif column_type == "Choice":
            common["AttributeType"] = "Picklist"
            common["AttributeTypeName"] = {"Value": "PicklistType"}
            common["SourceTypeMask"] = 0
            metadata_id = self.choice_metadata_ids.get(column["globalChoice"])
            if not metadata_id:
                raise ApplicatorError(f"Global choice metadata ID unavailable: {column['globalChoice']}")
            bind_key = "GlobalOptionSet" + "@odata" + ".bind"
            common[bind_key] = f"/GlobalOptionSetDefinitions({metadata_id})"
            if "default" in column:
                common["DefaultFormValue"] = int(column["default"])
        elif column_type == "DateTime":
            common["AttributeType"] = "DateTime"
            common["AttributeTypeName"] = {"Value": "DateTimeType"}
            common["DateTimeBehavior"] = {"Value": column["behavior"]}
            common["Format"] = column["format"]
        return common

    def _validate_column(
        self, table: dict[str, Any], column: dict[str, Any], existing: dict[str, Any]
    ) -> str:
        if existing.get("LogicalName") != column["logicalName"] or existing.get("SchemaName") != column["schemaName"]:
            raise ApplicatorError(f"Column identity drift: {table['logicalName']}.{column['logicalName']}")
        expected_attribute_type = self._expected_attribute_type(column["type"])
        if normalize_named_value(existing.get("AttributeType")) != expected_attribute_type:
            raise ApplicatorError(f"Column type drift: {table['logicalName']}.{column['logicalName']}")
        required = normalize_required_level(existing.get("RequiredLevel"))
        if required != column["requiredLevel"]:
            raise ApplicatorError(f"Column required-level drift: {table['logicalName']}.{column['logicalName']}")
        if normalize_managed_bool(existing.get("IsAuditEnabled")) != column["auditEnabled"]:
            raise ApplicatorError(f"Column audit drift: {table['logicalName']}.{column['logicalName']}")
        if column["type"] in {"String", "Memo"} and int(existing.get("MaxLength", -1)) != column["maxLength"]:
            raise ApplicatorError(f"Column length drift: {table['logicalName']}.{column['logicalName']}")
        if column["type"] == "String" and normalize_named_value(existing.get("FormatName")) != column.get("format", "Text"):
            raise ApplicatorError(f"Column format drift: {table['logicalName']}.{column['logicalName']}")
        if column["type"] == "Memo" and normalize_named_value(existing.get("Format")) != "TextArea":
            raise ApplicatorError(f"Column memo format drift: {table['logicalName']}.{column['logicalName']}")
        if column["type"] == "Boolean" and bool(existing.get("DefaultValue")) != bool(column.get("default", False)):
            raise ApplicatorError(f"Column default drift: {table['logicalName']}.{column['logicalName']}")
        if column["type"] == "DateTime":
            if normalize_named_value(existing.get("DateTimeBehavior")) != column["behavior"]:
                raise ApplicatorError(f"Column date behavior drift: {table['logicalName']}.{column['logicalName']}")
            if normalize_named_value(existing.get("Format")) != column["format"]:
                raise ApplicatorError(f"Column date format drift: {table['logicalName']}.{column['logicalName']}")
        if column["type"] == "Choice":
            global_choice = existing.get("GlobalOptionSet") or {}
            if global_choice.get("Name") != column["globalChoice"]:
                raise ApplicatorError(f"Column global-choice drift: {table['logicalName']}.{column['logicalName']}")
            if "default" in column and int(existing.get("DefaultFormValue", -1)) != int(column["default"]):
                raise ApplicatorError(f"Column choice default drift: {table['logicalName']}.{column['logicalName']}")
        metadata_id = str(existing.get("MetadataId", "")).lower()
        if not SAFE_GUID.fullmatch(metadata_id):
            raise ApplicatorError(f"Column metadata ID missing: {table['logicalName']}.{column['logicalName']}")
        return metadata_id

    def ensure_column(self, table: dict[str, Any], column: dict[str, Any]) -> None:
        full_name = f"{table['logicalName']}.{column['logicalName']}"
        if not self.apply and table["logicalName"] in self.missing_tables:
            self._missing("Column", full_name, details={"coveredByMissingTable": True})
            return
        path = self._column_path(table, column)
        response = self.transport.request("GET", path)
        if response.status == 200:
            existing = response.body or {}
            metadata_id = self._validate_column(table, column, existing)
            self._require_solution_membership(metadata_id, "Column", f"column {full_name}")
            self._record_reused({"kind": "Column", "name": full_name, "metadataId": metadata_id})
            return
        if response.status != 404:
            raise ApplicatorError(f"Column lookup failed: {full_name}: {response.status}")
        generic = self.transport.request("GET", self._column_base_path(table, column))
        if generic.status == 200:
            actual_type = normalize_named_value((generic.body or {}).get("AttributeType"))
            raise ApplicatorError(
                f"Column type drift: {full_name} is {actual_type!r}, "
                f"expected {self._expected_attribute_type(column['type'])!r}"
            )
        if generic.status != 404:
            raise ApplicatorError(
                f"Generic column lookup failed: {full_name}: {generic.status} {generic.body}"
            )
        if not self.apply:
            self._missing("Column", full_name)
            return
        table_name = escape_odata_string(table["logicalName"])
        created_response = self._request(
            "POST",
            f"EntityDefinitions(LogicalName='{table_name}')/Attributes",
            body=self._column_payload(column),
            solution_component=True,
        )
        metadata_id = parse_entity_id(created_response.headers)
        verified = self._wait_for_single(path, description=f"column {full_name}")
        verified_id = self._validate_column(table, column, verified)
        metadata_id = metadata_id or verified_id
        if metadata_id != verified_id:
            raise ApplicatorError(f"Column identity mismatch after create: {full_name}")
        self._require_solution_membership(metadata_id, "Column", f"column {full_name}", wait=True)
        self.journal.created(
            {
                "kind": "Column",
                "name": full_name,
                "table": table["logicalName"],
                "metadataId": metadata_id,
                "rollbackPath": f"EntityDefinitions(LogicalName='{table_name}')/Attributes({metadata_id})",
            }
        )

    def _keys_path(self, table: dict[str, Any]) -> str:
        table_name = escape_odata_string(table["logicalName"])
        return (
            f"EntityDefinitions(LogicalName='{table_name}')/Keys"
            "?$select=MetadataId,SchemaName,KeyAttributes,EntityKeyIndexStatus"
        )

    def _wait_for_active_key(
        self, table: dict[str, Any], key: dict[str, Any], *, timeout_seconds: int = 300
    ) -> dict[str, Any]:
        deadline = time.monotonic() + timeout_seconds
        while True:
            response = self._request("GET", self._keys_path(table))
            keys = (response.body or {}).get("value", [])
            matches = [item for item in keys if item.get("SchemaName") == key["schemaName"]]
            if len(matches) > 1:
                raise ApplicatorError(f"Duplicate alternate key metadata: {key['schemaName']}")
            if matches:
                existing = matches[0]
                if list(existing.get("KeyAttributes", [])) != key["columns"]:
                    raise ApplicatorError(f"Alternate key drift: {key['schemaName']}")
                metadata_id = str(existing.get("MetadataId", "")).lower()
                if not SAFE_GUID.fullmatch(metadata_id):
                    raise ApplicatorError(f"Alternate key metadata ID missing: {key['schemaName']}")
                status = normalize_key_index_status(existing.get("EntityKeyIndexStatus"))
                if status == "Active":
                    return existing
                if status == "Failed":
                    raise ApplicatorError(f"Alternate key index failed: {key['schemaName']}")
                if status not in {"Pending", "InProgress"}:
                    raise ApplicatorError(
                        f"Unknown alternate key index status: {key['schemaName']} "
                        f"({existing.get('EntityKeyIndexStatus')!r})"
                    )
            if time.monotonic() >= deadline:
                raise ApplicatorError(f"Timed out waiting for alternate key: {key['schemaName']}")
            time.sleep(5)

    def ensure_alternate_key(self, table: dict[str, Any], key: dict[str, Any]) -> None:
        if not self.apply and table["logicalName"] in self.missing_tables:
            self._missing(
                "Alternate key", key["schemaName"], details={"coveredByMissingTable": True}
            )
            return
        response = self._request("GET", self._keys_path(table))
        keys = (response.body or {}).get("value", [])
        matches = [item for item in keys if item.get("SchemaName") == key["schemaName"]]
        if len(matches) > 1:
            raise ApplicatorError(f"Duplicate alternate key metadata: {key['schemaName']}")
        if matches:
            existing = self._wait_for_active_key(table, key)
            metadata_id = str(existing.get("MetadataId", "")).lower()
            self._require_solution_membership(
                metadata_id, "AlternateKey", f"alternate key {key['schemaName']}"
            )
            self._record_reused(
                {"kind": "AlternateKey", "name": key["schemaName"], "metadataId": metadata_id}
            )
            return
        if not self.apply:
            self._missing("Alternate key", key["schemaName"])
            return
        table_name = escape_odata_string(table["logicalName"])
        payload = {
            "@odata.type": "Microsoft.Dynamics.CRM.EntityKeyMetadata",
            "SchemaName": key["schemaName"],
            "DisplayName": label(key["schemaName"]),
            "KeyAttributes": key["columns"],
        }
        created_response = self._request(
            "POST",
            f"EntityDefinitions(LogicalName='{table_name}')/Keys",
            body=payload,
            solution_component=True,
        )
        metadata_id = parse_entity_id(created_response.headers)
        existing = self._wait_for_active_key(table, key)
        verified_id = str(existing.get("MetadataId", "")).lower()
        metadata_id = metadata_id or verified_id
        if metadata_id != verified_id:
            raise ApplicatorError(f"Alternate key identity mismatch after create: {key['schemaName']}")
        self._require_solution_membership(
            metadata_id, "AlternateKey", f"alternate key {key['schemaName']}", wait=True
        )
        self.journal.created(
            {
                "kind": "AlternateKey",
                "name": key["schemaName"],
                "table": table["logicalName"],
                "metadataId": metadata_id,
                "rollbackPath": f"EntityDefinitions(LogicalName='{table_name}')/Keys({metadata_id})",
            }
        )

    def _relationship_query(self, schema_name: str) -> str:
        escaped = escape_odata_string(schema_name)
        return f"RelationshipDefinitions?$select=MetadataId,SchemaName&$filter=SchemaName eq '{escaped}'"

    @staticmethod
    def _relationship_payload(relationship: dict[str, Any]) -> dict[str, Any]:
        lookup = relationship["lookup"]
        return {
            "@odata.type": "Microsoft.Dynamics.CRM.OneToManyRelationshipMetadata",
            "SchemaName": relationship["schemaName"],
            "ReferencedEntity": relationship["referencedTable"],
            "ReferencingEntity": relationship["referencingTable"],
            "ReferencedAttribute": relationship["referencedTable"] + "id",
            "Lookup": {
                "@odata.type": "Microsoft.Dynamics.CRM.LookupAttributeMetadata",
                "AttributeType": "Lookup",
                "AttributeTypeName": {"Value": "LookupType"},
                "SchemaName": lookup["schemaName"],
                "DisplayName": label(lookup["displayName"]),
                "RequiredLevel": required_level(lookup["requiredLevel"]),
            },
            "CascadeConfiguration": {
                "Assign": relationship["cascade"]["assign"],
                "Delete": relationship["cascade"]["delete"],
                "Merge": relationship["cascade"]["merge"],
                "Reparent": relationship["cascade"]["reparent"],
                "Share": relationship["cascade"]["share"],
                "Unshare": relationship["cascade"]["unshare"],
            },
        }

    def _relationship_detail(self, metadata_id: str) -> dict[str, Any]:
        return self._query_single(
            f"RelationshipDefinitions({metadata_id})/Microsoft.Dynamics.CRM.OneToManyRelationshipMetadata"
            "?$select=MetadataId,SchemaName,ReferencedEntity,ReferencingEntity,ReferencedAttribute,CascadeConfiguration"
            "&$expand=Lookup($select=SchemaName,LogicalName,RequiredLevel)"
        ) or {}

    def _validate_relationship(
        self, relationship: dict[str, Any], detail: dict[str, Any]
    ) -> str:
        metadata_id = str(detail.get("MetadataId", "")).lower()
        if not SAFE_GUID.fullmatch(metadata_id):
            raise ApplicatorError(f"Relationship metadata ID missing: {relationship['schemaName']}")
        if detail.get("SchemaName") != relationship["schemaName"]:
            raise ApplicatorError(f"Relationship schema drift: {relationship['schemaName']}")
        if detail.get("ReferencedEntity") != relationship["referencedTable"]:
            raise ApplicatorError(f"Relationship parent drift: {relationship['schemaName']}")
        if detail.get("ReferencingEntity") != relationship["referencingTable"]:
            raise ApplicatorError(f"Relationship child drift: {relationship['schemaName']}")
        if detail.get("ReferencedAttribute") != relationship["referencedTable"] + "id":
            raise ApplicatorError(f"Relationship referenced-attribute drift: {relationship['schemaName']}")
        lookup = detail.get("Lookup") or {}
        if lookup.get("SchemaName") != relationship["lookup"]["schemaName"]:
            raise ApplicatorError(f"Relationship lookup drift: {relationship['schemaName']}")
        if lookup.get("LogicalName") != relationship["lookup"]["logicalName"]:
            raise ApplicatorError(f"Relationship lookup logical-name drift: {relationship['schemaName']}")
        if normalize_required_level(lookup.get("RequiredLevel")) != relationship["lookup"]["requiredLevel"]:
            raise ApplicatorError(f"Relationship lookup required-level drift: {relationship['schemaName']}")
        actual_cascade = detail.get("CascadeConfiguration") or {}
        normalized_cascade = {str(key).lower(): value for key, value in actual_cascade.items()}
        for action, expected_value in relationship["cascade"].items():
            if normalized_cascade.get(action) != expected_value:
                raise ApplicatorError(f"Relationship cascade drift: {relationship['schemaName']}.{action}")
        for action, actual_value in normalized_cascade.items():
            if action not in relationship["cascade"] and actual_value not in {None, "NoCascade"}:
                raise ApplicatorError(
                    f"Unexpected relationship cascade behavior: "
                    f"{relationship['schemaName']}.{action}={actual_value}"
                )
        return metadata_id

    def _require_relationship_lookup_slot_available(
        self, relationship: dict[str, Any]
    ) -> None:
        child = relationship["referencingTable"]
        lookup = relationship["lookup"]
        if not self.apply and child in self.missing_tables:
            return
        child_name = escape_odata_string(child)
        lookup_name = escape_odata_string(lookup["logicalName"])
        path = (
            f"EntityDefinitions(LogicalName='{child_name}')/"
            f"Attributes(LogicalName='{lookup_name}')"
            "?$select=MetadataId,LogicalName,SchemaName,AttributeType"
        )
        response = self.transport.request("GET", path)
        if response.status == 404:
            return
        if response.status != 200:
            raise ApplicatorError(
                f"Relationship lookup-slot preflight failed: "
                f"{child}.{lookup['logicalName']}: {response.status}"
            )
        existing = response.body or {}
        raise ApplicatorError(
            f"Relationship lookup name collision: {child}.{lookup['logicalName']} "
            f"already exists as {normalize_named_value(existing.get('AttributeType'))!r}."
        )

    def ensure_relationship(self, relationship: dict[str, Any]) -> None:
        existing = self._query_single(self._relationship_query(relationship["schemaName"]))
        if existing is not None:
            metadata_id = str(existing.get("MetadataId", "")).lower()
            if not SAFE_GUID.fullmatch(metadata_id):
                raise ApplicatorError(f"Relationship metadata ID missing: {relationship['schemaName']}")
            detail = self._relationship_detail(metadata_id)
            verified_id = self._validate_relationship(relationship, detail)
            if metadata_id != verified_id:
                raise ApplicatorError(f"Relationship identity drift: {relationship['schemaName']}")
            self._require_solution_membership(
                metadata_id, "Relationship", f"relationship {relationship['schemaName']}"
            )
            self._record_reused(
                {"kind": "Relationship", "name": relationship["schemaName"], "metadataId": metadata_id}
            )
            return
        self._require_relationship_lookup_slot_available(relationship)
        if not self.apply:
            self._missing("Relationship", relationship["schemaName"])
            return
        response = self._request(
            "POST",
            "RelationshipDefinitions",
            body=self._relationship_payload(relationship),
            solution_component=True,
        )
        metadata_id = parse_entity_id(response.headers)
        created = self._wait_for_single(
            self._relationship_query(relationship["schemaName"]),
            description=f"relationship {relationship['schemaName']}",
        )
        summary_id = str(created.get("MetadataId", "")).lower()
        if not SAFE_GUID.fullmatch(summary_id):
            raise ApplicatorError(f"Could not verify created relationship: {relationship['schemaName']}")
        detail = self._relationship_detail(summary_id)
        verified_id = self._validate_relationship(relationship, detail)
        metadata_id = metadata_id or verified_id
        if metadata_id != verified_id:
            raise ApplicatorError(f"Relationship identity mismatch after create: {relationship['schemaName']}")
        self._require_solution_membership(
            metadata_id, "Relationship", f"relationship {relationship['schemaName']}", wait=True
        )
        self.journal.created(
            {
                "kind": "Relationship",
                "name": relationship["schemaName"],
                "referencedTable": relationship["referencedTable"],
                "referencingTable": relationship["referencingTable"],
                "metadataId": metadata_id,
                "rollbackPath": f"RelationshipDefinitions({metadata_id})",
            }
        )

    def publish(self) -> None:
        if not self.apply:
            self.journal.check("Publish customizations", "WOULD_PUBLISH_ON_APPLY")
            return
        if not self.journal.data["created"]:
            self.journal.check("Publish customizations", "SKIPPED_NO_METADATA_CHANGES")
            return
        self._request("POST", "PublishAllXml", body={})
        self.journal.check("Publish customizations", "PASS")

    def _walk_contract(self) -> None:
        """Read-only or post-apply exact walk with no phase sleeps."""
        for choice in self.contract["globalChoices"]:
            self.ensure_global_choice(choice)
        for table in self.contract["tables"]:
            self.ensure_table(table)
        for table in self.contract["tables"]:
            if table["logicalName"] in self.table_metadata_ids:
                self.verify_primary_column(table)
        for table in self.contract["tables"]:
            for column in table["columns"]:
                self.ensure_column(table, column)
        for table in self.contract["tables"]:
            for key in table["alternateKeys"]:
                self.ensure_alternate_key(table, key)
        for relationship in self.contract["relationships"]:
            self.ensure_relationship(relationship)

    def _apply_contract(self) -> None:
        """Apply metadata in lock-safe phases with propagation barriers."""
        for choice in self.contract["globalChoices"]:
            self.ensure_global_choice(choice)

        created_tables_before = sum(
            1 for item in self.journal.data["created"] if item.get("kind") == "Table"
        )
        for table in self.contract["tables"]:
            self.ensure_table(table)
        created_tables_after = sum(
            1 for item in self.journal.data["created"] if item.get("kind") == "Table"
        )
        if created_tables_after > created_tables_before:
            self.journal.check("Table metadata propagation barrier", "WAIT_15_SECONDS")
            time.sleep(15)

        for table in self.contract["tables"]:
            if table["logicalName"] in self.table_metadata_ids:
                self.verify_primary_column(table)

        created_columns_before = sum(
            1 for item in self.journal.data["created"] if item.get("kind") == "Column"
        )
        for table in self.contract["tables"]:
            for column in table["columns"]:
                self.ensure_column(table, column)
        created_columns_after = sum(
            1 for item in self.journal.data["created"] if item.get("kind") == "Column"
        )
        if created_columns_after > created_columns_before:
            self.journal.check("Column metadata propagation barrier", "WAIT_15_SECONDS")
            time.sleep(15)

        created_keys_before = sum(
            1 for item in self.journal.data["created"] if item.get("kind") == "AlternateKey"
        )
        for table in self.contract["tables"]:
            for key in table["alternateKeys"]:
                self.ensure_alternate_key(table, key)
        created_keys_after = sum(
            1 for item in self.journal.data["created"] if item.get("kind") == "AlternateKey"
        )
        if created_keys_after > created_keys_before:
            self.journal.check("Alternate-key metadata propagation barrier", "WAIT_15_SECONDS")
            time.sleep(15)

        for relationship in self.contract["relationships"]:
            self.ensure_relationship(relationship)

    def _reset_walk_state(self) -> None:
        self.choice_metadata_ids.clear()
        self.table_metadata_ids.clear()
        self.missing_tables.clear()

    def run(self) -> dict[str, Any]:
        verify_public_artifacts(self.contract, self.plan, require_git_binding=False)
        self.verify_target()

        if self.apply:
            # Full check-first pass: detect every existing-name conflict before the
            # first metadata write, then re-check the target boundary to close the
            # race between inspection and mutation.
            self.record_reuse = False
            self.apply = False
            self._walk_contract()
            self.journal.check("Full metadata check-first preflight", "PASS")
            self._reset_walk_state()
            self.apply = True
            self.record_reuse = True
            self.verify_target()

        if self.apply:
            self._apply_contract()
        else:
            self._walk_contract()
        self.publish()

        if self.apply:
            # Read back every declared component after publish. Missing or drifted
            # metadata is fatal; no new writes can occur in this verification pass.
            self.record_reuse = False
            self.require_present = True
            self.apply = False
            self._reset_walk_state()
            self._walk_contract()
            self.journal.check("Post-apply exact metadata verification", "PASS")
            self.apply = True
            self.require_present = False
            self.record_reuse = True

        result = {
            "mode": "APPLY" if self.apply else "INSPECT_ONLY",
            "createdCount": len(self.journal.data["created"]),
            "reusedCount": len(self.journal.data["reused"]),
            "tablesCreated": sum(1 for item in self.journal.data["created"] if item["kind"] == "Table"),
            "rowsCreated": 0,
            "merge": False,
            "deployment": False,
        }
        self.journal.complete("PASS", result=result)
        return result


def target_table_row_exists(transport: Transport, contract: dict[str, Any]) -> tuple[bool, str | None]:
    for table in contract["tables"]:
        primary_id = table["logicalName"] + "id"
        response = transport.request(
            "GET", f"{table['entitySetName']}?$select={primary_id}&$top=1", headers={"ConsistencyLevel": "eventual"}
        )
        if response.status == 404:
            continue
        if response.status != 200:
            raise ApplicatorError(f"Could not verify rollback row boundary for {table['logicalName']}.")
        if (response.body or {}).get("value"):
            return True, table["logicalName"]
    return False, None


def _allowed_rollback_names(contract: dict[str, Any]) -> dict[str, set[str]]:
    return {
        "GlobalChoice": {item["logicalName"] for item in contract["globalChoices"]},
        "Table": {item["logicalName"] for item in contract["tables"]},
        "Column": {
            f"{table['logicalName']}.{column['logicalName']}"
            for table in contract["tables"]
            for column in table["columns"]
        },
        "AlternateKey": {
            key["schemaName"]
            for table in contract["tables"]
            for key in table["alternateKeys"]
        },
        "Relationship": {item["schemaName"] for item in contract["relationships"]},
    }


def _validate_rollback_entry(
    entry: dict[str, Any], allowed_names: dict[str, set[str]], seen_paths: set[str]
) -> str:
    kind = entry.get("kind")
    name = entry.get("name")
    path = entry.get("rollbackPath")
    metadata_id = str(entry.get("metadataId", "")).lower()
    if kind not in ROLLBACK_PATH_PATTERNS or name not in allowed_names.get(str(kind), set()):
        raise ApplicatorError(f"Rollback journal contains an unauthorized component: {kind} {name}")
    if not isinstance(path, str) or path in seen_paths:
        raise ApplicatorError(f"Rollback journal path is missing or duplicated: {name}")
    match = ROLLBACK_PATH_PATTERNS[str(kind)].fullmatch(path)
    if match is None:
        raise ApplicatorError(f"Rollback journal path is not allowlisted for {kind}: {path}")
    path_id = match.group(1).lower()
    if not SAFE_GUID.fullmatch(metadata_id) or path_id != metadata_id:
        raise ApplicatorError(f"Rollback journal metadata identity mismatch: {name}")
    seen_paths.add(path)
    return path


def rollback_from_journal(
    transport: Transport,
    journal_path: Path,
    authorization: dict[str, Any],
    contract: dict[str, Any],
    output_directory: Path,
) -> dict[str, Any]:
    journal_path = _require_private_path(
        journal_path, description="Rollback journal", must_exist=True
    )
    journal_bytes = journal_path.read_bytes()
    journal = json.loads(journal_bytes.decode("utf-8"))
    if authorization.get("mode") != "ROLLBACK_METADATA":
        raise ApplicatorError("Rollback requires a dedicated ROLLBACK_METADATA authorization.")
    if authorization.get("journalSha256") != hashlib.sha256(journal_bytes).hexdigest():
        raise ApplicatorError("Rollback authorization is not bound to this exact journal.")
    if journal.get("mode") != "APPLY":
        raise ApplicatorError("Rollback journal was not produced by an apply run.")
    if journal.get("contractSha256") != AUTHORIZED_CONTRACT_SHA256 or journal.get("planSha256") != AUTHORIZED_PLAN_SHA256:
        raise ApplicatorError("Rollback journal hash binding mismatch.")
    if authorization.get("rollbackDecision") != (
        "DELETE_ONLY_CREATED_COMPONENTS_IN_REVERSE_ORDER_IF_ALL_TARGET_TABLES_HAVE_ZERO_ROWS"
    ):
        raise ApplicatorError("Rollback decision is not the reviewed zero-row reverse-order policy.")
    target = journal.get("target") or {}
    if str(target.get("environmentUrl", "")).rstrip("/") != str(authorization.get("environmentUrl", "")).rstrip("/"):
        raise ApplicatorError("Rollback journal environment URL mismatch.")
    if target.get("environmentId") != authorization.get("environmentId"):
        raise ApplicatorError("Rollback journal environment ID mismatch.")
    if target.get("solution") != AUTHORIZED_SOLUTION:
        raise ApplicatorError("Rollback journal solution mismatch.")
    if target.get("applicatorCommit") != authorization.get("applicatorCommit"):
        raise ApplicatorError("Rollback journal applicator-commit mismatch.")

    created_entries = journal.get("created", [])
    if not isinstance(created_entries, list):
        raise ApplicatorError("Rollback journal created-component list is invalid.")
    allowed_names = _allowed_rollback_names(contract)
    seen_paths: set[str] = set()
    validated: list[tuple[dict[str, Any], str]] = []
    for entry in created_entries:
        if not isinstance(entry, dict):
            raise ApplicatorError("Rollback journal entry is invalid.")
        validated.append((entry, _validate_rollback_entry(entry, allowed_names, seen_paths)))

    has_rows, table = target_table_row_exists(transport, contract)
    if has_rows:
        raise ApplicatorError(f"Rollback refused: business rows exist in {table}.")
    rollback_log: list[dict[str, Any]] = []
    previous_kind: str | None = None
    for entry, rollback_path in reversed(validated):
        kind = str(entry.get("kind"))
        if previous_kind is not None and kind != previous_kind:
            time.sleep(10)
        response = transport.request("DELETE", rollback_path)
        if response.status not in {204, 404}:
            raise ApplicatorError(f"Rollback delete failed for {entry.get('name')}: {response.status}")
        rollback_log.append(
            {
                "atUtc": utc_now(),
                "kind": kind,
                "name": entry.get("name"),
                "status": "DELETED" if response.status == 204 else "ALREADY_ABSENT",
            }
        )
        previous_kind = kind
    customizations_published = False
    if rollback_log:
        publish = transport.request("POST", "PublishAllXml", body={})
        if publish.status not in {200, 204}:
            raise ApplicatorError(f"Rollback publish failed: {publish.status}")
        customizations_published = True
    output_directory.mkdir(parents=True, exist_ok=True)
    result = {
        "schemaVersion": "1.0",
        "mode": "ROLLBACK",
        "completedAtUtc": utc_now(),
        "zeroRowsVerified": True,
        "deleted": rollback_log,
        "customizationsPublished": customizations_published,
        "rowsDeleted": 0,
        "merge": False,
        "deployment": False,
    }
    (output_directory / "metadata-rollback-result.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    return result


def offline_plan(contract: dict[str, Any], plan: dict[str, Any]) -> dict[str, Any]:
    verify_public_artifacts(contract, plan, require_git_binding=False)
    return {
        "schemaVersion": "1.0",
        "mode": "OFFLINE_REVIEW",
        "authorizedBaseCommit": AUTHORIZED_BASE_COMMIT,
        "contractSha256": AUTHORIZED_CONTRACT_SHA256,
        "planSha256": AUTHORIZED_PLAN_SHA256,
        "solution": AUTHORIZED_SOLUTION,
        "counts": plan["counts"],
        "apply": False,
        "tablesCreated": 0,
        "rowsCreated": 0,
        "merge": False,
        "deployment": False,
    }


def read_token(path: Path) -> str:
    token = path.read_text(encoding="utf-8").strip()
    if not token:
        raise ApplicatorError("Access-token file is empty.")
    return token


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Fail-closed, check-first Dataverse schema applicator for OptimusAdminGateway."
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--inspect", action="store_true", help="Live read-only inspection; never writes metadata.")
    mode.add_argument("--apply", action="store_true", help="Apply the reviewed schema after private authorization.")
    mode.add_argument("--rollback-journal", type=Path, help="Rollback only components recorded as created by one run.")
    parser.add_argument("--environment-url")
    parser.add_argument("--environment-id")
    parser.add_argument("--access-token-file", type=Path)
    parser.add_argument("--authorization-file", type=Path)
    parser.add_argument("--output-directory", type=Path)
    parser.add_argument("--expected-component-count", type=int, default=EXPECTED_INITIAL_COMPONENT_COUNT)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    contract, plan = load_public_artifacts()

    if not (args.inspect or args.apply or args.rollback_journal):
        print(json.dumps(offline_plan(contract, plan), indent=2))
        return 0

    for name in ("environment_url", "environment_id", "access_token_file", "output_directory"):
        if getattr(args, name) in {None, ""}:
            parser.error(f"--{name.replace('_', '-')} is required for live modes")
    environment_url = normalize_environment_url(str(args.environment_url))
    environment_id = str(args.environment_id).lower()
    if not SAFE_GUID.fullmatch(environment_id):
        raise ApplicatorError("Environment ID must be a GUID.")
    access_token_file = _require_private_path(
        args.access_token_file, description="Access-token file", must_exist=True
    )
    output_directory = _require_private_path(
        args.output_directory, description="Evidence output directory", must_exist=False
    )
    token = read_token(access_token_file)
    transport = UrllibTransport(environment_url, token)

    authorization: dict[str, Any] | None = None
    applicator_commit: str | None = None
    if args.apply or args.rollback_journal:
        if args.authorization_file is None:
            parser.error("--authorization-file is required for apply or rollback")
        applicator_commit = verify_public_artifacts(contract, plan, require_git_binding=True)
        assert applicator_commit is not None
        expected_mode = "APPLY_METADATA" if args.apply else "ROLLBACK_METADATA"
        authorization = load_authorization(
            args.authorization_file,
            environment_url,
            environment_id,
            args.expected_component_count,
            applicator_commit,
            expected_mode=expected_mode,
            rollback_journal=args.rollback_journal,
        )

    target = {
        "environmentUrl": environment_url,
        "environmentId": environment_id,
        "solution": AUTHORIZED_SOLUTION,
    }
    if applicator_commit is not None:
        target["applicatorCommit"] = applicator_commit

    if args.rollback_journal:
        assert authorization is not None
        preflight_journal = EvidenceJournal(
            output_directory / "rollback-target-preflight",
            mode="ROLLBACK_PREFLIGHT",
            target=target,
        )
        SchemaApplicator(
            contract,
            plan,
            transport,
            preflight_journal,
            apply=False,
            expected_component_count=args.expected_component_count,
        ).verify_target()
        preflight_journal.complete("PASS", result={"metadataWrites": 0, "rowsWritten": 0})
        result = rollback_from_journal(
            transport, args.rollback_journal, authorization, contract, output_directory
        )
        print(json.dumps(result, indent=2))
        return 0

    journal = EvidenceJournal(output_directory, mode="APPLY" if args.apply else "INSPECT_ONLY", target=target)
    applicator = SchemaApplicator(
        contract,
        plan,
        transport,
        journal,
        apply=bool(args.apply),
        expected_component_count=args.expected_component_count,
    )
    try:
        result = applicator.run()
    except Exception as exc:
        journal.complete("FAILED", error={"type": type(exc).__name__, "message": str(exc)})
        raise
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ApplicatorError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
