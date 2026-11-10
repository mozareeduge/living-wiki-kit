"""Tests for C3: Chunk index in retrieval.sqlite."""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from gov_kernel.retrieval import (  # noqa: E402
    FTS5Unavailable,
    build_index,
    probe_fts5,
)


def _init_test_wiki(tmp_path: Path) -> Path:
    """Create minimal directory structure and config matching Living Wiki."""
    conf = tmp_path / "00-system" / "configuration"
    conf.mkdir(parents=True, exist_ok=True)
    profiles = {
        "profiles": {
            "all-governed": {
                "exclude_globs": [".git/**", "_search/**"],
                "include_globs": ["**/*.md", "**/*.txt"]
            },
            "canonical": {
                "exclude_globs": [],
                "include_globs": ["03-objects/**"]
            },
            "captures": {
                "exclude_globs": [],
                "include_globs": ["01-inbox/captures/**"]
            },
            "evidence-text": {
                "exclude_globs": [],
                "include_globs": ["02-sources/text/**"]
            }
        },
        "version": 2
    }
    (conf / "retrieval-profiles.v2.json").write_text(json.dumps(profiles), encoding="utf-8")
    return tmp_path


def test_build_index_creates_all_tables_on_fresh_instance(tmp_path: Path) -> None:
    wiki = _init_test_wiki(tmp_path)
    db_path = wiki / "_search" / "retrieval.sqlite"

    res = build_index(wiki, db_path)
    assert res["capability"] == "FTS5_AVAILABLE"
    assert db_path.exists()

    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        tables = {row[0] for row in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        # Check existing and new tables
        assert "docs" in tables
        assert "docs_fts" in tables
        assert "sources" in tables
        assert "chunks" in tables
        assert "chunks_fts" in tables

        # Check sources columns
        sources_cols = [c[1] for c in cur.execute("PRAGMA table_info(sources)").fetchall()]
        assert sources_cols == ["source_ref", "source_version", "path", "tier", "authority_level", "language_hint", "indexed_at"]

        # Check chunks columns
        chunks_cols = [c[1] for c in cur.execute("PRAGMA table_info(chunks)").fetchall()]
        assert chunks_cols == ["chunk_ref", "source_ref", "source_version", "start", "end", "heading_path", "text", "text_sha256"]
    finally:
        conn.close()


def test_build_index_fts5_missing_raises_exception(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    wiki = _init_test_wiki(tmp_path)
    db_path = wiki / "_search" / "retrieval.sqlite"

    import gov_kernel.retrieval as ret
    monkeypatch.setattr(ret, "probe_fts5", lambda conn: False)

    with pytest.raises(FTS5Unavailable) as exc_info:
        build_index(wiki, db_path)
    assert "FTS5_UNAVAILABLE" in str(exc_info.value)


def test_build_index_is_disposable_and_deterministic(tmp_path: Path) -> None:
    wiki = _init_test_wiki(tmp_path)
    db_path = wiki / "_search" / "retrieval.sqlite"

    # Create a source document with Persian fixture text (ZWNJ, ؟, ۔, mixed fa/en)
    src_dir = wiki / "02-sources" / "text"
    src_dir.mkdir(parents=True, exist_ok=True)
    persian_file = src_dir / "persian_source.md"
    persian_text = (
        "---\n"
        "id: mw-src-0123456789ab\n"
        "type: source-record\n"
        "title: راهنمای Living Wiki Kit\n"
        "language_hint: mixed\n"
        "updated: '2026-11-09T10:00:00Z'\n"
        "---\n"
        "# راهنمای Living Wiki Kit\n\n"
        "آیا این سیستم با دقت کار می‌کند؟ بله، تمام کتاب‌ها و نوشته‌ها ذخیره می‌شوند۔\n\n"
        "## بخش دوم\n\n"
        "این یک بخش تکمیلی با واژه‌های مختلف است.\n"
    )
    persian_file.write_text(persian_text, encoding="utf-8")

    # Run build_index pass 1
    build_index(wiki, db_path)
    conn1 = sqlite3.connect(db_path)
    try:
        docs_rows1 = conn1.execute("SELECT * FROM docs ORDER BY path").fetchall()
        sources_rows1 = conn1.execute("SELECT * FROM sources ORDER BY source_ref").fetchall()
        chunks_rows1 = conn1.execute("SELECT * FROM chunks ORDER BY chunk_ref").fetchall()
        fts_rows1 = conn1.execute("SELECT * FROM chunks_fts ORDER BY chunk_ref").fetchall()
    finally:
        conn1.close()

    assert len(sources_rows1) == 1
    assert len(chunks_rows1) >= 2

    # Delete index
    db_path.unlink()
    assert not db_path.exists()

    # Run build_index pass 2
    build_index(wiki, db_path)
    conn2 = sqlite3.connect(db_path)
    try:
        docs_rows2 = conn2.execute("SELECT * FROM docs ORDER BY path").fetchall()
        sources_rows2 = conn2.execute("SELECT * FROM sources ORDER BY source_ref").fetchall()
        chunks_rows2 = conn2.execute("SELECT * FROM chunks ORDER BY chunk_ref").fetchall()
        fts_rows2 = conn2.execute("SELECT * FROM chunks_fts ORDER BY chunk_ref").fetchall()
    finally:
        conn2.close()

    # Rebuild must yield identical rows
    assert docs_rows1 == docs_rows2
    assert sources_rows1 == sources_rows2
    assert chunks_rows1 == chunks_rows2
    assert fts_rows1 == fts_rows2

    # Verify search over chunks_fts
    conn3 = sqlite3.connect(db_path)
    try:
        from gov_kernel.normalize import normalize_persian_for_search
        # Search Persian with Arabic kaf 'كتاب‌ها' normalized to 'کتاب‌ها'
        q = normalize_persian_for_search("كتاب‌ها")
        hits = conn3.execute("SELECT chunk_ref FROM chunks_fts WHERE chunks_fts MATCH ?", (q,)).fetchall()
        assert len(hits) >= 1
    finally:
        conn3.close()
