#!/usr/bin/env python3
"""Instantiate a new living-wiki from this kit.

Rewrites the record-ID prefix (mw- -> <prefix>) across validators, the
capture core, MCP server, schemas, and templates; writes
00-system/registers/INSTANCE.json; and prints the follow-up checklist.

Usage:
    python scripts/instantiate.py --name "My Wiki" --prefix pmw
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Files where the mw- record prefix and corpus-id pattern live.
TARGET_GLOBS = [
    "scripts/*.py",
    "scripts/capture/*.py",
    "scripts/*.ps1",
    "00-system/schemas/*.json",
    "00-system/templates/*.md",
    "00-system/policies/*.md",
    "SYSTEM_DESIGN.md",
    "SEARCH_GUIDE.md",
    "SETUP_GUIDE_WINDOWS.md",
    "GPT_WORKFLOW.md",
    "AGENTS.md",
    "CLAUDE.md",
    "HOME.md",
    "README.md",
    "RUNBOOK_WEB_CAPTURE.md",
    "RUNBOOK_*.md",
    ".claude/skills/*/SKILL.md",
    ".mcp.json",
]

MW_ID = re.compile(r"\bmw-(?=src-|cap-|corpus-)")
MOZARE_WORDS = [
    ("mozare-wiki", "this-wiki"),
    ("Mozare Wiki", "This Wiki"),
    ("mozare", "wiki"),
    ("Mozare", "Wiki"),
    ("MOZARE", "WIKI"),
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True, help='instance name, e.g. "My Wiki"')
    ap.add_argument("--prefix", required=True, help="record-ID prefix, e.g. pmw")
    args = ap.parse_args()

    prefix = args.prefix.strip().lower()
    if not re.fullmatch(r"[a-z][a-z0-9]{1,7}", prefix):
        print("ERROR: prefix must be 2-8 chars, lowercase letters/digits, "
              "starting with a letter", file=sys.stderr)
        return 2

    # --- Preconditions: never reseed a live corpus (checked before writing) ---
    state_path = ROOT / "00-system/registers/CORPUS_STATE.json"
    manifest_path = ROOT / "00-system/registers/MATERIALS_INDEX.jsonl"
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"ERROR: cannot parse CORPUS_STATE.json: {exc}", file=sys.stderr)
        return 2
    count = state.get("source_material_count")
    rows = []
    if manifest_path.exists():
        for line in manifest_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rows.append(line)
    if not isinstance(count, int) or count < 0:
        print("ERROR: CORPUS_STATE.json source_material_count missing or "
              "invalid", file=sys.stderr)
        return 2
    if rows or count != 0:
        print(f"ERROR: instance is populated (manifest rows: {len(rows)}, "
              f"registered count: {count}); instantiate.py only seeds a fresh "
              "empty kit — never rerun it on a live instance", file=sys.stderr)
        return 2
    instance_path = ROOT / "00-system/registers/INSTANCE.json"
    if instance_path.exists():
        try:
            existing = json.loads(instance_path.read_text(encoding="utf-8"))
        except Exception as exc:
            print(f"ERROR: cannot parse INSTANCE.json: {exc}", file=sys.stderr)
            return 2
        if not (existing.get("record_prefix") == prefix
                and existing.get("id") == f"{prefix}-instance"):
            print(f"ERROR: INSTANCE.json identifies a different instance "
                  f"(id={existing.get('id')!r}, "
                  f"record_prefix={existing.get('record_prefix')!r}); "
                  "refusing to reseed", file=sys.stderr)
            return 2

    corpus_old = "wiki-corpus-empty"
    corpus_new = f"{prefix}-corpus-empty"
    entry_pages = ("HOME.md", "README.md", "SYSTEM_DESIGN.md", "CLAUDE.md")

    changed = []
    for pattern in TARGET_GLOBS:
        for path in ROOT.glob(pattern):
            if not path.is_file():
                continue
            text = path.read_text(encoding="utf-8")
            new = MW_ID.sub(f"{prefix}-", text)
            for old, repl in MOZARE_WORDS:
                new = new.replace(old, repl)
            if path.name in entry_pages:
                new = new.replace(
                    f"Current corpus snapshot: `{corpus_old}`",
                    f"Current corpus snapshot: `{corpus_new}`")
            if new != text:
                path.write_text(new, encoding="utf-8")
                changed.append(path.relative_to(ROOT).as_posix())

    # Corpus register: rename the empty-state id to the instance's own.
    if state.get("id") != corpus_new:
        state["id"] = corpus_new
        state_path.write_text(json.dumps(state, indent=2) + "\n",
                              encoding="utf-8")
        changed.append(state_path.relative_to(ROOT).as_posix())

    instance = {
        "id": f"{prefix}-instance",
        "name": args.name,
        "record_prefix": prefix,
        "created_from": "living-wiki-kit 1.1.0",
        "instantiated": date.today().isoformat(),
        "authority_hierarchy_version": "1.0.0",
    }
    out = ROOT / "00-system/registers/INSTANCE.json"
    out.write_text(json.dumps(instance, indent=2) + "\n", encoding="utf-8")

    print(f"Instance: {args.name} (prefix '{prefix}')")
    print(f"Rewrote {len(changed)} files:")
    for c in changed:
        print(f"  - {c}")
    print(f"Wrote {out.relative_to(ROOT).as_posix()}")
    print("\nNext steps:")
    print("  1. Review: git diff")
    print("  2. Edit HOME.md and README.md for your subject")
    print("  3. python scripts/validate_repo.py --full")
    print("  4. git add -A && git commit -m 'bootstrap: instantiate'")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
