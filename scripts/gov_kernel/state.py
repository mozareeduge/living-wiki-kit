from __future__ import annotations

import copy
import json
import pathlib
from typing import Any

from .common import stable_json_bytes
from .evidence import build_accepted_evidence
from .provenance import build_provenance, expected_generated_bytes
from .schemas import validate_record

DERIVED_KEYS = {"source_corpus", "accepted_evidence"}


def load_state(root: pathlib.Path) -> dict[str, Any]:
    p = root / "00-system/registers/SYSTEM_STATE.json"
    if not p.exists():
        raise FileNotFoundError(f"SYSTEM_STATE missing: {p}; initialize authored axes before cutover")
    return json.loads(p.read_text(encoding="utf-8"))


def rebuild_state(root: pathlib.Path) -> tuple[dict[str, Any], list[Any]]:
    current = load_state(root)
    provenance = build_provenance(root)
    erows, estate, efindings = build_accepted_evidence(root, provenance)
    new = copy.deepcopy(current)
    new["type"] = "system-state"
    manifest_bytes = expected_generated_bytes(provenance)["00-system/registers/MATERIALS_INDEX.jsonl"]
    from .common import sha256_bytes
    new["source_corpus"] = {
        "snapshot_id": provenance.corpus_state.get("id"),
        "snapshot_sha256": provenance.corpus_state.get("corpus_snapshot_sha256"),
        "source_material_count": provenance.corpus_state.get("source_material_count", 0),
        "registered_words": provenance.corpus_state.get("total_extracted_words", 0),
        "manifest_sha256": sha256_bytes(manifest_bytes),
    }
    new["accepted_evidence"] = estate
    findings = [*provenance.findings, *efindings]
    findings.extend(validate_record(new, root / "00-system/schemas", explicit_schema="system-state.schema.json"))
    return new, findings


def set_axis(root: pathlib.Path, dotted_axis: str, value: Any) -> dict[str, Any]:
    """Update an authored state axis through explicit configured transitions.

    The seed refuses unknown transitions rather than guessing repository policy.
    """
    transitions_path = root / "00-system/configuration/state-transitions.json"
    if not transitions_path.exists():
        raise RuntimeError("missing state-transitions.json; map AP-STATE-AXES before using set-axis")
    transitions = json.loads(transitions_path.read_text(encoding="utf-8"))
    if dotted_axis not in transitions:
        raise ValueError(f"axis not configured: {dotted_axis}")
    state = load_state(root)
    keys = dotted_axis.split(".")
    if keys[0] in DERIVED_KEYS:
        raise ValueError(f"derived axis cannot be authored: {dotted_axis}")
    node = state
    for k in keys[:-1]:
        node = node[k]
    old = node.get(keys[-1])
    allowed = transitions[dotted_axis].get(str(old), [])
    if value not in allowed:
        raise ValueError(f"transition not allowed for {dotted_axis}: {old!r} -> {value!r}")
    node[keys[-1]] = value
    findings = validate_record(state, root / "00-system/schemas", explicit_schema="system-state.schema.json")
    if findings:
        raise ValueError("; ".join(f.message for f in findings))
    return state


def state_bytes(state: dict[str, Any]) -> bytes:
    return stable_json_bytes(state)
