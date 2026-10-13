"""O9 (F14): lenses foreground relation language and sections.

A relation-object may carry an optional `relation_type` (relation before
type: it may also have none). A lens listing that type in
`foreground_relations` adds an inspectable reason to the relation and to the
records it joins. `foreground_sections` changes presentation order only.
Neither changes pack membership, authority, candidate visibility or content.
"""
from __future__ import annotations

import shutil
import sqlite3
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


def _rel(root: Path, rid: str, parts: list[str], rtype: str | None) -> None:
    line = f"relation_type: {rtype}\n" if rtype else ""
    _w(root / "06-relations" / f"{rid}.md",
       f"---\nid: {rid}\ntype: relation-object\ntitle: {rid}\n"
       f"participants: [{', '.join(parts)}]\n{line}"
       "relation_status: candidate\ncurrent_claim_permission: may-note\n---\n\nBody.\n")


@pytest.fixture()
def wiki(tmp_path: Path) -> Path:
    _w(tmp_path / "03-objects" / "work--piece.md",
       "---\nid: xx-obj-work\ntype: object\ntitle: The piece\nlabels: [score]\n---\n\n"
       "## Sources\nArchive box 4.\n\n## Characterization\nA work.\n\n"
       "## History\nRevised twice.\n\n## Open work\nThe ending.\n")
    _w(tmp_path / "03-objects" / "sess--one.md",
       "---\nid: xx-obj-sess\ntype: object\ntitle: Session one\n---\n\nBody.\n")
    _w(tmp_path / "03-objects" / "essay--two.md",
       "---\nid: xx-obj-essay\ntype: object\ntitle: Essay\n---\n\nBody.\n")
    _w(tmp_path / "03-objects" / "loose--three.md",
       "---\nid: xx-obj-loose\ntype: object\ntitle: Loose\n---\n\nBody.\n")
    _rel(tmp_path, "xx-rel-rehearses", ["xx-obj-sess", "xx-obj-work"], "Rehearses")
    _rel(tmp_path, "xx-rel-supports", ["xx-obj-essay", "xx-obj-work"], "supports")
    _rel(tmp_path, "xx-rel-untyped", ["xx-obj-loose", "xx-obj-work"], None)
    (tmp_path / "00-system" / "schemas").mkdir(parents=True)
    shutil.copy(ROOT / "00-system" / "schemas" / "wiki-lens.schema.json",
                tmp_path / "00-system" / "schemas" / "wiki-lens.schema.json")
    shutil.copytree(ROOT / "00-system" / "configuration" / "lenses",
                    tmp_path / "00-system" / "configuration" / "lenses")
    bgi.build(tmp_path)
    return tmp_path


def _pack(root: Path, lens: str | None = None, hops: int = 2) -> dict:
    return cp.build_pack(root, "xx-obj-work", hops=hops, search_fn=lambda q, n: [],
                         lens=lens)


def test_relation_type_indexed_as_non_evidence(wiki: Path) -> None:
    con = sqlite3.connect(wiki / "_search" / "graph.db")
    types = set(con.execute("SELECT relation_id, type_raw, type_norm FROM relation_types"))
    targets = {r[0] for r in con.execute("SELECT target FROM edges")}
    con.close()
    assert ("xx-rel-rehearses", "Rehearses", "rehearses") in types
    assert ("xx-rel-supports", "supports", "supports") in types
    assert not any(t[0] == "xx-rel-untyped" for t in types)
    assert "Rehearses" not in targets and "supports" not in targets


def test_lens_foregrounds_relation_language(wiki: Path) -> None:
    drama = {e["id"]: e for e in _pack(wiki, "lens-dramaturg")["records"]}
    tag = "lens lens-dramaturg foregrounds relation `rehearses`"
    # the relation itself and every record it joins
    for rid in ("xx-rel-rehearses", "xx-obj-sess", "xx-obj-work"):
        assert tag in drama[rid]["reason"], rid
        assert drama[rid]["foregrounded"] is True
        assert drama[rid]["foregrounded_relations"] == ["rehearses"]
    for rid in ("xx-rel-supports", "xx-obj-essay", "xx-rel-untyped", "xx-obj-loose"):
        assert "foregrounds relation" not in drama[rid]["reason"], rid
        assert "foregrounded" not in drama[rid]


def test_two_lenses_differ_only_in_reasons(wiki: Path) -> None:
    plain = _pack(wiki)
    drama = _pack(wiki, "lens-dramaturg")
    scholar = _pack(wiki, "lens-scholar")
    ids = [e["id"] for e in plain["records"]]
    assert [e["id"] for e in drama["records"]] == ids
    assert [e["id"] for e in scholar["records"]] == ids
    s = {e["id"]: e["reason"] for e in scholar["records"]}
    assert "lens lens-scholar foregrounds relation `supports`" in s["xx-obj-essay"]
    assert "foregrounds relation" not in s["xx-obj-sess"]
    for a, b in zip(plain["records"], drama["records"]):
        assert a["content"] == b["content"]
        assert a.get("authority") == b.get("authority")


def test_lens_sections_set_presentation_order_only(wiki: Path) -> None:
    plain = {e["id"]: e for e in _pack(wiki)["records"]}
    drama = {e["id"]: e for e in _pack(wiki, "lens-dramaturg")["records"]}
    work = drama["xx-obj-work"]
    # lens order first (Characterization, Open work), then the rest as written
    assert work["section_order"] == ["Characterization", "Open work", "Sources", "History"]
    assert work["sections_foregrounded"] == ["Characterization", "Open work"]
    assert work["content"] == plain["xx-obj-work"]["content"]
    assert "section_order" not in plain["xx-obj-work"]
    # a record without the lens's sections keeps its own order, nothing foregrounded
    assert drama["xx-obj-sess"]["sections_foregrounded"] == []


def test_no_lens_pack_carries_no_lens_fields(wiki: Path) -> None:
    for e in _pack(wiki)["records"]:
        for key in ("foregrounded", "foregrounded_relations",
                    "section_order", "sections_foregrounded"):
            assert key not in e
        assert "lens" not in e["reason"]


def test_accepted_only_still_explicit_with_relation_lens() -> None:
    entries = [{"id": "a", "reason": "seed"},
               {"id": "b", "authority": "candidate", "reason": "candidate: x"}]
    lens = {"candidate_visibility": "include", "foreground_relations": ["rehearses"]}
    joins = {"b": ["rehearses"]}
    kept = cp.apply_lens(entries, lens, "lens-t", relation_joins=joins)
    assert [e["id"] for e in kept] == ["a", "b"]
    assert kept[1]["authority"] == "candidate"
    assert "lens lens-t foregrounds relation `rehearses`" in kept[1]["reason"]
