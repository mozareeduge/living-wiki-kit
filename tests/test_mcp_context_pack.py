"""Tests for the wiki_context_pack MCP tool (rung W2).

The tool is a read-only wrapper over context_pack.build_pack: it must be
advertised in tools/list, return a governed pack (<= 30 records, <= 16k
tokens, a reason on every record), clamp caller-supplied limits, turn every
failure into a JSON error (a SystemExit must never kill the server), and
write nothing anywhere.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

KIT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KIT_ROOT / "scripts"))

import build_graph_index as bgi  # noqa: E402
import context_pack as cp  # noqa: E402
import wiki_mcp_server as srv  # noqa: E402

SEED = "mw-src-1111111111"


@pytest.fixture()
def wiki(tmp_path: Path, monkeypatch) -> Path:
    """Mini canonical wiki (same shape as test_context_compiler) with the
    MCP server pointed at it."""
    (tmp_path / "02-sources" / "records").mkdir(parents=True)
    (tmp_path / "03-objects" / "concepts").mkdir(parents=True)
    (tmp_path / "_search").mkdir(parents=True)
    (tmp_path / "02-sources" / "records" / "mw-src-1111111111--essay-grave-machine.md"
     ).write_text(
        "---\nid: mw-src-1111111111\ntype: source-record\ntitle: Grave Machine\n"
        "status: registered\n---\nBody links [[mw-con-2222222222]].\n", encoding="utf-8")
    (tmp_path / "03-objects" / "concepts" / "mw-con-2222222222--concept-machine.md"
     ).write_text(
        "---\nid: mw-con-2222222222\ntype: concept\nkind: concept\ntitle: Machine\n"
        "status: registered\n---\nSee [[mw-src-3333333333--essay-grave]].\n", encoding="utf-8")
    (tmp_path / "02-sources" / "records" / "mw-src-3333333333--essay-grave.md"
     ).write_text(
        "---\nid: mw-src-3333333333\ntype: source-record\ntitle: Grave\n"
        "status: pending-registration\n---\nStandalone leaf.\n", encoding="utf-8")
    monkeypatch.setattr(srv, "ROOT", tmp_path)
    return tmp_path


def _rpc(method: str, params: dict | None = None) -> dict:
    msg = {"jsonrpc": "2.0", "id": 1, "method": method}
    if params is not None:
        msg["params"] = params
    resp = srv.handle(msg)
    assert resp is not None
    return resp


def _call(**arguments) -> dict:
    resp = _rpc("tools/call", {"name": "wiki_context_pack", "arguments": arguments})
    assert "error" not in resp, resp
    return json.loads(resp["result"]["content"][0]["text"])


def _tree(root: Path) -> set[str]:
    return {p.relative_to(root).as_posix() for p in root.rglob("*")}


# ------------------------------------------------------------ advertisement

def test_tool_is_advertised_with_a_required_seed():
    tools = {t["name"]: t for t in _rpc("tools/list")["result"]["tools"]}
    assert "wiki_context_pack" in tools
    schema = tools["wiki_context_pack"]["inputSchema"]
    assert schema["required"] == ["seed"]
    assert set(schema["properties"]) >= {"seed", "hops", "query", "records", "budget"}
    desc = tools["wiki_context_pack"]["description"].lower()
    assert "never evidence" in desc and "read-only" in desc


def test_tool_is_dispatchable():
    assert "wiki_context_pack" in srv.DISPATCH


# ------------------------------------------------------------------- output

def test_returns_a_governed_pack_with_a_reason_on_every_record(wiki):
    bgi.build(wiki)
    out = _call(seed=SEED, hops=1)
    ids = [r["id"] for r in out["records"]]
    assert ids[0] == SEED and "mw-con-2222222222" in ids
    assert all(r.get("reason") for r in out["records"])
    assert out["records"][0]["reason"] == "seed"
    assert any(r["reason"].startswith("1-hop via") for r in out["records"])
    assert out["meta"]["records"] == len(out["records"]) <= 30
    assert out["meta"]["tokens_est"] <= out["meta"]["budget_tokens"] <= 16000
    assert "never evidence" in out["meta"]["authority_note"]


def test_hops_zero_is_honoured_not_defaulted(wiki):
    bgi.build(wiki)
    out = _call(seed=SEED, hops=0)
    assert [r["id"] for r in out["records"]] == [SEED]
    assert out["meta"]["hops"] == 0


def test_query_adds_lexical_hits_with_a_labelled_reason(wiki, monkeypatch):
    bgi.build(wiki)
    monkeypatch.setattr(cp, "default_search", lambda q, n, root: [
        {"file": "qmd://wiki/mw-src-3333333333--essay-grave", "score": 1.0}])
    out = _call(seed=SEED, hops=0, query="grave")
    by_id = {r["id"]: r for r in out["records"]}
    assert by_id["mw-src-3333333333"]["reason"] == "lexical: grave"


# ---------------------------------------------------------------- clamping

def test_caller_limits_are_clamped_to_the_governed_maxima(wiki):
    bgi.build(wiki)
    out = _call(seed=SEED, hops=99, records=999, budget=10**9)
    assert out["meta"]["max_records"] == 30
    assert out["meta"]["budget_tokens"] == 16000
    assert out["meta"]["hops"] == 2


def test_caller_limits_are_clamped_from_below(wiki):
    bgi.build(wiki)
    out = _call(seed=SEED, hops=-5, records=0, budget=0)
    assert out["meta"]["max_records"] >= 1
    assert out["meta"]["budget_tokens"] >= 1
    assert out["meta"]["hops"] == 0


def test_smaller_limits_are_respected(wiki):
    bgi.build(wiki)
    out = _call(seed=SEED, hops=2, records=2)
    assert out["meta"]["records"] <= 2


# ----------------------------------------------------------------- failures

def test_missing_graph_index_is_a_json_error_that_names_the_fix(wiki):
    out = _call(seed=SEED)
    assert "error" in out and "build_graph_index.py" in out["error"]
    assert str(wiki) not in out["error"]  # no machine path leaks to the agent


def test_unknown_seed_is_a_json_error_not_a_server_exit(wiki):
    bgi.build(wiki)
    out = _call(seed="mw-src-doesnotexist")
    assert "error" in out and "not in graph index" in out["error"]


def test_empty_seed_is_a_json_error(wiki):
    bgi.build(wiki)
    assert "error" in _call(seed="   ")


def test_non_numeric_limit_is_an_error_not_a_crash(wiki):
    bgi.build(wiki)
    resp = _rpc("tools/call", {"name": "wiki_context_pack",
                               "arguments": {"seed": SEED, "hops": "many"}})
    body = json.loads(resp["result"]["content"][0]["text"])
    assert "error" in body


# ---------------------------------------------------------------- read-only

def test_tool_writes_nothing(wiki, monkeypatch):
    bgi.build(wiki)
    monkeypatch.setattr(cp, "default_search", lambda q, n, root: [])  # never reach a real qmd
    before = _tree(wiki)
    _call(seed=SEED, hops=2, query="grave")
    assert _tree(wiki) == before  # no _search/packs, no _proposals, nothing
