from __future__ import annotations

from pathlib import Path
import json
import unittest

ROOT = Path(__file__).parents[1]


class BaselineB0Tests(unittest.TestCase):
    def test_sanitized_b0_binding(self):
        value = json.loads((ROOT / "dataverse/baselines/B0.json").read_text(encoding="utf-8"))
        self.assertEqual(value["classification"], "OPTIMUS_EVIDENCE_LAB_BASELINE_B0")
        self.assertEqual(value["directComponents"], 0)
        self.assertEqual(value["customRows"], 0)
        self.assertEqual(
            value["unmanagedBaselineSha256"],
            "3f141153424f178fae8007d0ac829932b8fff5ddecf21264c6c6b08714b0100b",
        )
        self.assertFalse(value["privateEnvironmentIdentifiersPublished"])
        self.assertFalse(value["metadataApplyExecuted"])

    def test_rollback_plan_is_zero_row_and_no_retry(self):
        value = json.loads(
            (ROOT / "dataverse/rollback/rollback-plan.template.json").read_text(encoding="utf-8")
        )
        self.assertEqual(value["expectedBefore"]["directComponents"], 11)
        self.assertEqual(value["expectedBefore"]["rowsAcrossTargetTables"], 0)
        self.assertEqual(value["publicationCount"], 1)
        self.assertFalse(value["automaticRollback"])
        self.assertFalse(value["automaticRetry"])


if __name__ == "__main__":
    unittest.main()
