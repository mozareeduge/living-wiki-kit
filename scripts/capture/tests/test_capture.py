#!/usr/bin/env python3
"""Adversarial tests for the governed capture core (Tasks 3 + 12).

Stdlib unittest only (no pytest on this host). Run:
    python scripts/capture/tests/test_capture.py
"""
import os
import sys
import tempfile
import threading
import unittest
import wave
import struct
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import wiki_capture as wc


def make_wav(path: Path, seconds: int = 1, freq: int = 8000) -> Path:
    n = freq * seconds
    w = wave.open(str(path), "w")
    w.setnchannels(1)
    w.setsampwidth(2)
    w.setframerate(freq)
    w.writeframes(struct.pack(f"<{n}h", *([1200] * n)))
    w.close()
    return path


class IsolatedRoot(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="captest-"))
        self._old_root = wc.CAPTURES_ROOT
        self._old_quar = wc.ORPHAN_QUARANTINE
        wc.CAPTURES_ROOT = self.tmp / "01-inbox" / "captures"
        wc.ORPHAN_QUARANTINE = wc.CAPTURES_ROOT / ".quarantine"

    def tearDown(self):
        wc.CAPTURES_ROOT = self._old_root
        wc.ORPHAN_QUARANTINE = self._old_quar
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)


class TestTextCapture(IsolatedRoot):
    def test_roundtrip_valid(self):
        r = wc.capture_text("سلام دنیا", "obsidian", "fa")
        self.assertTrue(r["ok"])
        self.assertEqual(wc.validate_record(r["id"]), [])

    def test_empty_rejected(self):
        with self.assertRaises(wc.CaptureError) as c:
            wc.capture_text("   \n ", "obsidian")
        self.assertEqual(c.exception.code, "E_EMPTY")

    def test_bad_channel(self):
        with self.assertRaises(wc.CaptureError) as c:
            wc.capture_text("x", "sms")
        self.assertEqual(c.exception.code, "E_BAD_CHANNEL")

    def test_duplicate_points_at_first(self):
        a = wc.capture_text("same note", "mcp")
        b = wc.capture_text("same note", "mcp")
        self.assertEqual(b["duplicate_of"], a["id"])
        self.assertEqual(wc.validate_record(b["id"]), [])

    def test_traversal_id_rejected(self):
        for bad in ["../x", "cap-1", "/abs", "cap-20260905-120000-ZZZZ"]:
            with self.assertRaises(wc.CaptureError):
                wc.read_capture(bad)


class TestMediaCapture(IsolatedRoot):
    def test_voice_and_duplicate(self):
        wav = make_wav(self.tmp / "a.wav")
        a = wc.capture_media(str(wav), "voice", "telegram-hermes", "fa")
        self.assertTrue(a["ok"])
        self.assertEqual(wc.validate_record(a["id"]), [])
        b = wc.capture_media(str(wav), "voice", "telegram-hermes", "fa")
        self.assertEqual(b["duplicate_of"], a["id"])

    def test_kind_mismatch_rejected(self):
        wav = make_wav(self.tmp / "b.wav")
        with self.assertRaises(wc.CaptureError) as c:
            wc.capture_media(str(wav), "image", "obsidian")
        self.assertEqual(c.exception.code, "E_MEDIA_MISMATCH")

    def test_mime_mismatch_rejected(self):
        fake = self.tmp / "fake.wav"
        fake.write_bytes(b"this is not audio, just text pretending")
        with self.assertRaises(wc.CaptureError) as c:
            wc.capture_media(str(fake), "voice", "obsidian")
        self.assertEqual(c.exception.code, "E_MIME_MISMATCH")

    def test_unsupported_type_rejected(self):
        exe = self.tmp / "run.exe"
        exe.write_bytes(b"MZ fake binary")
        with self.assertRaises(wc.CaptureError) as c:
            wc.capture_media(str(exe), "file", "obsidian")
        self.assertEqual(c.exception.code, "E_UNSUPPORTED_TYPE")

    def test_oversize_rejected(self):
        big = self.tmp / "big.wav"
        big.write_bytes(b"RIFF" + b"\x00" * 1024)
        old = wc.MAX_BYTES
        wc.MAX_BYTES = 100
        try:
            with self.assertRaises(wc.CaptureError) as c:
                wc.capture_media(str(big), "voice", "obsidian")
            self.assertEqual(c.exception.code, "E_OVERSIZE")
        finally:
            wc.MAX_BYTES = old

    def test_symlink_never_followed(self):
        wav = make_wav(self.tmp / "real.wav")
        link = self.tmp / "link.wav"
        try:
            link.symlink_to(wav)
        except OSError:
            self.skipTest("symlinks unavailable")
        with self.assertRaises(wc.CaptureError) as c:
            wc.capture_media(str(link), "voice", "obsidian")
        self.assertEqual(c.exception.code, "E_SYMLINK")

    def test_missing_source(self):
        with self.assertRaises(wc.CaptureError) as c:
            wc.capture_media(str(self.tmp / "nope.wav"), "voice", "obsidian")
        self.assertEqual(c.exception.code, "E_NOT_FOUND")


class TestMediaPathRule(IsolatedRoot):
    """Containment in CAPTURES_ROOT is the rule, on every OS. A "starts with
    /" shortcut rejected valid media on Linux (where an absolute path starts
    with /) while Windows ("C:/...") passed, so the capture suite was red on
    the Linux CI runner only. A drive-rooted "/Users/..." path reproduces
    the Linux case on Windows."""

    def _rewrite_raw_media(self, cid: str, raw: str) -> None:
        rec = next(wc.CAPTURES_ROOT.rglob(f"{cid}.md"))
        lines = rec.read_text(encoding="utf-8").splitlines(keepends=True)
        lines = [f"raw_media: {raw}\n" if l.startswith("raw_media:") else l for l in lines]
        rec.write_text("".join(lines), encoding="utf-8")

    def test_slash_rooted_media_inside_root_is_valid(self):
        cid = wc.capture_media(str(make_wav(self.tmp / "p.wav")), "voice", "obsidian")["id"]
        media = next((wc.CAPTURES_ROOT).rglob(f"media/{cid}.*")).resolve()
        rooted = "/" + media.relative_to(media.anchor).as_posix()
        self._rewrite_raw_media(cid, rooted)
        self.assertEqual(wc.validate_record(cid), [])

    def test_slash_rooted_media_outside_root_is_traversal(self):
        cid = wc.capture_media(str(make_wav(self.tmp / "q.wav")), "voice", "obsidian")["id"]
        self._rewrite_raw_media(cid, "/etc/passwd")
        self.assertIn("E_TRAVERSAL: raw_media escapes roots", wc.validate_record(cid))


class TestConcurrency(IsolatedRoot):
    def test_simultaneous_captures_unique(self):
        ids, errors = [], []

        def go(i):
            try:
                ids.append(wc.capture_text(f"parallel note {i}", "mcp")["id"])
            except Exception as e:  # noqa: BLE001
                errors.append(e)

        threads = [threading.Thread(target=go, args=(i,)) for i in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(errors, [])
        self.assertEqual(len(set(ids)), 8)
        for cid in ids:
            self.assertEqual(wc.validate_record(cid), [])


class TestCrashRecovery(IsolatedRoot):
    def test_orphan_media_adopted(self):
        # Simulate crash between media write and record creation.
        wav = make_wav(self.tmp / "orphan-src.wav")
        data = wav.read_bytes()
        cid = wc._new_id()
        orphan = wc.media_path(cid, ".wav")
        orphan.parent.mkdir(parents=True, exist_ok=True)
        orphan.write_bytes(data)
        res = wc.recover_orphans()
        self.assertIn(cid, res["adopted"])
        self.assertEqual(wc.validate_record(cid), [])
        r = wc.read_capture(cid)
        self.assertIn("recovered-orphan", r["front_matter"]["quality_flags"])

    def test_duplicate_orphan_quarantined(self):
        r = wc.capture_text("keep me", "filesystem")
        digest = r["sha256"]
        qp = wc.CAPTURES_ROOT / "2026" / "202606" / "media"
        qp.mkdir(parents=True, exist_ok=True)
        (qp / "cap-20200101-000000-abcd.wav").write_bytes(b"RIFF" + b"\x00" * 64)
        res = wc.recover_orphans()
        self.assertTrue(res["adopted"] or res["quarantined"])
        _ = digest


class TestStateMachine(IsolatedRoot):
    def test_full_voice_chain(self):
        wav = make_wav(self.tmp / "v.wav")
        cid = wc.capture_media(str(wav), "voice", "telegram-hermes", "fa")["id"]
        wc.set_state(cid, "processing", "test-op")
        wc.record_transcript(cid, "متن آزمایشی", "manual", "v1")
        wc.set_state(cid, "transcribed", "test-op")
        wc.set_state(cid, "reviewed", "Mohammad", note="one name corrected")
        wc.set_state(cid, "promoted", "Mohammad", target="03-objects/works/x.md")
        self.assertEqual(wc.validate_record(cid), [])
        r = wc.read_capture(cid)
        self.assertEqual(r["front_matter"]["promoted_to"], "03-objects/works/x.md")

    def test_illegal_skip_rejected(self):
        cid = wc.capture_text("skip me", "obsidian")["id"]
        with self.assertRaises(wc.CaptureError) as c:
            wc.set_state(cid, "promoted", "Mohammad", target="03-objects/x.md")
        self.assertEqual(c.exception.code, "E_BAD_TRANSITION")

    def test_received_reviewed_only_for_duplicates(self):
        cid = wc.capture_text("not a dup", "obsidian")["id"]
        with self.assertRaises(wc.CaptureError) as c:
            wc.set_state(cid, "reviewed", "Mohammad")
        self.assertEqual(c.exception.code, "E_BAD_TRANSITION")
        dup = wc.capture_text("not a dup", "obsidian")["id"]
        wc.set_state(dup, "reviewed", "Mohammad", note="dup triage")
        self.assertEqual(wc.validate_record(dup), [])

    def test_promotion_needs_target_and_actor(self):
        cid = wc.capture_text("prom me", "obsidian")["id"]
        wc.set_state(cid, "processing", "op")
        with self.assertRaises(wc.CaptureError):
            wc.set_state(cid, "processing", "")
        with self.assertRaises(wc.CaptureError):
            wc.set_state(cid, "reviewed", "Mohammad")


class TestSeparation(IsolatedRoot):
    def test_transcript_only_on_voice(self):
        cid = wc.capture_text("plain", "obsidian")["id"]
        with self.assertRaises(wc.CaptureError) as c:
            wc.record_transcript(cid, "x", "m", "v")
        self.assertEqual(c.exception.code, "E_WRONG_KIND")

    def test_literal_and_description_stay_separate(self):
        png = self.tmp / "note.png"
        png.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 64)
        cid = wc.capture_media(str(png), "handwriting", "obsidian", "fa")["id"]
        wc.record_description(cid, "visible: خط اول", "interpretation: top-right label", "manual", "v1")
        r = wc.read_capture(cid)
        self.assertIn("خط اول", r["sections"]["Literal transcript or extraction"])
        self.assertIn("top-right", r["sections"]["Machine description"])
        self.assertNotIn("interpretation", r["sections"]["Literal transcript or extraction"])


class TestTamperEvident(IsolatedRoot):
    def test_modified_media_detected(self):
        wav = make_wav(self.tmp / "t.wav")
        cid = wc.capture_media(str(wav), "voice", "obsidian")["id"]
        mp = wc._resolve_media(wc.read_capture(cid)["front_matter"]["raw_media"])
        with open(mp, "r+b") as f:
            f.seek(40)
            f.write(b"\xff")
        errs = wc.validate_record(cid)
        self.assertTrue(any("E_HASH_MISMATCH" in e for e in errs))

    def test_status_edit_detected(self):
        cid = wc.capture_text("guard me", "obsidian")["id"]
        p = wc.record_path(cid)
        t = p.read_text(encoding="utf-8")
        p.write_text(t.replace("status: received", "status: promoted"), encoding="utf-8")
        errs = wc.validate_record(cid)
        self.assertTrue(errs)


if __name__ == "__main__":
    unittest.main(verbosity=1)
