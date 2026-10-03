#!/usr/bin/env python3
"""Refresh the register numbers that an intake changes, after `wiki_state.py rebuild`.

Mechanical only; the intake itself still writes records, derivatives and register prose.
  1. CORPUS_STATE.json: held_artifact_count (files under _originals/) and holdings_by_tier
     (registered = manifest rows; other tiers from source records; unrecorded files ->
     HOLDINGS_POLICY default tier).
  2. Entry pages (HOME.md, README.md, SYSTEM_DESIGN.md, CLAUDE.md): the labelled markers
     `Current corpus snapshot: `<id>``, `Registered source artifacts: <n>`, `Artifacts held: <n>`.
  3. With --accept-corpus-change: the content-release corpus pin in
     00-system/configuration/content-release.json (a deliberate intake moves it; content-only
     work must not).

Dry run by default. Order for an intake:
    python scripts/wiki_state.py --repo . rebuild
    python scripts/sync_intake_registers.py --accept-corpus-change --apply
    python scripts/wiki_validate.py --format json && python scripts/wiki_state.py --repo . check
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from gov_kernel.frontmatter import load_markdown_frontmatter  # noqa: E402

ENTRY_PAGES = ("HOME.md", "README.md", "SYSTEM_DESIGN.md", "CLAUDE.md")
STATE_REL = "00-system/registers/CORPUS_STATE.json"
POLICY_REL = "00-system/policies/HOLDINGS_POLICY.json"
RELEASE_REL = "00-system/configuration/content-release.json"


def holdings(root: pathlib.Path, state: dict) -> tuple[int, dict[str, int]]:
    policy = json.loads((root / POLICY_REL).read_text(encoding="utf-8"))
    tiers = list((policy.get("tiers") or {}).keys())
    default = policy.get("default_tier_for_unregistered")
    files = {p.relative_to(root).as_posix() for p in (root / "_originals").rglob("*") if p.is_file()}
    counts = {t: 0 for t in tiers}
    recorded: set[str] = set()
    for rp in sorted((root / "02-sources/records").glob("*.md")):
        fm, _ = load_markdown_frontmatter(rp)
        op = fm.get("original_path")
        if fm.get("type") != "source-record" or not isinstance(op, str) or op not in files or op in recorded:
            continue
        status, held = fm.get("status"), fm.get("holdings_tier")
        tier = status if status in counts else held if held in counts else default
        if tier == "registered":
            recorded.add(op)
            continue
        counts[tier] += 1
        recorded.add(op)
    counts[default] += len(files - recorded)
    counts["registered"] = int(state.get("source_material_count") or 0)
    return len(files), counts


def replace_marker(text: str, label: str, value: str) -> tuple[str, int]:
    pattern = re.compile(re.escape(label) + (r"`[^`\n]*`" if value.startswith("`") else r"\d+"))
    return pattern.subn(lambda _m: label + value, text)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--repo", default=".")
    ap.add_argument("--apply", action="store_true", help="write changes (default: dry run)")
    ap.add_argument("--accept-corpus-change", action="store_true", help="move the content-release corpus pin to the current corpus")
    a = ap.parse_args()
    root = pathlib.Path(a.repo).resolve()
    report: dict = {"mode": "apply" if a.apply else "dry-run", "changes": [], "problems": []}

    state_path = root / STATE_REL
    state = json.loads(state_path.read_text(encoding="utf-8"))
    held, by_tier = holdings(root, state)
    if sum(by_tier.values()) != held:
        report["problems"].append(f"holdings_by_tier sums to {sum(by_tier.values())} but _originals/ holds {held} files")
    if state.get("held_artifact_count") != held or state.get("holdings_by_tier") != by_tier:
        report["changes"].append({STATE_REL: {"held_artifact_count": [state.get("held_artifact_count"), held], "holdings_by_tier": [state.get("holdings_by_tier"), by_tier]}})
        state["held_artifact_count"], state["holdings_by_tier"] = held, by_tier
        if a.apply and not report["problems"]:
            state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    markers = [
        ("Current corpus snapshot: ", f"`{state.get('id')}`"),
        ("Registered source artifacts: ", str(state.get("source_material_count"))),
        ("Artifacts held: ", str(held)),
    ]
    for page in ENTRY_PAGES:
        p = root / page
        text = p.read_text(encoding="utf-8")
        new = text
        for label, value in markers:
            new, n = replace_marker(new, label, value)
            if n == 0:
                report["problems"].append(f"{page}: no '{label.strip()}' marker to refresh; add the live-registers line once")
        if new != text:
            report["changes"].append(page)
            if a.apply:
                p.write_bytes(new.encode("utf-8"))

    rel_path = root / RELEASE_REL
    if rel_path.exists():
        rel = json.loads(rel_path.read_text(encoding="utf-8"))
        pin = {"id": state.get("id"), "source_material_count": state.get("source_material_count")}
        if rel.get("corpus_pin") != pin:
            if a.accept_corpus_change:
                report["changes"].append({RELEASE_REL: {"corpus_pin": [rel.get("corpus_pin"), pin]}})
                rel["corpus_pin"] = pin
                if a.apply:
                    rel_path.write_text(json.dumps(rel, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            else:
                report["problems"].append("corpus differs from the content-release pin; rerun with --accept-corpus-change only for a deliberate intake")

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if report["problems"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
