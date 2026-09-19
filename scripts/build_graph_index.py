#!/usr/bin/env python3
"""Build a rebuildable SQLite graph index over canonical wiki zones.

Scope (governance): navigation/production mechanism only. The graph index
NEVER upgrades evidence, NEVER writes to canonical zones, and lives in
_search/ (git-ignored, rebuildable at any time from the corpus).

Nodes: every canonical .md with a frontmatter `id` in 02-sources, 03-objects,
04-notes, 05-claims, 06-relations.
Edges: (a) wikilinks [[target]] in record bodies; (b) any frontmatter value
containing a wikilink or an id-like token (covers relation records without
hard-coding their field names).

Usage: python scripts/build_graph_index.py [--root WIKI_ROOT]
Output: <root>/_search/graph.db  (tables: nodes, edges, meta)
"""
from __future__ import annotations

import argparse
import re
import sqlite3
import sys
from pathlib import Path

CANONICAL_ZONES = ("02-sources", "03-objects", "04-notes", "05-claims", "06-relations")

FM_BLOCK = re.compile(r"\A---\r?\n(.*?)\r?\n---\r?\n", re.DOTALL)
FM_FIELD = re.compile(r"^([A-Za-z_][A-Za-z0-9_-]*):\s*(.*?)\s*$", re.MULTILINE)
WIKILINK = re.compile(r"\[\[([^\]|#]+)(?:[|#][^\]]*)?\]\]")
ID_TOKEN = re.compile(r"\b(?:mw|p)-[a-z0-9]{6,}(?:-[a-z0-9]+)*\b")
PATH_TOKEN = re.compile(
    r"\b(?:02-sources|03-objects|04-notes|05-claims|06-relations)/[^\s\"']+?\.md")


def parse_frontmatter(text: str) -> dict:
    m = FM_BLOCK.match(text)
    if not m:
        return {}
    return dict(FM_FIELD.findall(m.group(1)))


def build(root: Path) -> tuple[int, int]:
    db_path = root / "_search" / "graph.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()
    con = sqlite3.connect(db_path)
    con.executescript(
        """
        CREATE TABLE nodes (
            id TEXT PRIMARY KEY, path TEXT NOT NULL, zone TEXT NOT NULL,
            title TEXT, kind TEXT, status TEXT);
        CREATE TABLE edges (
            src_id TEXT NOT NULL, field TEXT NOT NULL, target TEXT NOT NULL,
            target_kind TEXT NOT NULL,  -- 'id' | 'link' | 'text'
            resolved_id TEXT,           -- set when target matches a node id
            PRIMARY KEY (src_id, field, target, target_kind));
        CREATE INDEX edges_src ON edges(src_id);
        CREATE INDEX edges_res ON edges(resolved_id);
        CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT);
        """
    )
    id_to_path: dict[str, Path] = {}
    rel_to_id: dict[str, str] = {}
    records: list[tuple[str, Path, str, dict, str]] = []  # id, path, zone, fm, body
    for zone in CANONICAL_ZONES:
        zone_dir = root / zone
        if not zone_dir.is_dir():
            continue
        for md in sorted(zone_dir.rglob("*.md")):
            try:
                text = md.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            fm = parse_frontmatter(text)
            rid = str(fm.get("id", "")).strip()
            if not rid:
                continue
            body = text[m.end():] if (m := FM_BLOCK.match(text)) else text
            records.append((rid, md, zone, fm, body))
            id_to_path[rid] = md
            rel_to_id[md.relative_to(root).as_posix().lower()] = rid
            rel_to_id[md.name.lower()] = rid
            rel_to_id[md.stem.lower()] = rid

    # Alias pass over ALL other .md files (entry pages, registers, indexes):
    # resolution-only mapping so wikilinks like [[the-black-bird]] resolve.
    # These files do NOT become nodes (canonical zones only).
    for md in sorted(root.rglob("*.md")):
        rel = md.relative_to(root).as_posix().lower()
        if rel in rel_to_id or rel.split("/")[0] in CANONICAL_ZONES:
            continue
        if rel.startswith(("_originals/", "_search/", "_proposals/", ".git/")):
            continue
        try:
            fm = parse_frontmatter(md.read_text(encoding="utf-8", errors="ignore"))
        except OSError:
            continue
        rid = str(fm.get("id", "")).strip()
        if not rid:
            continue
        rel_to_id[rel] = rid
        rel_to_id[md.stem.lower()] = rid

    # Slug aliases (navigation-only): each record's own stem minus trailing
    # --kind segments, and each trailing slug segment, resolve to that record.
    # First-wins on collisions; ambiguous keys are logged to meta.
    stem_aliases: dict[str, str] = {}
    ambiguous: set[str] = set()
    for rid, md, _, _, _ in records:
        stem = md.stem.lower()
        if "--" not in stem:
            continue
        parts = stem.split("--")
        keys = ["--".join(parts[:i]) for i in range(1, len(parts))]
        keys += parts[1:]
        for k in keys:
            if k in stem_aliases and stem_aliases[k] != rid:
                ambiguous.add(k)
            stem_aliases.setdefault(k, rid)
    for k in ambiguous:
        stem_aliases.pop(k, None)

    nodes = edges = 0
    for rid, md, zone, fm, body in records:
        rel = md.relative_to(root).as_posix()
        con.execute(
            "INSERT OR IGNORE INTO nodes VALUES (?,?,?,?,?,?)",
            (rid, rel, zone, str(fm.get("title", "")),
             str(fm.get("kind", fm.get("type", ""))),
             str(fm.get("status", fm.get("relation_status", "")))),
        )
        nodes += 1

        def add_edge(field: str, target: str, tkind: str) -> None:
            nonlocal edges
            target = target.strip()
            if not target:
                return
            resolved = None
            if target in id_to_path:
                resolved = target
            else:
                cand = target.replace("\\", "/").lstrip("./").lower()
                base = cand.rsplit("/", 1)[-1]
                resolved = (rel_to_id.get(cand) or rel_to_id.get(base)
                            or stem_aliases.get(cand)
                            or stem_aliases.get(base))
            cur = con.execute(
                "INSERT OR IGNORE INTO edges VALUES (?,?,?,?,?)",
                (rid, field, target, tkind, resolved))
            edges += cur.rowcount

        for target in WIKILINK.findall(body):
            add_edge("body-wikilink", target, "link")
        for field, value in fm.items():
            for target in WIKILINK.findall(value):
                add_edge(f"fm:{field}", target, "link")
            for token in ID_TOKEN.findall(value):
                if token != rid:
                    add_edge(f"fm:{field}", token, "id")
            for pmatch in PATH_TOKEN.findall(value):
                add_edge(f"fm:{field}", pmatch, "path")

    con.executemany(
        "INSERT INTO meta VALUES (?,?)",
        [("built_at_source", "build_graph_index.py"),
         ("nodes", str(nodes)), ("edges", str(edges)),
         ("zones", ",".join(CANONICAL_ZONES))],
    )
    con.commit()
    con.close()
    return nodes, edges


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default=None,
                    help="wiki root (default: parent of this script)")
    args = ap.parse_args()
    root = Path(args.root).resolve() if args.root else Path(__file__).resolve().parents[1]
    nodes, edges = build(root)
    print(f"graph index built: {root / '_search' / 'graph.db'} "
          f"({nodes} nodes, {edges} edges)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
