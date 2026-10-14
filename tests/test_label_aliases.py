"""D-c: optional label aliases help search meet the instance's vocabulary.

`00-system/configuration/LABEL_ALIASES.json` groups labels that mean the
same thing to this instance. Retrieval may reach a record through an alias
and says so in the reason. Aliases never rewrite a written label, never
merge records, never become graph rows, and a label belongs to one group.
"""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import build_graph_index as bgi  # noqa: E402
import context_pack as cp  # noqa: E402
import report_labels as rl  # noqa: E402


def _w(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _aliases(root: Path, groups: dict | None) -> None:
    f = root / "00-system" / "configuration" / "LABEL_ALIASES.json"
    if groups is None:
        f.unlink(missing_ok=True)
    else:
        _w(f, json.dumps({"aliases": groups}, ensure_ascii=False))


@pytest.fixture()
def wiki(tmp_path: Path) -> Path:
    _w(tmp_path / "03-objects" / "a.md",
       "---\nid: xx-obj-a\ntype: object\ntitle: A\nlabels: [Poem]\n---\n\nBody.\n")
    _w(tmp_path / "03-objects" / "b.md",
       "---\nid: xx-obj-b\ntype: object\ntitle: B\nlabels: [poetry]\n---\n\nBody.\n")
    _w(tmp_path / "03-objects" / "seed.md",
       "---\nid: xx-obj-seed\ntype: object\ntitle: Seed\n---\n\nBody.\n")
    bgi.build(tmp_path)
    return tmp_path


def _pack(root: Path, query: str) -> dict:
    p = cp.build_pack(root, "xx-obj-seed", hops=0, query=query, search_fn=lambda q, n: [])
    p["meta"].pop("generated_at_epoch")
    return p


def test_loader_groups_and_normalizes(tmp_path: Path) -> None:
    _aliases(tmp_path, {"poetry": ["Poem", "poems", "شعر"]})
    amap = bgi.load_label_aliases(tmp_path)
    assert amap["poem"] == ("poetry", {"poetry", "poem", "poems", "شعر"})
    assert amap["poetry"][1] == amap["شعر"][1]
    _aliases(tmp_path, None)
    assert bgi.load_label_aliases(tmp_path) == {}


@pytest.mark.parametrize("groups,needle", [
    ({"poetry": ["poem"], "verse": ["Poem"]}, "poem"),
    ({"poetry": "poem"}, "poetry"),
])
def test_bad_alias_file_named(tmp_path: Path, groups: dict, needle: str) -> None:
    _aliases(tmp_path, groups)
    with pytest.raises(ValueError, match=needle):
        bgi.load_label_aliases(tmp_path)


def test_alias_reaches_record_and_says_so(wiki: Path) -> None:
    _aliases(wiki, None)
    assert "xx-obj-a" not in {e["id"] for e in _pack(wiki, "poetry")["records"]}
    _aliases(wiki, {"poetry": ["poem"]})
    recs = {e["id"]: e for e in _pack(wiki, "poetry")["records"]}
    assert recs["xx-obj-b"]["reason"] == "label: `poetry` matched query context"
    assert recs["xx-obj-a"]["reason"] == (
        "label: `Poem` matched query context via alias `poetry` (LABEL_ALIASES.json)")


def test_aliases_never_merge_or_rewrite(wiki: Path) -> None:
    _aliases(wiki, {"poetry": ["poem"]})
    bgi.build(wiki)
    con = sqlite3.connect(wiki / "_search" / "graph.db")
    labels = sorted(con.execute("SELECT node_id, label_raw FROM labels").fetchall())
    con.close()
    assert labels == [("xx-obj-a", "Poem"), ("xx-obj-b", "poetry")]
    ids = [e["id"] for e in _pack(wiki, "poem")["records"]]
    assert ids.count("xx-obj-a") == 1 and ids.count("xx-obj-b") == 1


def test_empty_aliases_change_nothing(wiki: Path) -> None:
    _aliases(wiki, None)
    none = _pack(wiki, "poem")
    _aliases(wiki, {})
    assert _pack(wiki, "poem") == none


def test_label_report_lists_alias_groups(wiki: Path) -> None:
    _aliases(wiki, {"poetry": ["poem", "verse"]})
    rep = rl.build_report(wiki)
    assert rep["alias_groups"] == [{"preferred": "poetry",
                                    "members": ["poem", "poetry", "verse"],
                                    "objects": 2}]
    assert "aliases" in rl.render_text(rep)


def test_kit_ships_an_empty_alias_file() -> None:
    data = json.loads((ROOT / "00-system/configuration/LABEL_ALIASES.json").read_text())
    assert data["aliases"] == {}
