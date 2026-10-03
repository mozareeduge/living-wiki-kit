#!/usr/bin/env python3
"""Instance profiles: composable advisory bundles (dossier §14-19).

A profile suggests vocabulary, relation language, lenses and outputs for a
practice/domain/collaboration/compliance context. Profiles compose
additively, may tighten kernel rules, and can NEVER weaken them: the schema
accepts advisory keys only, so there is no key through which a profile could
disable validation, authority, or evidence rules.

Active set: `active_profiles` in 00-system/registers/INSTANCE.json
(absent file or key means []; the empty kit stays profile-neutral).
Single-value slots (preferred_lens/preferred_output) with different values
across active profiles are reported as conflicts, never silently resolved;
`profile_overrides` in INSTANCE.json may resolve them explicitly.

Usage:
  python scripts/wiki_profiles.py check [--repo .]
  python scripts/wiki_profiles.py compose [--repo .] [--format json]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gov_kernel.schemas import validate_record  # noqa: E402

PROFILES_DIRNAME = Path("00-system/configuration/profiles")
SCHEMAS_DIRNAME = Path("00-system/schemas")
INSTANCE_REL = Path("00-system/registers/INSTANCE.json")

LIST_KEYS = ("seed_labels", "suggested_relation_language",
             "suggested_lenses", "suggested_outputs")
SINGLE_KEYS = ("preferred_lens", "preferred_output")

_FM_BLOCK = re.compile(r"\A---\r?\n(.*?)\r?\n---\r?\n?", re.DOTALL)


def _split_flow(value: str) -> list[str]:
    items: list[str] = []
    depth = 0
    cur = ""
    for ch in value:
        if ch in "[{\"'":
            depth += ch in "[{"
        if ch in "]}":
            depth -= 1
        if ch == "," and depth <= 0:
            items.append(cur)
            cur = ""
        else:
            cur += ch
    if cur.strip():
        items.append(cur)
    return [i.strip().strip("\"'") for i in items if i.strip().strip("\"'")]


def parse_profile(text: str) -> dict:
    """Frontmatter of a profile .md: scalars + flow-style [a, b] lists."""
    m = _FM_BLOCK.match(text)
    if not m:
        return {}
    out: dict = {}
    for line in m.group(1).splitlines():
        if not line.strip() or line.strip().startswith("#"):
            continue
        k, sep, v = line.partition(":")
        if not sep:
            continue
        k = k.strip()
        v = v.strip()
        if v.startswith("[") and v.endswith("]"):
            out[k] = _split_flow(v[1:-1])
        elif v in ("null", "~", ""):
            out[k] = None
        else:
            out[k] = v.strip("\"'")
    return out


def _profiles_dir(root: Path) -> Path:
    return root / PROFILES_DIRNAME


def available(root: Path) -> dict[str, Path]:
    d = _profiles_dir(root)
    if not d.is_dir():
        return {}
    return {p.stem: p for p in sorted(d.glob("*.md"))}


def load_active_ids(root: Path) -> list[str]:
    inst = root / INSTANCE_REL
    if not inst.exists():
        return []
    try:
        data = json.loads(inst.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    ids = data.get("active_profiles", [])
    return [str(i) for i in ids] if isinstance(ids, list) else []


def load_overrides(root: Path) -> dict[str, str]:
    inst = root / INSTANCE_REL
    if not inst.exists():
        return {}
    try:
        data = json.loads(inst.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    ov = data.get("profile_overrides", {})
    return {str(k): str(v) for k, v in ov.items()} if isinstance(ov, dict) else {}


def read_profile(doc: Path, schema_dir: Path) -> tuple[dict, list[str]]:
    """Parse + schema-validate one profile doc. Returns (record, errors)."""
    try:
        record = parse_profile(doc.read_text(encoding="utf-8"))
    except OSError as exc:
        return {}, [f"{doc.name}: unreadable ({exc})"]
    findings = validate_record(record, schema_dir, explicit_schema="wiki-profile.schema.json")
    errs = [f.message for f in findings]
    if "type" in record and record.get("type") != "wiki-profile":
        errs.append(f"{doc.name}: type must be 'wiki-profile'")
    return record, errs


def compose(root: Path) -> tuple[dict, list[str]]:
    """Compose active profiles. Returns (composed, findings); findings
    non-empty means: unknown/retired/invalid profile, a weakening attempt
    (unknown control key), or an un-overridden slot conflict."""
    schema_dir = root / SCHEMAS_DIRNAME
    avail = available(root)
    active = load_active_ids(root)
    overrides = load_overrides(root)
    findings: list[str] = []
    records: list[tuple[str, dict]] = []
    for pid in active:
        doc = avail.get(pid)
        if doc is None:
            findings.append(f"unknown profile: {pid!r}")
            continue
        record, errs = read_profile(doc, schema_dir)
        if errs:
            findings += [f"{pid}: {e}" for e in errs]
            continue
        if record.get("status") == "retired":
            findings.append(f"{pid}: retired profile cannot be activated")
            continue
        records.append((pid, record))

    composed: dict = {"active_profiles": [pid for pid, _ in records]}
    for key in LIST_KEYS:
        seen: list[str] = []
        for _, rec in records:
            for item in rec.get(key) or []:
                if item not in seen:
                    seen.append(item)
        composed[key] = seen
    for key in SINGLE_KEYS:
        claimants = [(pid, rec[key]) for pid, rec in records if rec.get(key)]
        if not claimants:
            composed[key] = None
        elif len({v for _, v in claimants}) == 1:
            composed[key] = claimants[0][1]
        elif key in overrides:
            composed[key] = overrides[key]
        else:
            who = ", ".join(f"{pid}={v!r}" for pid, v in claimants)
            findings.append(f"profile conflict on {key}: {who} "
                            f"(resolve via profile_overrides in INSTANCE.json)")
            composed[key] = None
    return composed, findings


def cmd_check(root: Path) -> int:
    composed, findings = compose(root)
    if findings:
        print("profile check FAILED:")
        for f in findings:
            print(f"  - {f}")
        return 2
    actives = composed["active_profiles"]
    print(f"profile check OK: {len(actives)} active "
          f"({', '.join(actives) if actives else 'profile-neutral kit'})")
    return 0


def cmd_compose(root: Path) -> int:
    composed, findings = compose(root)
    print(json.dumps({"composed": composed, "findings": findings},
                     ensure_ascii=False, indent=1))
    return 2 if findings else 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("command", choices=("check", "compose"))
    ap.add_argument("--repo", default=None)
    args = ap.parse_args(argv)
    root = Path(args.repo).resolve() if args.repo else Path(__file__).resolve().parents[1]
    return cmd_compose(root) if args.command == "compose" else cmd_check(root)


if __name__ == "__main__":
    raise SystemExit(main())
