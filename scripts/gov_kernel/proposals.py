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


def _year(ts: str) -> str:
    return ts[:4]


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def create_proposal(root: pathlib.Path, *, kind: str, body: str, submitted_by: dict[str, Any], evidence_refs: list[str] | None = None, target_refs: list[str] | None = None, proposal_id: str | None = None, received: str | None = None) -> pathlib.Path:
    received = received or _now()
    proposal_id = proposal_id or f"prop-{uuid.uuid4().hex}"
    if not _ID_SAFE.match(proposal_id):
        raise ValueError("unsafe proposal id")
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
