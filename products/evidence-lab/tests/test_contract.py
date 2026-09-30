from __future__ import annotations
from pathlib import Path
import hashlib
import json
import unittest

ROOT = Path(__file__).parents[1]
CONTRACT = json.loads(
    (ROOT / "contract/optimus-evidence-lab.dataverse.json").read_text(
        encoding="utf-8"
    )
)


def canonical_sha256(value):
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


class ContractTests(unittest.TestCase):
    def test_solution_identity(self):
        solution = CONTRACT["solution"]
        self.assertEqual(solution["uniqueName"], "OptimusEvidenceLab")
        self.assertEqual(solution["publisher"], "HUB_Optimus")
        self.assertEqual(solution["prefix"], "opt")
        self.assertEqual(solution["version"], "0.1.0.0")
        self.assertFalse(CONTRACT["deploymentPolicy"]["productionAllowed"])

    def test_exact_inventory(self):
        self.assertEqual(len(CONTRACT["globalChoices"]), 6)
        self.assertEqual(
            sum(len(item["options"]) for item in CONTRACT["globalChoices"]),
            33,
        )
        self.assertEqual(len(CONTRACT["tables"]), 5)
        self.assertEqual(
            sum(len(table["columns"]) for table in CONTRACT["tables"]),
            50,
        )
        self.assertEqual(
            sum(len(table["alternateKeys"]) for table in CONTRACT["tables"]),
            5,
        )
        self.assertEqual(len(CONTRACT["relationships"]), 4)

    def test_table_names(self):
        self.assertEqual(
            {table["logicalName"] for table in CONTRACT["tables"]},
            {
                "opt_geography",
                "opt_source",
                "opt_release",
                "opt_metric",
                "opt_observation",
            },
        )

    def test_names_are_prefixed(self):
        for choice in CONTRACT["globalChoices"]:
            self.assertTrue(choice["logicalName"].startswith("opt_"))
        for table in CONTRACT["tables"]:
            self.assertTrue(table["logicalName"].startswith("opt_"))
            for item in table["columns"]:
                self.assertTrue(item["logicalName"].startswith("opt_"))

    def test_choice_values_are_unique_and_in_range(self):
        values = [
            option["value"]
            for choice in CONTRACT["globalChoices"]
            for option in choice["options"]
        ]
        self.assertEqual(len(values), len(set(values)))
        self.assertTrue(all(str(value).startswith("88483") for value in values))

    def test_alternate_keys_reference_existing_columns(self):
        for table in CONTRACT["tables"]:
            available = {
                table["primaryName"]["logicalName"],
                *(item["logicalName"] for item in table["columns"]),
            }
            for key in table["alternateKeys"]:
                self.assertTrue(set(key["columns"]) <= available)

    def test_relationships_are_restrictive(self):
        tables = {table["logicalName"] for table in CONTRACT["tables"]}
        lookups = set()
        for relationship in CONTRACT["relationships"]:
            self.assertIn(relationship["referencedTable"], tables)
            self.assertIn(relationship["referencingTable"], tables)
            self.assertEqual(
                relationship["cascade"],
                "ReferentialRestrictDelete",
            )
            identity = (
                relationship["referencingTable"],
                relationship["lookup"]["logicalName"],
            )
            self.assertNotIn(identity, lookups)
            lookups.add(identity)

    def test_observation_is_aggregate_only(self):
        observation = next(
            table for table in CONTRACT["tables"]
            if table["logicalName"] == "opt_observation"
        )
        governance = observation["governance"]
        self.assertTrue(governance["aggregateOnly"])
        self.assertFalse(governance["personalDataAllowed"])
        self.assertFalse(governance["individualRiskScoringAllowed"])

    def test_contract_hash_shape(self):
        self.assertRegex(canonical_sha256(CONTRACT), r"^[a-f0-9]{64}$")


if __name__ == "__main__":
    unittest.main()
