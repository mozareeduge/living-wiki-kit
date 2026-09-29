#!/usr/bin/env python3
"""Evidence audit for the candidate layer (Phase 3).

Reads _proposals/proposals.jsonl, validates every record against
00-system/policies/proposal_schema.json, and AUTO-REJECTS any proposal
whose required evidence is missing or unverifiable:
  - source_passage.quote must be >= 20 chars
  - source_passage.path must exist and be inside a canonical zone
  - intake-registration: original_path must exist; sha256 must be 64-hex
  - tier-change.to_tier must be an allowed tier

Writes ONLY an audit report to _audits/ (never mutates the queue, never
touches canonical zones - the human adjudicates from the report).
Retrieval/search scores are never evidence; a passage that cannot be
found verbatim in the cited file fails even if a score is high.

Usage: python scripts/evidence_audit.py [--root WIKI_ROOT] [--verbose]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from pathlib import Path

SCHEMA_REL = Path("00-system/policies/proposal_schema.json")
QUEUE_REL = Path("_proposals/proposals.jsonl")
RECORDS_REL = Path("_proposals/records")
ADJUDICATIONS_REL = Path("_proposals/adjudications")
CANONICAL_ZONES = ("02-sources", "03-objects", "04-notes", "05-claims", "06-relations")
SHA256_RE = re.compile(r"\b[0-9a-f]{64}\b", re.IGNORECASE)
TERMINAL_DECISIONS = {"accepted", "rejected"}


def _load_proposals(root: Path) -> list[dict]:
    p = root / QUEUE_REL
    if not p.exists():
        return []
    out = []
    for line in p.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if line:
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                out.append({"id": None, "kind": None, "body": line,
                            "received": None, "status": "new",
                            "_malformed": True})
    return out


def _load_durable(root: Path) -> tuple[list[dict], dict[str, str]]:
    """Durable kernel proposals (_proposals/records/) + terminal adjudications.

    Legacy proposals.jsonl stays read-only history; the durable queue is the
    live one. Returns (records, {proposal_id: terminal decision}).
    """
    records: list[dict] = []
    rec_dir = root / RECORDS_REL
    if rec_dir.exists():
        for p in sorted(rec_dir.rglob("*.json")):
            try:
                records.append(json.loads(p.read_text(encoding="utf-8")))
            except json.JSONDecodeError:
                records.append({"id": None, "kind": None, "body": p.read_text(),
                                "received": None, "status": "new",
                                "_malformed": True})
    terminal: dict[str, str] = {}
    adj_dir = root / ADJUDICATIONS_REL
    if adj_dir.exists():
        for p in sorted(adj_dir.rglob("*.json")):
            try:
                d = json.loads(p.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            if d.get("decision") in TERMINAL_DECISIONS and d.get("proposal_id"):
                terminal[str(d["proposal_id"])] = str(d["decision"])
    return records, terminal


def _body_struct(body) -> dict | None:
    if isinstance(body, dict):
        return body
    if isinstance(body, str):
        s = body.strip()
        if s.startswith("{"):
            try:
                v = json.loads(s)
                return v if isinstance(v, dict) else None
            except json.JSONDecodeError:
                return None
    return None


def _extract_passage_from_prose(body: str) -> dict | None:
    """Free-prose fallback: find quote/path evidence markers in text."""
    pm = re.search(r'(?:source_passage|path)\s*[:=]\s*["\']?([^\n"\']+\.md)', body)
    qm = re.search(r'[""\"]([^""\"]{20,})[""\"]', body)
    if pm and qm:
        return {"path": pm.group(1).strip(), "quote": qm.group(1).strip()}
    return None


def _check_passage(root: Path, sp: dict) -> list[str]:
    errs: list[str] = []
    quote = str(sp.get("quote", ""))
    path = str(sp.get("path", "")).strip()
    if len(quote) < 20:
        errs.append(f"source_passage.quote too short ({len(quote)} chars, min 20)")
    if not path:
        errs.append("source_passage.path missing")
        return errs
    norm = path.replace("\\", "/")
    if not norm.startswith(CANONICAL_ZONES):
        errs.append(f"source_passage.path not canonical: {path}")
    f = root / norm
    if not f.exists():
        errs.append(f"source_passage.path does not exist: {path}")
    elif quote and quote not in f.read_text(encoding="utf-8", errors="ignore"):
        errs.append("source_passage.quote NOT found verbatim in cited file")
    return errs


def assess_proposals(root: Path, proposals: list[dict],
                     terminal: dict[str, str]) -> tuple[list[dict], int, int, int]:
    """Pure per-record audit (no I/O besides reading cited files).

    Returns (results, accepted, rejected, skipped). audit() writes the
    report; candidate_projection.py reuses the verdicts without writing.
    """
    schema = json.loads((root / SCHEMA_REL).read_text(encoding="utf-8-sig"))
    kinds = schema["kinds"]
    results: list[dict] = []
    accepted = rejected = skipped = 0
    for rec in proposals:
        pid = rec.get("id") or f"unparsed-line-{len(results)+1}"
        errs: list[str] = []
        if rec.get("_malformed"):
            errs.append("unparseable JSONL line")
        kind = rec.get("kind")
        if not rec.get("_malformed"):
            if not kind or kind not in kinds:
                errs.append(f"unknown kind: {kind!r}")
            if rec.get("authority_tier") != "candidate":
                errs.append(f"authority_tier must be 'candidate', got {rec.get('authority_tier')!r}")
            struct = _body_struct(rec.get("body")) or {}
            if not struct and isinstance(rec.get("body"), str):
                struct = _extract_passage_from_prose(rec.get("body", "")) or {}
            if kind in kinds:
                missing = [f for f in kinds[kind]["required"] if f not in struct
                           and f != "source_passage"
                           and not (f == "capture_refs" and rec.get("evidence_refs"))]
                if missing:
                    errs.append(f"missing body fields: {missing}")
                sp = struct.get("source_passage")
                if "source_passage" in kinds[kind]["required"]:
                    if isinstance(sp, dict):
                        errs += _check_passage(root, sp)
                    elif isinstance(sp, str):
                        errs += _check_passage(root, {"path": sp, "quote": ""})
                    else:
                        errs.append("source_passage missing (auto-reject per schema)")
                if kind == "intake-registration":
                    op = root / str(struct.get("original_path", ""))
                    if not op.exists():
                        errs.append(f"original_path does not exist: {struct.get('original_path')}")
                    if not SHA256_RE.search(str(struct.get("sha256", ""))):
                        errs.append("sha256 not 64-hex")
                if kind == "tier-change":
                    allowed = kinds[kind].get("to_tier_enum", [])
                    if struct.get("to_tier") not in allowed:
                        errs.append(f"to_tier {struct.get('to_tier')!r} not in {allowed}")
                if kind == "capture-promotion":
                    refs = list(rec.get("evidence_refs") or []) or struct.get("capture_ids") or []
                    if not refs or not all(str(r).startswith("capture:") for r in refs):
                        errs.append("capture_refs missing: capture-promotion needs capture: evidence_refs")
        verdict = "rejected-audit" if errs else "audited"
        if errs:
            rejected += 1
        elif pid in terminal:
            skipped += 1
            verdict = f"skipped (adjudicated: {terminal[pid]})"
        elif rec.get("status") not in (None, "new"):
            skipped += 1
            verdict = f"skipped (status={rec.get('status')})"
        else:
            accepted += 1
        results.append({"id": pid, "kind": kind, "verdict": verdict,
                        "errors": errs})
    return results, accepted, rejected, skipped


def audit(root: Path, verbose: bool = False) -> tuple[int, int, int]:
    schema = json.loads((root / SCHEMA_REL).read_text(encoding="utf-8-sig"))
    proposals = _load_proposals(root)
    durable, terminal = _load_durable(root)
    proposals = proposals + durable

    results, accepted, rejected, skipped = assess_proposals(root, proposals, terminal)

    report = {
        "generated_by": "evidence_audit.py",
        "generated_at_epoch": int(time.time()),
        "schema_version": schema.get("version"),
        "totals": {"audited": accepted, "rejected-audit": rejected,
                   "skipped": skipped, "total": len(proposals)},
        "authority_note": ("Audit is deterministic tooling; its verdicts are "
                            "advisory to the human adjudicator. Durable proposals stay "
                            "inert in _proposals/records/; legacy proposals.jsonl is "
                            "read-only history."),
        "results": results,
    }
    out_dir = root / "_audits"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"evidence-audit-{time.strftime('%Y%m%d-%H%M%S')}.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"evidence audit: {len(proposals)} proposals -> "
          f"{accepted} pass / {rejected} auto-reject / {skipped} skipped")
    print(f"report: {out}")
    if verbose:
        for r in results:
            if r["errors"]:
                print(f"  REJECT {r['id']} ({r['kind']}): {r['errors']}")
    return 0 if not rejected else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default=None)
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()
    root = Path(args.root).resolve() if args.root else Path(__file__).resolve().parents[1]
    return audit(root, args.verbose)


if __name__ == "__main__":
    sys.exit(main())
