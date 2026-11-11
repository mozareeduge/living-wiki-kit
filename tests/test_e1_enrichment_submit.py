"""E1: enrichment sidecar store, validation, concurrency, and independence from the corpus."""
from __future__ import annotations

import copy
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))

from _enrich_fixture import VER, VER2, chunk_ref, make_instance  # noqa: E402
from gov_kernel import enrichment as en  # noqa: E402

C0 = chunk_ref("src-a", 0)
C1 = chunk_ref("src-a", 1)


@pytest.fixture()
def inst(tmp_path: Path) -> Path:
    return make_instance(tmp_path)


def args(**over):
    a = {
        "source_ref": "src-a", "source_version": VER, "expected_annotation_revision": 0,
        "idempotency_key": "key-00000001",
        "producer": {"harness": "h", "model": "m", "prompt_version": "p1"},
        "annotation": {
            "summary": "A short summary.", "topics": ["origins"], "tags": ["a"],
            "entities": [{"name": "Alpha", "kind": "project", "mention": {"chunk_ref": C0, "text": "Alpha Project"}}],
            "links": [{"relation": "supports", "target": "obj-1",
                       "evidence": [{"chunk_ref": C1, "quote": "contradicted the first account"}]}],
            "chunk_annotations": [{"chunk_ref": C0, "note": "opening"}],
            "uncertainty": ["date is vague"],
        },
    }
    a.update(over)
    return a


def code(inst, a):
    with pytest.raises(en.EnrichmentError) as ei:
        en.submit(inst, a)
    return ei.value.code


def _sidecar_lines(inst: Path) -> list[str]:
    return (inst / "_search/enrichment/src-a.jsonl").read_text(encoding="utf-8").splitlines()


def test_submit_appends_revision_level7(inst: Path) -> None:
    r = en.submit(inst, args())
    assert r["ok"] and r["revision"] == 1 and r["non_evidence"] is True
    rec = json.loads(_sidecar_lines(inst)[0])
    assert rec["authority_level"] == 7 and rec["non_evidence"] is True and rec["revision"] == 1
    r2 = en.submit(inst, args(expected_annotation_revision=1, idempotency_key="key-00000002"))
    assert r2["revision"] == 2
    assert len(_sidecar_lines(inst)) == 2


def test_revision_conflict(inst: Path) -> None:
    en.submit(inst, args())
    assert code(inst, args(expected_annotation_revision=0, idempotency_key="key-00000002")) == "E_REVISION_CONFLICT"


def test_stale_source(inst: Path) -> None:
    assert code(inst, args(source_version=VER2)) == "E_STALE_SOURCE"


def test_unknown_source(inst: Path) -> None:
    assert code(inst, args(source_ref="nope")) == "E_UNKNOWN_SOURCE"


def test_missing_index_fails_closed(tmp_path: Path) -> None:
    assert code(tmp_path, args()) == "E_INDEX_MISSING"


def test_unsafe_source_ref(inst: Path) -> None:
    assert code(inst, args(source_ref="../evil")) == "E_INVALID"


def test_missing_expected_revision(inst: Path) -> None:
    a = args()
    del a["expected_annotation_revision"]
    assert code(inst, a) == "E_INVALID"


def test_idempotent_replay(inst: Path) -> None:
    en.submit(inst, args())
    r = en.submit(inst, args())  # same key, stale expected revision: replay, not conflict
    assert r["replayed"] is True and r["revision"] == 1
    assert len(_sidecar_lines(inst)) == 1


def _bad(inst, mut, key="key-bad00001"):
    a = args(idempotency_key=key)
    mut(a["annotation"])
    return code(inst, a)


def test_mention_text_must_be_exact_substring(inst: Path) -> None:
    assert _bad(inst, lambda an: an["entities"][0]["mention"].update(text="alpha project")) == "E_VALIDATION"


def test_quote_must_be_exact_substring(inst: Path) -> None:
    assert _bad(inst, lambda an: an["links"][0]["evidence"][0].update(quote="contradicted the second account")) == "E_VALIDATION"


def test_quote_from_wrong_chunk_rejected(inst: Path) -> None:
    assert _bad(inst, lambda an: an["links"][0]["evidence"][0].update(chunk_ref=C0)) == "E_VALIDATION"


def test_unknown_chunk_rejected(inst: Path) -> None:
    unknown = "chk:" + "9" * 32
    assert _bad(inst, lambda an: an["entities"][0]["mention"].update(chunk_ref=unknown)) == "E_VALIDATION"


def test_chunk_of_other_source_rejected(tmp_path: Path) -> None:
    inst = make_instance(tmp_path, {"src-a": ["Alpha Project one."], "src-b": ["Beta text here."]})
    a = args()
    a["annotation"] = {"summary": "s", "entities": [
        {"name": "B", "kind": "other", "mention": {"chunk_ref": chunk_ref("src-b", 0), "text": "Beta"}}]}
    assert code(inst, a) == "E_VALIDATION"


def test_closed_relation_vocabulary(inst: Path) -> None:
    assert _bad(inst, lambda an: an["links"][0].update(relation="proves")) == "E_VALIDATION"
    for n, rel in enumerate(en.RELATIONS):
        a = args(idempotency_key=f"key-rel-{n:04d}", expected_annotation_revision=n)
        a["annotation"]["links"][0]["relation"] = rel
        assert en.submit(inst, a)["ok"]


@pytest.mark.parametrize("field,value", [
    ("summary", "x" * 801), ("tags", ["t"] * 13), ("topics", ["t"] * 6), ("uncertainty", ["u"] * 9),
])
def test_limits_annotation(inst: Path, field, value) -> None:
    assert _bad(inst, lambda an: an.update({field: value})) == "E_VALIDATION"


def test_limits_entities_links_chunk_annotations_quote(inst: Path) -> None:
    ent = {"name": "Alpha", "kind": "project", "mention": {"chunk_ref": C0, "text": "Alpha"}}
    assert _bad(inst, lambda an: an.update(entities=[copy.deepcopy(ent) for _ in range(11)])) == "E_VALIDATION"
    link = {"relation": "about", "target": "t", "evidence": [{"chunk_ref": C0, "quote": "Alpha Project"}]}
    assert _bad(inst, lambda an: an.update(links=[copy.deepcopy(link) for _ in range(11)])) == "E_VALIDATION"
    assert _bad(inst, lambda an: an["links"][0].update(evidence=[link["evidence"][0]] * 4)) == "E_VALIDATION"
    assert _bad(inst, lambda an: an.update(chunk_annotations=[{"chunk_ref": C0, "note": "n"}] * 21)) == "E_VALIDATION"
    assert _bad(inst, lambda an: an["links"][0]["evidence"][0].update(quote="Alpha P")) == "E_VALIDATION"  # < 8 chars
    assert _bad(inst, lambda an: an["entities"][0].update(kind="alien")) == "E_VALIDATION"


def test_level_is_always_7(inst: Path) -> None:
    a = args()
    a["authority_level"] = 2  # not a caller field; ignored
    en.submit(inst, a)
    assert json.loads(_sidecar_lines(inst)[0])["authority_level"] == 7


def test_failure_does_not_write_revision(inst: Path) -> None:
    _bad(inst, lambda an: an["entities"][0]["mention"].update(text="nope nope"))
    assert not (inst / "_search/enrichment/src-a.jsonl").exists()


def test_sidecar_deletion_does_not_change_validator_result() -> None:
    """The sidecar lives in gitignored _search/, outside the corpus."""
    def run():
        p = subprocess.run([sys.executable, str(ROOT / "scripts/wiki_validate.py"), "--repo", str(ROOT),
                            "--format", "json"], capture_output=True, text=True, encoding="utf-8")
        return p.returncode, p.stdout

    side = ROOT / "_search" / "enrichment"
    assert not side.exists()
    try:
        base = run()
        side.mkdir(parents=True)
        (side / "src-a.jsonl").write_text(json.dumps({"revision": 1, "junk": True}) + "\n", encoding="utf-8")
        with_sidecar = run()
        shutil.rmtree(side)
        without = run()
    finally:
        shutil.rmtree(side, ignore_errors=True)
    assert base == with_sidecar == without


def test_write_tool_hidden_in_read_profile_and_auth_required_over_http() -> None:
    import wiki_mcp_server as srv
    assert srv.REGISTRY.get_tool("wiki_enrichment_submit").is_write is True
    assert "wiki_enrichment_submit" not in {t["name"] for t in srv.REGISTRY.advertised_tools("read")}
    resp = srv.REGISTRY.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                                "params": {"name": "wiki_enrichment_submit", "arguments": {}}},
                               profile="capture", transport="http")
    assert json.loads(resp["result"]["content"][0]["text"])["code"] == "E_AUTH_REQUIRED"
