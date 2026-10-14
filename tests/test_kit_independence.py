"""The kit is its own product: no other project's naming in what it ships.

Record schemas must accept any instance prefix (`mw-` in the kit, the
`--prefix` of an instantiated wiki) and must not carry another wiki's name.
"""
from __future__ import annotations

import base64
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from gov_kernel.schemas import validate_record  # noqa: E402

SCHEMAS = ROOT / "00-system" / "schemas"
# Names of the owner's personal wikis, machines and people that must never
# appear in the kit. Stored encoded so this guard is not itself a trace.
FOREIGN = tuple(base64.b64decode(w).decode() for w in (
    "cmVmIHdpa2k=",
    "cmVmLXdpa2k=",
    "bW96YXJlLXdpa2k=",
    "bW96YXJlIHdpa2k=",
    "emFyaW5wYWw=",
    "bW9oYW1tYWQ=",
    "YmxhY2stYmlyZA==",
    "YmxhY2tiaXJk",
    "YmFldGVucw==",
    "cGVyc29uYWwgZm9ybWFsIGRvY3VtZW50cw==",
))


@pytest.mark.parametrize("schema", sorted(p.name for p in SCHEMAS.glob("*.json")))
def test_schema_names_no_other_project(schema: str) -> None:
    d = json.loads((SCHEMAS / schema).read_text(encoding="utf-8"))
    head = f"{d.get('$id', '')} {d.get('title', '')}".lower()
    assert not any(word in head for word in FOREIGN), (schema, head)


@pytest.mark.parametrize("prefix", ["mw", "smk", "ab12"])
def test_object_and_claim_ids_accept_any_instance_prefix(prefix: str) -> None:
    obj = {"id": f"{prefix}-obj-first-session", "type": "object",
           "title": "First session", "status": "active-record", "labels": []}
    claim = {"id": f"{prefix}-claim-turn", "type": "claim-object", "title": "Turn",
             "statement": "The session marks a turn.",
             "supporting_sources": [f"{prefix}-src-0123456789ab"],
             "unsupported_zones": [], "counter_evidence": [],
             "certainty": "candidate", "current_claim_permission": "may-note",
             "responsible_language": "en"}
    assert validate_record(obj, SCHEMAS, explicit_schema="object-record.schema.json") == []
    assert validate_record(claim, SCHEMAS) == []


def test_no_tracked_file_carries_a_personal_wiki_trace() -> None:
    """Owner decision 2026-10-13: no trace of the owner's personal wikis in
    any tracked file, history included (history is kept, names neutralised).
    The kit's GitHub account name is allowed: the repository lives under it."""
    files = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True,
                           text=True, check=True).stdout.splitlines()
    hits = []
    for rel in files:
        try:
            text = (ROOT / rel).read_text(encoding="utf-8").lower()
        except (UnicodeDecodeError, OSError):
            continue
        hits += [f"{rel}: {w}" for w in FOREIGN if w in text]
    assert hits == []
