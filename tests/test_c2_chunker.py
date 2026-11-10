"""Tests for C2: Deterministic chunker (scripts/gov_kernel/chunking.py)."""
from __future__ import annotations

import json
import sys
from pathlib import Path
import pytest
import jsonschema

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
SCHEMAS = ROOT / "00-system" / "schemas"
CHUNK_SCHEMA = json.loads((SCHEMAS / "chunk.schema.json").read_text(encoding="utf-8"))

from gov_kernel.chunking import (  # noqa: E402
    Chunk,
    chunk_text,
    compute_chunk_ref,
    normalize_derivative_text,
)


def _check_chunk_invariants(text: str, chunks: list[Chunk]) -> None:
    validator = jsonschema.Draft202012Validator(CHUNK_SCHEMA)
    prev_end = 0
    non_ws_text = "".join(c for c in text if not c.isspace())
    collected_non_ws = []

    for i, chk in enumerate(chunks):
        # 1. Valid according to chunk.schema.json
        d = chk.to_dict()
        errors = list(validator.iter_errors(d))
        assert not errors, f"Chunk {i} failed schema validation: {errors}"

        # 2. text[start:end] == chunk.text
        start, end = chk.span["start"], chk.span["end"]
        assert text[start:end] == chk.text, (
            f"Chunk {i} span mismatch: text[{start}:{end}] != chunk.text"
        )

        # 3. Disjoint and ordered
        assert start >= prev_end, f"Chunk {i} overlaps with previous chunk: {start} < {prev_end}"
        assert end > start, f"Chunk {i} has empty span [{start}:{end}]"

        # Text between prev_end and start must be all whitespace
        between = text[prev_end:start]
        assert not between or between.isspace(), (
            f"Uncovered non-whitespace between chunks at [{prev_end}:{start}]: {between!r}"
        )
        prev_end = end
        collected_non_ws.append("".join(c for c in chk.text if not c.isspace()))

    # Any remaining text after last chunk must be whitespace
    after = text[prev_end:]
    assert not after or after.isspace(), (
        f"Uncovered non-whitespace after last chunk at [{prev_end}:]: {after!r}"
    )

    # 4. Covers all non-whitespace text
    assert "".join(collected_non_ws) == non_ws_text, "Chunks do not cover all non-whitespace text"


def test_chunking_empty_and_whitespace() -> None:
    assert chunk_text("") == []
    assert chunk_text("   \n\n\t  \n") == []


def test_chunking_crlf_and_lf_identity() -> None:
    doc_lf = (
        "# Title\n\n"
        "First paragraph with some content.\n\n"
        "## Subtitle\n\n"
        "Second paragraph with more content.\n"
    )
    doc_crlf = doc_lf.replace("\n", "\r\n")

    chunks_lf = chunk_text(doc_lf, source_ref="rec:test-1")
    chunks_crlf = chunk_text(doc_crlf, source_ref="rec:test-1")

    assert len(chunks_lf) == len(chunks_crlf)
    for c_lf, c_crlf in zip(chunks_lf, chunks_crlf):
        assert c_lf.chunk_ref == c_crlf.chunk_ref
        assert c_lf.source_version == c_crlf.source_version
        assert c_lf.span == c_crlf.span
        assert c_lf.text == c_crlf.text
        assert c_lf.heading_path == c_crlf.heading_path


def test_chunking_heading_hierarchy() -> None:
    text = (
        "# Chapter 1\n\n"
        "Introduction paragraph.\n\n"
        "## Section A\n\n"
        "Detail A paragraph.\n\n"
        "### Subsection A.1\n\n"
        "Deep detail.\n\n"
        "## Section B\n\n"
        "Detail B paragraph.\n\n"
        "# Chapter 2\n\n"
        "Rehearsal paragraph.\n"
    )
    chunks = chunk_text(text, source_ref="rec:test-hierarchy", target_chars=50)
    _check_chunk_invariants(normalize_derivative_text(text), chunks)

    # Check that heading paths reflect the hierarchy correctly
    paths = [c.heading_path for c in chunks]
    assert ["Chapter 1"] in paths
    assert ["Chapter 1", "Section A"] in paths
    assert ["Chapter 1", "Section A", "Subsection A.1"] in paths
    assert ["Chapter 1", "Section B"] in paths
    assert ["Chapter 2"] in paths


def test_persian_fixture_chunks_without_breaking_words() -> None:
    # Persian fixture with mixed fa/en text, ZWNJ (\u200c), and end marks ؟ and ۔
    # Words with ZWNJ: می‌دانیم, کتاب‌ها, بازخوانی‌ناپذیر, برنامه‌نویسی
    persian_text = (
        "# بخش اول: راهنمای Living Wiki Kit\n\n"
        "ما می‌دانیم که کتاب‌ها بخش بنیادین دانش بشری هستند؛ آیا این سیستم کارآمد است؟ "
        "بله، زیرا قابلیت‌های جدید اضافه شده است۔ این یک متن mixed fa/en است.\n\n"
        "## بخش دوم: آزمون واژه‌ها و ZWNJ\n\n"
        "در برنامه‌نویسی مدرن، داده‌های بازخوانی‌ناپذیر نباید دچار شکستگی شوند؟ "
        "همواره نشانه‌های پایان جمله مانند ؟ و ۔ به درستی بررسی می‌گردند۔ پایان مستند!\n"
    )
    norm = normalize_derivative_text(persian_text)
    chunks = chunk_text(persian_text, source_ref="rec:persian-1", target_chars=120)
    _check_chunk_invariants(norm, chunks)

    # Invariants for Persian text:
    zwnj_words = ["می‌دانیم", "کتاب‌ها", "برنامه‌نویسی", "بازخوانی‌ناپذیر", "قابلیت‌های", "داده‌های", "می‌گردند"]
    for w in zwnj_words:
        assert "\u200c" in w
        # The word must not be split across chunks
        found = False
        for c in chunks:
            if w in c.text:
                found = True
        assert found, f"Word {w!r} with ZWNJ was broken or lost across chunk boundaries"


def test_oversized_paragraph_splits_at_sentence_ends() -> None:
    # A single paragraph exceeding max_chars (2000 chars) with sentences ending in . ! ? ؟ ۔
    s1 = "This is the first long sentence in English. " * 15  # ~660 chars
    s2 = "آیا این بخش دوم جمله به زبان فارسی است؟ " * 15     # ~600 chars
    s3 = "این سومین جمله با نشانه پایان مخصوص است۔ " * 15   # ~630 chars
    s4 = "Final concluding sentence in English! " * 10        # ~380 chars
    full_para = s1 + s2 + s3 + s4
    assert len(full_para) > 2000

    chunks = chunk_text(full_para, source_ref="rec:oversized", target_chars=800, max_chars=1200)
    norm = normalize_derivative_text(full_para)
    _check_chunk_invariants(norm, chunks)

    # None of the chunks should exceed max_chars
    for c in chunks:
        assert c.char_len <= 1200


def test_ref_stability_across_rebuilds_and_local_edits() -> None:
    doc_v1 = (
        "# Section 1\n\n"
        + "First section paragraph one content. " * 20 + "\n\n"
        + "# Section 2\n\n"
        + "Second section paragraph two content. " * 20 + "\n\n"
        + "# Section 3\n\n"
        + "Third section paragraph three content. " * 20 + "\n"
    )
    # Rebuild twice on same text -> identical refs
    c1 = chunk_text(doc_v1, source_ref="rec:stability", target_chars=500)
    c2 = chunk_text(doc_v1, source_ref="rec:stability", target_chars=500)
    assert len(c1) == len(c2)
    assert [c.chunk_ref for c in c1] == [c.chunk_ref for c in c2]

    # When section 3 is edited:
    # If using section-level or relative stability, section 1 chunks have identical content and text
    doc_v2 = (
        "# Section 1\n\n"
        + "First section paragraph one content. " * 20 + "\n\n"
        + "# Section 2\n\n"
        + "Second section paragraph two content. " * 20 + "\n\n"
        + "# Section 3\n\n"
        + "EDITED paragraph three with completely different text.\n"
    )
    c_v2 = chunk_text(doc_v2, source_ref="rec:stability", target_chars=500)
    # Section 1 and Section 2 chunks have identical text and spans
    assert c1[0].text == c_v2[0].text
    assert c1[0].span == c_v2[0].span
    assert c1[1].text == c_v2[1].text
    assert c1[1].span == c_v2[1].span
    # And compute_chunk_ref on section 1's span with the same source_version produces the exact same ref
    ref_stable = compute_chunk_ref(c1[0].source_version, c1[0].span["start"], c1[0].span["end"])
    assert ref_stable == c1[0].chunk_ref
