#!/usr/bin/env python3
"""Schema-drift fixer (Phase 2 execution arm) - path-derivable frontmatter only.

Governance: writes into content zones travel ONLY through a patch manifest.
This tool (1) derives corrections from the validator's own error output and
each file's path, (2) freezes them as PATCH_MANIFEST.json, (3) --apply
executes exactly the manifest (line-based, format-preserving; never rewrites
whole YAML). Semantic fields are NEVER touched: missing counter_evidence,
unknown status values, mojibake aliases, etc. stay for human judgment.

Derivation rules (all path- or sibling-derived, none invented):
  - 02-sources/records missing 'filename'      -> basename(original_path)
  - 02-sources/records wrong 'type'            -> 'source-record'
  - 03-objects wrong 'type'                    -> 'object'
  - 03-objects missing/wrong 'kind'            -> OBJECT_KIND_BY_DIR[dir]
  - 05-claims missing 'type'                   -> 'claim-object'
  - 06-relations missing 'type'                -> 'relation-object'

Usage:
  python scripts/schema_drift_fixer.py --errors <validate-full-output.txt> [--root R]
      -> writes _audits/<run>/PATCH_MANIFEST.json + fix-plan summary (dry run)
  ... --apply
      -> executes the frozen manifest on the current branch
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

OBJECT_KIND_BY_DIR = {
    "concepts": "concept", "institutions": "institution", "methods": "method",
    "people": "person", "references": "reference", "works": "work",
    "projects": "project", "collections": "collection",
}

ERR_FILENAME = re.compile(r"^ERROR: (\S+): missing required field 'filename'$")
ERR_TYPE_SRC = re.compile(r"^ERROR: (\S+): source record type must be 'source-record'$")
ERR_TYPE_OBJ = re.compile(r"^ERROR: (\S+): object type must be 'object', got (.+)$")
ERR_KIND_MISS = re.compile(r"^ERROR: (03-objects/[^:]+): missing required field 'kind'$")
ERR_KIND_WRONG = re.compile(
    r"^ERROR: (03-objects/[^:]+): object kind must be '([^']+)' for 03-objects/([^/]+)/, got (.+)$")
ERR_TYPE_CLAIM = re.compile(r"^ERROR: (\S+): missing required field 'type'$")
ERR_TYPE_REL = re.compile(r"^ERROR: (\S+): missing required field 'type'$")


def _fm_span(text: str) -> tuple[int, int] | None:
    """Return (start, end) char offsets of the top frontmatter block."""
    if not text.startswith("---"):
        m = re.match(r"^\uFEFF?---\r?\n", text)
        if not m:
            return None
        start = m.end() - len("\n")
    else:
        start = 3
    end = text.find("\n---", start)
    if end < 0:
        return None
    return (start, end)


def _has_key(block: str, key: str) -> bool:
    return re.search(rf"^{key}:", block, re.MULTILINE) is not None


def plan_ops(root: Path, err_file: Path) -> tuple[list[dict], list[str]]:
    ops: dict[str, dict] = {}
    skipped: list[str] = []
    for raw in err_file.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if m := ERR_FILENAME.match(line):
            rel = m.group(1)
            p = root / rel
            text = p.read_text(encoding="utf-8-sig", errors="ignore") if p.exists() else ""
            om = re.search(r"^original_path:\s*(.+)$", text, re.MULTILINE)
            if om:
                raw = om.group(1).strip().strip('"\'').replace("\\", "/")
                fname = raw.rsplit("/", 1)[-1]
                if fname and not fname.startswith(("[", "{")) and len(fname) < 260:
                    ops[rel] = {"path": rel, "op": "insert",
                                "after_key": "id", "field": "filename", "value": fname}
                else:
                    skipped.append(f"{rel}: filename underivable (unusable original_path: {raw[:60]})")
            else:
                skipped.append(f"{rel}: filename underivable (no original_path)")
        elif m := ERR_TYPE_SRC.match(line):
            ops[m.group(1)] = {"path": m.group(1), "op": "set",
                               "field": "type", "value": "source-record"}
        elif m := ERR_TYPE_OBJ.match(line):
            ops[m.group(1)] = {"path": m.group(1), "op": "set",
                               "field": "type", "value": "object"}
        elif m := ERR_KIND_MISS.match(line):
            folder = m.group(1).split("/")[1]
            kind = OBJECT_KIND_BY_DIR.get(folder)
            if kind:
                ops[m.group(1)] = {"path": m.group(1), "op": "insert",
                                   "after_key": "type", "field": "kind", "value": kind}
            else:
                skipped.append(f"{m.group(1)}: kind underivable (unknown dir)")
        elif m := ERR_KIND_WRONG.match(line):
            ops[m.group(1)] = {"path": m.group(1), "op": "set",
                               "field": "kind", "value": m.group(2)}
        elif m := ERR_TYPE_CLAIM.match(line):
            rel = m.group(1)
            if rel.startswith("05-claims/"):
                ops[rel] = {"path": rel, "op": "insert",
                            "after_key": "id", "field": "type", "value": "claim-object"}
            elif rel.startswith("06-relations/"):
                ops[rel] = {"path": rel, "op": "insert",
                            "after_key": "id", "field": "type", "value": "relation-object"}
            elif rel.startswith("03-objects/"):
                ops[rel] = {"path": rel, "op": "insert",
                            "after_key": "id", "field": "type", "value": "object"}
            else:
                skipped.append(f"{rel}: type underivable (zone unknown)")
    return list(ops.values()), skipped


def apply_manifest(root: Path, manifest: dict) -> tuple[int, int]:
    changed = failed = 0
    for op in manifest["operations"]:
        p = root / op["path"]
        if not p.exists():
            failed += 1
            continue
        text = p.read_text(encoding="utf-8-sig", errors="ignore")
        span = _fm_span(text)
        if span is None:
            failed += 1
            continue
        block = text[span[0]:span[1]]
        field = op["field"]
        if op["op"] == "insert":
            if _has_key(block, field):
                failed += 1
                continue
            anchor = op.get("after_key", "id")
            am = re.search(rf"^{anchor}:.*(?:\n(?![A-Za-z_-]+:).*)*", block, re.MULTILINE)
            new_line = f"\n{field}: {op['value']}"
            if am:
                new_block = block[:am.end()] + new_line + block[am.end():]
            else:
                new_block = block + new_line
        else:  # set
            vm = re.search(rf"^{field}:.*$", block, re.MULTILINE)
            if not vm:
                new_block = block + f"\n{field}: {op['value']}"
            else:
                new_block = block[:vm.start()] + f"{field}: {op['value']}" + block[vm.end():]
        # preserve original BOM/leading text; replace only the block interior
        new_text = text[:span[0]] + new_block + text[span[1]:]
        if new_text != text:
            p.write_text(new_text, encoding="utf-8", newline="")
            changed += 1
    return changed, failed


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--errors", type=Path, required=True,
                    help="validator --full output file")
    ap.add_argument("--root", default=None)
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    root = Path(args.root).resolve() if args.root else Path(__file__).resolve().parents[1]
    ops, skipped = plan_ops(root, args.errors)
    run_id = time.strftime("2026-%m-%d--schema-drift-reconcile")
    run_dir = root / "_audits" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "id": f"mw-patch-{run_id}",
        "status": "auto-derived-path-fields",
        "purpose": ("Path-derivable frontmatter drift (type/kind/filename) per "
                    "validator error output; derivation documented per op; "
                    "semantic fields untouched, left for human adjudication."),
        "derivation": ("filename=basename(original_path); type/kind from canonical "
                       "zone+dir (OBJECT_KIND_BY_DIR); no values invented"),
        "generated_by": "scripts/schema_drift_fixer.py",
        "generated_at_epoch": int(time.time()),
        "operations": ops,
        "skipped_underivable": skipped,
    }
    out = run_dir / "PATCH_MANIFEST.json"
    out.write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"manifest: {out} ops={len(ops)} skipped={len(skipped)}")
    if args.apply:
        changed, failed = apply_manifest(root, manifest)
        print(f"applied: {changed} changed, {failed} failed")
        return 0 if not failed else 1
    for s in skipped[:6]:
        print(f"  skip: {s}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
