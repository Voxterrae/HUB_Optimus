from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from jsonschema import Draft202012Validator


PACKAGE_ROOT = Path(__file__).parents[1]
CONTRACT_PATH = PACKAGE_ROOT / "dataverse" / "schema" / "optimus-admin-gateway.dataverse.json"
SCHEMA_PATH = PACKAGE_ROOT / "dataverse" / "schema" / "optimus-admin-gateway.dataverse.schema.json"
PLAN_PATH = PACKAGE_ROOT / "dataverse" / "plans" / "optimus-admin-gateway.schema-plan.json"


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _action(index: int, action: str, target: str, phase: str, details: dict) -> dict:
    return {
        "index": index,
        "phase": phase,
        "action": action,
        "target": target,
        "wouldMutateEnvironment": True,
        "details": details,
    }


def build_plan() -> dict:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    meta_schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator(meta_schema).validate(contract)

    actions: list[dict] = []
    index = 1
    actions.append(
        {
            "index": index,
            "phase": "VerifyTargetSolutionAndPublisher",
            "action": "Verify",
            "target": contract["solution"]["uniqueName"],
            "wouldMutateEnvironment": False,
            "details": {
                "publisher": contract["solution"]["publisher"],
                "prefix": contract["solution"]["prefix"],
                "choiceValuePrefix": contract["solution"]["choiceValuePrefix"],
                "expectedPackageType": contract["solution"]["packageType"],
            },
        }
    )
    index += 1

    for choice in contract["globalChoices"]:
        actions.append(
            _action(
                index,
                "CreateGlobalChoice",
                choice["logicalName"],
                "CreateGlobalChoices",
                {
                    "schemaName": choice["schemaName"],
                    "displayName": choice["displayName"],
                    "options": choice["options"],
                },
            )
        )
        index += 1

    for table in contract["tables"]:
        actions.append(
            _action(
                index,
                "CreateTable",
                table["logicalName"],
                "CreateTablesWithPrimaryColumns",
                {
                    "schemaName": table["schemaName"],
                    "entitySetName": table["entitySetName"],
                    "ownershipType": table["ownershipType"],
                    "primaryName": table["primaryName"],
                    "auditEnabled": table["auditEnabled"],
                    "changeTrackingEnabled": table["changeTrackingEnabled"],
                    "hasActivities": table["hasActivities"],
                    "hasNotes": table["hasNotes"],
                },
            )
        )
        index += 1

    for table in contract["tables"]:
        for column in table["columns"]:
            actions.append(
                _action(
                    index,
                    "CreateColumn",
                    f"{table['logicalName']}.{column['logicalName']}",
                    "CreateScalarColumns",
                    column,
                )
            )
            index += 1

    for table in contract["tables"]:
        for key in table["alternateKeys"]:
            actions.append(
                _action(
                    index,
                    "CreateAlternateKey",
                    f"{table['logicalName']}.{key['schemaName']}",
                    "CreateAlternateKeysAndWaitForIndexes",
                    {"columns": key["columns"]},
                )
            )
            index += 1

    for relationship in contract["relationships"]:
        actions.append(
            _action(
                index,
                "CreateOneToManyRelationship",
                relationship["schemaName"],
                "CreateRestrictiveRelationships",
                relationship,
            )
        )
        index += 1

    actions.append(
        _action(
            index,
            "PublishCustomizations",
            contract["solution"]["uniqueName"],
            "PublishCustomizations",
            {"scope": "solution"},
        )
    )
    index += 1
    actions.append(
        {
            "index": index,
            "phase": "VerifyMetadataAndExportSolution",
            "action": "VerifyAndExport",
            "target": contract["solution"]["uniqueName"],
            "wouldMutateEnvironment": False,
            "details": {
                "verifyChoices": True,
                "verifyTables": True,
                "verifyColumns": True,
                "verifyAlternateKeys": True,
                "verifyRelationships": True,
                "exportUnmanaged": True,
            },
        }
    )

    scalar_columns = sum(len(table["columns"]) for table in contract["tables"])
    primary_columns = len(contract["tables"])
    lookup_columns = len(contract["relationships"])
    alternate_keys = sum(len(table["alternateKeys"]) for table in contract["tables"])
    choice_options = sum(len(choice["options"]) for choice in contract["globalChoices"])

    plan = {
        "schemaVersion": "1.0",
        "mode": "DRY_RUN",
        "apply": False,
        "solution": contract["solution"],
        "contractSha256": hashlib.sha256(_canonical_bytes(contract)).hexdigest(),
        "counts": {
            "globalChoices": len(contract["globalChoices"]),
            "choiceOptions": choice_options,
            "tables": len(contract["tables"]),
            "primaryColumns": primary_columns,
            "scalarColumns": scalar_columns,
            "lookupColumns": lookup_columns,
            "alternateKeys": alternate_keys,
            "relationships": len(contract["relationships"]),
            "plannedActions": len(actions),
        },
        "actions": actions,
        "safety": {
            "containsExecutableMutationCommands": False,
            "environmentBinding": "private-runtime-only",
            "requiresExplicitApplyAuthorization": True,
            "tablesCreatedByThisPlan": 0,
            "rowsCreatedByThisPlan": 0,
            "merge": False,
            "deployment": False,
        },
    }
    plan["planHash"] = hashlib.sha256(_canonical_bytes(plan)).hexdigest()
    return plan


def render_plan() -> str:
    return json.dumps(build_plan(), indent=2, ensure_ascii=False) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Build or verify the deterministic Dataverse schema dry-run plan.")
    parser.add_argument("--write", action="store_true", help="Write the deterministic plan artifact.")
    parser.add_argument("--stdout", action="store_true", help="Print the deterministic plan.")
    args = parser.parse_args()

    rendered = render_plan()
    if args.stdout:
        print(rendered, end="")
    if args.write:
        PLAN_PATH.parent.mkdir(parents=True, exist_ok=True)
        PLAN_PATH.write_text(rendered, encoding="utf-8", newline="\n")
        return 0
    if not PLAN_PATH.exists() or PLAN_PATH.read_text(encoding="utf-8") != rendered:
        raise SystemExit("Dataverse schema plan is stale; run build-dataverse-schema-plan.py --write")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
