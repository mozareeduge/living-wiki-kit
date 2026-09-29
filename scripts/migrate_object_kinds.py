#!/usr/bin/env python3
"""Migrate legacy object `kind` values toward labels (dossier §42).

Read-only by default (--dry-run): reports, for every 03-objects/*.md
carrying a `kind:` field, the proposed mapping

    kind: person  ->  labels: [person], legacy_kind: person, kind removed

--apply rewrites files, but ONLY on a clean working tree, and a populated
instance still needs its operator: this tool never runs automatically and
never touches _originals/, manifests, or checksums.

Usage:
  python scripts/migrate_object_kinds.py [--repo .] [--dry-run | --apply]
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

FM_BLOCK = re.compile(r"\A---\r?\n(.*?)\r?\n---\r?\n?", re.DOTALL)
KIND_LINE = re.compile(r"^kind:\s*(.+?)\s*$", re.MULTILINE)
LABELS_LINE = re.compile(r"^labels:\s*\[(.*)\]\s*$", re.MULTILINE)


def _clean_tree(root: Path) -> bool:
    try:
        out = subprocess.run(["git", "status", "--porcelain"], cwd=root,
                             capture_output=True, text=True, timeout=60)
    except Exception:
        return False
    return out.returncode == 0 and not out.stdout.strip()


def _parse_flow_list(inner: str) -> list[str]:
    return [i.strip().strip("\"'") for i in inner.split(",") if i.strip().strip("\"'")]


def plan(root: Path) -> list[dict]:
    items: list[dict] = []
    zone = root / "03-objects"
    if not zone.is_dir():
        return items
    for md in sorted(zone.rglob("*.md")):
        try:
            text = md.read_text(encoding="utf-8")
        except OSError:
            continue
        m = FM_BLOCK.match(text)
        if not m:
            continue
        km = KIND_LINE.search(m.group(1))
        if not km:
            continue
        kind = km.group(1).strip().strip("\"'")
        lm = LABELS_LINE.search(m.group(1))
        labels = _parse_flow_list(lm.group(1)) if lm else []
        items.append({"path": md.relative_to(root).as_posix(), "kind": kind,
                      "labels": labels,
                      "would_add_label": kind not in labels})
    return items


def apply_migration(root: Path, items: list[dict]) -> int:
    n = 0
    for item in items:
        p = root / item["path"]
        text = p.read_text(encoding="utf-8")
        m = FM_BLOCK.match(text)
        assert m is not None
        fm = m.group(1)
        labels = list(item["labels"])
        if item["would_add_label"]:
            labels.append(item["kind"])
        if LABELS_LINE.search(fm):
            fm = LABELS_LINE.sub(
                "labels: [" + ", ".join(labels) + "]", fm, count=1)
        else:
            fm = fm.rstrip("\n") + "\nlabels: [" + ", ".join(labels) + "]\n"
        fm = KIND_LINE.sub(f"legacy_kind: {item['kind']}", fm, count=1)
        p.write_text(text[:m.start(1)] + fm + text[m.end(1):], encoding="utf-8")
        n += 1
    return n


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo", default=None)
    ap.add_argument("--dry-run", action="store_true", default=True)
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args(argv)
    root = Path(args.repo).resolve() if args.repo else Path(__file__).resolve().parents[1]
    items = plan(root)
    print(f"legacy kinds to migrate: {len(items)}")
    for item in items:
        print(f"  {item['path']}: kind={item['kind']!r} "
              f"-> labels+=({item['kind']!r} if missing), legacy_kind set, kind removed")
    if not args.apply:
        print("(dry run: tree unchanged)")
        return 0
    if not _clean_tree(root):
        print("ERROR: --apply refuses on a dirty (or non-git) tree", file=sys.stderr)
        return 2
    n = apply_migration(root, items)
    print(f"migrated {n} records (operator-gated; review the diff before committing)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
