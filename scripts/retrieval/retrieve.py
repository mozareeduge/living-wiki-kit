#!/usr/bin/env python3
"""wiki_retrieve (C4) and wiki_artifact_read (C5): chunk-level retrieval over _search/retrieval.sqlite.

Read-only. No model at query time. Ranking is navigation, never evidence.
"""
from __future__ import annotations

import argparse
import base64
import json
import pathlib
import re
import sqlite3
import sys
from typing import Any

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from gov_kernel.normalize import normalize_persian_for_search  # noqa: E402
from gov_kernel.retrieval import (  # noqa: E402
    FTS5Unavailable,
    index_status,
    load_profiles,
    probe_fts5,
    profile_allows,
)

AUTHORITY_NOTE = "ranking is not evidence"
SCOPES = ("canonical", "captures", "all")
GROUPS = ("canonical", "captures", "sources")
CHARS_PER_TOKEN = 4
DB_REL = "_search/retrieval.sqlite"
_TOKEN_RE = re.compile(r"[\w‌]+", re.UNICODE)


class RetrieveError(Exception):
    def __init__(self, code: str, message: str, **extra: Any) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.extra = extra

    def to_dict(self) -> dict[str, Any]:
        return {"ok": False, "code": self.code, "error": self.code, "message": self.message, **self.extra}


def _open(root: pathlib.Path, db_path: pathlib.Path | None = None) -> sqlite3.Connection:
    db = db_path or (root / DB_REL)
    if not db.is_file():
        raise RetrieveError("E_INDEX_MISSING", "retrieval index not found; build it first")
    conn = sqlite3.connect(db)
    if not probe_fts5(conn):
        conn.close()
        raise FTS5Unavailable("FTS5_UNAVAILABLE")
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if not {"sources", "chunks", "chunks_fts"} <= tables:
        conn.close()
        raise RetrieveError("E_INDEX_MISSING", "chunk tables missing from the index")
    return conn


def _tokens(text: str) -> list[str]:
    return _TOKEN_RE.findall(normalize_persian_for_search(text))


def _fts_expr(tokens: list[str]) -> str:
    return " ".join('"' + t.replace('"', '""') + '"' for t in tokens)


def load_alias_groups(root: pathlib.Path) -> list[list[str]]:
    """Groups from LABEL_ALIASES.json: the key plus its members all match each other."""
    p = root / "00-system" / "configuration" / "LABEL_ALIASES.json"
    if not p.is_file():
        return []
    try:
        doc = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    groups: list[list[str]] = []
    for key, members in (doc.get("aliases") or {}).items():
        if isinstance(members, list):
            groups.append([str(key)] + [str(m) for m in members])
    return groups


def _group_of(path: str, profiles: dict[str, Any]) -> str:
    if "captures" in profiles and profile_allows(path, profiles["captures"]):
        return "captures"
    if "canonical" in profiles and profile_allows(path, profiles["canonical"]):
        return "canonical"
    return "sources"


def _encode_cursor(offsets: dict[str, int], qkey: str) -> str:
    raw = json.dumps({"o": offsets, "q": qkey}, sort_keys=True).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii")


def _decode_cursor(cursor: str, qkey: str) -> dict[str, int]:
    try:
        doc = json.loads(base64.urlsafe_b64decode(cursor.encode("ascii")))
        offsets = {k: int(v) for k, v in doc["o"].items()}
        if doc["q"] != qkey:
            raise ValueError("cursor belongs to a different query")
        if any(v < 0 for v in offsets.values()):
            raise ValueError("negative offset")
        return offsets
    except Exception as exc:  # noqa: BLE001
        raise RetrieveError("E_BAD_CURSOR", f"invalid cursor: {exc}") from exc


def _candidates(
    conn: sqlite3.Connection, tokens: list[str], alias_groups: list[list[str]]
) -> dict[str, dict[str, Any]]:
    """chunk_ref -> {score, reasons, alias}: primary AND-query plus alias-substituted queries."""
    found: dict[str, dict[str, Any]] = {}

    def run(toks: list[str], reason: str, alias: dict[str, str] | None) -> None:
        if not toks:
            return
        rows = conn.execute(
            "SELECT chunk_ref, bm25(chunks_fts) FROM chunks_fts WHERE chunks_fts MATCH ?",
            (f"normalized_text : ({_fts_expr(toks)})",),
        ).fetchall()
        for ref, bm in rows:
            score = round(-float(bm), 6)
            cur = found.get(ref)
            if cur is None:
                found[ref] = {"score": score, "reasons": [reason], "alias": [alias] if alias else []}
            else:
                if reason not in cur["reasons"]:
                    cur["reasons"].append(reason)
                if alias and alias not in cur["alias"]:
                    cur["alias"].append(alias)
                cur["score"] = max(cur["score"], score)

    run(tokens, "fts-match", None)
    for i, tok in enumerate(tokens):
        for grp in alias_groups:
            norm = [normalize_persian_for_search(m).strip().lower() for m in grp]
            if tok.lower() in norm:
                for member, nm in zip(grp, norm):
                    if nm == tok.lower():
                        continue
                    sub = tokens[:i] + _tokens(member) + tokens[i + 1:]
                    run(sub, "alias-match", {"from": tok, "to": member})
    return found


def wiki_retrieve(
    root: pathlib.Path | str,
    *,
    query: str,
    scope: str = "all",
    limit: int = 10,
    budget_tokens: int = 6000,
    cursor: str | None = None,
    db_path: pathlib.Path | None = None,
) -> dict[str, Any]:
    root = pathlib.Path(root).resolve()
    if not isinstance(query, str) or not query.strip():
        raise RetrieveError("E_BAD_ARGS", "query is required")
    if scope not in SCOPES:
        raise RetrieveError("E_BAD_ARGS", f"scope must be one of {SCOPES}")
    if not isinstance(limit, int) or not 1 <= limit <= 50:
        raise RetrieveError("E_BAD_ARGS", "limit must be 1..50")
    if not isinstance(budget_tokens, int) or not 500 <= budget_tokens <= 32000:
        raise RetrieveError("E_BAD_ARGS", "budget_tokens must be 500..32000")

    qkey = f"{normalize_persian_for_search(query).strip()}|{scope}"
    offsets = _decode_cursor(cursor, qkey) if cursor else {}
    tokens = _tokens(query)
    if not tokens:
        raise RetrieveError("E_BAD_ARGS", "query has no searchable terms")

    conn = _open(root, db_path)
    try:
        profiles = load_profiles(root)
        cands = _candidates(conn, tokens, load_alias_groups(root))
        meta: dict[str, tuple] = {}
        for ref in cands:
            row = conn.execute(
                "SELECT c.source_ref, c.start, c.end, c.text, s.path, s.tier, s.authority_level "
                "FROM chunks c LEFT JOIN sources s ON s.source_ref = c.source_ref WHERE c.chunk_ref=?",
                (ref,),
            ).fetchone()
            if row:
                meta[ref] = row
    finally:
        conn.close()

    wanted = GROUPS if scope == "all" else (scope,)
    ranked: dict[str, list[str]] = {g: [] for g in wanted}
    for ref, row in meta.items():
        g = _group_of(row[4] or "", profiles)
        if g in ranked:
            ranked[g].append(ref)
    for g in wanted:
        ranked[g].sort(key=lambda r: (-cands[r]["score"], r))

    budget_chars = budget_tokens * CHARS_PER_TOKEN
    used = 0
    groups_out: dict[str, list[dict[str, Any]]] = {g: [] for g in wanted}
    new_offsets: dict[str, int] = {}
    returned_any = False
    out_of_budget = False
    for g in wanted:
        pos = offsets.get(g, 0)
        taken = 0
        while pos < len(ranked[g]) and taken < limit and not out_of_budget:
            ref = ranked[g][pos]
            src_ref, start, end, text, _path, tier, auth = meta[ref]
            cand = cands[ref]
            truncated = False
            if used + len(text) > budget_chars:
                if returned_any:
                    out_of_budget = True
                    break
                text = text[:budget_chars]  # only when a single chunk exceeds the whole budget
                end = start + len(text)
                truncated = True
            reasons = list(cand["reasons"])
            if query.strip() in text and "exact-match" not in reasons:
                reasons.insert(0, "exact-match")
            hit = {
                "source_ref": src_ref,
                "chunk_ref": ref,
                "span": {"start": start, "end": end},
                "text": text,
                "tier": tier,
                "authority_level": auth,
                "inclusion_reason": reasons,
                "score": cand["score"],
                "coverage": {"returned_chars": len(text), "truncated": truncated},
            }
            if cand["alias"]:
                hit["alias_matches"] = cand["alias"]
            groups_out[g].append(hit)
            used += len(text)
            returned_any = True
            pos += 1
            taken += 1
        new_offsets[g] = pos
    more = any(new_offsets.get(g, 0) < len(ranked[g]) for g in wanted)
    status = index_status(root, db_path)
    out: dict[str, Any] = {
        "ok": True,
        "query": query,
        "scope": scope,
        "groups": groups_out,
        "total_matches": {g: len(ranked[g]) for g in wanted},
        "budget": {"budget_tokens": budget_tokens, "used_chars": used},
        "next_cursor": _encode_cursor(new_offsets, qkey) if more else None,
        "index_state": status["status"],
        "authority_note": AUTHORITY_NOTE,
    }
    if status["degraded"]:
        out["warnings"] = ["index-" + status["status"]] + list(status["reasons"])
    return out


# ---------------------------------------------------------------- C5

def wiki_artifact_read(
    root: pathlib.Path | str,
    *,
    source_ref: str | None = None,
    chunk_ref: str | None = None,
    source_version: str | None = None,
    offset: int = 0,
    limit: int = 20,
    db_path: pathlib.Path | None = None,
) -> dict[str, Any]:
    """Read one source (layers + paginated chunk list) or one chunk with prev/next refs.

    A ref whose source_version is no longer current fails with E_STALE_SOURCE, never a remap.
    ``source_ref`` may accompany ``chunk_ref`` so a vanished chunk is recognised as stale.
    """
    root = pathlib.Path(root).resolve()
    if not source_ref and not chunk_ref:
        raise RetrieveError("E_BAD_ARGS", "give source_ref or chunk_ref")
    if not isinstance(offset, int) or offset < 0 or not isinstance(limit, int) or not 1 <= limit <= 100:
        raise RetrieveError("E_BAD_ARGS", "offset >= 0 and limit 1..100 required")

    conn = _open(root, db_path)
    try:
        if chunk_ref:
            row = conn.execute(
                "SELECT source_ref, source_version, start, end, heading_path, text, text_sha256 "
                "FROM chunks WHERE chunk_ref=?",
                (chunk_ref,),
            ).fetchone()
            if row is None:
                if source_ref:
                    cur = conn.execute("SELECT source_version FROM sources WHERE source_ref=?", (source_ref,)).fetchone()
                    if cur is None:
                        raise RetrieveError("E_UNKNOWN_REF", "source_ref not in the index",
                                            source_ref=source_ref, chunk_ref=chunk_ref)
                    raise RetrieveError("E_STALE_SOURCE",
                                        "chunk_ref belongs to a source version that is no longer current",
                                        source_ref=source_ref, chunk_ref=chunk_ref,
                                        current_source_version=cur[0])
                raise RetrieveError("E_UNKNOWN_REF",
                                    "chunk_ref not in the current index; pass source_ref to detect a stale ref",
                                    chunk_ref=chunk_ref)
            src_ref, sv, start, end, hp, text, tsha = row
            cur = conn.execute("SELECT source_version FROM sources WHERE source_ref=?", (src_ref,)).fetchone()
            if cur is None or cur[0] != sv or (source_version and source_version != sv):
                raise RetrieveError("E_STALE_SOURCE", "source version changed", chunk_ref=chunk_ref,
                                    current_source_version=cur[0] if cur else None)
            order = [r[0] for r in conn.execute(
                "SELECT chunk_ref FROM chunks WHERE source_ref=? ORDER BY start", (src_ref,))]
            i = order.index(chunk_ref)
            return {
                "ok": True,
                "chunk": {
                    "chunk_ref": chunk_ref, "source_ref": src_ref, "source_version": sv,
                    "span": {"start": start, "end": end}, "heading_path": json.loads(hp or "[]"),
                    "text": text, "text_sha256": tsha,
                },
                "prev": order[i - 1] if i > 0 else None,
                "next": order[i + 1] if i + 1 < len(order) else None,
                "authority_note": AUTHORITY_NOTE,
            }

        src = conn.execute(
            "SELECT source_version, path, tier, authority_level, language_hint, indexed_at "
            "FROM sources WHERE source_ref=?",
            (source_ref,),
        ).fetchone()
        if src is None:
            raise RetrieveError("E_UNKNOWN_REF", "source_ref not in the index", source_ref=source_ref)
        if source_version and source_version != src[0]:
            raise RetrieveError("E_STALE_SOURCE", "source version changed", source_ref=source_ref,
                                current_source_version=src[0])
        total = conn.execute("SELECT count(*) FROM chunks WHERE source_ref=?", (source_ref,)).fetchone()[0]
        rows = conn.execute(
            "SELECT chunk_ref, start, end, heading_path, text FROM chunks WHERE source_ref=? "
            "ORDER BY start LIMIT ? OFFSET ?",
            (source_ref, limit, offset),
        ).fetchall()
        disk = root / src[1]
        return {
            "ok": True,
            "source_ref": source_ref,
            "source_version": src[0],
            "layers": {"derivative": {"path": src[1], "present": disk.is_file()}},
            "tier": src[2],
            "authority_level": src[3],
            "language_hint": src[4],
            "quality_flags": [] if disk.is_file() else ["source-file-missing"],
            "chunks": {
                "total": total, "offset": offset, "limit": limit,
                "next_offset": offset + len(rows) if offset + len(rows) < total else None,
                "items": [
                    {"chunk_ref": r[0], "span": {"start": r[1], "end": r[2]},
                     "heading_path": json.loads(r[3] or "[]"), "text": r[4]}
                    for r in rows
                ],
            },
            "authority_note": AUTHORITY_NOTE,
        }
    finally:
        conn.close()


# ---------------------------------------------------------------- tool handlers

def _wrap(fn, root: pathlib.Path, args: dict[str, Any]) -> str:
    try:
        return json.dumps(fn(root, **args), ensure_ascii=False)
    except RetrieveError as exc:
        return json.dumps(exc.to_dict(), ensure_ascii=False)
    except FTS5Unavailable:
        return json.dumps({"ok": False, "code": "FTS5_UNAVAILABLE", "error": "FTS5_UNAVAILABLE"})
    except TypeError as exc:
        return json.dumps({"ok": False, "code": "E_BAD_ARGS", "error": "E_BAD_ARGS", "message": str(exc)})


def make_retrieve_handler(root: pathlib.Path):
    return lambda args: _wrap(wiki_retrieve, root, dict(args))


def make_artifact_read_handler(root: pathlib.Path):
    return lambda args: _wrap(wiki_artifact_read, root, dict(args))


RETRIEVE_SCHEMA = {
    "type": "object",
    "properties": {
        "query": {"type": "string"},
        "scope": {"type": "string", "enum": list(SCOPES), "default": "all"},
        "limit": {"type": "integer", "minimum": 1, "maximum": 50, "default": 10},
        "budget_tokens": {"type": "integer", "minimum": 500, "maximum": 32000, "default": 6000},
        "cursor": {"type": "string"},
    },
    "required": ["query"],
    "additionalProperties": False,
}
ARTIFACT_READ_SCHEMA = {
    "type": "object",
    "properties": {
        "source_ref": {"type": "string"},
        "chunk_ref": {"type": "string"},
        "source_version": {"type": "string"},
        "offset": {"type": "integer", "minimum": 0, "default": 0},
        "limit": {"type": "integer", "minimum": 1, "maximum": 100, "default": 20},
    },
    "additionalProperties": False,
}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Chunk retrieval over the instance index (read-only).")
    ap.add_argument("query", nargs="?")
    ap.add_argument("--repo", default=".")
    ap.add_argument("--scope", default="all", choices=SCOPES)
    ap.add_argument("--limit", type=int, default=10)
    ap.add_argument("--budget-tokens", type=int, default=6000)
    ap.add_argument("--cursor")
    ap.add_argument("--artifact", help="source_ref or chunk_ref (chk:...) to read instead of searching")
    ap.add_argument("--source-ref", help="with a chunk ref: the source it came from (detects stale refs)")
    ap.add_argument("--offset", type=int, default=0)
    a = ap.parse_args(argv)
    root = pathlib.Path(a.repo).resolve()
    try:
        if a.artifact:
            kw: dict[str, Any] = {"offset": a.offset, "limit": a.limit}
            if a.artifact.startswith("chk:"):
                kw["chunk_ref"] = a.artifact
                kw["source_ref"] = a.source_ref
            else:
                kw["source_ref"] = a.artifact
            res = wiki_artifact_read(root, **kw)
        else:
            if not a.query:
                ap.error("query required")
            res = wiki_retrieve(root, query=a.query, scope=a.scope, limit=a.limit,
                                budget_tokens=a.budget_tokens, cursor=a.cursor)
    except RetrieveError as exc:
        print(json.dumps(exc.to_dict(), ensure_ascii=False, indent=2))
        return 1
    except FTS5Unavailable:
        print(json.dumps({"ok": False, "code": "FTS5_UNAVAILABLE"}))
        return 2
    print(json.dumps(res, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
