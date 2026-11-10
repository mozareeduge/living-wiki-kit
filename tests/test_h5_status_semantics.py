"""Tests for H5: Status semantics fix (scripts/gov_kernel/retrieval.py)."""
from __future__ import annotations

import json
import sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from gov_kernel.retrieval import (  # noqa: E402
    build_index,
    index_status,
    wiki_status,
)


def _init_test_wiki(tmp_path: Path) -> Path:
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


def test_fresh_instance_empty_corpus_not_degraded(tmp_path: Path) -> None:
    wiki = _init_test_wiki(tmp_path)
    db_path = wiki / "_search" / "retrieval.sqlite"

    # 1. No database exists and no documents exist
    res = index_status(wiki, db_path)
    assert res["status"] == "empty"
    assert res["degraded"] is False
    assert res["reasons"] == []

    w_stat = wiki_status(wiki, db_path)
    assert w_stat["degraded"] is False
    assert w_stat["search_index"]["status"] == "empty"

    # 2. Database built on empty corpus
    build_index(wiki, db_path)
    res2 = index_status(wiki, db_path)
    assert res2["status"] == "empty"
    assert res2["degraded"] is False
    assert res2["reasons"] == []


def test_missing_index_when_corpus_has_documents(tmp_path: Path) -> None:
    wiki = _init_test_wiki(tmp_path)
    db_path = wiki / "_search" / "retrieval.sqlite"

    src_dir = wiki / "02-sources" / "text"
    src_dir.mkdir(parents=True, exist_ok=True)
    (src_dir / "doc1.md").write_text("# Doc 1\n\nContent", encoding="utf-8")

    res = index_status(wiki, db_path)
    assert res["status"] == "missing"
    assert res["degraded"] is True
    assert len(res["reasons"]) > 0

    w_stat = wiki_status(wiki, db_path)
    assert w_stat["degraded"] is True
    assert w_stat["search_index"]["status"] == "missing"


def test_after_ingest_without_rebuild_is_stale_and_degraded(tmp_path: Path) -> None:
    wiki = _init_test_wiki(tmp_path)
    db_path = wiki / "_search" / "retrieval.sqlite"

    src_dir = wiki / "02-sources" / "text"
    src_dir.mkdir(parents=True, exist_ok=True)
    doc1 = src_dir / "doc1.md"
    doc1.write_text("# Doc 1\n\nInitial content", encoding="utf-8")

    # Build initial index
    build_index(wiki, db_path)
    fresh_stat = index_status(wiki, db_path)
    assert fresh_stat["status"] == "fresh"
    assert fresh_stat["degraded"] is False

    # Ingest a new Persian document (containing ZWNJ, ؟, ۔, mixed fa/en) without rebuild
    persian_doc = src_dir / "persian_ingested.md"
    persian_text = (
        "---\n"
        "id: mw-src-9999999999ab\n"
        "type: source-record\n"
        "title: مستند ورودی جدید Living Wiki Kit\n"
        "language_hint: mixed\n"
        "---\n"
        "# مستند ورودی\n\n"
        "آیا این فایل جدید پس از ورود به سامانه ذخیره می‌شود؟ بله، اضافه شد۔\n"
    )
    persian_doc.write_text(persian_text, encoding="utf-8")

    # Check status without rebuilding index -> must be stale and degraded
    stale_stat = index_status(wiki, db_path)
    assert stale_stat["status"] == "stale"
    assert stale_stat["degraded"] is True
    assert any("stale" in r for r in stale_stat["reasons"])

    w_stat = wiki_status(wiki, db_path)
    assert w_stat["degraded"] is True
    assert w_stat["search_index"]["status"] == "stale"

    # Now rebuild index -> must become fresh and not degraded
    build_index(wiki, db_path)
    rebuilt_stat = index_status(wiki, db_path)
    assert rebuilt_stat["status"] == "fresh"
    assert rebuilt_stat["degraded"] is False

    # Modify doc1 without rebuild -> must become stale and degraded
    doc1.write_text("# Doc 1\n\nModified content that alters sha256", encoding="utf-8")
    mod_stat = index_status(wiki, db_path)
    assert mod_stat["status"] == "stale"
    assert mod_stat["degraded"] is True
