from __future__ import annotations
from pathlib import Path
import hashlib
import json
import unittest

ROOT = Path(__file__).parents[1]


def canonical_sha256(value):
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


CONTRACT = json.loads(
    (ROOT / "contract/optimus-evidence-lab.dataverse.json").read_text(
        encoding="utf-8"
    )
)
SEED = json.loads(
    (ROOT / "seed/hiv-global-2026.seed.json").read_text(encoding="utf-8")
)
PLAN = json.loads(
    (ROOT / "plans/optimus-evidence-lab.schema-plan.json").read_text(
        encoding="utf-8"
    )
)
SEED_PLAN = json.loads(
    (ROOT / "plans/hiv-global-2026.seed-plan.json").read_text(
        encoding="utf-8"
    )
)
DRY_RUN = json.loads(
    (ROOT / "plans/optimus-evidence-lab.dry-run.json").read_text(
        encoding="utf-8"
    )
)


class PlanTests(unittest.TestCase):
    def test_schema_hash_binding(self):
        unsigned = dict(PLAN)
        embedded = unsigned.pop("planHash")
        self.assertEqual(embedded, canonical_sha256(unsigned))
        self.assertEqual(PLAN["contractSha256"], canonical_sha256(CONTRACT))

    def test_schema_counts(self):
        self.assertEqual(
            PLAN["counts"],
            {
                "globalChoices": 6,
                "choiceOptions": 33,
                "tables": 5,
                "primaryColumns": 5,
                "scalarColumns": 50,
                "lookupColumns": 4,
                "alternateKeys": 5,
                "relationships": 4,
                "logicalSchemaComponents": 70,
                "plannedActions": 74,
                "plannedWrites": 72,
                "plannedReads": 2,
            },
        )

    def test_seed_hash_binding_and_counts(self):
        unsigned = dict(SEED_PLAN)
        embedded = unsigned.pop("planHash")
        self.assertEqual(embedded, canonical_sha256(unsigned))
        self.assertEqual(SEED_PLAN["seedSha256"], canonical_sha256(SEED))
        self.assertEqual(SEED_PLAN["counts"]["rows"], 17)
        self.assertEqual(SEED_PLAN["counts"]["lookupBindings"], 20)
        self.assertEqual(SEED_PLAN["counts"]["plannedActions"], 37)
        self.assertEqual(SEED_PLAN["counts"]["plannedWrites"], 17)
        self.assertEqual(SEED_PLAN["counts"]["plannedReads"], 20)

    def test_zero_write_dry_run(self):
        self.assertEqual(DRY_RUN["status"], "PASS")
        self.assertFalse(DRY_RUN["apply"])
        self.assertEqual(DRY_RUN["metadataWritesExecuted"], 0)
        self.assertEqual(DRY_RUN["rowsWritten"], 0)
        self.assertFalse(DRY_RUN["productionTouched"])
        self.assertFalse(DRY_RUN["merge"])
        self.assertFalse(DRY_RUN["deployment"])
        self.assertFalse(DRY_RUN["liveTargetInspectionExecuted"])


if __name__ == "__main__":
    unittest.main()
