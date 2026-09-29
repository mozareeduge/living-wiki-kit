#!/usr/bin/env python3
"""Context packer: assemble a governed neighborhood pack for a seed record.

Contract (Phase 1):
- max 30 records, budget <= 16000 estimated tokens (chars/4 heuristic)
- every included record carries a `reason` field ("seed" / "1-hop via ..."
  / "lexical: ...") so the pack is auditable
- output goes ONLY to _search/packs/ (git-ignored); canonical zones are
  never touched; retrieval scores organize attention and are never evidence.

Usage:
  python scripts/context_pack.py --seed mw-xxxx [--hops 1] \
      [--query "optional lexical query"] [--records 30] [--budget 16000]

The lexical search is injectable: --search-fn names a module-level function
`search(query, n) -> list[dict]` in a user module; default uses the MCP
server's lexical helper (qmd typed lex: query). Tests inject a fake.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_graph_index as bgi  # noqa: E402
import wiki_profiles as wp  # noqa: E402  (frontmatter parser only; lenses are advisory)
import candidate_projection as _cp  # noqa: E402  (disposable projections; never canonical)
from gov_kernel.schemas import validate_record  # noqa: E402

MAX_RECORDS_DEFAULT = 30
TOKEN_BUDGET_DEFAULT = 16000
CHARS_PER_TOKEN = 4


def default_search(query: str, n: int, root: Path) -> list[dict]:
    """Deterministic lexical search via qmd typed query (no LLM expansion)."""
    import shutil
    import subprocess
    qmd = shutil.which("qmd")
    if not qmd:
        return []
    proc = subprocess.run(
        [qmd, "query", f"lex: {query}", "--no-rerank", "--json", "-n", str(n),
         "--collection", "wiki"],
        cwd=str(root), text=True, capture_output=True, timeout=90,
    )
    try:
        return json.loads(proc.stdout)
    except (json.JSONDecodeError, ValueError):
        return []


def _neighborhood(con, seed: str, hops: int) -> list[tuple[str, str, str]]:
    """BFS from seed over resolved edges; returns (node_id, reason, depth)."""
    out: dict[str, tuple[str, str]] = {}
    frontier = {seed}
    for depth in range(1, max(1, hops) + 1):
        nxt: set[str] = set()
        qmarks = ",".join("?" * len(frontier))
        rows = con.execute(
            f"SELECT src_id, resolved_id, field FROM edges "
            f"WHERE src_id IN ({qmarks}) AND resolved_id IS NOT NULL",
            tuple(frontier)).fetchall()
        rows += con.execute(
            f"SELECT resolved_id, src_id, field FROM edges "
            f"WHERE resolved_id IN ({qmarks}) AND src_id IS NOT NULL",
            tuple(frontier)).fetchall()
        for a, b, field in rows:
            if b == seed or b in out or b in frontier:
                continue
            out[b] = (f"{depth}-hop via {field}", str(depth))
            nxt.add(b)
        frontier = nxt
        if not frontier:
            break
    return [(nid, reason, d) for nid, (reason, d) in out.items()]


def build_pack(root: Path, seed: str, hops: int = 1, query: str | None = None,
               max_records: int = MAX_RECORDS_DEFAULT,
               budget_tokens: int = TOKEN_BUDGET_DEFAULT,
               search_fn=None, lens: str | dict | None = None,
               accepted_only: bool = False,
               include_candidates: bool = True) -> dict:
    db = root / "_search" / "graph.db"
    if not db.exists():
        raise SystemExit(f"no graph index at {db}; run build_graph_index.py first")
    con = sqlite3_connect(db)
    seed_row = con.execute("SELECT path, title FROM nodes WHERE id=?", (seed,)).fetchone()
    if not seed_row:
        raise SystemExit(f"seed id {seed!r} not in graph index")

    entries: list[dict] = []
    used = {seed}
    entries.append({"id": seed, "path": seed_row[0], "title": seed_row[1],
                    "reason": "seed", "depth": 0})

    if hops >= 1:
        for nid, reason, depth in _neighborhood(con, seed, hops):
            if nid in used or len(entries) >= max_records:
                continue
            used.add(nid)
            row = con.execute("SELECT path, title FROM nodes WHERE id=?", (nid,)).fetchone()
            if not row:
                # resolved to a page outside the canonical zones (register,
                # audit, entry page): resolvable for links, never a node
                continue
            entries.append({"id": nid, "path": row[0], "title": row[1],
                            "reason": reason, "depth": int(depth)})

    if query and len(entries) < max_records:
        # Label match first: local, deterministic, inspectable. A label is a
        # retrieval aid, never evidence — the reason says MATCHED, never IS.
        qtokens = {bgi.normalize_label(t) for t in query.split()} | {bgi.normalize_label(query)}
        qtokens.discard("")
        try:
            label_rows = con.execute(
                "SELECT node_id, label_raw, label_norm, label_source FROM labels").fetchall()
        except Exception:  # index built before labels existed; rebuild it
            label_rows = []
        for nid, raw, norm, source in sorted(label_rows, key=lambda r: (r[0], r[2])):
            if nid in used or len(entries) >= max_records:
                continue
            if norm in qtokens:
                used.add(nid)
                row = con.execute("SELECT path, title FROM nodes WHERE id=?", (nid,)).fetchone()
                if not row:
                    continue
                reason = f"label: `{raw}` matched query context"
                if source == "legacy-kind":
                    reason += " (legacy kind compatibility)"
                entries.append({"id": nid, "path": row[0], "title": row[1],
                                "reason": reason, "depth": None,
                                "label_source": source})
                if len(entries) >= max_records:
                    break

    if query and len(entries) < max_records:
        fn = search_fn or (lambda q, n: default_search(q, n, root))
        want = min(12, max_records - len(entries))
        if include_candidates:
            # Candidate projections: same tier as label matches, never
            # penalized for being candidate; marked so they cannot
            # masquerade as canonical records.
            for c in _cp.query_projections(root, query):
                pid = c["proposal_id"]
                if pid in used or len(entries) >= max_records:
                    continue
                used.add(pid)
                entries.append({"id": pid, "path": None, "title": c["title"],
                                "reason": f"candidate: proposal {pid} matched query context",
                                "depth": None, "authority": "candidate",
                                "proposal_status": c["proposal_status"],
                                "proposal_id": pid,
                                "candidate": True,
                                "source_passage": c["source_passage"],
                                "candidate_labels": c["labels"],
                                "candidate_text": c["characterization"]})
                if len(entries) >= max_records:
                    break
        for hit in fn(query, want):
            # qmd hits carry file paths like qmd://wiki/<name> — map by stem
            f = str(hit.get("file", ""))
            stem = Path(f.replace("qmd://wiki/", "")).stem
            row = con.execute(
                "SELECT id, path, title FROM nodes WHERE path LIKE ?",
                (f"%{stem}%",)).fetchone()
            if not row or row[0] in used:
                continue
            used.add(row[0])
            entries.append({"id": row[0], "path": row[1], "title": row[2],
                            "reason": f"lexical: {query}", "depth": None,
                            "score": hit.get("score")})
            if len(entries) >= max_records:
                break

    # Attach content under the global token budget.
    spent = 0
    per_cap_chars = (budget_tokens * CHARS_PER_TOKEN) // max(1, len(entries))
    for e in entries:
        if e.get("candidate"):
            sp = e.get("source_passage") or {}
            text = (f"{e.get('title', '')}\n{e.get('candidate_text', '')}\n"
                    f"passage: {sp.get('quote', '')} ({sp.get('path', '')})")
        else:
            p = root / e["path"]
            try:
                text = p.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                text = ""
        body = text[:per_cap_chars]
        est = len(body) // CHARS_PER_TOKEN
        e["content"] = body
        e["content_truncated"] = len(text) > len(body)
        e["tokens_est"] = est
        spent += est

    lens_id: str | None = None
    lens_record: dict | None = None
    if lens is not None or accepted_only:
        if isinstance(lens, dict):
            lens_record = lens
            lens_id = str(lens.get("id", "inline"))
        elif isinstance(lens, str) and lens:
            try:
                lens_record = resolve_lens(root, lens)
            except ValueError as exc:
                raise SystemExit(str(exc))
            lens_id = lens
        else:
            lens_record = {"candidate_visibility": "include",
                           "authority_mode": "annotate",
                           "foreground_labels": []}
        if accepted_only:
            lens_record = dict(lens_record)
            lens_record["candidate_visibility"] = "exclude"
            lens_record["authority_mode"] = "accepted-only"
        entries = apply_lens(entries, lens_record, lens_id or "accepted-only")

    return {
        "meta": {
            "generated_by": "context_pack.py",
            "seed": seed, "hops": hops, "query": query,
            "records": len(entries), "tokens_est": spent,
            "budget_tokens": budget_tokens, "max_records": max_records,
            "lens": lens_id, "accepted_only": bool(accepted_only),
            "authority_note": ("Pack is a navigation/production mechanism; "
                               "scores and inclusion reasons are never evidence; "
                               "model output from it stays candidate-tier."),
            "generated_at_epoch": int(time.time()),
        },
        "records": entries,
    }


def sqlite3_connect(db: Path):
    import sqlite3
    return sqlite3.connect(db)


LENSES_DIRNAME = Path("00-system/configuration/lenses")


def resolve_lens(root: Path, lens_id: str) -> dict:
    """Load + schema-validate a lens doc. Raises ValueError naming the problem."""
    doc = root / LENSES_DIRNAME / f"{lens_id}.md"
    if not doc.is_file():
        return _raise_unknown_lens(root, lens_id)
    record = wp.parse_profile(doc.read_text(encoding="utf-8"))
    findings = validate_record(record, root / "00-system/schemas",
                               explicit_schema="wiki-lens.schema.json")
    if findings:
        raise ValueError(f"lens {lens_id!r} invalid: " +
                         "; ".join(f.message for f in findings))
    if record.get("status") == "retired":
        raise ValueError(f"lens {lens_id!r} is retired")
    return record


def _raise_unknown_lens(root: Path, lens_id: str):
    known = sorted(p.stem for p in (root / LENSES_DIRNAME).glob("*.md")) \
        if (root / LENSES_DIRNAME).is_dir() else []
    raise ValueError(f"unknown lens {lens_id!r}"
                     + (f" (known: {', '.join(known)})" if known else ""))


def apply_lens(entries: list[dict], lens: dict, lens_id: str) -> list[dict]:
    """Foreground per a lens; never alters authority, never silently drops.

    Entries carrying authority == "candidate" are dropped ONLY when the lens
    explicitly says candidate_visibility == "exclude" (the accepted-only
    view, always explicit). Everything else passes through annotated.
    """
    exclude = lens.get("candidate_visibility") == "exclude"
    fg = {bgi.normalize_label(str(x)) for x in (lens.get("foreground_labels") or [])}
    fg.discard("")
    out: list[dict] = []
    for e in entries:
        if exclude and e.get("authority") == "candidate":
            continue
        e = dict(e)
        reason = str(e.get("reason", ""))
        m = re.search(r"label:\s*`([^`]+)`", reason)
        if fg and m and bgi.normalize_label(m.group(1)) in fg:
            e["reason"] = reason + f" (foregrounded by lens {lens_id})"
            e["foregrounded"] = True
        elif fg and e.get("candidate"):
            cand_norms = {bgi.normalize_label(str(x)) for x in (e.get("candidate_labels") or [])}
            if cand_norms & fg:
                e["reason"] = reason + f" (foregrounded by lens {lens_id})"
                e["foregrounded"] = True
        out.append(e)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default=None)
    ap.add_argument("--seed", required=True)
    ap.add_argument("--hops", type=int, default=1)
    ap.add_argument("--query", default=None)
    ap.add_argument("--records", type=int, default=MAX_RECORDS_DEFAULT)
    ap.add_argument("--budget", type=int, default=TOKEN_BUDGET_DEFAULT)
    ap.add_argument("--lens", default=None,
                    help="lens id from 00-system/configuration/lenses/ (foregrounding only)")
    ap.add_argument("--accepted-only", action="store_true",
                    help="explicit accepted-only view: drop candidate-authority entries")
    args = ap.parse_args()
    root = Path(args.root).resolve() if args.root else Path(__file__).resolve().parents[1]
    pack = build_pack(root, args.seed, args.hops, args.query,
                      args.records, args.budget, lens=args.lens,
                      accepted_only=args.accepted_only)
    out_dir = root / "_search" / "packs"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"pack-{args.seed}-{int(time.time())}.json"
    out.write_text(json.dumps(pack, ensure_ascii=False, indent=1), encoding="utf-8")
    m = pack["meta"]
    print(f"pack: {out} | records={m['records']} tokens_est={m['tokens_est']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
