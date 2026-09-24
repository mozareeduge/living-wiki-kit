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
               search_fn=None) -> dict:
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
        fn = search_fn or (lambda q, n: default_search(q, n, root))
        want = min(12, max_records - len(entries))
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

    return {
        "meta": {
            "generated_by": "context_pack.py",
            "seed": seed, "hops": hops, "query": query,
            "records": len(entries), "tokens_est": spent,
            "budget_tokens": budget_tokens, "max_records": max_records,
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


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default=None)
    ap.add_argument("--seed", required=True)
    ap.add_argument("--hops", type=int, default=1)
    ap.add_argument("--query", default=None)
    ap.add_argument("--records", type=int, default=MAX_RECORDS_DEFAULT)
    ap.add_argument("--budget", type=int, default=TOKEN_BUDGET_DEFAULT)
    args = ap.parse_args()
    root = Path(args.root).resolve() if args.root else Path(__file__).resolve().parents[1]
    pack = build_pack(root, args.seed, args.hops, args.query,
                      args.records, args.budget)
    out_dir = root / "_search" / "packs"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"pack-{args.seed}-{int(time.time())}.json"
    out.write_text(json.dumps(pack, ensure_ascii=False, indent=1), encoding="utf-8")
    m = pack["meta"]
    print(f"pack: {out} | records={m['records']} tokens_est={m['tokens_est']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
