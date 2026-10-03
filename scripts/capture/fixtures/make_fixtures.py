#!/usr/bin/env python3
"""Build Task 2 fixtures: valid captures for every state/kind + invalid
captures that must each fail validation for ONE intended reason.

Regenerate: python scripts/capture/fixtures/make_fixtures.py
Verify:     python scripts/capture/tests/test_fixtures.py
"""
import hashlib
import shutil
import sys
import wave
import struct
from pathlib import Path

SYS = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(SYS / "scripts" / "capture"))
import wiki_capture as wc

FIX = Path(__file__).resolve().parent
VALID = FIX / "valid"
INVALID = FIX / "invalid"

def png_bytes() -> bytes:
    """Minimal valid 1x1 RGB PNG via stdlib zlib (no Pillow needed)."""
    import zlib
    ihdr = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    raw = b"\x00\xff\x00\x00"  # filter 0 + one red pixel
    idat = zlib.compress(raw)

    def chunk(typ: bytes, data: bytes) -> bytes:
        c = typ + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c))

    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", idat) + chunk(b"IEND", b""))


def wav_bytes(seconds=1) -> bytes:
    import io
    buf = io.BytesIO()
    w = wave.open(buf, "w")
    w.setnchannels(1)
    w.setsampwidth(2)
    w.setframerate(8000)
    n = 8000 * seconds
    w.writeframes(struct.pack(f"<{n}h", *([900] * n)))
    w.close()
    return buf.getvalue()


def fresh_root(name: str) -> Path:
    root = FIX / ".build" / name
    shutil.rmtree(root, ignore_errors=True)
    (root / "01-inbox" / "captures").mkdir(parents=True)
    wc.CAPTURES_ROOT = root / "01-inbox" / "captures"
    wc.ORPHAN_QUARANTINE = wc.CAPTURES_ROOT / ".quarantine"
    return root


def export_valid(root: Path):
    for p in sorted((root / "01-inbox" / "captures").rglob("cap-*.md")):
        rel = p.relative_to(root / "01-inbox" / "captures")
        dest = VALID / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        text = p.read_text(encoding="utf-8")
        media = p.parent / "media" / (p.stem + ".*")
        import glob as _g
        for m in _g.glob(str(media)):
            mp = Path(m)
            md = VALID / rel.parent / "media" / mp.name
            md.parent.mkdir(parents=True, exist_ok=True)
            md.write_bytes(mp.read_bytes())
            old = next(l for l in text.splitlines() if l.startswith("raw_media:"))
            text = text.replace(old, f"raw_media: media/{mp.name}")
        dest.write_text(text, encoding="utf-8")


def main() -> int:
    shutil.rmtree(VALID, ignore_errors=True)
    shutil.rmtree(INVALID, ignore_errors=True)
    (FIX / ".build").mkdir(exist_ok=True)

    # ---- valid set, one build dir per case for deterministic ids ----
    root = fresh_root("all")
    t = wc.capture_text("متن فارسی برای آزمون", "obsidian", "fa")["id"]          # text/received
    wav_src = root / "v.wav"
    wav_src.write_bytes(wav_bytes())
    v = wc.capture_media(str(wav_src), "voice", "telegram-hermes", "fa")["id"]   # voice/received
    wc.set_state(v, "processing", "fixture")
    wc.record_transcript(v, "متن پیاده‌شده", "manual", "v1")
    wc.set_state(v, "transcribed", "fixture")
    png_src = root / "n.png"
    png_src.write_bytes(png_bytes())
    h = wc.capture_media(str(png_src), "handwriting", "obsidian", "fa")["id"]    # handwriting
    wc.set_state(h, "processing", "fixture")
    wc.record_description(h, "خط visible", "top label", "manual", "v1")
    wc.set_state(h, "described", "fixture")
    d = wc.capture_text("drawing labels: A, B", "obsidian", "en")["id"]          # drawing-as-text-labels
    f = wc.capture_text("this will fail processing", "mcp")["id"]                # failed
    wc.set_state(f, "processing", "fixture")
    wc.set_state(f, "processing-failed", "fixture")
    dup = wc.capture_text("متن فارسی برای آزمون", "obsidian", "fa")["id"]        # duplicate
    wc.set_state(dup, "reviewed", "Mohammad", note="dup triage")
    r = wc.capture_text("reviewed note", "claude-mobile", "en")["id"]            # reviewed
    wc.set_state(r, "processing", "fixture")
    wc.set_state(r, "needs-review", "fixture")
    wc.set_state(r, "reviewed", "Mohammad", note="checked")
    p = wc.capture_text("promoted note", "obsidian", "en")["id"]                 # promoted
    wc.set_state(p, "processing", "fixture")
    wc.set_state(p, "needs-review", "fixture")
    wc.set_state(p, "reviewed", "Mohammad", note="good")
    wc.set_state(p, "promoted", "Mohammad", target="04-notes/research/x.md")
    export_valid(root)

    # ---- invalid set: copies of a valid record, each broken one way ----
    # The base must be a fresh, media-less capture: every case below edits
    # "status: received" / "raw_media: null". Ids end in a random suffix, so
    # "first file by name" picked a random record and made the gate flaky.
    base = None
    for c in sorted(VALID.rglob("cap-*.md")):
        text = c.read_text(encoding="utf-8")
        if "\nstatus: received\n" in text and "\nraw_media: null\n" in text:
            base = text
            break
    assert base, "no received text fixture built"
    bad_jump = base.replace("status: received", "status: promoted").rstrip("\n") + (
        "\n- 2020-01-01T00:00:00+03:30 | state:promoted | fixture | ok | actor:x\n")
    cases = {
        "traversal": base.replace("raw_media: null", "raw_media: ../../../../etc/passwd"),
        "missing-hash": base.replace(
            next(l for l in base.splitlines() if l.startswith("sha256:")), "sha256: null"),
        "bad-transition": bad_jump,
        "bad-schema": base.replace("schema_version: 1.0.0", "schema_version: 9.9.9"),
        "missing-section": base.split("## Provenance events")[0],
    }
    for i, (name, text) in enumerate(cases.items()):
        fake = f"cap-20200101-000000-{i + 1:04x}"
        text = text.replace(base.splitlines()[0], "---", 1)
        # normalize id + filename so ONLY the intended defect fires
        import re as _re
        text = _re.sub(r"^id: .*$", f"id: {fake}", text, count=1, flags=_re.M)
        (INVALID / name).mkdir(parents=True, exist_ok=True)
        (INVALID / name / f"{fake}.md").write_text(text, encoding="utf-8")

    # media-mismatch: a real voice record whose bytes wear a .png name.
    voice_recs = [c for c in VALID.rglob("cap-*.md")
                  if "\ncapture_kind: voice\n" in c.read_text(encoding="utf-8")]
    assert voice_recs, "no voice fixture built"
    vtext = voice_recs[0].read_text(encoding="utf-8")
    mm_dir = INVALID / "media-mismatch"
    mm_dir.mkdir(parents=True, exist_ok=True)
    src_media = next((voice_recs[0].parent / "media").glob("*.wav"))
    (mm_dir / "mismatch.png").write_bytes(src_media.read_bytes())
    old_media = next(l for l in vtext.splitlines() if l.startswith("raw_media:"))
    mm_fake = "cap-20200101-000000-00ff"
    mm_text = vtext.replace(old_media, "raw_media: REWRITE-ME-mismatch.png")
    import re as _re2
    mm_text = _re2.sub(r"^id: .*$", f"id: {mm_fake}", mm_text, count=1, flags=_re2.M)
    (mm_dir / f"{mm_fake}.md").write_text(mm_text, encoding="utf-8")

    expect = {
        "traversal": "E_TRAVERSAL", "missing-hash": "E_BAD_HASH",
        "bad-transition": "E_BAD_TRANSITION", "media-mismatch": "E_MEDIA_MISMATCH",
        "bad-schema": "E_BAD_SCHEMA", "missing-section": "E_MISSING_SECTION",
    }
    # media-mismatch text record claims voice: validator flags kind/structure gap.
    # Verify each invalid fixture fails (exact code asserted in test_fixtures.py).
    n_valid = len(list(VALID.rglob("cap-*.md")))
    print(f"valid: {n_valid}, invalid cases: {sorted(expect)}")
    (FIX / "expected-invalid.json").write_text(
        __import__("json").dumps(expect, indent=1), encoding="utf-8")
    shutil.rmtree(FIX / ".build", ignore_errors=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
