"""F19: the graph index resolves record IDs in the instance's own scheme.

Records are identified as `<prefix>-<layer>-<slug>` (`mw-obj-…`, `smk-rel-…`,
`xx-src-…`). A relation that names its participants by id must join them in
the graph whatever the prefix is; before F19 only `mw-`/`p-` tokens with a
6-character head were recognised, so `participants: [mw-obj-a, mw-obj-b]`
produced no edge at all.
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import build_graph_index as bgi  # noqa: E402


def _w(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _edges(root: Path) -> set[tuple[str, str, str]]:
    con = sqlite3.connect(root / "_search" / "graph.db")
    rows = con.execute(
        "SELECT src_id, field, resolved_id FROM edges WHERE resolved_id IS NOT NULL").fetchall()
    con.close()
    return {tuple(r) for r in rows}


def _relation_wiki(root: Path, prefix: str) -> None:
    _w(root / "03-objects" / "a--one.md",
       f"---\nid: {prefix}-obj-one\ntype: object\ntitle: One\n---\n\nBody.\n")
    _w(root / "03-objects" / "b--two.md",
       f"---\nid: {prefix}-obj-two\ntype: object\ntitle: Two\n---\n\nBody.\n")
    _w(root / "06-relations" / "r--one-two.md",
       f"---\nid: {prefix}-rel-one-two\ntype: relation-object\ntitle: One and two\n"
       f"participants: [{prefix}-obj-one, {prefix}-obj-two]\n"
       "relation_status: candidate\ncurrent_claim_permission: may-note\n---\n\nBody.\n")


def test_relation_participants_resolve_for_kit_prefix(tmp_path: Path) -> None:
    _relation_wiki(tmp_path, "mw")
    bgi.build(tmp_path)
    edges = _edges(tmp_path)
    assert ("mw-rel-one-two", "fm:participants", "mw-obj-one") in edges
    assert ("mw-rel-one-two", "fm:participants", "mw-obj-two") in edges


def test_relation_participants_resolve_for_instance_prefix(tmp_path: Path) -> None:
    _relation_wiki(tmp_path, "smk")
    bgi.build(tmp_path)
    edges = _edges(tmp_path)
    assert ("smk-rel-one-two", "fm:participants", "smk-obj-one") in edges
    assert ("smk-rel-one-two", "fm:participants", "smk-obj-two") in edges


def test_ordinary_words_never_become_id_edges(tmp_path: Path) -> None:
    """Hyphenated vocabulary (`may-note`, `work-in-progress`) is not an id."""
    _relation_wiki(tmp_path, "mw")
    bgi.build(tmp_path)
    con = sqlite3.connect(tmp_path / "_search" / "graph.db")
    targets = {r[0] for r in con.execute(
        "SELECT target FROM edges WHERE target_kind='id'").fetchall()}
    con.close()
    assert "may-note" not in targets
    assert targets <= {"mw-obj-one", "mw-obj-two"}
