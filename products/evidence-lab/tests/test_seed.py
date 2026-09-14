from __future__ import annotations
from copy import deepcopy
from pathlib import Path
import json
import unittest

ROOT = Path(__file__).parents[1]
SEED = json.loads(
    (ROOT / "seed/hiv-global-2026.seed.json").read_text(encoding="utf-8")
)


class SeedTests(unittest.TestCase):
    def test_exact_17_rows(self):
        counts = {
            table: len(rows) for table, rows in SEED["tables"].items()
        }
        self.assertEqual(
            counts,
            {
                "opt_geography": 1,
                "opt_source": 2,
                "opt_release": 2,
                "opt_metric": 6,
                "opt_observation": 6,
            },
        )
        self.assertEqual(sum(counts.values()), 17)

    def test_source_rows_match_corpus(self):
        sources = {
            row["values"]["opt_sourcekey"]: row["values"]
            for row in SEED["tables"]["opt_source"]
        }
        self.assertEqual(
            sources["UNM49_CURRENT"]["opt_sha256"],
            "748f6ff7380c8a50ea9448f068b79e3a1ee31be63207249e8cc89bf1eb969d11",
        )
        self.assertIsNone(sources["UNAIDS_FACTS_2026"]["opt_sha256"])
        self.assertIn(
            "20260612_Global_HIV_Factsheet.pdf",
            sources["UNAIDS_FACTS_2026"]["opt_url"],
        )

    def test_six_global_observations(self):
        observations = {
            row["values"]["opt_observationkey"]: row["values"]
            for row in SEED["tables"]["opt_observation"]
        }
        expected = {
            "OBS|WLD|2025|PLHIV_TOTAL|UNAIDS_FACTS_2026":
                (41000000, 35300000, 47500000),
            "OBS|WLD|2025|NEW_ACQUISITIONS|UNAIDS_FACTS_2026":
                (1200000, 950000, 1700000),
            "OBS|WLD|2025|AIDS_DEATHS|UNAIDS_FACTS_2026":
                (570000, 430000, 780000),
            "OBS|WLD|2025|ON_ART|UNAIDS_FACTS_2026":
                (32100000, None, None),
            "OBS|WLD|2025|CUMULATIVE_ACQUISITIONS|UNAIDS_FACTS_2026":
                (92000000, 70200000, 123500000),
            "OBS|WLD|2025|CUMULATIVE_AIDS_DEATHS|UNAIDS_FACTS_2026":
                (44200000, 33800000, 61100000),
        }
        self.assertEqual(set(observations), set(expected))
        for key, triple in expected.items():
            row = observations[key]
            self.assertEqual(
                (
                    row["opt_pointvalue"],
                    row["opt_lowerbound"],
                    row["opt_upperbound"],
                ),
                triple,
            )

    def test_bounds_are_ordered(self):
        for row in SEED["tables"]["opt_observation"]:
            values = row["values"]
            if values["opt_lowerbound"] is not None:
                self.assertLessEqual(
                    values["opt_lowerbound"],
                    values["opt_pointvalue"],
                )
            if values["opt_upperbound"] is not None:
                self.assertLessEqual(
                    values["opt_pointvalue"],
                    values["opt_upperbound"],
                )

    def test_all_lookups_resolve(self):
        index = {}
        for table, rows in SEED["tables"].items():
            index[table] = {
                json.dumps(row["alternateKey"], sort_keys=True)
                for row in rows
            }
        for rows in SEED["tables"].values():
            for row in rows:
                for lookup in row["lookups"].values():
                    self.assertIn(
                        json.dumps(lookup["alternateKey"], sort_keys=True),
                        index[lookup["targetTable"]],
                    )

    def test_alternate_keys_are_unique(self):
        for table, rows in SEED["tables"].items():
            keys = [
                json.dumps(row["alternateKey"], sort_keys=True)
                for row in rows
            ]
            self.assertEqual(len(keys), len(set(keys)), table)

    def test_idempotent_upsert_simulation(self):
        store = {}
        for _ in range(2):
            for table, rows in SEED["tables"].items():
                target = store.setdefault(table, {})
                for row in rows:
                    target[
                        json.dumps(row["alternateKey"], sort_keys=True)
                    ] = deepcopy(row)
        self.assertEqual(sum(len(rows) for rows in store.values()), 17)

    def test_aggregate_and_no_personal_data(self):
        self.assertTrue(SEED["corpusBasis"]["aggregateOnly"])
        self.assertFalse(SEED["corpusBasis"]["containsPersonalData"])
        serialized = json.dumps(SEED, ensure_ascii=False).lower()
        for forbidden in (
            "patient",
            "person_name",
            "email",
            "telephone",
            "national_id",
            "individual_risk",
        ):
            self.assertNotIn(forbidden, serialized)

    def test_cut_and_data_year(self):
        self.assertEqual(SEED["corpusBasis"]["cutoffDate"], "2026-08-14")
        self.assertEqual(SEED["corpusBasis"]["dataYear"], 2025)


if __name__ == "__main__":
    unittest.main()
