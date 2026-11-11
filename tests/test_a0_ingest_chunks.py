"""A0: ingest wires the derivative into the chunk index (C2 + C3)."""
from __future__ import annotations

import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures" / "ingest"
sys.path.insert(0, str(ROOT / "scripts"))


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
        cwd=wiki, capture_output=True, text=True,
    )
    assert res.returncode == 0, res.stdout + res.stderr
    return wiki


def _rows(wiki: Path, source_ref: str):
    db = wiki / "_search" / "retrieval.sqlite"
    assert db.is_file()
    conn = sqlite3.connect(db)
    try:
        src = conn.execute(
            "SELECT source_version, path FROM sources WHERE source_ref=?", (source_ref,)
        ).fetchone()
        rows = conn.execute(
            "SELECT chunk_ref, start, end, text FROM chunks WHERE source_ref=? ORDER BY start",
            (source_ref,),
        ).fetchall()
        fts = conn.execute("SELECT count(*) FROM chunks_fts").fetchone()[0]
    finally:
        conn.close()
    return src, rows, fts


@pytest.mark.parametrize("name", ["sample.md", "sample_fa.txt"])
def test_ingest_reports_real_chunk_count_and_rows(clean_wiki: Path, name: str) -> None:
    from gov_kernel import ingest

    receipt = ingest.ingest_file(FIXTURES / name, root=clean_wiki)
    assert receipt["chunk_count"] > 0
    assert "_index_ctx" not in receipt
    src, rows, fts = _rows(clean_wiki, receipt["source_ref"])
    assert len(rows) == receipt["chunk_count"]
    assert fts == len(rows)
    assert src[0] == receipt["source_version"]
    text = (clean_wiki / src[1]).read_text(encoding="utf-8")
    for _ref, start, end, chunk in rows:
        assert text[start:end] == chunk


def test_second_ingest_keeps_first_source_chunks(clean_wiki: Path) -> None:
    from gov_kernel import ingest

    r1 = ingest.ingest_file(FIXTURES / "sample.md", root=clean_wiki)
    r2 = ingest.ingest_file(FIXTURES / "sample_fa.txt", root=clean_wiki)
    assert len(_rows(clean_wiki, r1["source_ref"])[1]) == r1["chunk_count"]
    assert len(_rows(clean_wiki, r2["source_ref"])[1]) == r2["chunk_count"]


def test_ingest_succeeds_when_indexer_fails(clean_wiki: Path, monkeypatch) -> None:
    from gov_kernel import retrieval, ingest

    def boom(*a, **k):
        raise RuntimeError("index down")

    monkeypatch.setattr(retrieval, "index_derivative", boom)
    receipt = ingest.ingest_file(FIXTURES / "sample.md", root=clean_wiki)
    assert receipt["ok"] is True
    assert receipt["chunk_count"] == 0
    assert "index-failed" in receipt.get("warnings", [])
