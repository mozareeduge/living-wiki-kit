#!/usr/bin/env python3
"""Retier held-but-unregistered source records (task A5, design.md section 8).

The migration instrument for populated instances. Safe by construction:

- default is a dry run: it prints the plan and writes nothing;
- ``--apply`` performs the same plan, but only after every precondition in
  ``check_working_tree_clean`` / ``build_plan`` passes -- each failure exits
  nonzero with a one-line reason, before any file is touched. This mirrors
  the precondition-then-write shape of ``scripts/instantiate.py``.

Tier selection per record: ``family_tier_overrides[family]`` (declared in
``00-system/policies/HOLDINGS_POLICY.json``) if that family is present,
else ``default_tier_for_unregistered``.

Never touches ``_originals/``, ``MATERIALS_INDEX.jsonl``, or any ``sha256``
value, and never changes a record that is already correctly ``registered``
(design.md section 8; tasks.md A5 Negative).
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import yaml

SCRIPTS_DIR = Path(__file__).resolve().parent
ROOT = SCRIPTS_DIR.parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))
import validate_repo  # noqa: E402

HOLDINGS_TIER_REGISTERED = validate_repo.HOLDINGS_TIER_REGISTERED
MANIFEST_REL = "00-system/registers/MATERIALS_INDEX.jsonl"
STATE_REL = "00-system/registers/CORPUS_STATE.json"


class RetierRefusal(Exception):
    """A precondition failed; str(exc) is the one-line refusal reason."""


def _originals_files(root: Path) -> list[Path]:
    d = root / "_originals"
    return sorted(p for p in d.rglob("*") if p.is_file()) if d.exists() else []


def _load_records(root: Path) -> dict[str, dict]:
    records_dir = root / "02-sources" / "records"
    records: dict[str, dict] = {}
    if records_dir.exists():
        for path in sorted(records_dir.rglob("*.md")):
            rel = path.relative_to(root).as_posix()
            records[rel] = validate_repo.parse_frontmatter(path)
    return records


def working_tree_is_dirty(root: Path) -> bool:
    """True only when `root` is a git worktree with uncommitted changes.

    A fixture directory with no `.git` (as produced by test helpers that
    copy tracked files without history) cannot be inspected for
    dirtiness and is treated as clean -- there is nothing to compare
    against. A real git worktree is checked with `git status --porcelain`.
    """
    if not (root / ".git").exists():
        return False
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"], cwd=root,
            capture_output=True, text=True, encoding="utf-8",
            errors="replace",
        )
    except (OSError, subprocess.SubprocessError):
        return False
    if result.returncode != 0:
        return False
    return bool(result.stdout.strip())


def build_plan(root: Path) -> dict:
    """Compute the retiering plan, or raise RetierRefusal.

    Reads only; performs no writes. Raises before returning a partial plan
    on any of the four refusal conditions named in tasks.md A5:
    manifest/state count disagreement, a missing or malformed
    HOLDINGS_POLICY.json, an unknown tier named by
    default_tier_for_unregistered or a family override, or a
    family_tier_overrides key matching no record's family.
    """
    state_path = root / STATE_REL
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 - surfaced as a refusal, not a crash
        raise RetierRefusal(f"cannot parse {STATE_REL}: {exc}") from exc

    try:
        policy = validate_repo.load_holdings_policy(root)
    except ValueError as exc:
        raise RetierRefusal(str(exc)) from exc

    declared_tiers = policy["tiers"]
    default_tier = policy["default_tier_for_unregistered"]
    overrides = policy.get("family_tier_overrides") or {}

    manifest_path = root / MANIFEST_REL
    rows: list[dict] = []
    if manifest_path.exists():
        for number, line in enumerate(
            manifest_path.read_text(encoding="utf-8").splitlines(), 1
        ):
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise RetierRefusal(f"{MANIFEST_REL}: line {number}: {exc}") from exc

    source_count = state.get("source_material_count")
    if len(rows) != source_count:
        raise RetierRefusal(
            f"manifest row count ({len(rows)}) disagrees with "
            f"source_material_count ({source_count}); the base state is "
            f"already broken, fix it before retiering"
        )

    registered_record_paths = {
        row["source_record_path"] for row in rows if row.get("source_record_path")
    }
    manifest_original_paths = {
        row["original_path"] for row in rows if row.get("original_path")
    }

    records = _load_records(root)

    known_families = {
        fm.get("family") for fm in records.values() if fm.get("family")
    }
    for family in overrides:
        if family not in known_families:
            raise RetierRefusal(
                f"family_tier_overrides names family {family!r} which "
                f"matches no record's family field"
            )

    correctly_registered = 0
    to_retier: list[dict] = []
    per_family: dict[str, int] = {}
    resulting_tier_by_rel: dict[str, str] = {}

    for rel, fm in sorted(records.items()):
        if rel in registered_record_paths:
            correctly_registered += 1
            resulting_tier_by_rel[rel] = HOLDINGS_TIER_REGISTERED
            continue

        family = fm.get("family")
        new_tier = overrides.get(family, default_tier)
        if new_tier not in declared_tiers:
            raise RetierRefusal(
                f"{rel}: resolved holdings tier {new_tier!r} is not "
                f"declared in HOLDINGS_POLICY.json"
            )
        resulting_tier_by_rel[rel] = new_tier

        if fm.get("status") == new_tier and fm.get("holdings_tier") == new_tier:
            # Already correctly tiered; nothing would change.
            continue
        to_retier.append({"rel": rel, "fm": fm, "family": family, "new_tier": new_tier})
        per_family[family] = per_family.get(family, 0) + 1

    # holdings_by_tier / held_artifact_count are counted over the physical
    # files under _originals/, exactly as check_holdings_census counts
    # them, so a following `validate_repo.py --full` agrees with what
    # --apply writes.
    by_original_path = {
        fm["original_path"]: rel
        for rel, fm in records.items()
        if fm.get("original_path")
    }
    holdings_by_tier = {tier: 0 for tier in declared_tiers}
    for path in _originals_files(root):
        rel_file = path.relative_to(root).as_posix()
        if rel_file in manifest_original_paths:
            holdings_by_tier[HOLDINGS_TIER_REGISTERED] += 1
            continue
        record_rel = by_original_path.get(rel_file)
        tier = resulting_tier_by_rel.get(record_rel) if record_rel else None
        if tier in holdings_by_tier:
            holdings_by_tier[tier] += 1
    held_artifact_count = sum(holdings_by_tier.values())

    return {
        "state": state,
        "correctly_registered": correctly_registered,
        "to_retier": to_retier,
        "per_family": per_family,
        "holdings_by_tier": holdings_by_tier,
        "held_artifact_count": held_artifact_count,
    }


def _rewrite_record(path: Path, new_status: str, new_tier: str) -> None:
    """Set status and holdings_tier; preserve every other field and the body."""
    text = path.read_text(encoding="utf-8")
    end = text.find("\n---\n", 4)
    if not text.startswith("---\n") or end < 0:
        raise RetierRefusal(f"{path}: frontmatter does not open/close as expected")
    fm_text = text[4:end]
    body = text[end + len("\n---\n"):]
    fm = yaml.safe_load(fm_text) or {}
    fm["status"] = new_status
    fm["holdings_tier"] = new_tier
    new_text = "---\n" + yaml.safe_dump(fm, sort_keys=False, allow_unicode=True) + "---\n" + body
    path.write_text(new_text, encoding="utf-8")


def _print_plan(plan: dict) -> None:
    print(f"{plan['correctly_registered']} records correctly registered")
    print(f"{len(plan['to_retier'])} records to retier")
    if plan["per_family"]:
        print("per-family counts to retier:")
        for family, count in sorted(plan["per_family"].items(), key=lambda kv: str(kv[0])):
            print(f"  {family}: {count}")
    else:
        print("per-family counts to retier: (none)")
    print(
        "resulting holdings_by_tier: "
        + json.dumps(plan["holdings_by_tier"], sort_keys=True)
    )
    print(f"held_artifact_count (would write): {plan['held_artifact_count']}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--apply", action="store_true",
        help="write the retiering plan; default is a dry run that writes nothing",
    )
    ap.add_argument(
        "--dry-run", action="store_true",
        help="print the plan and write nothing (the default; accepted explicitly too)",
    )
    args = ap.parse_args(argv)

    root = ROOT

    if args.apply and working_tree_is_dirty(root):
        print(
            "ERROR: refusing --apply on a dirty working tree; commit or "
            "stash first",
            file=sys.stderr,
        )
        return 2

    try:
        plan = build_plan(root)
    except RetierRefusal as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    _print_plan(plan)

    if not args.apply:
        return 0

    for entry in plan["to_retier"]:
        _rewrite_record(root / entry["rel"], entry["new_tier"], entry["new_tier"])

    state = plan["state"]
    state["held_artifact_count"] = plan["held_artifact_count"]
    state["holdings_by_tier"] = plan["holdings_by_tier"]
    (root / STATE_REL).write_text(
        json.dumps(state, indent=2) + "\n", encoding="utf-8"
    )
    print(f"applied: retiered {len(plan['to_retier'])} record(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
