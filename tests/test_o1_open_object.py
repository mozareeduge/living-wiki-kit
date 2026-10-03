"""O1: open object schema (dossier §27-28).

- kind leaves required; enum removed (optional deprecated string);
- labels[] added with mechanical rules only (non-empty, <=120 chars,
  unique, no newlines); unfamiliar labels always valid;
- TEMPLATE_object.md carries labels: [], not kind.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from gov_kernel.schemas import validate_record  # noqa: E402

SCHEMAS = ROOT / "00-system" / "schemas"


def _obj(**kw) -> dict:
    rec = {"id": "ref-obj-1", "type": "object", "title": "A thing",
           "status": "active-record"}
    rec.update(kw)
    return rec


def _findings(rec: dict) -> list[str]:
    return [f.message for f in validate_record(rec, SCHEMAS,
                                               explicit_schema="object-record.schema.json")]


def test_kindless_object_validates() -> None:
    assert _findings(_obj()) == []


def test_legacy_kind_still_validates() -> None:
    assert _findings(_obj(kind="person")) == []


def test_multiple_labels_validate() -> None:
    assert _findings(_obj(labels=["rehearsal", "phase/rehearsal"])) == []


def test_unfamiliar_label_is_not_rejected() -> None:
    assert _findings(_obj(labels=["quux-neologism-xyz"])) == []


def test_unicode_label_validates() -> None:
    assert _findings(_obj(labels=["تئاتر"])) == []


def test_exact_duplicate_labels_fail() -> None:
    assert _findings(_obj(labels=["rehearsal", "rehearsal"])) != []


def test_empty_label_fails() -> None:
    assert _findings(_obj(labels=[""])) != []


def test_overlong_label_fails() -> None:
    assert _findings(_obj(labels=["x" * 121])) != []


def test_template_carries_labels_not_kind() -> None:
    text = (ROOT / "00-system" / "templates" / "TEMPLATE_object.md").read_text(encoding="utf-8")
    assert "labels: []" in text
    assert "kind:" not in text
