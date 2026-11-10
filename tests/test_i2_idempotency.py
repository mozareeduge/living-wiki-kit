"""Tests for Rung I2: Idempotency.

Acceptance criteria:
- wiki_capture_text and wiki_ingest_file accept optional request_id (8-100 chars).
- Store request_id -> receipt in _intake/idempotency.jsonl (append-only).
- Same id + same payload -> return stored receipt.
- Same id + different payload -> error E_IDEMPOTENCY_CONFLICT.
- Concurrency: two processes, same id -> exactly one write.
"""
from __future__ import annotations

import json
import multiprocessing
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "scripts" / "capture"))

import wiki_capture as wc
from gov_kernel import ingest

FIXTURES = ROOT / "tests" / "fixtures" / "ingest"


@pytest.fixture
def clean_wiki(tmp_path: Path) -> Path:
    wiki = tmp_path / "wiki"
    listed = subprocess.run(
        ["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, check=True
    ).stdout.decode("utf-8").split("\0")
    for rel in filter(None, listed):
        src = ROOT / rel
        if src.is_file():
            (wiki / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, wiki / rel)
    res = subprocess.run(
        [sys.executable, "scripts/instantiate.py", "--name", "Test Wiki", "--prefix", "tst"],
        cwd=wiki, capture_output=True, text=True
    )
    assert res.returncode == 0, res.stdout + res.stderr
    return wiki


def test_request_id_validation() -> None:
    # Too short (< 8 chars)
    with pytest.raises(wc.CaptureError) as excinfo:
        wc.capture_text("Hello", channel="mcp", request_id="short")
    assert excinfo.value.code == "E_BAD_REQUEST_ID"

    # Too long (> 100 chars)
    with pytest.raises(wc.CaptureError) as excinfo:
        wc.capture_text("Hello", channel="mcp", request_id="x" * 101)
    assert excinfo.value.code == "E_BAD_REQUEST_ID"

    # Ingest too short
    with pytest.raises(ingest.IngestError) as excinfo_ing:
        ingest.ingest_file(FIXTURES / "sample.txt", request_id="short")
    assert excinfo_ing.value.code == "E_BAD_REQUEST_ID"


def test_capture_text_idempotency_retry(clean_wiki: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(wc, "REPO_ROOT", clean_wiki)
    monkeypatch.setattr(wc, "CAPTURES_ROOT", clean_wiki / "01-inbox" / "captures")

    req_id = "req-capture-retry-12345"
    res1 = wc.capture_text("Capture content for retry test.", channel="mcp", request_id=req_id)
    assert res1["ok"] is True

    # Retry with same request_id and same payload
    res2 = wc.capture_text("Capture content for retry test.", channel="mcp", request_id=req_id)
    assert res2["ok"] is True
    assert res2["id"] == res1["id"]
    assert res2["sha256"] == res1["sha256"]

    # Verify idempotency log
    log_file = clean_wiki / "_intake" / "idempotency.jsonl"
    assert log_file.is_file()
    lines = [json.loads(line) for line in log_file.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(lines) == 1
    assert lines[0]["request_id"] == req_id


def test_capture_text_idempotency_conflict(clean_wiki: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(wc, "REPO_ROOT", clean_wiki)
    monkeypatch.setattr(wc, "CAPTURES_ROOT", clean_wiki / "01-inbox" / "captures")

    req_id = "req-capture-conflict-123"
    res1 = wc.capture_text("First payload", channel="mcp", request_id=req_id)
    assert res1["ok"] is True

    # Call with same request_id but different text payload
    with pytest.raises(wc.CaptureError) as excinfo:
        wc.capture_text("Second payload differing from first", channel="mcp", request_id=req_id)
    assert excinfo.value.code == "E_IDEMPOTENCY_CONFLICT"


def test_ingest_file_idempotency_retry(clean_wiki: Path) -> None:
    req_id = "req-ingest-retry-98765"
    txt_file = FIXTURES / "sample.txt"

    res1 = ingest.ingest_file(txt_file, root=clean_wiki, request_id=req_id)
    assert res1["ok"] is True

    # Retry with same request_id and same file
    res2 = ingest.ingest_file(txt_file, root=clean_wiki, request_id=req_id)
    assert res2["ok"] is True
    assert res2["source_ref"] == res1["source_ref"]
    assert res2["sha256"] == res1["sha256"]


def test_ingest_file_idempotency_conflict(clean_wiki: Path) -> None:
    req_id = "req-ingest-conflict-987"
    txt1 = FIXTURES / "sample.txt"
    txt2 = FIXTURES / "sample_fa.txt"

    res1 = ingest.ingest_file(txt1, root=clean_wiki, request_id=req_id)
    assert res1["ok"] is True

    # Call with same request_id but different file
    with pytest.raises(ingest.IngestError) as excinfo:
        ingest.ingest_file(txt2, root=clean_wiki, request_id=req_id)
    assert excinfo.value.code == "E_IDEMPOTENCY_CONFLICT"


def _worker_ingest(wiki_str: str, file_str: str, req_id: str, queue: multiprocessing.Queue) -> None:
    try:
        from gov_kernel import ingest
        r = ingest.ingest_file(file_str, root=Path(wiki_str), request_id=req_id)
        queue.put(("ok", r["source_ref"]))
    except Exception as exc:
        queue.put(("error", str(exc)))


def test_concurrency_same_id_one_write(clean_wiki: Path) -> None:
    req_id = "req-concurrent-same-id-12345"
    txt_file = FIXTURES / "sample.txt"

    q: multiprocessing.Queue = multiprocessing.Queue()
    p1 = multiprocessing.Process(target=_worker_ingest, args=(str(clean_wiki), str(txt_file), req_id, q))
    p2 = multiprocessing.Process(target=_worker_ingest, args=(str(clean_wiki), str(txt_file), req_id, q))

    p1.start()
    p2.start()
    p1.join(timeout=10)
    p2.join(timeout=10)

    assert not p1.is_alive()
    assert not p2.is_alive()

    results = [q.get() for _ in range(2)]
    assert results[0][0] == "ok"
    assert results[1][0] == "ok"
    # Both processes must get the exact same source_ref
    assert results[0][1] == results[1][1]

    # Exactly one record file created
    records = list((clean_wiki / "02-sources" / "records").glob("*.md"))
    assert len(records) == 1
