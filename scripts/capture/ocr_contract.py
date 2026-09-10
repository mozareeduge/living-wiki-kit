#!/usr/bin/env python3
"""Provider-neutral image/handwriting contract — 1.2.0 (Task 10).

Spec §7: original image immutable (core enforces); SHA-256 before
processing (core enforces); orientation fixed only in a derivative preview;
literal visible text and descriptive interpretation stored separately;
page/region refs when possible; illegible regions flagged, never guessed;
user corrections live alongside machine output; a diagram description is
never a substitute for the diagram.

Ships one working local adapter (RapidOCR, onnxruntime) for literal
extraction. Description (semantic interpretation) is manual-only in 1.2.0:
no vision model is invoked by the pipeline.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

SYS = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SYS / "scripts" / "capture"))
import wiki_capture as wc

CAPTURE_DIR = Path(__file__).resolve().parent


class OCRAdapter:
    name = "base"
    version = "0"

    def available(self) -> tuple[bool, str]:
        return False, "base adapter extracts nothing"

    def extract(self, image_path: str) -> dict:
        """Return {regions: [{page, box, text}], illegible: [boxes],
        quality_flags: [...]}. Never guess: low-confidence text is reported
        with its box, not smoothed into sentences."""
        raise NotImplementedError


class RapidOCAdapter(OCRAdapter):
    name = "rapidocr"
    version = "1.4.4"

    def available(self):
        try:
            import rapidocr_onnxruntime  # noqa: F401
            return True, f"rapidocr-onnxruntime {self.version}"
        except Exception as exc:  # noqa: BLE001
            return False, f"rapidocr unusable: {exc}"

    def extract(self, image_path: str) -> dict:
        ok, why = self.available()
        if not ok:
            raise wc.CaptureError("E_ENGINE_UNAVAILABLE", why)
        from rapidocr_onnxruntime import RapidOCR
        engine = RapidOCR()
        result, _ = engine(str(image_path))
        regions, illegible, flags = [], [], []
        if not result:
            flags.append("incomplete")
            return {"regions": regions, "illegible": illegible,
                    "quality_flags": flags}
        for box, text, conf in result:
            try:
                conf_f = float(conf)
            except (TypeError, ValueError):
                conf_f = 0.0
            entry = {"page": 1, "box": [list(map(float, p)) for p in box],
                     "text": text, "confidence": conf_f}
            if conf_f < 0.5:
                illegible.append(entry)
                flags.append("uncertain-reading")
            else:
                regions.append(entry)
        return {"regions": regions, "illegible": illegible,
                "quality_flags": sorted(set(flags))}


ADAPTERS: dict[str, OCRAdapter] = {"rapidocr": RapidOCAdapter()}


def make_preview(image_path: str, capture_id: str) -> dict:
    """Derivative preview: orientation-corrected copy beside the media.
    The original is never touched. Returns the preview's repo-relative path."""
    try:
        from PIL import Image, ImageOps
    except ImportError:
        raise wc.CaptureError("E_NO_PREVIEW",
                              "Pillow is not installed; preview skipped")
    src = Path(image_path)
    dest = src.parent / f"{src.stem}.preview{src.suffix or '.jpg'}"
    img = Image.open(src)
    img = ImageOps.exif_transpose(img)
    img.thumbnail((1600, 1600))
    img.save(dest)
    try:
        rel = str(dest.relative_to(wc.REPO_ROOT)).replace("\\", "/")
    except ValueError:
        rel = dest.as_posix()
    return {"ok": True, "preview": rel}


def extract_capture(capture_id: str, adapter_name: str = "rapidocr") -> dict:
    rec = wc.read_capture(capture_id)
    if rec["front_matter"]["capture_kind"] not in (
            "handwriting", "drawing", "image", "mixed", "file"):
        raise wc.CaptureError("E_WRONG_KIND",
                              "extraction is for visual/file captures")
    adapter = ADAPTERS.get(adapter_name)
    if adapter is None:
        raise wc.CaptureError("E_UNKNOWN_ADAPTER", f"unknown adapter: {adapter_name}")
    media = wc._resolve_media(rec["front_matter"]["raw_media"])
    out = adapter.extract(str(media))
    lines = []
    for r in out["regions"]:
        lines.append(f"- p{r['page']} {r['box'][0]}: {r['text']}")
    for r in out["illegible"]:
        lines.append(f"- p{r['page']} {r['box'][0]}: ILLEGIBLE ({r['text']!r})")
    literal = "\n".join(lines) + ("\n" if lines else "")
    wc.record_description(capture_id, literal, "",
                          adapter.name, adapter.version)
    try:
        preview = make_preview(str(media), capture_id)["preview"]
    except wc.CaptureError:
        preview = None
    return {"ok": True, "id": capture_id, "adapter": adapter.name,
            "regions": len(out["regions"]),
            "illegible": len(out["illegible"]),
            "flags": out["quality_flags"], "preview": preview,
            "message": "literal extraction stored; interpretation stays manual"}


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(prog="ocr_contract")
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("extract")
    e.add_argument("--id", required=True)
    e.add_argument("--adapter", default="rapidocr")
    args = ap.parse_args()
    try:
        if args.cmd == "extract":
            print(json.dumps(extract_capture(args.id, args.adapter),
                             ensure_ascii=False, indent=1))
    except wc.CaptureError as exc:
        print(json.dumps({"ok": False, "code": exc.code, "message": exc.message},
                         ensure_ascii=False), file=sys.stderr)
        raise SystemExit(1)
