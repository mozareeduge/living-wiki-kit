"""O3: labels in graph/search/context (dossier §39).

- build_graph_index stores raw + normalized labels, object→label rows in a
  dedicated table, never as evidence edges;
- context_pack selects on label match with an explicit label-match reason
  that never claims the object IS the label.
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import build_graph_index as bgi  # noqa: E402
import context_pack as cp  # noqa: E402


def _obj(path: Path, rid: str, title: str, labels: list[str]) -> None:
    listed = "\n".join(f"  - {lb}" for lb in labels)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"---\nid: {rid}\ntype: object\ntitle: {title}\n"
                    f"status: active-record\nlabels:\n{listed}\n---\n\nBody text here.\n",
                    encoding="utf-8")


def _wiki(tmp_path: Path) -> Path:
    _obj(tmp_path / "03-objects" / "r1--session.md", "xx-obj-r1",
         "First session", ["rehearsal", "تئاتر "])
    _obj(tmp_path / "03-objects" / "plain--note.md", "xx-obj-plain",
         "Plain note", [])
    _obj(tmp_path / "03-objects" / "odd--thing.md", "xx-obj-odd",
         "Odd thing", ["quux-neologism-xyz"])
    return tmp_path


def _labels_db(tmp_path: Path):
    root = _wiki(tmp_path)
    nodes, edges = bgi.build(root)
    assert nodes == 3
    con = sqlite3.connect(root / "_search" / "graph.db")
    return root, con


def test_labels_indexed_raw_and_normalized(tmp_path: Path) -> None:
    root, con = _labels_db(tmp_path)
    rows = con.execute("SELECT label_raw, label_norm FROM labels WHERE node_id='xx-obj-r1'"
                       " ORDER BY label_norm").fetchall()
    assert ("rehearsal", "rehearsal") in rows
    assert ("تئاتر ", "تئاتر") in rows
    assert root is not None


def test_labels_are_not_evidence_edges(tmp_path: Path) -> None:
    _, con = _labels_db(tmp_path)
    fields = {r[0] for r in con.execute("SELECT DISTINCT field FROM edges").fetchall()}
    assert not any(f.startswith("label") for f in fields)
    kinds = {r[0] for r in con.execute("SELECT DISTINCT target_kind FROM edges").fetchall()}
    assert "label" not in kinds


def test_unknown_label_indexes_normally(tmp_path: Path) -> None:
    _, con = _labels_db(tmp_path)
    rows = con.execute("SELECT label_norm FROM labels WHERE node_id='xx-obj-odd'").fetchall()
    assert rows == [("quux-neologism-xyz",)]


def test_pack_selects_on_label_match_with_reason(tmp_path: Path) -> None:
    root, con = _labels_db(tmp_path)
    con.close()
    pack = cp.build_pack(root, "xx-obj-plain", hops=0, query="rehearsal",
                         search_fn=lambda q, n: [])
    ids = {e["id"]: e["reason"] for e in pack["records"]}
    assert "xx-obj-r1" in ids
    assert "rehearsal" in ids["xx-obj-r1"]
    assert "known to be" not in ids["xx-obj-r1"]


def test_pack_unicode_label_query(tmp_path: Path) -> None:
    root, con = _labels_db(tmp_path)
    con.close()
    pack = cp.build_pack(root, "xx-obj-plain", hops=0, query="تئاتر",
                         search_fn=lambda q, n: [])
    assert "xx-obj-r1" in {e["id"] for e in pack["records"]}


def test_unlabeled_object_has_no_label_rows(tmp_path: Path) -> None:
    _, con = _labels_db(tmp_path)
    assert con.execute("SELECT * FROM labels WHERE node_id='xx-obj-plain'").fetchall() == []
