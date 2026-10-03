#!/usr/bin/env python3
"""Provider-neutral file-processing contract — 1.2.0 (U1).

Spec: file captures (PDF, TXT, MD, CSV) get a structured metadata
receipt via a local adapter. The adapter never modifies the original
media; it reads bytes, computes hashes, and optionally extracts text
for indexing. No network, no model calls.

The SingleFileAdapter is the base contract. Concrete adapters (e.g.,
PDF text extraction) subclass it and implement extract().
"""
from __future__ import annotations

import hashlib
import json
import mimetypes
import sys
from pathlib import Path

SYS = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SYS / "scripts" / "capture"))
import wiki_capture as wc

CAPTURE_DIR = Path(__file__).resolve().parent

# Text-based suffixes that can be safely read as UTF-8 for indexing
TEXT_SUFFIXES = {".txt", ".md", ".csv"}


class FileAdapter:
    name = "base"
    version = "0"

    def available(self) -> tuple[bool, str]:
        return False, "base adapter extracts nothing"

    def extract(self, file_path: str) -> dict:
        """Return {mime, size, sha256, text (optional), metadata, quality_flags}.
        Never guess: low-confidence extraction is flagged, not smoothed."""
        raise NotImplementedError


class SingleFileAdapter(FileAdapter):
    """Local single-file processor. Always available; the 1.2.0 default.

    Reads the file, computes SHA-256, detects MIME, and for text-based
    suffixes extracts the full text content for indexing. For binary
    formats (PDF, images) it returns metadata only — text extraction
    requires a concrete subclass.
    """
    name = "singlefile"
    version = "1.0.0"

    def available(self):
        return True, f"singlefile {self.version} (local, deterministic)"

    def extract(self, file_path: str) -> dict:
        p = Path(file_path)
        if not p.is_file():
            raise wc.CaptureError("E_NOT_FOUND", f"file not found: {file_path}")
        data = p.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        mime, _ = mimetypes.guess_type(str(p))
        mime = mime or "application/octet-stream"
        suffix = p.suffix.lower()
        text = None
        flags = []
        if suffix in TEXT_SUFFIXES:
            try:
                text = data.decode("utf-8")
            except UnicodeDecodeError:
                flags.append("binary-in-text-suffix")
                text = None
        elif suffix == ".pdf":
            flags.append("pdf-text-extraction-not-implemented")
        return {
            "mime": mime,
            "size": len(data),
            "sha256": digest,
            "text": text,
            "metadata": {
                "filename": p.name,
                "suffix": suffix,
            },
            "quality_flags": sorted(set(flags)),
        }


ADAPTERS: dict[str, FileAdapter] = {
    "singlefile": SingleFileAdapter(),
}


def process_capture(capture_id: str, adapter_name: str = "singlefile") -> dict:
    """Process a file capture: read metadata, optionally extract text,
    store the extraction in the capture record. Never modifies media."""
    rec = wc.read_capture(capture_id)
    if rec["front_matter"]["capture_kind"] not in ("file", "mixed"):
        raise wc.CaptureError("E_WRONG_KIND",
                              "file processing is for file/mixed captures")
    adapter = ADAPTERS.get(adapter_name)
    if adapter is None:
        raise wc.CaptureError("E_UNKNOWN_ADAPTER", f"unknown adapter: {adapter_name}")
    media = wc._resolve_media(rec["front_matter"]["raw_media"])
    out = adapter.extract(str(media))
    # Store extracted text as literal extraction (if any)
    if out.get("text"):
        wc.record_description(capture_id, out["text"], "",
                              adapter.name, adapter.version)
    return {
        "ok": True,
        "id": capture_id,
        "adapter": adapter.name,
        "mime": out["mime"],
        "size": out["size"],
        "sha256": out["sha256"],
        "flags": out["quality_flags"],
        "message": f"file processed ({adapter.name})",
    }


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(prog="file_contract")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("process")
    p.add_argument("--id", required=True)
    p.add_argument("--adapter", default="singlefile")
    sub.add_parser("status")
    args = ap.parse_args()
    try:
        if args.cmd == "process":
            print(json.dumps(process_capture(args.id, args.adapter),
                             ensure_ascii=False, indent=1))
        elif args.cmd == "status":
            print(json.dumps({
                "adapters": {k: {"available": a.available()[0],
                                 "detail": a.available()[1]}
                             for k, a in ADAPTERS.items()},
            }, ensure_ascii=False, indent=1))
    except wc.CaptureError as e:
        print(json.dumps({"ok": False, "code": e.code, "message": e.message},
                         ensure_ascii=False), file=sys.stderr)
        raise SystemExit(1)
