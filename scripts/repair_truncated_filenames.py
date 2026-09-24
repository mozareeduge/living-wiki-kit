#!/usr/bin/env python3
"""Repair source-record `filename` values that an earlier intake step cut at the first space.

Only provable cases are repaired: the stored value equals the first space-separated token of
basename(original_path), including YAML's coercion of that token to a number or boolean
(e.g. `filename: 4` for "4 Nayebzadah.pdf", `filename: True` for "On DETECt ... .pdf").
Everything else is listed for human review and left untouched. Only the `filename` line of
each record changes; the file is re-read to prove no other field moved.

Dry run by default. Usage:
    python scripts/repair_truncated_filenames.py [--repo .] [--status pending-registration] [--apply]
"""
from __future__ import annotations

import argparse
import json
import pathlib
import posixpath
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from gov_kernel.frontmatter import load_markdown_frontmatter  # noqa: E402

YAML_BOOL = {"y", "yes", "on", "true", "n", "no", "off", "false"}


def is_truncation(have: object, want: str) -> bool:
    if " " not in want:
        return False
    first = want.split(" ")[0]
    if isinstance(have, bool):
        return first.lower() in YAML_BOOL and have == (first.lower() in {"y", "yes", "on", "true"})
    if isinstance(have, (int, float)):
        return first == str(have)
    return have == first


def plan(root: pathlib.Path, status: str | None) -> tuple[list[dict], list[dict]]:
    fixes, review = [], []
    for rp in sorted((root / "02-sources/records").glob("*.md")):
        fm, _ = load_markdown_frontmatter(rp)
        if fm.get("type") != "source-record" or not isinstance(fm.get("original_path"), str):
            continue
        if status and fm.get("status") != status:
            continue
        want = posixpath.basename(fm["original_path"])
        have = fm.get("filename")
        if have == want:
            continue
        row = {"record": rp.relative_to(root).as_posix(), "id": fm.get("id"), "status": fm.get("status"), "filename": have, "basename": want}
        (fixes if is_truncation(have, want) else review).append(row)
    return fixes, review


def apply_fix(root: pathlib.Path, row: dict) -> None:
    rp = root / row["record"]
    before, _ = load_markdown_frontmatter(rp)
    raw = rp.read_bytes()
    nl = b"\r\n" if b"\r\n" in raw else b"\n"
    lines = raw.split(nl)
    end = lines.index(b"---", 1)
    idx = [i for i in range(1, end) if lines[i].startswith(b"filename:")]
    if len(idx) != 1 or lines[idx[0] + 1][:1] in (b" ", b"\t"):
        raise RuntimeError(f"unexpected filename layout in {row['record']}")
    lines[idx[0]] = ("filename: " + json.dumps(row["basename"], ensure_ascii=False)).encode("utf-8")
    rp.write_bytes(nl.join(lines))
    after, _ = load_markdown_frontmatter(rp)
    if after.get("filename") != row["basename"] or {k: v for k, v in after.items() if k != "filename"} != {k: v for k, v in before.items() if k != "filename"}:
        rp.write_bytes(raw)
        raise RuntimeError(f"verification failed, restored {row['record']}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--repo", default=".")
    ap.add_argument("--status", help="only records with this status (e.g. pending-registration)")
    ap.add_argument("--apply", action="store_true", help="write the repairs (default: dry run)")
    a = ap.parse_args()
    root = pathlib.Path(a.repo).resolve()
    fixes, review = plan(root, a.status)
    if a.apply:
        for row in fixes:
            apply_fix(root, row)
    print(json.dumps({"mode": "apply" if a.apply else "dry-run", "repairable": len(fixes), "needs_review": review, "repaired": len(fixes) if a.apply else 0}, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
