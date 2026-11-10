#!/usr/bin/env python3
"""CLI interface for Living Wiki file ingestion.

Usage:
    python scripts/ingest_file.py <path> [--repo <dir>] [--title <title>] [--description <desc>] [--request-id <id>] [--json]
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from gov_kernel.ingest import IngestError, ingest_file  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("file", help="Path to staged file to ingest")
    ap.add_argument("--repo", default=".", help="Repository root directory")
    ap.add_argument("--title", default=None, help="Optional title for the source document")
    ap.add_argument("--description", default=None, help="Optional description")
    ap.add_argument("--request-id", default=None, help="Optional idempotency request ID")
    ap.add_argument("--json", action="store_true", help="Print receipt as JSON to stdout")

    args = ap.parse_args(argv)
    root = pathlib.Path(args.repo).resolve()

    try:
        receipt = ingest_file(
            staged_path=args.file,
            root=root,
            title=args.title,
            description=args.description,
            request_id=args.request_id,
        )
        if args.json:
            print(json.dumps(receipt, ensure_ascii=False, indent=2))
        else:
            print(f"Ingested: {receipt.get('source_ref')}")
            print(f"  SHA-256:        {receipt.get('sha256')}")
            print(f"  Bytes:          {receipt.get('bytes')}")
            print(f"  MIME:           {receipt.get('mime')}")
            print(f"  Source Version: {receipt.get('source_version')}")
            print(f"  Status:         {receipt.get('extraction', {}).get('status')}")
            if receipt.get("duplicate_of"):
                print(f"  (Duplicate of: {receipt.get('duplicate_of')})")
        return 0
    except IngestError as exc:
        err = {"ok": False, "code": exc.code, "message": exc.message}
        if args.json:
            print(json.dumps(err, ensure_ascii=False))
        else:
            print(f"ERROR [{exc.code}]: {exc.message}", file=sys.stderr)
        return 1
    except Exception as exc:
        err = {"ok": False, "code": "E_INTERNAL", "message": str(exc)}
        if args.json:
            print(json.dumps(err, ensure_ascii=False))
        else:
            print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
