from __future__ import annotations

from pathlib import Path
import hashlib
import json
from typing import Any

ROOT = Path(__file__).parents[1]
CONTRACT_PATH = ROOT / "contract" / "optimus-evidence-lab.dataverse.json"
SEED_PATH = ROOT / "seed" / "hiv-global-2026.seed.json"
SCHEMA_PLAN_PATH = ROOT / "plans" / "optimus-evidence-lab.schema-plan.json"
SEED_PLAN_PATH = ROOT / "plans" / "hiv-global-2026.seed-plan.json"
DRY_RUN_PATH = ROOT / "plans" / "optimus-evidence-lab.dry-run.json"


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def build_schema_plan(contract: dict[str, Any]) -> dict[str, Any]:
    actions: list[dict[str, Any]] = [
        {
            "phase": 0,
            "action": "VERIFY_PUBLISHER",
            "target": contract["solution"]["publisher"],
            "write": False,
        },
        {
            "phase": 1,
            "action": "ENSURE_SOLUTION",
            "target": contract["solution"]["uniqueName"],
            "write": True,
        },
    ]

    for item in sorted(contract["globalChoices"], key=lambda row: row["logicalName"]):
        actions.append(
            {
                "phase": 2,
                "action": "ENSURE_GLOBAL_CHOICE",
                "target": item["logicalName"],
                "optionCount": len(item["options"]),
                "write": True,
            }
        )

    for table in sorted(contract["tables"], key=lambda row: row["logicalName"]):
        actions.append(
            {
                "phase": 3,
                "action": "ENSURE_TABLE",
                "target": table["logicalName"],
                "write": True,
            }
        )

    for table in sorted(contract["tables"], key=lambda row: row["logicalName"]):
        for item in sorted(table["columns"], key=lambda row: row["logicalName"]):
            actions.append(
                {
                    "phase": 4,
                    "action": "ENSURE_SCALAR_COLUMN",
                    "target": f"{table['logicalName']}.{item['logicalName']}",
                    "columnType": item["type"],
                    "write": True,
                }
            )

    for table in sorted(contract["tables"], key=lambda row: row["logicalName"]):
        for item in sorted(table["alternateKeys"], key=lambda row: row["schemaName"]):
            actions.append(
                {
                    "phase": 5,
                    "action": "ENSURE_ALTERNATE_KEY",
                    "target": item["schemaName"],
                    "table": table["logicalName"],
                    "columns": item["columns"],
                    "write": True,
                }
            )

    for item in sorted(contract["relationships"], key=lambda row: row["schemaName"]):
        actions.append(
            {
                "phase": 6,
                "action": "ENSURE_RELATIONSHIP",
                "target": item["schemaName"],
                "referencedTable": item["referencedTable"],
                "referencingTable": item["referencingTable"],
                "lookup": item["lookup"]["logicalName"],
                "write": True,
            }
        )

    actions.extend(
        [
            {
                "phase": 7,
                "action": "PUBLISH_CUSTOMIZATIONS",
                "target": contract["solution"]["uniqueName"],
                "write": True,
            },
            {
                "phase": 8,
                "action": "VERIFY_EXACT_SCHEMA",
                "target": contract["solution"]["uniqueName"],
                "write": False,
            },
        ]
    )

    counts = {
        "globalChoices": len(contract["globalChoices"]),
        "choiceOptions": sum(
            len(item["options"]) for item in contract["globalChoices"]
        ),
        "tables": len(contract["tables"]),
        "primaryColumns": len(contract["tables"]),
        "scalarColumns": sum(
            len(table["columns"]) for table in contract["tables"]
        ),
        "lookupColumns": len(contract["relationships"]),
        "alternateKeys": sum(
            len(table["alternateKeys"]) for table in contract["tables"]
        ),
        "relationships": len(contract["relationships"]),
        "logicalSchemaComponents": (
            len(contract["globalChoices"])
            + len(contract["tables"])
            + sum(len(table["columns"]) for table in contract["tables"])
            + sum(len(table["alternateKeys"]) for table in contract["tables"])
            + len(contract["relationships"])
        ),
        "plannedActions": len(actions),
        "plannedWrites": sum(1 for item in actions if item["write"]),
        "plannedReads": sum(1 for item in actions if not item["write"]),
    }

    unsigned = {
        "schemaVersion": "1.0",
        "mode": "SCHEMA_DRY_RUN",
        "apply": False,
        "solution": contract["solution"]["uniqueName"],
        "contractSha256": canonical_sha256(contract),
        "counts": counts,
        "actions": actions,
        "metadataWritesExecuted": 0,
        "rowsWritten": 0,
        "productionTouched": False,
        "merge": False,
        "deployment": False,
    }
    result = dict(unsigned)
    result["planHash"] = canonical_sha256(unsigned)
    return result


def build_seed_plan(
    contract: dict[str, Any],
    seed: dict[str, Any],
) -> dict[str, Any]:
    choice_values = {
        item["logicalName"]: {
            option["name"]: option["value"]
            for option in item["options"]
        }
        for item in contract["globalChoices"]
    }
    table_definitions = {
        table["logicalName"]: table for table in contract["tables"]
    }

    actions: list[dict[str, Any]] = []
    lookup_count = 0
    row_count = 0

    for table_name in sorted(seed["tables"]):
        table = table_definitions[table_name]
        columns = {
            item["logicalName"]: item for item in table["columns"]
        }

        for row in seed["tables"][table_name]:
            row_count += 1
            resolved = dict(row["values"])
            for name, value in list(resolved.items()):
                definition = columns.get(name)
                if (
                    definition
                    and definition["type"] == "Choice"
                    and value is not None
                ):
                    resolved[name] = choice_values[
                        definition["globalChoice"]
                    ][value]

            for lookup_name, lookup in sorted(row["lookups"].items()):
                lookup_count += 1
                actions.append(
                    {
                        "phase": 0,
                        "action": "RESOLVE_LOOKUP_BY_ALTERNATE_KEY",
                        "table": table_name,
                        "lookup": lookup_name,
                        "targetTable": lookup["targetTable"],
                        "alternateKey": lookup["alternateKey"],
                        "write": False,
                    }
                )

            actions.append(
                {
                    "phase": 1,
                    "action": "UPSERT_ROW_BY_ALTERNATE_KEY",
                    "table": table_name,
                    "alternateKey": row["alternateKey"],
                    "values": resolved,
                    "write": True,
                }
            )

    actions.sort(
        key=lambda item: (
            item["phase"],
            item["action"],
            item["table"],
            item.get("lookup", ""),
            json.dumps(item.get("alternateKey", {}), sort_keys=True),
        )
    )

    counts = {
        "rows": row_count,
        "lookupBindings": lookup_count,
        "tableRows": {
            table_name: len(rows)
            for table_name, rows in sorted(seed["tables"].items())
        },
        "plannedActions": len(actions),
        "plannedWrites": row_count,
        "plannedReads": lookup_count,
    }

    unsigned = {
        "schemaVersion": "1.0",
        "mode": "SEED_DRY_RUN",
        "apply": False,
        "seedName": seed["seedName"],
        "targetSolution": seed["targetSolution"],
        "contractSha256": canonical_sha256(contract),
        "seedSha256": canonical_sha256(seed),
        "counts": counts,
        "actions": actions,
        "rowsWritten": 0,
        "productionTouched": False,
        "merge": False,
        "deployment": False,
    }
    result = dict(unsigned)
    result["planHash"] = canonical_sha256(unsigned)
    return result


def main() -> int:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    seed = json.loads(SEED_PATH.read_text(encoding="utf-8"))

    schema_plan = build_schema_plan(contract)
    seed_plan = build_seed_plan(contract, seed)

    dry_run = {
        "schemaVersion": "1.0",
        "mode": "OFFLINE_DRY_RUN",
        "status": "PASS",
        "intendedTarget": "LCDH-OS DEV",
        "intendedEnvironmentType": "Sandbox",
        "solution": contract["solution"]["uniqueName"],
        "solutionVersion": contract["solution"]["version"],
        "publisher": contract["solution"]["publisher"],
        "prefix": contract["solution"]["prefix"],
        "contractSha256": canonical_sha256(contract),
        "schemaPlanSha256": schema_plan["planHash"],
        "seedName": seed["seedName"],
        "seedSha256": canonical_sha256(seed),
        "seedPlanSha256": seed_plan["planHash"],
        "schemaCounts": schema_plan["counts"],
        "seedCounts": seed_plan["counts"],
        "apply": False,
        "metadataWritesExecuted": 0,
        "rowsWritten": 0,
        "productionTouched": False,
        "merge": False,
        "deployment": False,
        "liveTargetInspectionExecuted": False,
        "nextGate": (
            "Run the separate private read-only LCDH-OS DEV collision "
            "inspection before any apply authorization."
        ),
    }

    write_json(SCHEMA_PLAN_PATH, schema_plan)
    write_json(SEED_PLAN_PATH, seed_plan)
    write_json(DRY_RUN_PATH, dry_run)

    print(json.dumps(dry_run, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
