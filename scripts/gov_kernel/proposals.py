from __future__ import annotations

import datetime as dt
import json
import pathlib
import re
import uuid
from typing import Any

from .common import atomic_write, sha256_bytes, stable_json_bytes
from .schemas import validate_record

_ID_SAFE = re.compile(r"^[A-Za-z0-9._:-]+$")

# H0 (union, 17): the fixed proposal-protocol vocabulary. Objects stay open;
# this enum constrains proposal records only, never what the world contains.
PROPOSAL_KINDS = (
    "relation-edge", "claim-amendment", "object-note", "intake-registration",
    "tier-change", "record-correction", "link-repair", "retirement-request",
    "object-create", "object-update", "relation-create", "relation-amend",
    "claim-create", "claim-amend", "lineage-link", "research-question",
    "capture-promotion",
)

# Kinds whose evidence is not a quoted canonical passage: intake carries its
# artifact; capture-promotion carries capture: refs.
PASSAGE_EXEMPT_KINDS = frozenset({"intake-registration", "capture-promotion"})

CANONICAL_ZONES = ("02-sources", "03-objects", "04-notes", "05-claims", "06-relations")

_PASSAGE_PATH_RE = re.compile(r"(?:source_passage|path)\s*[:=]\s*[\"']?([^\n\"']+\.md)")
_PASSAGE_QUOTE_RE = re.compile(r"[\"“”\"]([^\"“”\"]{20,})[\"“”\"]")


def _extract_passage(body: Any) -> dict[str, str] | None:
    """Best-effort source_passage from a proposal body (dict or prose)."""
    struct: dict[str, Any] = {}
    if isinstance(body, dict):
        struct = body
    elif isinstance(body, str):
        s = body.strip()
        if s.startswith("{"):
            try:
                v = json.loads(s)
                struct = v if isinstance(v, dict) else {}
            except json.JSONDecodeError:
                struct = {}
    sp = struct.get("source_passage")
    if isinstance(sp, dict):
        return {"path": str(sp.get("path", "")), "quote": str(sp.get("quote", ""))}
    if isinstance(body, str):
        pm = _PASSAGE_PATH_RE.search(body)
        qm = _PASSAGE_QUOTE_RE.search(body)
        if pm and qm:
            return {"path": pm.group(1).strip(), "quote": qm.group(1).strip()}
    return None


def door_errors(root: pathlib.Path, *, kind: str, body: Any,
                evidence_refs: list[str] | None = None) -> list[str]:
    """Door validation for a candidate proposal. Non-empty means refuse."""
    if kind not in PROPOSAL_KINDS:
        return [f"unknown proposal kind: {kind!r}"]
    if kind == "capture-promotion":
        refs = [str(x) for x in (evidence_refs or [])]
        if not refs or not all(r.startswith("capture:") for r in refs):
            return ["capture-promotion requires non-empty capture: evidence_refs"]
        return []
    if kind == "intake-registration":
        return []
    sp = _extract_passage(body)
    if sp is None:
        return ["source_passage missing: quote (>= 20 chars verbatim) + canonical path required"]
    quote = sp["quote"]
    path = sp["path"].strip()
    if len(quote) < 20:
        return [f"source_passage.quote too short ({len(quote)} chars, min 20)"]
    if not path:
        return ["source_passage.path missing"]
    norm = path.replace("\\", "/")
    if not norm.startswith(CANONICAL_ZONES):
        return [f"source_passage.path not canonical: {path}"]
    f = root / norm
    if not f.exists():
        return [f"source_passage.path does not exist: {path}"]
    if quote not in f.read_text(encoding="utf-8", errors="ignore"):
        return ["source_passage.quote NOT found verbatim in cited file"]
    return []


def _year(ts: str) -> str:
    return ts[:4]


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def create_proposal(root: pathlib.Path, *, kind: str, body: str, submitted_by: dict[str, Any], evidence_refs: list[str] | None = None, target_refs: list[str] | None = None, proposal_id: str | None = None, received: str | None = None) -> pathlib.Path:
    received = received or _now()
    proposal_id = proposal_id or f"prop-{uuid.uuid4().hex}"
    if not _ID_SAFE.match(proposal_id):
        raise ValueError("unsafe proposal id")
    refused = door_errors(root, kind=kind, body=body, evidence_refs=evidence_refs)
    if refused:
        raise ValueError("proposal refused at the door: " + "; ".join(refused))
    record = {
        "type": "proposal",
        "id": proposal_id,
        "received": received,
        "kind": kind,
        "authority_tier": "candidate",
        "submitted_by": submitted_by,
        "body": body,
        "body_sha256": sha256_bytes(body.encode("utf-8")),
        "evidence_refs": evidence_refs or [],
        "target_refs": target_refs or [],
    }
    findings = validate_record(record, root / "00-system/schemas", explicit_schema="proposal.schema.json")
    if findings:
        raise ValueError("; ".join(f.message for f in findings))
    path = root / "_proposals/records" / _year(received) / f"{proposal_id}.json"
    if path.exists():
        raise FileExistsError(f"proposal immutable record already exists: {path}")
    atomic_write(path, stable_json_bytes(record))
    return path


def adjudicate(root: pathlib.Path, *, proposal_id: str, decision: str, by: str, decision_note: str, applied_to: list[str] | None = None, evidence_scope: str | None = None, event_id: str | None = None, date: str | None = None) -> pathlib.Path:
    date = date or _now()
    event_id = event_id or f"adj-{uuid.uuid4().hex}"
    record = {
        "type": "adjudication",
        "id": event_id,
        "proposal_id": proposal_id,
        "decision": decision,
        "by": by,
        "date": date,
        "decision_note": decision_note,
        "applied_to": applied_to or [],
        "evidence_scope": evidence_scope,
    }
    findings = validate_record(record, root / "00-system/schemas", explicit_schema="adjudication.schema.json")
    if findings:
        raise ValueError("; ".join(f.message for f in findings))
    p = root / "_proposals/adjudications" / _year(date) / f"{proposal_id}--{event_id}.json"
    if p.exists():
        raise FileExistsError(f"adjudication immutable record already exists: {p}")
    atomic_write(p, stable_json_bytes(record))
    return p


def pending(root: pathlib.Path) -> list[dict[str, Any]]:
    proposals: dict[str, dict[str, Any]] = {}
    for p in sorted((root / "_proposals/records").rglob("*.json")) if (root / "_proposals/records").exists() else []:
        d = json.loads(p.read_text(encoding="utf-8")); proposals[str(d["id"])] = d
    terminal: set[str] = set()
    for p in sorted((root / "_proposals/adjudications").rglob("*.json")) if (root / "_proposals/adjudications").exists() else []:
        d = json.loads(p.read_text(encoding="utf-8"))
        if d.get("decision") in {"accepted", "rejected"}:
            terminal.add(str(d.get("proposal_id")))
    return [proposals[k] for k in sorted(proposals) if k not in terminal]
