#!/usr/bin/env python3
"""Task 2 gate: every valid fixture passes, every invalid fixture fails
for its intended reason. Stdlib unittest only.

Run: python scripts/capture/tests/test_fixtures.py
"""
import json
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

CAPTURE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CAPTURE_DIR))
sys.path.insert(0, str(CAPTURE_DIR / "fixtures"))
import wiki_capture as wc
import make_fixtures

# Fixtures are regenerated into a temp dir: running the tests must never
# rewrite the tracked scripts/capture/fixtures/ tree.
FIX = Path(tempfile.mkdtemp(prefix="fixgen-"))


class FixtureGate(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        saved = (wc.CAPTURES_ROOT, wc.ORPHAN_QUARANTINE)
        make_fixtures.FIX = FIX
        make_fixtures.VALID = FIX / "valid"
        make_fixtures.INVALID = FIX / "invalid"
        try:
            rc = make_fixtures.main()
        finally:
            wc.CAPTURES_ROOT, wc.ORPHAN_QUARANTINE = saved
        assert rc == 0, "fixture generation failed"

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(FIX, ignore_errors=True)

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="fixtest-"))
        self._old_root = wc.CAPTURES_ROOT
        self._old_quar = wc.ORPHAN_QUARANTINE
        wc.CAPTURES_ROOT = self.tmp / "caps"
        wc.ORPHAN_QUARANTINE = wc.CAPTURES_ROOT / ".quarantine"
        wc.CAPTURES_ROOT.mkdir(parents=True)

    def tearDown(self):
        wc.CAPTURES_ROOT = self._old_root
        wc.ORPHAN_QUARANTINE = self._old_quar
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _install_valid(self):
        """Copy the valid fixture tree in, rewriting raw_media to isolated absolutes."""
        for src in (FIX / "valid").rglob("cap-*.md"):
            rel = src.relative_to(FIX / "valid")
            dest = wc.CAPTURES_ROOT / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            text = src.read_text(encoding="utf-8")
            mates = list((src.parent / "media").glob(src.stem + ".*")) if (src.parent / "media").exists() else []
            for med in mates:
                mdest = dest.parent / "media" / med.name
                mdest.parent.mkdir(parents=True, exist_ok=True)
                mdest.write_bytes(med.read_bytes())
                old = next(l for l in text.splitlines() if l.startswith("raw_media:"))
                text = text.replace(old, f"raw_media: {mdest.as_posix()}")
            dest.write_text(text, encoding="utf-8")

    def test_all_valid_pass(self):
        self._install_valid()
        recs = list(wc.CAPTURES_ROOT.rglob("cap-*.md"))
        self.assertGreaterEqual(len(recs), 7, "expected 7+ valid fixtures")
        kinds = set()
        for p in recs:
            errs = wc.validate_record(str(p))
            self.assertEqual(errs, [], f"{p.name}: {errs}")
            fm, _ = wc.parse_record_text(p.read_text(encoding="utf-8"))
            kinds.add((fm["capture_kind"], fm["status"]))
        for want in [("text", "received"), ("voice", "transcribed"),
                     ("handwriting", "described"), ("text", "reviewed"),
                     ("text", "promoted")]:
            self.assertIn(want, kinds, f"missing fixture {want}")

    def test_all_invalid_fail_for_reason(self):
        expect = json.loads((FIX / "expected-invalid.json").read_text(encoding="utf-8"))
        self.assertEqual(len(expect), 6)
        for name, code in expect.items():
            src = next((FIX / "invalid" / name).glob("cap-*.md"))
            dest = wc.CAPTURES_ROOT / "2020" / "202001" / src.name
            dest.parent.mkdir(parents=True, exist_ok=True)
            text = src.read_text(encoding="utf-8")
            sibling_png = src.parent / "mismatch.png"
            if sibling_png.exists():
                pdest = dest.parent / "media" / "mismatch.png"
                pdest.parent.mkdir(parents=True, exist_ok=True)
                pdest.write_bytes(sibling_png.read_bytes())
                text = text.replace("raw_media: REWRITE-ME-mismatch.png",
                                    f"raw_media: {pdest.as_posix()}")
            dest.write_text(text, encoding="utf-8")
            errs = wc.validate_record(str(dest))
            self.assertTrue(errs, f"{name}: expected failure, got pass")
            self.assertTrue(any(e.startswith(code) for e in errs),
                            f"{name}: expected {code} in {errs}")


if __name__ == "__main__":
    unittest.main(verbosity=1)
