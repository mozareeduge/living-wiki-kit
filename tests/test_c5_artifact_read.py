"""C5: wiki_artifact_read, stale-ref handling, and tool registration (C4 + C5)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "scripts" / "retrieval"))

from gov_kernel.retrieval import build_index  # noqa: E402
import retrieve as R  # noqa: E402

PROFILES = {
    "profiles": {
        "all-governed": {"exclude_globs": [".git/**", "_search/**"], "include_globs": ["**/*.md"]},
        "canonical": {"exclude_globs": ["02-sources/**"], "include_globs": ["03-objects/**"]},
        "captures": {"exclude_globs": [], "include_globs": ["01-inbox/captures/**"]},
        "evidence-text": {"exclude_globs": [], "include_globs": ["02-sources/text/**"]},
    }
}
DERIV = "02-sources/text/tst-src-aaaa.extracted.md"
SRC = "rec:tst-src-aaaa"


def _write(root: Path, rel: str, text: str) -> None:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8", newline="\n")


def _book(paragraphs: int, word: str = "lantern") -> str:
    parts = ["# Book", ""]
    for i in range(paragraphs):
        parts += [f"## Part {i}", "", (f"The {word} paragraph {i} text. " * 40).strip(), ""]
    return "\n".join(parts)


@pytest.fixture
def wiki(tmp_path: Path) -> Path:
    _write(tmp_path, "00-system/configuration/retrieval-profiles.v2.json", json.dumps(PROFILES))
    _write(tmp_path, DERIV, _book(4))
    build_index(tmp_path, tmp_path / "_search" / "retrieval.sqlite")
    return tmp_path


def test_read_source_with_layers_and_paginated_chunks(wiki: Path) -> None:
    page1 = R.wiki_artifact_read(wiki, source_ref=SRC, limit=2)
    assert page1["ok"] and page1["layers"]["derivative"] == {"path": DERIV, "present": True}
    assert page1["chunks"]["total"] >= 3 and len(page1["chunks"]["items"]) == 2
    assert page1["chunks"]["next_offset"] == 2
    page2 = R.wiki_artifact_read(wiki, source_ref=SRC, limit=2, offset=2)
    refs = [c["chunk_ref"] for c in page1["chunks"]["items"] + page2["chunks"]["items"]]
    assert len(set(refs)) == len(refs)
    text = (wiki / DERIV).read_text(encoding="utf-8")
    for c in page1["chunks"]["items"]:
        assert text[c["span"]["start"]:c["span"]["end"]] == c["text"]


def test_read_chunk_with_prev_next(wiki: Path) -> None:
    items = R.wiki_artifact_read(wiki, source_ref=SRC, limit=100)["chunks"]["items"]
    mid = items[1]["chunk_ref"]
    res = R.wiki_artifact_read(wiki, chunk_ref=mid)
    assert res["chunk"]["text"] == items[1]["text"]
    assert res["prev"] == items[0]["chunk_ref"] and res["next"] == items[2]["chunk_ref"]
    assert R.wiki_artifact_read(wiki, chunk_ref=items[0]["chunk_ref"])["prev"] is None
    assert R.wiki_artifact_read(wiki, chunk_ref=items[-1]["chunk_ref"])["next"] is None


def test_stale_ref_after_edit_and_rebuild(wiki: Path) -> None:
    old = R.wiki_artifact_read(wiki, source_ref=SRC, limit=100)
    old_ref = old["chunks"]["items"][1]["chunk_ref"]
    old_version = old["source_version"]
    _write(wiki, DERIV, _book(4, word="harbour"))  # edit derivative
    build_index(wiki, wiki / "_search" / "retrieval.sqlite")  # rebuild
    with pytest.raises(R.RetrieveError) as ei:
        R.wiki_artifact_read(wiki, chunk_ref=old_ref, source_ref=SRC)
    err = ei.value
    assert err.code == "E_STALE_SOURCE"
    new_version = R.wiki_artifact_read(wiki, source_ref=SRC)["source_version"]
    assert new_version != old_version and err.extra["current_source_version"] == new_version
    # claiming the old version on the source itself is also stale
    with pytest.raises(R.RetrieveError) as ei2:
        R.wiki_artifact_read(wiki, source_ref=SRC, source_version=old_version)
    assert ei2.value.code == "E_STALE_SOURCE"
    # never remapped: without the source hint the old ref is unknown, not silently resolved
    with pytest.raises(R.RetrieveError) as ei3:
        R.wiki_artifact_read(wiki, chunk_ref=old_ref)
    assert ei3.value.code == "E_UNKNOWN_REF"


def test_unknown_source_and_bad_args(wiki: Path) -> None:
    with pytest.raises(R.RetrieveError) as ei:
        R.wiki_artifact_read(wiki, source_ref="rec:nope")
    assert ei.value.code == "E_UNKNOWN_REF"
    with pytest.raises(R.RetrieveError):
        R.wiki_artifact_read(wiki)
    with pytest.raises(R.RetrieveError):
        R.wiki_artifact_read(wiki, source_ref=SRC, limit=0)


def test_missing_derivative_file_is_flagged(wiki: Path) -> None:
    (wiki / DERIV).unlink()
    res = R.wiki_artifact_read(wiki, source_ref=SRC)
    assert "source-file-missing" in res["quality_flags"]


def test_cli_artifact_read(wiki: Path) -> None:
    import subprocess

    out = subprocess.run(
        [sys.executable, str(ROOT / "scripts/retrieval/retrieve.py"), "--repo", str(wiki), "--artifact", SRC],
        capture_output=True, text=True, encoding="utf-8",
    )
    assert out.returncode == 0, out.stderr
    assert json.loads(out.stdout)["source_ref"] == SRC


def test_tools_registered_in_read_profile_and_callable(wiki: Path) -> None:
    from mcp_transport.registry import ToolRegistry, register_retrieval_tools

    reg = ToolRegistry()
    register_retrieval_tools(reg, wiki)
    names = {t["name"] for t in reg.advertised_tools("read")}
    assert {"wiki_retrieve", "wiki_artifact_read"} <= names
    resp = reg.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                       "params": {"name": "wiki_retrieve", "arguments": {"query": "lantern"}}}, "read", "http")
    assert resp["result"]["isError"] is False
    payload = json.loads(resp["result"]["content"][0]["text"])
    assert payload["ok"] and payload["groups"]["sources"]
    resp = reg.handle({"jsonrpc": "2.0", "id": 2, "method": "tools/call",
                       "params": {"name": "wiki_artifact_read", "arguments": {"source_ref": SRC}}}, "read", "stdio")
    assert json.loads(resp["result"]["content"][0]["text"])["source_ref"] == SRC


def test_real_server_registry_advertises_new_tools() -> None:
    import wiki_mcp_server as srv

    names = {t["name"] for t in srv.REGISTRY.advertised_tools("read")}
    assert {"wiki_retrieve", "wiki_artifact_read"} <= names
