"""E3/E4: enrichment in retrieval is labelled non-evidence; coverage tells the truth."""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "scripts" / "retrieval"))

from gov_kernel import enrichment as en  # noqa: E402
from gov_kernel.retrieval import build_index  # noqa: E402
import retrieve as R  # noqa: E402

PROFILES = {"profiles": {
    "all-governed": {"exclude_globs": [".git/**", "_search/**"], "include_globs": ["**/*.md"]},
    "canonical": {"exclude_globs": ["02-sources/**"], "include_globs": ["03-objects/**"]},
    "captures": {"exclude_globs": [], "include_globs": ["01-inbox/captures/**"]},
    "evidence-text": {"exclude_globs": [], "include_globs": ["02-sources/text/**"]},
}}
DERIV = "02-sources/text/tst-src-aaaa.extracted.md"
SRC = "rec:tst-src-aaaa"
PRODUCER = {"harness": "h", "model": "m", "prompt_version": "p"}


def _book() -> str:
    parts = ["# Book", ""]
    for i, w in enumerate(["lantern", "harbor", "orchard"]):
        parts += [f"## Part {i}", "", (f"The {w} paragraph {i} text. " * 40).strip(), ""]
    return "\n".join(parts)


@pytest.fixture
def wiki(tmp_path: Path) -> Path:
    shutil.copytree(ROOT / "00-system" / "schemas", tmp_path / "00-system" / "schemas")
    cfg = tmp_path / "00-system/configuration/retrieval-profiles.v2.json"
    cfg.parent.mkdir(parents=True, exist_ok=True)
    cfg.write_text(json.dumps(PROFILES), encoding="utf-8")
    d = tmp_path / DERIV
    d.parent.mkdir(parents=True, exist_ok=True)
    d.write_text(_book(), encoding="utf-8", newline="\n")
    build_index(tmp_path, tmp_path / "_search" / "retrieval.sqlite")
    return tmp_path


def _chunks(wiki: Path) -> tuple[str, list[dict]]:
    r = R.wiki_artifact_read(wiki, source_ref=SRC, limit=100)
    return r["source_version"], r["chunks"]["items"]


def _submit(wiki: Path, annotation: dict, exp: int = 0, key: str = "key-00000001") -> None:
    ver, _ = _chunks(wiki)
    out = en.submit(wiki, {"source_ref": SRC, "source_version": ver, "expected_annotation_revision": exp,
                           "idempotency_key": key, "producer": PRODUCER, "annotation": annotation})
    assert out["ok"], out


def _hits(r: dict) -> list[dict]:
    return [h for g in r["groups"].values() for h in g]


def test_enrichment_only_match_returns_chunk_text_labelled_non_evidence(wiki: Path) -> None:
    """A reader searching by an enrichment topic finds the chunk, sees the real text, and is told it is not evidence."""
    _, items = _chunks(wiki)
    harbor = next(c for c in items if "harbor" in c["text"])
    assert not _hits(R.wiki_retrieve(wiki, query="maritime"))
    _submit(wiki, {"summary": "SUMMARY-ONLY-MARKER about ships",
                   "chunk_annotations": [{"chunk_ref": harbor["chunk_ref"], "note": "n", "topics": ["maritime"]}]})
    r = R.wiki_retrieve(wiki, query="maritime")
    hits = _hits(r)
    assert [h["chunk_ref"] for h in hits] == [harbor["chunk_ref"]]
    h = hits[0]
    assert h["inclusion_reason"] == ["enrichment-topic"] and h["non_evidence"] is True
    assert h["text"] == harbor["text"] and "SUMMARY-ONLY-MARKER" not in h["text"]
    assert r["enrichment"]["non_evidence"] is True


def test_entity_name_and_alias_find_the_mention_chunk(wiki: Path) -> None:
    """Searching an entity by name or alias leads to the chunk where it is mentioned, labelled non-evidence."""
    _, items = _chunks(wiki)
    orchard = next(c for c in items if "orchard" in c["text"])
    _submit(wiki, {"summary": "s", "entities": [{"name": "Grove Keeper", "kind": "person", "aliases": ["Warden"],
                                                  "mention": {"chunk_ref": orchard["chunk_ref"], "text": "orchard"}}]})
    for q in ("grove keeper", "Warden"):
        hits = _hits(R.wiki_retrieve(wiki, query=q))
        assert [h["inclusion_reason"] for h in hits] == [["enrichment-entity"]]
        assert hits[0]["non_evidence"] is True and hits[0]["chunk_ref"] == orchard["chunk_ref"]


def test_text_match_stays_evidence_and_enrichment_never_outranks_text(wiki: Path) -> None:
    """A real text hit is never downgraded; enrichment only adds a labelled reason and ranks below text."""
    _, items = _chunks(wiki)
    lantern = next(c for c in items if "lantern" in c["text"])
    harbor = next(c for c in items if "harbor" in c["text"])
    _submit(wiki, {"summary": "s", "chunk_annotations": [
        {"chunk_ref": lantern["chunk_ref"], "note": "n", "topics": ["lantern"]},
        {"chunk_ref": harbor["chunk_ref"], "note": "n", "topics": ["lantern"]}]})
    ordered = _hits(R.wiki_retrieve(wiki, query="lantern"))
    hits = {h["chunk_ref"]: h for h in ordered}
    assert "non_evidence" not in hits[lantern["chunk_ref"]]
    assert hits[lantern["chunk_ref"]]["inclusion_reason"][0] in ("exact-match", "fts-match")
    assert hits[lantern["chunk_ref"]]["non_evidence_reasons"] == ["enrichment-topic"]
    assert hits[harbor["chunk_ref"]]["non_evidence"] is True
    refs = [h["chunk_ref"] for h in ordered]
    assert refs.index(lantern["chunk_ref"]) < refs.index(harbor["chunk_ref"])


def test_stale_enrichment_is_ignored_after_source_changes(wiki: Path) -> None:
    """When the source text changes, old annotations must not steer retrieval or claim coverage."""
    _, items = _chunks(wiki)
    _submit(wiki, {"summary": "s", "chunk_annotations": [
        {"chunk_ref": items[0]["chunk_ref"], "note": "n", "topics": ["maritime"]}]})
    assert _hits(R.wiki_retrieve(wiki, query="maritime"))
    (wiki / DERIV).write_text(_book() + "\n\n## Part 9\n\nA new tail paragraph.\n", encoding="utf-8", newline="\n")
    build_index(wiki, wiki / "_search" / "retrieval.sqlite")
    assert not _hits(R.wiki_retrieve(wiki, query="maritime"))
    assert R.wiki_artifact_read(wiki, source_ref=SRC)["annotation_coverage"]["state"] == "none"


def test_coverage_reports_annotated_over_total(wiki: Path) -> None:
    """A reader can see how much of a source the enrichment really covers, not just that some exists."""
    _, items = _chunks(wiki)
    total = len(items)
    cov = R.wiki_artifact_read(wiki, source_ref=SRC)["annotation_coverage"]
    assert cov == {"annotated_chunks": 0, "total_chunks": total, "ratio": 0.0,
                   "annotation_revision": None, "state": "none", "non_evidence": True}
    _submit(wiki, {"summary": "s", "chunk_annotations": [
        {"chunk_ref": items[0]["chunk_ref"], "note": "n"}, {"chunk_ref": items[0]["chunk_ref"], "note": "dup"}]})
    cov = R.wiki_artifact_read(wiki, source_ref=SRC)["annotation_coverage"]
    assert (cov["annotated_chunks"], cov["total_chunks"], cov["state"], cov["annotation_revision"]) == (
        1, total, "partial", 1)
    _submit(wiki, {"summary": "s", "chunk_annotations": [{"chunk_ref": c["chunk_ref"], "note": "n"} for c in items]},
            exp=1, key="key-00000002")
    cov = R.wiki_artifact_read(wiki, source_ref=SRC)["annotation_coverage"]
    assert (cov["annotated_chunks"], cov["state"], cov["ratio"]) == (total, "full", 1.0)
