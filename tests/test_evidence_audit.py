"""Tests for evidence_audit.py (Phase 3 candidate layer)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

KIT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KIT_ROOT / "scripts"))

import evidence_audit as ea  # noqa: E402


@pytest.fixture()
def wiki(tmp_path: Path) -> Path:
    (tmp_path / "00-system" / "policies").mkdir(parents=True)
    (tmp_path / "_proposals").mkdir()
    (tmp_path / "_audits").mkdir()
    (tmp_path / "00-system" / "registers").mkdir(parents=True)
    (tmp_path / "00-system" / "registers" / "CORPUS_STATE.json").write_text(
        json.dumps({"source_material_count": 1}), encoding="utf-8")
    # copy the kit schema
    import shutil
    shutil.copy(KIT_ROOT / "00-system" / "policies" / "proposal_schema.json",
                tmp_path / "00-system" / "policies" / "proposal_schema.json")
    # a canonical record with a known passage
    rec = tmp_path / "02-sources" / "records" / "mw-src-1111111111--n.md"
    rec.parent.mkdir(parents=True, exist_ok=True)
    rec.write_text("---\nid: mw-src-1111111111\n---\n"
                   "The grave machine organizes absence into citation.\n",
                   encoding="utf-8")
    return tmp_path


def _prop(pid: str, kind: str, body: dict, **over) -> dict:
    p = {"id": pid, "received": "2026-09-19T00:00:00Z", "kind": kind,
         "authority_tier": "candidate", "status": "new", "body": body}
    p.update(over)
    return p


def _run(wiki: Path) -> dict:
    import io, contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = ea.audit(wiki)
    assert rc in (0, 1)
    rep = sorted((wiki / "_audits").glob("evidence-audit-*.json"))[-1]
    return json.loads(rep.read_text(encoding="utf-8-sig"))


def test_valid_relation_passes(wiki: Path) -> None:
    body = {"target_id": "mw-con-2222222222", "proposed_type": "supports",
            "why": "structural parallel",
            "source_passage": {"path": "02-sources/records/mw-src-1111111111--n.md",
                               "quote": "The grave machine organizes absence into citation."}}
    (wiki / "_proposals" / "proposals.jsonl").write_text(
        json.dumps(_prop("p1", "relation-edge", body)) + "\n", encoding="utf-8")
    rep = _run(wiki)
    assert rep["totals"]["audited"] == 1
    assert rep["totals"]["rejected-audit"] == 0


def test_missing_passage_auto_rejects(wiki: Path) -> None:
    body = {"target_id": "mw-con-2222222222", "proposed_type": "supports",
            "why": "structural parallel"}  # no source_passage at all
    (wiki / "_proposals" / "proposals.jsonl").write_text(
        json.dumps(_prop("p2", "relation-edge", body)) + "\n", encoding="utf-8")
    rep = _run(wiki)
    assert rep["totals"]["rejected-audit"] == 1
    r = rep["results"][0]
    assert any("source_passage" in e for e in r["errors"])


def test_fabricated_quote_auto_rejects(wiki: Path) -> None:
    body = {"target_id": "mw-con-2222222222", "proposed_type": "supports",
            "why": "structural parallel",
            "source_passage": {"path": "02-sources/records/mw-src-1111111111--n.md",
                               "quote": "This sentence does not exist anywhere in the file."}}
    (wiki / "_proposals" / "proposals.jsonl").write_text(
        json.dumps(_prop("p3", "relation-edge", body)) + "\n", encoding="utf-8")
    rep = _run(wiki)
    r = rep["results"][0]
    assert any("NOT found verbatim" in e for e in r["errors"])
    assert rep["totals"]["rejected-audit"] == 1


def test_noncanonical_path_auto_rejects(wiki: Path) -> None:
    body = {"object_id": "mw-src-1111111111", "note": "n", "why": "w",
            "source_passage": {"path": "_originals/something.md",
                               "quote": "quote long enough to pass the length check here"}}
    (wiki / "_proposals" / "proposals.jsonl").write_text(
        json.dumps(_prop("p4", "object-note", body)) + "\n", encoding="utf-8")
    rep = _run(wiki)
    assert any("not canonical" in e for e in rep["results"][0]["errors"])


def test_intake_registration_checks(wiki: Path) -> None:
    good = {"original_path": "00-system/registers/CORPUS_STATE.json",
            "sha256": "a" * 64, "why": "new intake"}
    (wiki / "_proposals" / "proposals.jsonl").write_text(
        json.dumps(_prop("p5", "intake-registration", good)) + "\n", encoding="utf-8")
    rep = _run(wiki)
    assert rep["totals"]["audited"] == 1
    bad = {"original_path": "00-system/registers/MISSING.json",
           "sha256": "not-a-hash", "why": "new intake"}
    (wiki / "_proposals" / "proposals.jsonl").write_text(
        json.dumps(_prop("p6", "intake-registration", bad)) + "\n", encoding="utf-8")
    rep = _run(wiki)
    errs = rep["results"][0]["errors"]
    assert any("original_path does not exist" in e for e in errs)
    assert any("sha256 not 64-hex" in e for e in errs)


def test_tier_change_enum(wiki: Path) -> None:
    body = {"target_id": "mw-src-1111111111", "from_tier": "pending-registration",
            "to_tier": "registered", "why": "identity verified",
            "source_passage": {"path": "02-sources/records/mw-src-1111111111--n.md",
                               "quote": "The grave machine organizes absence into citation."}}
    (wiki / "_proposals" / "proposals.jsonl").write_text(
        json.dumps(_prop("p7", "tier-change", body)) + "\n", encoding="utf-8")
    rep = _run(wiki)
    assert rep["totals"]["audited"] == 1


def test_free_prose_passage_extraction(wiki: Path) -> None:
    prose = ('Relation noted while reading: path=02-sources/records/mw-src-1111111111--n.md '
             'quote="The grave machine organizes absence into citation."')
    rec = _prop("p8", "relation-edge", prose)
    (wiki / "_proposals" / "proposals.jsonl").write_text(
        json.dumps(rec) + "\n", encoding="utf-8")
    rep = _run(wiki)
    # prose fallback still must satisfy passage verification
    r = rep["results"][0]
    assert not any("NOT found verbatim" in e for e in r["errors"]), r


def test_queue_never_mutated(wiki: Path) -> None:
    rec = json.dumps(_prop("p9", "relation-edge", {"target_id": "x"}))
    q = wiki / "_proposals" / "proposals.jsonl"
    q.write_text(rec + "\n", encoding="utf-8")
    before = q.read_text(encoding="utf-8")
    _run(wiki)
    assert q.read_text(encoding="utf-8") == before


def test_malformed_line_flagged_not_crashing(wiki: Path) -> None:
    q = wiki / "_proposals" / "proposals.jsonl"
    q.write_text("{broken json here\n", encoding="utf-8")
    rep = _run(wiki)
    assert rep["totals"]["rejected-audit"] == 1
    assert rep["results"][0]["errors"] == ["unparseable JSONL line"]
