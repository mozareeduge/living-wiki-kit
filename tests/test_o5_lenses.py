"""O5: lens substrate (dossier §20-22).

Lenses foreground labels/relations in pack reasons, never alter authority,
never silently filter. Candidates stay visible by default; the accepted-only
view is always explicit.
"""
from __future__ import annotations

import json
import shutil
import sqlite3
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import build_graph_index as bgi  # noqa: E402
import context_pack as cp  # noqa: E402
from gov_kernel.schemas import validate_record  # noqa: E402


def _obj(path: Path, rid: str, title: str, labels: list[str]) -> None:
    listed = "\n".join(f"  - {lb}" for lb in labels)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"---\nid: {rid}\ntype: object\ntitle: {title}\n"
                    f"status: active-record\nlabels:\n{listed}\n---\n\nBody.\n",
                    encoding="utf-8")


@pytest.fixture()
def lens_wiki(tmp_path: Path) -> Path:
    _obj(tmp_path / "03-objects" / "r1--session.md", "xx-obj-r1",
         "First session", ["rehearsal"])
    _obj(tmp_path / "03-objects" / "plain--note.md", "xx-obj-plain",
         "Plain note", [])
    (tmp_path / "00-system" / "schemas").mkdir(parents=True, exist_ok=True)
    shutil.copy(ROOT / "00-system" / "schemas" / "wiki-lens.schema.json",
                tmp_path / "00-system" / "schemas" / "wiki-lens.schema.json")
    lenses = tmp_path / "00-system" / "configuration" / "lenses"
    lenses.mkdir(parents=True, exist_ok=True)
    shutil.copy(ROOT / "00-system" / "configuration" / "lenses" / "lens-dramaturg.md",
                lenses / "lens-dramaturg.md")
    bgi.build(tmp_path)
    return tmp_path


def test_shipped_lenses_validate_and_stay_inactive() -> None:
    schema_dir = ROOT / "00-system" / "schemas"
    for lid in ("lens-dramaturg", "lens-scholar"):
        doc = ROOT / "00-system" / "configuration" / "lenses" / f"{lid}.md"
        assert doc.exists(), lid
        record = cp.resolve_lens(ROOT, lid)
        assert record["status"] == "example", lid
        assert record["candidate_visibility"] == "include"
        assert record["authority_mode"] == "annotate"
        assert validate_record(record, schema_dir,
                               explicit_schema="wiki-lens.schema.json") == []


def test_bad_lens_values_rejected(lens_wiki: Path) -> None:
    bad = lens_wiki / "00-system" / "configuration" / "lenses" / "lens-bad.md"
    bad.write_text("---\nid: lens-bad\ntype: wiki-lens\ntitle: Bad\nversion: 1.0.0\n"
                   "status: example\ncandidate_visibility: sometimes\n---\n\nBody.\n",
                   encoding="utf-8")
    with pytest.raises(ValueError, match="candidate_visibility"):
        cp.resolve_lens(lens_wiki, "lens-bad")


def test_unknown_lens_named(lens_wiki: Path) -> None:
    with pytest.raises((ValueError, SystemExit), match="unknown lens"):
        cp.build_pack(lens_wiki, "xx-obj-plain", hops=0, query="rehearsal",
                      search_fn=lambda q, n: [], lens="lens-nope")


def test_lens_foregrounds_label_match(lens_wiki: Path) -> None:
    plain = cp.build_pack(lens_wiki, "xx-obj-plain", hops=0, query="rehearsal",
                          search_fn=lambda q, n: [])
    lensed = cp.build_pack(lens_wiki, "xx-obj-plain", hops=0, query="rehearsal",
                           search_fn=lambda q, n: [], lens="lens-dramaturg")
    base = {e["id"]: e["reason"] for e in plain["records"]}
    fore = {e["id"]: e["reason"] for e in lensed["records"]}
    assert "xx-obj-r1" in fore
    assert "foregrounded by lens lens-dramaturg" in fore["xx-obj-r1"]
    assert "foregrounded" not in base["xx-obj-r1"]
    assert lensed["meta"]["lens"] == "lens-dramaturg"


def test_lens_changes_reasons_not_authority(lens_wiki: Path) -> None:
    lensed = cp.build_pack(lens_wiki, "xx-obj-plain", hops=0, query="rehearsal",
                           search_fn=lambda q, n: [], lens="lens-dramaturg")
    for e in lensed["records"]:
        assert "authority" not in e


def test_candidates_visible_by_default_excluded_only_explicitly() -> None:
    entries = [{"id": "a", "authority": "accepted", "reason": "seed"},
               {"id": "b", "authority": "candidate", "reason": "label match"}]
    keep = cp.apply_lens(entries, {"candidate_visibility": "include",
                                   "foreground_labels": []}, "lens-t")
    assert {e["id"] for e in keep} == {"a", "b"}
    drop = cp.apply_lens(entries, {"candidate_visibility": "exclude",
                                   "foreground_labels": []}, "lens-t")
    assert [e["id"] for e in drop] == ["a"]


def test_accepted_only_flag_recorded_in_meta(lens_wiki: Path) -> None:
    pack = cp.build_pack(lens_wiki, "xx-obj-plain", hops=0,
                         search_fn=lambda q, n: [], accepted_only=True)
    assert pack["meta"]["accepted_only"] is True
    assert pack["meta"]["lens"] is None
