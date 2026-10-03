#!/usr/bin/env python3
"""Tests for URL, photo, and file (SingleFile adapter) capture — U1.

Stdlib unittest only. Run:
    python scripts/capture/tests/test_url_photo_file.py
"""
import contextlib
import io
import json
import os
import shutil
import struct
import sys
import tempfile
import unittest
import zlib
from pathlib import Path

CAPTURE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CAPTURE_DIR))
import wiki_capture as wc
import file_contract as fc


def png_bytes() -> bytes:
    """Minimal valid 1x1 RGB PNG via stdlib zlib."""
    ihdr = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    raw = b"\x00\xff\x00\x00"
    idat = zlib.compress(raw)

    def chunk(typ: bytes, data: bytes) -> bytes:
        c = typ + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c))

    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", idat) + chunk(b"IEND", b""))


class IsolatedRoot(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="u1test-"))
        self._old_root = wc.CAPTURES_ROOT
        self._old_quar = wc.ORPHAN_QUARANTINE
        wc.CAPTURES_ROOT = self.tmp / "01-inbox" / "captures"
        wc.ORPHAN_QUARANTINE = wc.CAPTURES_ROOT / ".quarantine"

    def tearDown(self):
        wc.CAPTURES_ROOT = self._old_root
        wc.ORPHAN_QUARANTINE = self._old_quar
        shutil.rmtree(self.tmp, ignore_errors=True)


class TestURLCapture(IsolatedRoot):
    def test_url_capture_valid(self):
        r = wc.capture_url("https://example.com/article", "obsidian", "en")
        self.assertTrue(r["ok"])
        self.assertEqual(r["status"], "received")
        self.assertIsNone(r["duplicate_of"])
        self.assertEqual(wc.validate_record(r["id"]), [])

    def test_url_capture_stores_url_in_body(self):
        url = "https://example.com/path?q=1"
        r = wc.capture_url(url, "mcp", "en")
        rec = wc.read_capture(r["id"])
        self.assertIn(url, rec["sections"]["User-supplied text"])
        self.assertEqual(rec["front_matter"]["capture_kind"], "url")

    def test_url_capture_duplicate(self):
        url = "https://example.com/dup"
        a = wc.capture_url(url, "obsidian", "en")
        b = wc.capture_url(url, "obsidian", "en")
        self.assertEqual(b["duplicate_of"], a["id"])
        self.assertEqual(wc.validate_record(b["id"]), [])

    def test_url_capture_empty_rejected(self):
        with self.assertRaises(wc.CaptureError) as c:
            wc.capture_url("   ", "obsidian")
        self.assertEqual(c.exception.code, "E_EMPTY")

    def test_url_capture_non_http_rejected(self):
        with self.assertRaises(wc.CaptureError) as c:
            wc.capture_url("ftp://example.com", "obsidian")
        self.assertEqual(c.exception.code, "E_BAD_URL")

    def test_url_capture_bad_channel(self):
        with self.assertRaises(wc.CaptureError) as c:
            wc.capture_url("https://example.com", "sms")
        self.assertEqual(c.exception.code, "E_BAD_CHANNEL")

    def test_url_capture_custom_title(self):
        r = wc.capture_url("https://example.com", "obsidian", "en",
                           title="My Article")
        rec = wc.read_capture(r["id"])
        self.assertEqual(rec["front_matter"]["title"], "My Article")

    def test_url_capture_hash_matches_body(self):
        url = "https://example.com/hash-test"
        r = wc.capture_url(url, "obsidian", "en")
        rec = wc.read_capture(r["id"])
        body = rec["sections"]["User-supplied text"]
        import hashlib
        expected = hashlib.sha256(body.encode("utf-8")).hexdigest()
        self.assertEqual(rec["front_matter"]["sha256"], expected)

    def test_url_capture_state_machine(self):
        cid = wc.capture_url("https://example.com/sm", "obsidian", "en")["id"]
        wc.set_state(cid, "processing", "op")
        wc.set_state(cid, "needs-review", "op")
        wc.set_state(cid, "reviewed", "Mohammad", note="checked")
        wc.set_state(cid, "promoted", "Mohammad", target="04-notes/web/x.md")
        self.assertEqual(wc.validate_record(cid), [])
        r = wc.read_capture(cid)
        self.assertEqual(r["front_matter"]["promoted_to"], "04-notes/web/x.md")

    def test_url_capture_description_allowed(self):
        cid = wc.capture_url("https://example.com/desc", "obsidian", "en")["id"]
        wc.set_state(cid, "processing", "op")
        wc.record_description(cid, "extracted text", "interpretation",
                              "manual", "v1")
        wc.set_state(cid, "described", "op")
        self.assertEqual(wc.validate_record(cid), [])


class TestPhotoCapture(IsolatedRoot):
    def test_photo_capture_valid(self):
        png = self.tmp / "photo.png"
        png.write_bytes(png_bytes())
        r = wc.capture_photo(str(png), "obsidian", "fa")
        self.assertTrue(r["ok"])
        self.assertEqual(r["status"], "received")
        self.assertEqual(wc.validate_record(r["id"]), [])

    def test_photo_capture_kind_is_image(self):
        png = self.tmp / "photo.png"
        png.write_bytes(png_bytes())
        r = wc.capture_photo(str(png), "obsidian", "fa")
        rec = wc.read_capture(r["id"])
        self.assertEqual(rec["front_matter"]["capture_kind"], "image")

    def test_photo_capture_duplicate(self):
        png = self.tmp / "photo.png"
        png.write_bytes(png_bytes())
        a = wc.capture_photo(str(png), "obsidian", "fa")
        b = wc.capture_photo(str(png), "obsidian", "fa")
        self.assertEqual(b["duplicate_of"], a["id"])

    def test_photo_capture_stores_media(self):
        png = self.tmp / "photo.png"
        png.write_bytes(png_bytes())
        r = wc.capture_photo(str(png), "obsidian", "fa")
        rec = wc.read_capture(r["id"])
        self.assertIsNotNone(rec["front_matter"]["raw_media"])
        self.assertTrue(rec["front_matter"]["raw_media_available"])

    def test_photo_capture_non_image_rejected(self):
        txt = self.tmp / "not_photo.txt"
        txt.write_bytes(b"just text, not an image")
        with self.assertRaises(wc.CaptureError) as c:
            wc.capture_photo(str(txt), "obsidian")
        self.assertEqual(c.exception.code, "E_MEDIA_MISMATCH")

    def test_photo_capture_mime_mismatch_rejected(self):
        fake = self.tmp / "fake.png"
        fake.write_bytes(b"not a real png")
        with self.assertRaises(wc.CaptureError) as c:
            wc.capture_photo(str(fake), "obsidian")
        self.assertEqual(c.exception.code, "E_MIME_MISMATCH")

    def test_photo_capture_oversize_rejected(self):
        big = self.tmp / "big.png"
        big.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 1024)
        old = wc.MAX_BYTES
        wc.MAX_BYTES = 100
        try:
            with self.assertRaises(wc.CaptureError) as c:
                wc.capture_photo(str(big), "obsidian")
            self.assertEqual(c.exception.code, "E_OVERSIZE")
        finally:
            wc.MAX_BYTES = old

    def test_photo_capture_symlink_rejected(self):
        png = self.tmp / "real.png"
        png.write_bytes(png_bytes())
        link = self.tmp / "link.png"
        try:
            link.symlink_to(png)
        except OSError:
            self.skipTest("symlinks unavailable")
        with self.assertRaises(wc.CaptureError) as c:
            wc.capture_photo(str(link), "obsidian")
        self.assertEqual(c.exception.code, "E_SYMLINK")

    def test_photo_capture_description_flow(self):
        png = self.tmp / "photo.png"
        png.write_bytes(png_bytes())
        cid = wc.capture_photo(str(png), "obsidian", "fa")["id"]
        wc.set_state(cid, "processing", "op")
        wc.record_description(cid, "visible: برچسب", "interpretation: top",
                              "manual", "v1")
        wc.set_state(cid, "described", "op")
        self.assertEqual(wc.validate_record(cid), [])
        r = wc.read_capture(cid)
        self.assertIn("برچسب", r["sections"]["Literal transcript or extraction"])


class TestFileContract(IsolatedRoot):
    def test_singlefile_adapter_available(self):
        ok, detail = fc.SingleFileAdapter().available()
        self.assertTrue(ok)
        self.assertIn("singlefile", detail)

    def test_process_text_file(self):
        txt = self.tmp / "doc.txt"
        txt.write_bytes("Hello, world!\n".encode("utf-8"))
        cid = wc.capture_media(str(txt), "file", "obsidian", "en")["id"]
        r = fc.process_capture(cid)
        self.assertTrue(r["ok"])
        self.assertEqual(r["adapter"], "singlefile")
        self.assertEqual(r["mime"], "text/plain")
        self.assertIsNotNone(r["sha256"])

    def test_process_md_file(self):
        md = self.tmp / "note.md"
        md.write_bytes("# Title\n\nContent\n".encode("utf-8"))
        cid = wc.capture_media(str(md), "file", "obsidian", "en")["id"]
        r = fc.process_capture(cid)
        self.assertTrue(r["ok"])
        # MIME for .md is platform-dependent; just check it's non-empty
        self.assertTrue(r["mime"])

    def test_process_csv_file(self):
        csv = self.tmp / "data.csv"
        csv.write_bytes("a,b,c\n1,2,3\n".encode("utf-8"))
        cid = wc.capture_media(str(csv), "file", "obsidian", "en")["id"]
        r = fc.process_capture(cid)
        self.assertTrue(r["ok"])
        # MIME for .csv is platform-dependent (text/csv on Linux,
        # application/vnd.ms-excel on Windows); just check it's non-empty
        self.assertTrue(r["mime"])

    def test_process_pdf_flags_not_implemented(self):
        pdf = self.tmp / "doc.pdf"
        pdf.write_bytes(b"%PDF-1.4\n%%EOF\n")
        cid = wc.capture_media(str(pdf), "file", "obsidian", "en")["id"]
        r = fc.process_capture(cid)
        self.assertTrue(r["ok"])
        self.assertIn("pdf-text-extraction-not-implemented", r["flags"])

    def test_process_stores_text_extraction(self):
        txt = self.tmp / "extract.txt"
        txt.write_bytes("extracted content here\n".encode("utf-8"))
        cid = wc.capture_media(str(txt), "file", "obsidian", "en")["id"]
        fc.process_capture(cid)
        rec = wc.read_capture(cid)
        self.assertIn("extracted content here",
                      rec["sections"]["Literal transcript or extraction"])

    def test_process_wrong_kind_rejected(self):
        cid = wc.capture_text("plain text", "obsidian")["id"]
        with self.assertRaises(wc.CaptureError) as c:
            fc.process_capture(cid)
        self.assertEqual(c.exception.code, "E_WRONG_KIND")

    def test_process_unknown_adapter(self):
        txt = self.tmp / "doc.txt"
        txt.write_bytes(b"hello")
        cid = wc.capture_media(str(txt), "file", "obsidian", "en")["id"]
        with self.assertRaises(wc.CaptureError) as c:
            fc.process_capture(cid, "nonexistent")
        self.assertEqual(c.exception.code, "E_UNKNOWN_ADAPTER")

    def test_process_missing_file_rejected(self):
        with self.assertRaises(wc.CaptureError) as c:
            fc.process_capture("cap-20000101-000000-dead")
        self.assertEqual(c.exception.code, "E_NOT_FOUND")

    def test_adapter_extract_directly(self):
        txt = self.tmp / "direct.txt"
        content = "direct extract\n"
        txt.write_bytes(content.encode("utf-8"))
        adapter = fc.SingleFileAdapter()
        out = adapter.extract(str(txt))
        self.assertEqual(out["mime"], "text/plain")
        self.assertEqual(out["size"], len(content.encode("utf-8")))
        self.assertIsNotNone(out["sha256"])
        self.assertIn("direct extract", out["text"])

    def test_adapter_extract_binary_suffix(self):
        """A .txt file with non-UTF-8 bytes gets flagged, not crashed on."""
        txt = self.tmp / "binary.txt"
        txt.write_bytes(b"\xff\xfe\x00\x01")
        adapter = fc.SingleFileAdapter()
        out = adapter.extract(str(txt))
        self.assertIsNone(out["text"])
        self.assertIn("binary-in-text-suffix", out["quality_flags"])


class TestCaptureCLI(IsolatedRoot):
    """The CLI subcommands must exercise real argument wiring without
    writing into the repository (K1c invariant: a test run leaves
    ``git status --porcelain`` empty). ``main()`` runs in-process against
    the isolated root instead of a subprocess, so ``CAPTURES_ROOT`` stays
    inside the temp tree where the production containment check allows it.
    """

    def _run_main(self, argv):
        old_repo = wc.REPO_ROOT
        wc.REPO_ROOT = self.tmp
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                rc = wc.main(argv)
        finally:
            wc.REPO_ROOT = old_repo
        return rc, buf.getvalue()

    def test_cli_capture_url(self):
        rc, out = self._run_main(
            ["--json", "capture-url", "--url", "https://example.com/cli",
             "--channel", "obsidian"])
        self.assertEqual(rc, 0, out)
        data = json.loads(out)
        self.assertTrue(data["ok"])
        self.assertIn("id", data)

    def test_cli_capture_photo(self):
        png = self.tmp / "cli_photo.png"
        png.write_bytes(png_bytes())
        rc, out = self._run_main(
            ["--json", "capture-photo", "--src", str(png),
             "--channel", "obsidian"])
        self.assertEqual(rc, 0, out)
        data = json.loads(out)
        self.assertTrue(data["ok"])
        self.assertIn("id", data)


class TestReceiptEquivalence(IsolatedRoot):
    """All three modalities produce identical receipt structure."""

    def test_receipt_keys_match(self):
        # URL receipt
        url_r = wc.capture_url("https://example.com/eq", "obsidian", "en")
        # Photo receipt
        png = self.tmp / "eq.png"
        png.write_bytes(png_bytes())
        photo_r = wc.capture_photo(str(png), "obsidian", "en")
        # File receipt
        txt = self.tmp / "eq.txt"
        txt.write_bytes(b"equivalent\n")
        file_r = wc.capture_media(str(txt), "file", "obsidian", "en")

        for r in (url_r, photo_r, file_r):
            self.assertIn("ok", r)
            self.assertIn("id", r)
            self.assertIn("status", r)
            self.assertIn("path", r)
            self.assertIn("sha256", r)
            self.assertIn("bytes", r)
            self.assertIn("duplicate_of", r)
            self.assertIn("message", r)
            self.assertTrue(r["ok"])
            self.assertEqual(r["status"], "received")
            self.assertIsNone(r["duplicate_of"])

    def test_all_validate_clean(self):
        url_r = wc.capture_url("https://example.com/val", "obsidian", "en")
        png = self.tmp / "val.png"
        png.write_bytes(png_bytes())
        photo_r = wc.capture_photo(str(png), "obsidian", "en")
        txt = self.tmp / "val.txt"
        txt.write_bytes(b"validate me\n")
        file_r = wc.capture_media(str(txt), "file", "obsidian", "en")

        for r in (url_r, photo_r, file_r):
            self.assertEqual(wc.validate_record(r["id"]), [],
                             f"{r['id']} failed validation")


class TestSchemaParity(unittest.TestCase):
    """The shipped client copy (scripts/capture) and the canonical contract
    (00-system/schemas) must expose the same ``capture_kind`` vocabulary.
    Adding a modality in one file and not the other is silent schema drift
    (the defect this test was added to catch), so the sets are compared as
    sets — the two files differ only in instance id/title flavour."""

    def _enum(self, path: Path) -> set[str]:
        schema = json.loads(path.read_text(encoding="utf-8"))
        return set(schema["properties"]["capture_kind"]["enum"])

    def test_capture_kind_enums_match(self):
        repo_root = Path(__file__).resolve().parents[3]
        client = self._enum(CAPTURE_DIR / "capture.schema.json")
        canonical = self._enum(
            repo_root / "00-system" / "schemas" / "capture.schema.json")
        self.assertEqual(client, canonical)
        self.assertIn("url", client)


if __name__ == "__main__":
    unittest.main(verbosity=1)
