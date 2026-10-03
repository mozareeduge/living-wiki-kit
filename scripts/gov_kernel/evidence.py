from __future__ import annotations

import json
import pathlib
import re
from typing import Any

from .common import jsonl_bytes, sha256_bytes, sha256_file
from .findings import Finding
from .frontmatter import load_markdown_frontmatter
from .provenance import ProvenanceResult
from .schemas import validate_record

PROMOTED_EVENT_RE = re.compile(r"(?m)^-\s*([^|\n]+)\|\s*state:promoted\s*\|.*?(?:actor:([^|\n]+))?\s*$")


def evidence_snapshot(rows: list[dict[str, Any]]) -> tuple[str, str]:
    payload = "".join(f"{row['evidence_id']}:{row['content_sha256']}\n" for row in sorted(rows, key=lambda r: str(r["evidence_id"]))).encode("utf-8")
    digest = sha256_bytes(payload)
    return f"mw-evidence-{digest[:12]}", digest


def _accepted_adjudications(root: pathlib.Path) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    base = root / "_proposals/adjudications"
    if not base.exists():
        return out
    for p in sorted(base.rglob("*.json")):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        if data.get("decision") == "accepted" and data.get("proposal_id"):
            out[str(data["proposal_id"])] = data
    return out


def _capture_rows(root: pathlib.Path, patterns: list[str], findings: list[Finding]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen_paths: set[str] = set()
    for pattern in patterns:
        for p in sorted(root.glob(pattern)):
            if not p.is_file() or p.suffix.lower() != ".md":
                continue
            rel = str(p.relative_to(root)).replace("\\", "/")
            if rel in seen_paths:
                continue
            seen_paths.add(rel)
            try:
                rec, body = load_markdown_frontmatter(p)
            except Exception as exc:
                findings.append(Finding("EVIDENCE.CAPTURE_PARSE_FAILURE", "error", str(exc), rel, waivable=False))
                continue
            if rec.get("type") != "capture" or rec.get("status") != "promoted":
                continue
            cid = str(rec.get("id") or "")
            sha = str(rec.get("sha256") or "")
            promoted_to = rec.get("promoted_to")
            m = PROMOTED_EVENT_RE.search(body)
            if not cid or not re.fullmatch(r"[0-9a-f]{64}", sha) or not promoted_to or not m:
                findings.append(Finding(
                    "EVIDENCE.INVALID_PROMOTION",
                    "error",
                    "promoted capture lacks resolvable id/hash/promoted_to/provenance state:promoted event",
                    rel,
                    cid or None,
                    False,
                ))
                continue
            accepted_at = m.group(1).strip() or None
            actor = (m.group(2) or "").strip()
            authority_level = 3 if actor.casefold().startswith("mohammad") else 6
            row = {
                "type": "accepted-evidence-row",
                "evidence_id": f"capture:{cid}",
                "kind": "author-capture" if authority_level == 3 else "promoted-capture",
                "record_path": rel,
                "content_sha256": sha,
                "authority_level": authority_level,
                "authority_scope": "promoted capture; scope limited to the reviewed capture record and its explicit promoted target",
                "status": "accepted",
                "accepted_at": accepted_at,
                "acceptance_event": f"capture-promotion:{cid}",
                "promoted_to": promoted_to,
            }
            findings.extend(validate_record(row, root / "00-system/schemas", path=rel, explicit_schema="accepted-evidence-row.schema.json"))
            rows.append(row)
    return rows


def build_accepted_evidence(root: pathlib.Path, provenance: ProvenanceResult) -> tuple[list[dict[str, Any]], dict[str, Any], list[Finding]]:
    schema_dir = root / "00-system/schemas"
    findings: list[Finding] = []
    rows: list[dict[str, Any]] = []

    for src in provenance.rows:
        rows.append({
            "type": "accepted-evidence-row",
            "evidence_id": f"source:{src['id']}",
            "kind": "source-artifact",
            "record_path": src["source_record_path"],
            "content_sha256": src["sha256"],
            "authority_level": 1,
            "authority_scope": src.get("authority_scope") or "source-artifact",
            "status": "accepted",
            "accepted_at": None,
            "acceptance_event": f"source-record:{src['id']}",
        })

    cfg_path = root / "00-system/configuration/evidence-sources.json"
    cfg = json.loads(cfg_path.read_text(encoding="utf-8")) if cfg_path.exists() else {}
    rows.extend(_capture_rows(root, list(cfg.get("promoted_capture_globs", [])), findings))

    accepted_adjs = _accepted_adjudications(root)
    for pattern in cfg.get("accepted_record_globs", []):
        for p in sorted(root.glob(pattern)):
            if not p.is_file():
                continue
            rel = str(p.relative_to(root)).replace("\\", "/")
            try:
                if p.suffix.lower() == ".md":
                    rec, body = load_markdown_frontmatter(p)
                    content_sha = sha256_bytes(body.encode("utf-8"))
                else:
                    rec = json.loads(p.read_text(encoding="utf-8"))
                    content_sha = sha256_file(p)
            except Exception as exc:
                findings.append(Finding("EVIDENCE.RECORD_PARSE_FAILURE", "error", str(exc), rel, waivable=False))
                continue
            event = rec.get("acceptance_event") or rec.get("proposal_id")
            if isinstance(event, str) and event.startswith("prop-") and event not in accepted_adjs:
                findings.append(Finding("EVIDENCE.INVALID_PROMOTION", "error", "promotion references proposal without accepted adjudication", rel, str(rec.get("id") or ""), False, {"proposal_id": event}))
                continue
            row = {
                "type": "accepted-evidence-row",
                "evidence_id": str(rec.get("evidence_id") or rec.get("id") or rel),
                "kind": str(rec.get("kind") or "author-capture"),
                "record_path": rel,
                "content_sha256": str(rec.get("content_sha256") or content_sha),
                "authority_level": int(rec.get("authority_level", 1)),
                "authority_scope": rec.get("authority_scope"),
                "status": "accepted",
                "accepted_at": rec.get("accepted_at"),
                "acceptance_event": rec.get("acceptance_event") or event,
            }
            findings.extend(validate_record(row, schema_dir, path=rel, explicit_schema="accepted-evidence-row.schema.json"))
            rows.append(row)

    ids: set[str] = set()
    unique: list[dict[str, Any]] = []
    for row in sorted(rows, key=lambda r: str(r["evidence_id"])):
        if row["evidence_id"] in ids:
            findings.append(Finding("EVIDENCE.DUPLICATE_ID", "error", f"duplicate evidence id {row['evidence_id']}", row["record_path"], row["evidence_id"], False))
            continue
        ids.add(row["evidence_id"]); unique.append(row)
    sid, sha = evidence_snapshot(unique)
    state = {"snapshot_id": sid, "snapshot_sha256": sha, "evidence_object_count": len(unique), "manifest_sha256": sha256_bytes(jsonl_bytes(unique))}
    return unique, state, findings


def expected_evidence_bytes(rows: list[dict[str, Any]]) -> bytes:
    return jsonl_bytes(rows)
