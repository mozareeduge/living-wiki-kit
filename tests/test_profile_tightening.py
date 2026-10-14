"""D-b: a profile may make kernel rules stricter, never looser.

`tighten: [...]` names rules from a closed set. Active profiles' rules are
unioned (the strictest wins) and enforced by `wiki_profiles.py check`:
  object-labels      every object record carries at least one label
  relation-type      every relation-object names its relation_type
  record-visibility  every canonical record declares `visibility`
An unknown rule is a schema error. No value can switch a kernel rule off.
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import wiki_profiles as wp  # noqa: E402


def _w(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _profile(root: Path, pid: str, tighten: list[str] | None) -> None:
    line = f"tighten: [{', '.join(tighten)}]\n" if tighten is not None else ""
    _w(root / "00-system/configuration/profiles" / f"{pid}.md",
       f"---\nid: {pid}\ntype: wiki-profile\nprofile_class: compliance\ntitle: {pid}\n"
       f"version: 1.0.0\nstatus: active\n{line}---\n\nBody.\n")


def _activate(root: Path, ids: list[str]) -> None:
    _w(root / "00-system/registers/INSTANCE.json", json.dumps({"active_profiles": ids}))


@pytest.fixture()
def wiki(tmp_path: Path) -> Path:
    _w(tmp_path / "00-system/schemas/wiki-profile.schema.json",
       (ROOT / "00-system/schemas/wiki-profile.schema.json").read_text(encoding="utf-8"))
    _w(tmp_path / "03-objects/bare.md",
       "---\nid: xx-obj-bare\ntype: object\ntitle: Bare\nvisibility: private\n---\n\nBody.\n")
    _w(tmp_path / "03-objects/labelled.md",
       "---\nid: xx-obj-lab\ntype: object\ntitle: L\nlabels: [score]\nvisibility: private\n---\n")
    _w(tmp_path / "06-relations/r.md",
       "---\nid: xx-rel-r\ntype: relation-object\ntitle: r\nparticipants: [xx-obj-lab]\n"
       "relation_status: candidate\ncurrent_claim_permission: may-note\n---\n")
    return tmp_path


def test_no_tightening_no_findings(wiki: Path) -> None:
    _profile(wiki, "comp", None)
    _activate(wiki, ["comp"])
    assert wp.compose(wiki)[1] == []
    assert wp.tightening_findings(wiki) == []


def test_object_labels_rule_names_record_and_profile(wiki: Path) -> None:
    _profile(wiki, "comp", ["object-labels"])
    _activate(wiki, ["comp"])
    assert wp.tightening_findings(wiki) == [
        "03-objects/bare.md: object has no labels (tighten object-labels, profile comp)"]
    assert wp.cmd_check(wiki) == 2


def test_relation_type_and_visibility_rules(wiki: Path) -> None:
    _profile(wiki, "comp", ["relation-type", "record-visibility"])
    _activate(wiki, ["comp"])
    assert wp.tightening_findings(wiki) == [
        "06-relations/r.md: relation has no relation_type (tighten relation-type, profile comp)",
        "06-relations/r.md: record has no visibility (tighten record-visibility, profile comp)"]


def test_strictest_wins_across_profiles(wiki: Path) -> None:
    _profile(wiki, "loose", [])
    _profile(wiki, "strict", ["object-labels"])
    _activate(wiki, ["loose", "strict"])
    composed, findings = wp.compose(wiki)
    assert findings == []
    assert composed["tighten"] == {"object-labels": ["strict"]}
    assert len(wp.tightening_findings(wiki)) == 1


def test_unknown_rule_is_rejected(wiki: Path) -> None:
    _profile(wiki, "comp", ["allow-anything"])
    _activate(wiki, ["comp"])
    findings = wp.compose(wiki)[1]
    assert findings and "allow-anything" in " ".join(findings)


def test_inactive_profile_tightens_nothing(wiki: Path) -> None:
    _profile(wiki, "comp", ["object-labels"])
    _activate(wiki, [])
    assert wp.tightening_findings(wiki) == []
    assert wp.cmd_check(wiki) == 0
