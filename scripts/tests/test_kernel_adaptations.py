"""Repository adaptations of the Governance Kernel v1.2.1 (see ADAPTATION_RECEIPT.json).

Run: python -m unittest discover -s scripts/tests -v
"""
from __future__ import annotations

import datetime
import json
import pathlib
import sqlite3
import sys
import tempfile
import unittest

SCRIPTS = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))

from gov_kernel.provenance import _manifest_tier_filter  # noqa: E402
from gov_kernel.retrieval import _scalar  # noqa: E402

POLICY = {
    "tiers": {
        "registered": {"manifest_row": "required"},
        "pending-registration": {"manifest_row": "forbidden"},
        "reference-shelf": {"manifest_row": "forbidden"},
    },
    "default_tier_for_unregistered": "pending-registration",
}


class HoldingsTier(unittest.TestCase):
    def classify(self, fm):
        with tempfile.TemporaryDirectory() as tmp:
            p = pathlib.Path(tmp) / "00-system/policies/HOLDINGS_POLICY.json"
            p.parent.mkdir(parents=True)
            p.write_text(json.dumps(POLICY), encoding="utf-8")
            return _manifest_tier_filter(pathlib.Path(tmp))(fm)

    def test_registered_status_is_manifest_row(self):
        self.assertEqual(self.classify({"status": "registered"}), (True, None))

    def test_status_wins_over_stale_holdings_tier(self):
        self.assertEqual(self.classify({"status": "registered", "holdings_tier": "pending-registration"}), (True, None))

    def test_held_record_is_not_manifest_row(self):
        self.assertEqual(self.classify({"status": "pending-registration", "holdings_tier": "pending-registration"}), (False, None))

    def test_unknown_status_is_reported_not_hidden(self):
        member, problem = self.classify({"status": "registred"})
        self.assertFalse(member)
        self.assertIn("registred", problem)

    def test_no_policy_counts_every_record(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(_manifest_tier_filter(pathlib.Path(tmp))({}), (True, None))


class ScalarBinding(unittest.TestCase):
    def test_values_bind_into_sqlite(self):
        conn = sqlite3.connect(":memory:")
        conn.execute("CREATE TABLE t(v TEXT)")
        for value in (["en", "fa"], {"a": 1}, datetime.date(2026, 9, 16), datetime.datetime(2026, 9, 16, 12, 0), "x", 3, None):
            conn.execute("INSERT INTO t VALUES(?)", (_scalar(value),))
        self.assertEqual(_scalar(["en", "fa"]), "en,fa")
        self.assertEqual(_scalar(datetime.date(2026, 9, 16)), "2026-09-16")


if __name__ == "__main__":
    unittest.main()
