"""The kernel MCP server in the kit: profile-scoped and instance-agnostic.

- default profile is read-only; capture/proposal tools need --profile capture;
- QMD collection names come from 00-system/configuration/qmd-collections-v1.1.0.json
  (by folder), never hardcoded to one instance's names;
- proposals become immutable durable records, never canonical writes.
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import wiki_mcp_server as srv  # noqa: E402


def _rpc(method: str, params: dict | None = None) -> dict:
    msg = {"jsonrpc": "2.0", "id": 1, "method": method}
    if params is not None:
        msg["params"] = params
    return srv.handle(msg)


def _names() -> set[str]:
    return {t["name"] for t in _rpc("tools/list")["result"]["tools"]}


def test_default_profile_is_read_only():
    assert srv.ACTIVE_PROFILE == "read"
    names = _names()
    assert {"wiki_read_text", "wiki_search", "wiki_resolve_id", "wiki_context_pack", "wiki_state"} <= names
    assert not names & {"wiki_propose", "wiki_capture_text", "wiki_propose_from_capture",
                        "wiki_mark_capture_reviewed", "wiki_transcribe_capture"}
    err = _rpc("tools/call", {"name": "wiki_propose", "arguments": {"kind": "x", "body": "y"}})
    assert "not enabled in 'read' profile" in err["error"]["message"]


def test_qmd_collections_come_from_the_config_by_folder(tmp_path: Path):
    cfg = tmp_path / "00-system" / "configuration"
    cfg.mkdir(parents=True)
    (cfg / "qmd-collections-v1.1.0.json").write_text(json.dumps({"collections": [
        {"name": "abc-objects", "path": "03-objects"},
        {"name": "abc-claims", "path": "05-claims"},
        {"name": "abc-source-records", "path": "02-sources/records"},
        {"name": "abc-derivatives", "path": "02-sources/text"},
    ]}), encoding="utf-8")
    canonical, provenance = srv.qmd_collections(tmp_path)
    assert canonical == ("abc-objects", "abc-claims")
    assert provenance == ("abc-source-records",)


def test_missing_qmd_config_means_no_qmd_not_a_crash(tmp_path: Path):
    assert srv.qmd_collections(tmp_path) == ((), ())


def test_kit_config_names_are_generic():
    canonical, provenance = srv.qmd_collections(ROOT)
    assert canonical and provenance
    assert all(n.startswith("wiki-") for n in canonical + provenance)


def test_capture_profile_proposal_is_a_durable_candidate_record(tmp_path: Path, monkeypatch):
    shutil.copytree(ROOT / "00-system" / "schemas", tmp_path / "00-system" / "schemas")
    monkeypatch.setattr(srv, "ROOT", tmp_path)
    monkeypatch.setattr(srv, "ACTIVE_PROFILE", "capture")
    resp = _rpc("tools/call", {"name": "wiki_propose",
                               "arguments": {"kind": "relation-edge", "body": "A relates to B"}})
    out = json.loads(resp["result"]["content"][0]["text"])
    assert out["accepted"] is True and out["authority_tier"] == "candidate"
    rec = json.loads((tmp_path / out["proposal_path"]).read_text(encoding="utf-8"))
    assert out["proposal_path"].startswith("_proposals/records/")
    assert rec["authority_tier"] == "candidate" and rec["type"] == "proposal"
    written = {p.relative_to(tmp_path).as_posix() for p in tmp_path.rglob("*") if p.is_file()}
    assert all(w.startswith(("00-system/schemas/", "_proposals/records/")) for w in written)
