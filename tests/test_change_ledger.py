"""OM-888 product contract: no approval gate, but every change says who made it,
every answer can be traced to a verbatim original, and the owner can correct any
hop without anything being deleted.

Each test is one owner-visible promise, run in a throwaway wiki.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import shutil
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

from gov_kernel.changes import (LedgerError, annotate_hits, append_change,  # noqa: E402
                                check_ledger, feedback, read_ledger, trace)
import wiki_mcp_server as mcp  # noqa: E402

STAMP = {"model": "claude-opus-5-5", "provider": "anthropic", "effort": "high",
         "host": "nanobot", "harness": "wiki-intake"}


@pytest.fixture()
def wiki(tmp_path: pathlib.Path) -> pathlib.Path:
    cfg = tmp_path / "00-system/configuration"
    cfg.mkdir(parents=True)
    shutil.copy(REPO / "00-system/configuration/retrieval-profiles.v2.json", cfg)
    original = tmp_path / "_originals/letter.txt"
    original.parent.mkdir(parents=True)
    original.write_bytes("The letter was sent in 2019.\n".encode("utf-8"))
    digest = hashlib.sha256(original.read_bytes()).hexdigest()
    rec = tmp_path / "02-sources/records/mw-src-aaaa--letter.md"
    rec.parent.mkdir(parents=True)
    rec.write_text(f"---\nid: mw-src-aaaa\ntype: source-record\ntitle: Letter\nstatus: registered\n"
                   f"sha256: {digest}\noriginal_path: _originals/letter.txt\n---\nLetter.\n", encoding="utf-8")
    claim = tmp_path / "05-claims/letter-date.md"
    claim.parent.mkdir(parents=True)
    claim.write_text("---\nid: mw-claim-letter-date\ntype: claim-object\ntitle: Letter date\nstatus: active\n"
                     "supporting_sources:\n- mw-src-aaaa\n---\nThe letter dates from 2019.\n", encoding="utf-8")
    note = tmp_path / "04-notes/letter-note.md"
    note.parent.mkdir(parents=True)
    note.write_text("---\nid: mw-note-letter\ntype: note\ntitle: Letter note\nstatus: active\n---\n"
                    "See [[mw-claim-letter-date]].\n", encoding="utf-8")
    return tmp_path


def test_answer_traces_to_the_verbatim_original_with_its_hash(wiki):
    t = trace(wiki, "mw-claim-letter-date")
    assert t["ok"] and t["record"]["path"] == "05-claims/letter-date.md"
    [src] = t["sources"]
    assert src["id"] == "mw-src-aaaa"
    assert src["verbatim"][0] == {"path": "_originals/letter.txt", "sha256": src["sha256"], "state": "verified"}


def test_trace_reaches_sources_through_a_cited_page(wiki):
    [src] = trace(wiki, "mw-note-letter")["sources"]
    assert (src["id"], src["via"]) == ("mw-src-aaaa", "mw-claim-letter-date")


def test_a_changed_original_shows_up_in_the_trace(wiki):
    (wiki / "_originals/letter.txt").write_text("edited\n", encoding="utf-8")
    assert trace(wiki, "mw-claim-letter-date")["sources"][0]["verbatim"][0]["state"] == "hash-differs"


def test_every_change_names_who_made_it(wiki):
    row = append_change(wiki, action="intake", level="L2", targets=["mw-src-aaaa"], stamp=STAMP)
    assert row["stamp"] == STAMP
    assert trace(wiki, "mw-claim-letter-date")["sources"][0]["changes"][0]["change_id"] == row["change_id"]
    for gap in ("model", "provider", "effort", "host", "harness"):
        with pytest.raises(LedgerError):
            append_change(wiki, action="edit", targets=["x"], stamp={**STAMP, gap: " "})


def test_owner_says_outdated_then_the_page_is_superseded_not_deleted(wiki):
    before = (wiki / "05-claims/letter-date.md").read_bytes()
    row = feedback(wiki, target="mw-claim-letter-date", verdict="outdated", note="it was 2018",
                   replaced_by="mw-claim-letter-date-r2", stamp=STAMP)
    assert row["action"] == "supersede"
    t = trace(wiki, "mw-claim-letter-date")
    assert t["correction_state"] == "superseded"
    assert t["corrections"][0]["replaced_by"] == "mw-claim-letter-date-r2"
    assert (wiki / "05-claims/letter-date.md").read_bytes() == before
    hit = annotate_hits(wiki, [{"record_id": "mw-claim-letter-date", "path": "05-claims/letter-date.md"}])[0]
    assert hit["correction_state"] == "superseded"


def test_owner_says_wrong_then_restore_undoes_it_and_history_stays(wiki):
    bad = feedback(wiki, target="mw-src-aaaa", verdict="wrong", note="wrong letter", stamp=STAMP)
    assert trace(wiki, "mw-claim-letter-date")["sources"][0]["corrections"][0]["action"] == "retract"
    append_change(wiki, action="restore", targets=[bad["change_id"]], stamp=STAMP, reason="owner: it was right")
    assert trace(wiki, "mw-claim-letter-date")["sources"][0]["corrections"] == []
    assert [r["action"] for r in read_ledger(wiki)] == ["retract", "restore"]
    with pytest.raises(LedgerError):
        append_change(wiki, action="restore", targets=["chg-not-a-correction"], stamp=STAMP, reason="x")


def test_an_edited_ledger_row_is_caught(wiki):
    append_change(wiki, action="edit", targets=["mw-claim-letter-date"], stamp=STAMP)
    assert check_ledger(wiki) == []
    p = wiki / "00-system/registers/CHANGE_LEDGER.jsonl"
    row = json.loads(p.read_text(encoding="utf-8"))
    row["stamp"]["model"] = "someone-else"
    p.write_text(json.dumps(row) + "\n", encoding="utf-8")
    assert any("never edited" in x for x in check_ledger(wiki))


def test_repository_ledger_is_whole():
    assert check_ledger(REPO) == []


def _call(profile: str, name: str, args: dict) -> dict:
    resp = mcp.REGISTRY.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                                "params": {"name": name, "arguments": args}}, profile=profile)
    if "error" in resp:
        return {"rpc_error": resp["error"]["message"]}
    return json.loads(resp["result"]["content"][0]["text"])


def test_mcp_trace_is_readable_and_corrections_need_the_write_profile(wiki, monkeypatch):
    monkeypatch.setattr(mcp, "ROOT", wiki)
    assert _call("read", "wiki_trace", {"id_or_path": "mw-claim-letter-date"})["sources"][0]["id"] == "mw-src-aaaa"
    for write in ("wiki_feedback", "wiki_record_change"):
        assert mcp.REGISTRY.get_tool(write).is_write is True
        assert write not in {t["name"] for t in mcp.REGISTRY.advertised_tools("read")}
    assert "rpc_error" in _call("read", "wiki_feedback", {"target": "mw-src-aaaa", "verdict": "wrong", "stamp": STAMP})
    out = _call("capture", "wiki_feedback", {"target": "mw-claim-letter-date", "verdict": "not-needed", "stamp": STAMP})
    assert out["ok"] and out["change"]["action"] == "retract"
    assert _call("read", "wiki_trace", {"id_or_path": "mw-claim-letter-date"})["correction_state"] == "retracted"
    assert not _call("capture", "wiki_record_change", {"action": "merge", "targets": ["x"], "stamp": {}})["ok"]