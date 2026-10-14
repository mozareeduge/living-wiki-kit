"""O10 (F15): active profiles steer attention, never truth.

The union of active profiles' `seed_labels` adds an inspectable reason to
pack records already selected; `suggested_lenses` are offered in pack meta
and never applied implicitly. A profile never adds, removes or reorders a
record and never touches authority. No active profile: output as before.
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import build_graph_index as bgi  # noqa: E402
import context_pack as cp  # noqa: E402


def _w(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _activate(root: Path, ids: list[str] | None) -> None:
    inst = root / "00-system" / "registers" / "INSTANCE.json"
    if ids is None:
        inst.unlink(missing_ok=True)
        return
    _w(inst, json.dumps({"active_profiles": ids}))


@pytest.fixture()
def wiki(tmp_path: Path) -> Path:
    _w(tmp_path / "03-objects" / "work--piece.md",
       "---\nid: xx-obj-work\ntype: object\ntitle: The piece\nlabels: [Score, methodological]\n"
       "---\n\nBody.\n")
    _w(tmp_path / "03-objects" / "sess--one.md",
       "---\nid: xx-obj-sess\ntype: object\ntitle: Session one\nlabels: [rehearsal]\n---\n\nBody.\n")
    _w(tmp_path / "03-objects" / "note--plain.md",
       "---\nid: xx-obj-plain\ntype: object\ntitle: Plain\nlabels: [unrelated]\n---\n\nBody.\n")
    _w(tmp_path / "06-relations" / "r.md",
       "---\nid: xx-rel-r\ntype: relation-object\ntitle: r\n"
       "participants: [xx-obj-work, xx-obj-sess, xx-obj-plain]\n"
       "relation_status: candidate\ncurrent_claim_permission: may-note\n---\n\nBody.\n")
    for s in ("wiki-profile.schema.json", "wiki-lens.schema.json"):
        _w(tmp_path / "00-system" / "schemas" / s,
           (ROOT / "00-system" / "schemas" / s).read_text(encoding="utf-8"))
    shutil.copytree(ROOT / "00-system" / "configuration" / "profiles",
                    tmp_path / "00-system" / "configuration" / "profiles")
    shutil.copytree(ROOT / "00-system" / "configuration" / "lenses",
                    tmp_path / "00-system" / "configuration" / "lenses")
    bgi.build(tmp_path)
    return tmp_path


def _pack(root: Path, **kw) -> dict:
    p = cp.build_pack(root, "xx-obj-work", hops=2, search_fn=lambda q, n: [], **kw)
    p["meta"].pop("generated_at_epoch")
    return p


def test_seed_label_adds_profile_reason(wiki: Path) -> None:
    _activate(wiki, ["practice-creative"])
    recs = {e["id"]: e for e in _pack(wiki)["records"]}
    assert "(profile practice-creative seed label `rehearsal`)" in recs["xx-obj-sess"]["reason"]
    # the written label is quoted as written; matching is normalized
    assert "(profile practice-creative seed label `Score`)" in recs["xx-obj-work"]["reason"]
    assert recs["xx-obj-sess"]["profile_attention"] == [
        {"profile": "practice-creative", "label": "rehearsal"}]
    assert "profile" not in recs["xx-obj-plain"]["reason"]
    assert "profile_attention" not in recs["xx-obj-plain"]


def test_two_profiles_each_give_their_own_reason(wiki: Path) -> None:
    _activate(wiki, ["practice-research", "practice-creative"])
    work = {e["id"]: e for e in _pack(wiki)["records"]}["xx-obj-work"]
    assert "(profile practice-research seed label `methodological`)" in work["reason"]
    assert "(profile practice-creative seed label `Score`)" in work["reason"]


def test_profile_never_adds_removes_reorders_or_changes_authority(wiki: Path) -> None:
    _activate(wiki, None)
    plain = _pack(wiki)
    _activate(wiki, ["practice-creative", "practice-research"])
    steered = _pack(wiki)
    assert [e["id"] for e in steered["records"]] == [e["id"] for e in plain["records"]]
    for a, b in zip(plain["records"], steered["records"]):
        assert a.get("authority") == b.get("authority")
        assert a["content"] == b["content"]
        assert b["reason"].startswith(a["reason"])


def test_empty_actives_identical_to_no_profile_file(wiki: Path) -> None:
    _activate(wiki, None)
    none = _pack(wiki)
    _activate(wiki, [])
    empty = _pack(wiki)
    assert json.dumps(none, sort_keys=True) == json.dumps(empty, sort_keys=True)
    assert "active_profiles" not in none["meta"]
    assert "profile_offers" not in none["meta"]


def test_suggested_lenses_offered_never_applied(wiki: Path) -> None:
    _activate(wiki, ["practice-creative"])
    pack = _pack(wiki)
    assert pack["meta"]["active_profiles"] == ["practice-creative"]
    offers = pack["meta"]["profile_offers"]["suggested_lenses"]
    assert offers == [{"id": "lens-dramaturg", "profiles": ["practice-creative"],
                       "available": True}]
    assert pack["meta"]["lens"] is None
    assert not any("lens" in e["reason"] for e in pack["records"])


def test_offer_marks_a_missing_lens_unavailable(wiki: Path) -> None:
    (wiki / "00-system" / "configuration" / "lenses" / "lens-dramaturg.md").unlink()
    _activate(wiki, ["practice-creative"])
    offers = _pack(wiki)["meta"]["profile_offers"]["suggested_lenses"]
    assert offers == [{"id": "lens-dramaturg", "profiles": ["practice-creative"],
                       "available": False}]


def test_candidate_labels_get_profile_reason() -> None:
    entries = [{"id": "prop-1", "reason": "candidate: proposal prop-1 matched query context",
                "candidate": True, "authority": "candidate",
                "candidate_labels": ["Rehearsal"]}]
    seeds = {"rehearsal": [("practice-creative", "rehearsal")]}
    out = cp.apply_profiles(entries, seeds, {})
    assert out[0]["authority"] == "candidate"
    assert "(profile practice-creative seed label `Rehearsal`)" in out[0]["reason"]
