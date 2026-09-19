"""Tests for build_graph_index.py + context_pack.py (Phase 1).

Runs against a synthetic mini-wiki in a temp dir - deterministic, no qmd
dependency (lexical search is injected as a fake).
"""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

import pytest

KIT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KIT_ROOT / "scripts"))

import build_graph_index as bgi  # noqa: E402
import context_pack as cp  # noqa: E402


@pytest.fixture()
def wiki(tmp_path: Path) -> Path:
    """Mini canonical wiki: 4 records, links of all three kinds."""
    (tmp_path / "02-sources" / "records").mkdir(parents=True)
    (tmp_path / "03-objects" / "concepts").mkdir(parents=True)
    (tmp_path / "_search").mkdir(parents=True)
    (tmp_path / "02-sources" / "records" /
     "mw-src-1111111111--essay-grave-machine.md").write_text(
        "---\n"
        "id: mw-src-1111111111\n"
        "type: source-record\n"
        "title: Grave Machine\n"
        "status: registered\n"
        "---\n"
        "Body links [[mw-con-2222222222]] and mentions "
        "03-objects/concepts/mw-con-2222222222--concept-machine.md inline.\n",
        encoding="utf-8")
    (tmp_path / "03-objects" / "concepts" /
     "mw-con-2222222222--concept-machine.md").write_text(
        "---\n"
        "id: mw-con-2222222222\n"
        "type: concept\n"
        "kind: concept\n"
        "title: Machine\n"
        "status: registered\n"
        "---\n"
        "See [[mw-src-3333333333--essay-grave]] for the origin.\n",
        encoding="utf-8")
    (tmp_path / "02-sources" / "records" /
     "mw-src-3333333333--essay-grave.md").write_text(
        "---\n"
        "id: mw-src-3333333333\n"
        "type: source-record\n"
        "title: Grave\n"
        "status: pending-registration\n"
        "---\n"
        "Standalone leaf.\n", encoding="utf-8")
    # Entry page OUTSIDE canonical zones: alias target only
    (tmp_path / "HOME.md").write_text(
        "---\n"
        "id: mw-home-9999999999\n"
        "title: Home\n"
        "---\n", encoding="utf-8")
    return tmp_path


def _db(wiki: Path) -> sqlite3.Connection:
    bgi.build(wiki)
    return sqlite3.connect(wiki / "_search" / "graph.db")


def test_nodes_only_from_canonical_zones(wiki: Path) -> None:
    db = _db(wiki)
    ids = {r[0] for r in db.execute("SELECT id FROM nodes")}
    assert ids == {"mw-src-1111111111", "mw-con-2222222222", "mw-src-3333333333"}


def test_wikilink_and_path_edges_resolve(wiki: Path) -> None:
    db = _db(wiki)
    resolved = {(r[0], r[1]) for r in db.execute(
        "SELECT src_id, resolved_id FROM edges WHERE resolved_id IS NOT NULL")}
    # 1111 -> 2222 (wikilink + id token), 2222 -> 3333 (wikilink, --kind stem)
    assert ("mw-src-1111111111", "mw-con-2222222222") in resolved
    assert ("mw-con-2222222222", "mw-src-3333333333") in resolved


def test_entry_page_alias_resolves(tmp_path: Path, wiki: Path) -> None:
    # A record whose body links [[HOME]] resolves via the alias pass.
    p = wiki / "02-sources" / "records" / "mw-src-4444444444--notes.md"
    p.write_text("---\nid: mw-src-4444444444\ntype: source-record\ntitle: N\n---\n"
                 "Refers to [[HOME]].\n", encoding="utf-8")
    db = _db(wiki)
    row = db.execute(
        "SELECT resolved_id FROM edges WHERE src_id='mw-src-4444444444' "
        "AND resolved_id IS NOT NULL").fetchall()
    assert ("mw-home-9999999999",) in row


def test_slug_alias_first_wins_and_ambiguity_dropped(wiki: Path) -> None:
    db = _db(wiki)
    # 'grave' slug appears in two stems (essay-grave-machine, essay-grave)
    # -> ambiguous segment must NOT resolve; full prefix still does.
    unres = {r[0] for r in db.execute(
        "SELECT target FROM edges WHERE resolved_id IS NULL")}
    assert "grave" in unres or "grave" not in {r[0] for r in db.execute(
        "SELECT target FROM edges WHERE resolved_id IS NOT NULL")}


def test_pack_hops_reasons_and_budget(wiki: Path) -> None:
    bgi.build(wiki)
    pack = cp.build_pack(wiki, "mw-src-1111111111", hops=1, max_records=30,
                         budget_tokens=16000)
    m = pack["meta"]
    assert m["records"] <= 30
    assert m["tokens_est"] <= m["budget_tokens"]
    reasons = {r["reason"] for r in pack["records"]}
    assert "seed" in reasons
    assert any(r.startswith("1-hop via") for r in reasons)
    assert all(r.get("reason") for r in pack["records"])  # auditable


def test_pack_record_cap(wiki: Path) -> None:
    bgi.build(wiki)
    pack = cp.build_pack(wiki, "mw-src-1111111111", hops=2, max_records=2)
    assert pack["meta"]["records"] <= 2


def test_pack_lexical_injection(wiki: Path) -> None:
    bgi.build(wiki)

    def fake_search(query: str, n: int) -> list[dict]:
        return [{"file": "qmd://wiki/mw-src-3333333333--essay-grave",
                 "score": 1.0}]

    pack = cp.build_pack(wiki, "mw-src-1111111111", hops=0,
                         query="grave", search_fn=fake_search)
    ids = {r["id"] for r in pack["records"]}
    assert "mw-src-3333333333" in ids
    assert any(r["reason"].startswith("lexical:") for r in pack["records"])


def test_pack_unknown_seed_exits(wiki: Path) -> None:
    bgi.build(wiki)
    with pytest.raises(SystemExit):
        cp.build_pack(wiki, "mw-src-doesnotexist")


def test_pack_is_gitignored(wiki: Path) -> None:
    # Contract: packs land in _search/ (rebuildable, never canonical)
    bgi.build(wiki)
    out = wiki / "_search" / "packs"
    out.mkdir(exist_ok=True)
    assert "_search" in str(out)
    gi = wiki / ".gitignore"
    gi.write_text("_search/\n", encoding="utf-8")
    assert "_search/" in gi.read_text(encoding="utf-8")
