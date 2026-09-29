#!/usr/bin/env python3
"""Candidate object projection (dossier §23-25, §40).

Eligible durable proposals (currently: object-create) project into
disposable index space (_search/candidate_projections.json) so candidate
discoveries are visible and clearly marked WITHOUT writing canonical
03-objects/ files.

Status rules:
- terminally adjudicated (accepted/rejected) -> no projection. Accepted
  resolves to its canonical successor (no duplicate); rejected lives on in
  audit/genesis scope, not in ordinary retrieval.
- latest audit verdict rejected-audit -> no projection (audit scope only).
- otherwise (new/audited) -> projected with authority=candidate.

Projections carry proposal id/status/authority/source passage/labels, so no
candidate can masquerade as a canonical record.

Usage:
  python scripts/candidate_projection.py rebuild [--repo .]
  python scripts/candidate_projection.py list [--repo .] [--query TEXT]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_graph_index as bgi  # noqa: E402
import evidence_audit as ea  # noqa: E402

PROJECTIONS_REL = Path("_search/candidate_projections.json")

# Minimum viable set (dossier §40): object-create visibility is the critical
# acceptance case. Extend deliberately, never silently.
SUPPORTED_KINDS = ("object-create",)

ELIGIBLE_VERDICTS = ("audited", "new")


def _struct_of(body) -> dict:
    if isinstance(body, dict):
        return body
    if isinstance(body, str) and body.strip().startswith("{"):
        try:
            v = json.loads(body)
            return v if isinstance(v, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}


def proposal_states(root: Path) -> dict[str, str]:
    """Latest status per durable proposal id: terminal adjudication decision,
    else latest audit verdict (audited / rejected-audit / new)."""
    _, terminal = ea._load_durable(root)
    durable, _ = ea._load_durable(root)
    states: dict[str, str] = dict(terminal)
    if durable:
        results, _, _, _ = ea.assess_proposals(root, durable, terminal)
        for r in results:
            pid = str(r["id"])
            if pid not in states:
                states[pid] = r["verdict"] if r["verdict"] in ("audited", "rejected-audit") else "new"
    return states


def build_projections(root: Path) -> list[dict]:
    durable, _ = ea._load_durable(root)
    states = proposal_states(root)
    out: list[dict] = []
    for rec in durable:
        pid = str(rec.get("id"))
        if rec.get("kind") not in SUPPORTED_KINDS:
            continue
        status = states.get(pid, "new")
        if status not in ELIGIBLE_VERDICTS:
            continue
        struct = _struct_of(rec.get("body"))
        sp = struct.get("source_passage") or {}
        labels = struct.get("labels") or []
        out.append({
            "candidate_id": pid,
            "proposal_id": pid,
            "proposal_kind": rec.get("kind"),
            "proposal_status": status,
            "authority": "candidate",
            "title": str(struct.get("title") or pid),
            "characterization": str(struct.get("characterization") or ""),
            "labels": [str(x) for x in labels] if isinstance(labels, list) else [],
            "source_passage": {"path": str(sp.get("path", "")),
                               "quote": str(sp.get("quote", ""))} if isinstance(sp, dict) else {},
            "evidence_refs": list(rec.get("evidence_refs") or []),
        })
    return out


def rebuild(root: Path) -> dict:
    projections = build_projections(root)
    dest = root / PROJECTIONS_REL
    dest.parent.mkdir(parents=True, exist_ok=True)
    payload = {"generated_by": "candidate_projection.py",
               "projections": projections}
    dest.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"candidate projections: {len(projections)} "
          f"(_search/candidate_projections.json)")
    return payload


def load_projections(root: Path) -> list[dict]:
    dest = root / PROJECTIONS_REL
    if not dest.exists():
        return []
    try:
        return json.loads(dest.read_text(encoding="utf-8")).get("projections", [])
    except (json.JSONDecodeError, OSError, AttributeError):
        return []


def query_projections(root: Path, query: str) -> list[dict]:
    """Match projections by label norm or query token in title/text."""
    qtokens = {bgi.normalize_label(t) for t in query.split()} | {bgi.normalize_label(query)}
    qtokens.discard("")
    hits: list[dict] = []
    for c in load_projections(root):
        label_norms = {bgi.normalize_label(str(x)) for x in c.get("labels", [])}
        hay = f"{c.get('title', '')}\n{c.get('characterization', '')}".casefold()
        if (label_norms & qtokens
                or any(t in hay for t in qtokens if len(t) >= 3)):
            hits.append(c)
    return hits


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("command", choices=("rebuild", "list"))
    ap.add_argument("--repo", default=None)
    ap.add_argument("--query", default="")
    args = ap.parse_args(argv)
    root = Path(args.repo).resolve() if args.repo else Path(__file__).resolve().parents[1]
    if args.command == "rebuild":
        rebuild(root)
        return 0
    print(json.dumps(query_projections(root, args.query), ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
