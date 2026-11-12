#!/usr/bin/env python3
"""Fresh-instance flow check, run by release_smoke.py inside the new wiki.

A reader's whole path on a brand-new instance: ingest a file, find its text by
retrieval, add an enrichment revision, find the same chunk by an enrichment
topic (labelled non-evidence), and see annotation coverage. Prints
`FLOW OK` or exits non-zero naming the first broken step.
"""
from __future__ import annotations

import json
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "scripts" / "retrieval"))

from gov_kernel import enrichment  # noqa: E402
from gov_kernel.ingest import ingest_file  # noqa: E402
import retrieve  # noqa: E402

WORD = "zyxsmokelantern"
TOPIC = "smokemaritime"


def fail(step: str, detail: object) -> None:
    print(f"FLOW FAIL at {step}: {detail}")
    raise SystemExit(1)


def hits(result: dict) -> list[dict]:
    return [h for g in result["groups"].values() for h in g]


def main() -> int:
    with tempfile.TemporaryDirectory() as td:
        staged = pathlib.Path(td) / "smoke-note.md"
        staged.write_text(f"# Smoke note\n\nThe {WORD} paragraph is the only place this word appears.\n",
                          encoding="utf-8", newline="\n")
        receipt = ingest_file(staged_path=staged, root=ROOT, request_id="release-smoke-flow")
    ref = receipt.get("source_ref")
    if not ref or receipt.get("chunk_count", 0) < 1:
        fail("ingest", f"no source_ref or no chunks: {receipt}")

    found = hits(retrieve.wiki_retrieve(ROOT, query=WORD))
    if not found or WORD not in found[0]["text"] or found[0].get("non_evidence"):
        fail("retrieve", "ingested text not found as evidence-level chunk text")
    chunk = found[0]

    version = retrieve.wiki_artifact_read(ROOT, source_ref=ref)["source_version"]
    sub = enrichment.submit(ROOT, {
        "source_ref": ref, "source_version": version, "expected_annotation_revision": 0,
        "idempotency_key": "release-smoke-0001",
        "producer": {"harness": "release-smoke", "model": "none", "prompt_version": "1"},
        "annotation": {"summary": "smoke summary SUMMARY-ONLY",
                       "chunk_annotations": [{"chunk_ref": chunk["chunk_ref"], "note": "smoke", "topics": [TOPIC]}]},
    })
    if not sub.get("ok"):
        fail("enrichment submit", sub)

    by_topic = hits(retrieve.wiki_retrieve(ROOT, query=TOPIC))
    if len(by_topic) != 1 or by_topic[0]["chunk_ref"] != chunk["chunk_ref"] or not by_topic[0].get("non_evidence"):
        fail("enrichment retrieve", json.dumps(by_topic)[:400])
    if by_topic[0]["text"] != chunk["text"] or "SUMMARY-ONLY" in by_topic[0]["text"]:
        fail("enrichment retrieve", "returned text is not the chunk text")

    cov = retrieve.wiki_artifact_read(ROOT, source_ref=ref)["annotation_coverage"]
    if cov["annotated_chunks"] != 1 or cov["total_chunks"] != receipt["chunk_count"]:
        fail("coverage", cov)
    print("FLOW OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
