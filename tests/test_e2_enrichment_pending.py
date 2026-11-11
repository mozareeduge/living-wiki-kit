"""E2: wiki_enrichment_pending work queue (read-only)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))

from _enrich_fixture import VER, chunk_ref, make_instance  # noqa: E402
from gov_kernel import enrichment as en  # noqa: E402


def _sub(inst, ref, exp=0, key="key-00000001", mention="Alpha"):
    return en.submit(inst, {
        "source_ref": ref, "source_version": VER, "expected_annotation_revision": exp, "idempotency_key": key,
        "producer": {"harness": "h", "model": "m", "prompt_version": "p"},
        "annotation": {"summary": "s", "entities": [
            {"name": "A", "kind": "other", "mention": {"chunk_ref": chunk_ref(ref, 0), "text": mention}}]},
    })


def test_pending_lists_unannotated_with_chunk_texts(tmp_path: Path) -> None:
    inst = make_instance(tmp_path, {"s1": ["Alpha one.", "Beta two."], "s2": ["Alpha three."]})
    r = en.pending(inst)
    assert [i["source_ref"] for i in r["items"]] == ["s1", "s2"]
    it = r["items"][0]
    assert it["expected_annotation_revision"] == 0 and it["source_version"] == VER
    assert it["chunks"][0]["text"] == "Alpha one." and it["chunks"][0]["span"] == {"start": 0, "end": 10}
    assert r["next_cursor"] is None


def test_pending_skips_annotated_current_version(tmp_path: Path) -> None:
    inst = make_instance(tmp_path, {"s1": ["Alpha one."], "s2": ["Alpha two."]})
    _sub(inst, "s1")
    assert [i["source_ref"] for i in en.pending(inst)["items"]] == ["s2"]


def test_limit_capped_at_5_and_cursor_pages(tmp_path: Path) -> None:
    inst = make_instance(tmp_path, {f"s{i}": ["Alpha text."] for i in range(7)})
    p1 = en.pending(inst, limit=50)
    assert len(p1["items"]) == 5 and p1["next_cursor"] == "s4"
    p2 = en.pending(inst, limit=50, cursor=p1["next_cursor"])
    assert [i["source_ref"] for i in p2["items"]] == ["s5", "s6"] and p2["next_cursor"] is None


def test_retry_failed(tmp_path: Path) -> None:
    inst = make_instance(tmp_path, {"s1": ["Alpha one."], "s2": ["Alpha two."]})
    try:
        _sub(inst, "s1", mention="not in chunk")
    except en.EnrichmentError:
        pass
    assert [i["source_ref"] for i in en.pending(inst)["items"]] == ["s2"]
    assert [i["source_ref"] for i in en.pending(inst, retry_failed=True)["items"]] == ["s1", "s2"]


def test_pending_is_read_only_and_tool_registered_read(tmp_path: Path) -> None:
    inst = make_instance(tmp_path)
    before = sorted(p.relative_to(inst).as_posix() for p in inst.rglob("*"))
    out = json.loads(en.tool_pending(inst, {"limit": 3}))
    assert out["ok"] and sorted(p.relative_to(inst).as_posix() for p in inst.rglob("*")) == before
    import wiki_mcp_server as srv
    t = srv.REGISTRY.get_tool("wiki_enrichment_pending")
    assert t.is_write is False and t.profile == "read"


def test_missing_index_fails_closed(tmp_path: Path) -> None:
    out = json.loads(en.tool_pending(tmp_path, {}))
    assert out["ok"] is False and out["code"] == "E_INDEX_MISSING"


def test_long_source_chunks_are_page_sized(tmp_path: Path) -> None:
    inst = make_instance(tmp_path, {"big": ["x" * 2000 for _ in range(6)]})
    it = en.pending(inst)["items"][0]
    assert it["chunks_total"] == 6 and it["chunks_truncated"] is True and len(it["chunks"]) == 3
