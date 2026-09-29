"""Intake helpers: truncated-filename repair rule and entry-page marker refresh.

Run: python -m unittest discover -s scripts/tests -v
"""
from __future__ import annotations

import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from repair_truncated_filenames import is_truncation  # noqa: E402
from sync_intake_registers import replace_marker  # noqa: E402


class TruncationRule(unittest.TestCase):
    def test_cut_at_first_space(self):
        self.assertTrue(is_truncation("Academic", "Academic Background Dossier - Attachment 1 (2).docx"))

    def test_yaml_coerced_number_and_bool(self):
        self.assertTrue(is_truncation(4, "4 Nayebzadah.pdf"))
        self.assertTrue(is_truncation(True, "On DETECt _ European Review _ Cambridge Core.pdf"))
        self.assertTrue(is_truncation(False, "No beauty for me there.pdf"))

    def test_not_a_truncation(self):
        self.assertFalse(is_truncation("single.pdf", "single.pdf"))
        self.assertFalse(is_truncation("Other", "Academic Background.docx"))
        self.assertFalse(is_truncation("مجموعه‌ی داستان کوتاه- عناصر ابتلا - Copy.docx", "Blood-Jetting_Elements-of-Affliction_short-story-collection_fa.docx"))
        self.assertFalse(is_truncation(False, "Yes indeed.pdf"))


class MarkerRefresh(unittest.TestCase):
    LINE = "Live: Current corpus snapshot: `mw-corpus-old` · Registered source artifacts: 97 · Artifacts held: 544"

    def test_replaces_each_marker(self):
        text, n1 = replace_marker(self.LINE, "Current corpus snapshot: ", "`mw-corpus-new`")
        text, n2 = replace_marker(text, "Registered source artifacts: ", "98")
        text, n3 = replace_marker(text, "Artifacts held: ", "545")
        self.assertEqual((n1, n2, n3), (1, 1, 1))
        self.assertEqual(text, "Live: Current corpus snapshot: `mw-corpus-new` · Registered source artifacts: 98 · Artifacts held: 545")

    def test_missing_marker_reports_zero(self):
        self.assertEqual(replace_marker("no markers here", "Artifacts held: ", "1")[1], 0)


if __name__ == "__main__":
    unittest.main()
