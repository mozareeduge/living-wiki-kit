"""Tests for C1: Retrieval model policy + chunk schema."""
from __future__ import annotations

import json
from pathlib import Path
import pytest
import jsonschema

ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = ROOT / "00-system" / "schemas"
POLICIES = ROOT / "00-system" / "policies"
SCHEMA_PATH = SCHEMAS / "chunk.schema.json"
POLICY_PATH = POLICIES / "RETRIEVAL_MODEL.md"
SYSTEM_DESIGN_PATH = ROOT / "SYSTEM_DESIGN.md"


def test_retrieval_model_policy_exists_and_contains_vocabulary() -> None:
    assert POLICY_PATH.is_file(), f"Policy missing at {POLICY_PATH}"
    content = POLICY_PATH.read_text(encoding="utf-8")
    required_terms = [
        "source",
        "source_version",
        "chunk",
        "span",
        "chunk_ref",
        "stale ref",
        "inclusion_reason",
        "receipt",
        "E_STALE_SOURCE",
    ]
    for term in required_terms:
        assert term in content, f"Term {term!r} missing from {POLICY_PATH}"


def test_system_design_links_retrieval_model_policy() -> None:
    assert SYSTEM_DESIGN_PATH.is_file()
    content = SYSTEM_DESIGN_PATH.read_text(encoding="utf-8")
    assert "00-system/policies/RETRIEVAL_MODEL.md" in content, (
        "SYSTEM_DESIGN.md must link 00-system/policies/RETRIEVAL_MODEL.md"
    )


def test_chunk_schema_exists_and_is_valid_json_schema() -> None:
    assert SCHEMA_PATH.is_file(), f"Schema missing at {SCHEMA_PATH}"
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator.check_schema(schema)


def test_chunk_schema_validates_fixtures() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = jsonschema.Draft202012Validator(schema)

    valid_chunk = {
        "chunk_ref": "chk:0123456789abcdef0123456789abcdef",
        "source_ref": "rec:mw-src-0123456789ab",
        "source_version": "a" * 64,
        "span": {"start": 0, "end": 45},
        "text_sha256": "b" * 64,
        "heading_path": ["Chapter 1", "Introduction"],
        "language_hint": "en",
        "char_len": 45,
        "text": "This is an introductory chunk of valid text.",
    }
    assert list(validator.iter_errors(valid_chunk)) == []

    # Persian fixture with mixed fa/en text, a ZWNJ (\u200c), and end marks ؟ (\u061f) and ۔ (\u06d4)
    persian_text = "متن آزمایشی Living Wiki Kit با نیم‌فاصله ذخیره می‌شود؟ بله، نسخه جدید منتشر شد۔"
    persian_chunk = {
        "chunk_ref": "chk:fedcba9876543210fedcba9876543210",
        "source_ref": "rec:mw-src-abcdef012345",
        "source_version": "c" * 64,
        "span": {"start": 100, "end": 100 + len(persian_text)},
        "text_sha256": "d" * 64,
        "heading_path": ["بخش ۱", "معرفی"],
        "language_hint": "mixed",
        "char_len": len(persian_text),
        "text": persian_text,
    }
    assert "\u200c" in persian_text, "Persian fixture must contain ZWNJ"
    assert "؟" in persian_text, "Persian fixture must contain Persian question mark"
    assert "۔" in persian_text, "Persian fixture must contain Arabic/Urdu full stop"
    assert "Living Wiki Kit" in persian_text, "Persian fixture must contain mixed fa/en text"
    assert list(validator.iter_errors(persian_chunk)) == []


def test_chunk_schema_rejects_invalid_records() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = jsonschema.Draft202012Validator(schema)

    # Missing required field chunk_ref
    bad_missing = {
        "source_ref": "rec:mw-src-0123456789ab",
        "source_version": "a" * 64,
        "span": {"start": 0, "end": 10},
        "text_sha256": "b" * 64,
        "heading_path": [],
        "language_hint": "en",
        "char_len": 10,
    }
    assert len(list(validator.iter_errors(bad_missing))) > 0

    # Bad chunk_ref format (must be chk: + 32 hex)
    bad_ref = dict(bad_missing, chunk_ref="bad:ref123")
    assert len(list(validator.iter_errors(bad_ref))) > 0

    # Bad source_version (must be 64 hex)
    bad_version = dict(bad_missing, chunk_ref="chk:0123456789abcdef0123456789abcdef", source_version="short")
    assert len(list(validator.iter_errors(bad_version))) > 0

    # Bad span (negative start)
    bad_span = dict(bad_missing, chunk_ref="chk:0123456789abcdef0123456789abcdef", span={"start": -1, "end": 10})
    assert len(list(validator.iter_errors(bad_span))) > 0
