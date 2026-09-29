"""O6: candidate object projection (dossier §23-25, §40).

Eligible object-create proposals project into disposable index space
(_search/candidate_projections.json): visible + marked candidate in
context/search, never a canonical 03-objects/ file. Adjudication decides
projection fate; rejected stays in audit scope; accepted resolves to
canonical with no duplicate.
"""
from __future__ import annotations

import io
import contextlib
import json
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from gov_kernel import proposals as kp  # noqa: E402
import build_graph_index as bgi  # noqa: E402
import context_pack as cp  # noqa: E402
import candidate_projection as cand  # noqa: E402
import evidence_audit as ea  # noqa: E402
import wiki_mcp_server as srv  # noqa: E402

PASSAGE = "The grave machine organizes absence into citation."
CANON = "02-sources/records/mw-src-1111111111--n.md"


@pytest.fixture()
def proj_wiki(tmp_path: Path) -> Path:
    shutil.copytree(ROOT / "00-system" / "schemas", tmp_path / "00-system" / "schemas")
    (tmp_path / "00-system" / "policies").mkdir(parents=True, exist_ok=True)
    shutil.copy(ROOT / "00-system" / "policies" / "proposal_schema.json",
                tmp_path / "00-system" / "policies" / "proposal_schema.json")
    rec = tmp_path / CANON
    rec.parent.mkdir(parents=True, exist_ok=True)
    rec.write_text(f"---\nid: mw-src-1111111111\n---\n{PASSAGE}\n", encoding="utf-8")
    (tmp_path / "_audits").mkdir(exist_ok=True)
    return tmp_path


def _body(**kw) -> str:
    base = {"title": "First session", "characterization": "A first gathering",
            "labels": ["rehearsal"], "why": "stable identity useful",
            "source_passage": {"path": CANON, "quote": PASSAGE}}
    base.update(kw)
    return json.dumps(base)


def _propose(wiki: Path, **kw) -> str:
    p = kp.create_proposal(wiki, kind="object-create", body=_body(**kw),
                           submitted_by={"actor_type": "agent", "tool": "t"})
    return json.loads(p.read_text(encoding="utf-8"))["id"]


def test_rebuild_projects_candidate_without_canonical_write(proj_wiki: Path) -> None:
    pid = _propose(proj_wiki)
    proj = cand.rebuild(proj_wiki)
    assert len(proj["projections"]) == 1
    c = proj["projections"][0]
    assert c["proposal_id"] == pid
    assert c["authority"] == "candidate"
    assert c["proposal_status"] in ("new", "audited")
    assert c["source_passage"]["quote"] == PASSAGE
    assert "rehearsal" in c["labels"]
    assert c["title"] == "First session"
    assert not (proj_wiki / "03-objects").exists()


def test_candidate_appears_in_pack_marked_not_penalized(proj_wiki: Path) -> None:
    _propose(proj_wiki)
    cand.rebuild(proj_wiki)
    bgi.build(proj_wiki)
    pack = cp.build_pack(proj_wiki, "mw-src-1111111111", hops=0,
                         query="rehearsal", search_fn=lambda q, n: [])
    found = [e for e in pack["records"] if e.get("proposal_id")]
    assert len(found) == 1
    assert found[0]["authority"] == "candidate"
    assert "candidate" in found[0]["reason"]
    assert "known to be" not in found[0]["reason"]


def test_accepted_only_excludes_candidate(proj_wiki: Path) -> None:
    _propose(proj_wiki)
    cand.rebuild(proj_wiki)
    bgi.build(proj_wiki)
    pack = cp.build_pack(proj_wiki, "mw-src-1111111111", hops=0,
                         query="rehearsal", search_fn=lambda q, n: [],
                         accepted_only=True)
    assert [e for e in pack["records"] if e.get("proposal_id")] == []
    assert pack["meta"]["accepted_only"] is True


def test_rejected_excluded_from_default_but_in_audit_scope(proj_wiki: Path) -> None:
    pid = _propose(proj_wiki)
    kp.adjudicate(proj_wiki, proposal_id=pid, decision="rejected", by="owner",
                  decision_note="not now")
    proj = cand.rebuild(proj_wiki)
    assert proj["projections"] == []
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        ea.audit(proj_wiki)
    rep = sorted((proj_wiki / "_audits").glob("evidence-audit-*.json"))[-1]
    data = json.loads(rep.read_text())
    assert any(r["id"] == pid for r in data["results"])


def test_stale_passage_rejected_audit_leaves_projections(proj_wiki: Path) -> None:
    _propose(proj_wiki)
    (proj_wiki / CANON).write_text("---\nid: mw-src-1111111111\n---\nRewritten entirely.\n",
                                   encoding="utf-8")
    proj = cand.rebuild(proj_wiki)
    assert proj["projections"] == []


def test_accepted_resolves_to_canonical_without_duplicate(proj_wiki: Path) -> None:
    pid = _propose(proj_wiki)
    kp.adjudicate(proj_wiki, proposal_id=pid, decision="accepted", by="owner",
                  decision_note="good", applied_to=["03-objects/session.md"])
    obj = proj_wiki / "03-objects" / "session.md"
    obj.parent.mkdir(parents=True, exist_ok=True)
    obj.write_text("---\nid: xx-obj-s1\ntype: object\ntitle: First session\n"
                   "status: active-record\nlabels:\n  - rehearsal\n---\n\nBody.\n",
                   encoding="utf-8")
    proj = cand.rebuild(proj_wiki)
    assert proj["projections"] == []
    bgi.build(proj_wiki)
    pack = cp.build_pack(proj_wiki, "xx-obj-s1", hops=0, query="rehearsal",
                         search_fn=lambda q, n: [])
    ids = [e["id"] for e in pack["records"]]
    assert ids.count("xx-obj-s1") == 1
    assert not [e for e in pack["records"] if e.get("proposal_id")]


def test_search_lists_candidates_marked(proj_wiki: Path, monkeypatch) -> None:
    _propose(proj_wiki)
    cand.rebuild(proj_wiki)
    monkeypatch.setattr(srv, "ROOT", proj_wiki)
    resp = srv.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                       "params": {"name": "wiki_search",
                                  "arguments": {"query": "rehearsal", "n": 8}}})
    out = json.loads(resp["result"]["content"][0]["text"])
    assert "candidates" in out
    assert any(c["authority"] == "candidate" for c in out["candidates"])
