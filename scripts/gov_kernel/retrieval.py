from __future__ import annotations

import datetime
import fnmatch
import json
import pathlib
import sqlite3
from dataclasses import dataclass
from typing import Any

from .common import repo_path, sha256_file
from .frontmatter import load_markdown_frontmatter
from .normalize import normalize_persian_for_search

TEXT_EXTS = {".md", ".json", ".jsonl", ".yaml", ".yml", ".txt", ".base"}


class FTS5Unavailable(RuntimeError):
    pass


@dataclass(frozen=True)
class Profile:
    name: str
    include_globs: tuple[str, ...]
    exclude_globs: tuple[str, ...]
    required_mapping: bool = False


def load_profiles(root: pathlib.Path) -> dict[str, Profile]:
    cfg = json.loads((root / "00-system/configuration/retrieval-profiles.v2.json").read_text(encoding="utf-8"))
    out: dict[str, Profile] = {}
    for name, spec in cfg["profiles"].items():
        includes = tuple(spec.get("include_globs", []))
        required = bool(spec.get("required_mapping", False))
        if required and not includes:
            raise RuntimeError(f"retrieval profile {name!r} requires live-repo mapping before use")
        out[name] = Profile(name, includes, tuple(spec.get("exclude_globs", [])), required)
    return out


def profile_allows(path: str, profile: Profile) -> bool:
    p = path.replace("\\", "/")
    if profile.include_globs and not any(fnmatch.fnmatch(p, g) for g in profile.include_globs):
        return False
    if any(fnmatch.fnmatch(p, g) for g in profile.exclude_globs):
        return False
    return True


def probe_fts5(conn: sqlite3.Connection) -> bool:
    try:
        conn.execute("CREATE VIRTUAL TABLE temp.__fts_probe USING fts5(x)")
        conn.execute("DROP TABLE temp.__fts_probe")
        return True
    except sqlite3.OperationalError:
        return False


def _scalar(value: Any) -> Any:
    """SQLite columns are scalar; a frontmatter list (e.g. multiple language codes) is joined."""
    if isinstance(value, (list, tuple)):
        return ",".join(str(v) for v in value) if value else None
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    if isinstance(value, (datetime.date, datetime.time)):
        return value.isoformat()
    return value


def _metadata(path: pathlib.Path, root: pathlib.Path) -> tuple[dict[str, Any], str]:
    rel = str(path.relative_to(root)).replace("\\", "/")
    text = path.read_text(encoding="utf-8", errors="replace")
    fm: dict[str, Any] = {}
    body = text
    if path.suffix.lower() == ".md":
        try:
            fm, body = load_markdown_frontmatter(path)
        except Exception:
            pass
    return {
        "path": rel,
        "record_id": _scalar(fm.get("id")),
        "record_type": _scalar(fm.get("type")),
        "status": _scalar(fm.get("status") or fm.get("validation_status")),
        "authority_level": _scalar(fm.get("authority_level")),
        "title": _scalar(fm.get("title")) or path.stem,
        "language_hint": _scalar(fm.get("language") or fm.get("language_hint")),
        "content_sha256": sha256_file(path),
        "updated": _scalar(fm.get("updated")),
    }, body


def build_index(root: pathlib.Path, db_path: pathlib.Path) -> dict[str, Any]:
    profiles = load_profiles(root)
    governed = profiles.get("all-governed")
    if not governed:
        raise RuntimeError("all-governed profile is required")
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()
    conn = sqlite3.connect(db_path)
    try:
        if not probe_fts5(conn):
            raise FTS5Unavailable("FTS5_UNAVAILABLE")
        conn.execute("CREATE TABLE docs(path TEXT PRIMARY KEY, record_id TEXT, record_type TEXT, status TEXT, authority_level INTEGER, title TEXT, language_hint TEXT, content_sha256 TEXT, updated TEXT)")
        conn.execute("CREATE VIRTUAL TABLE docs_fts USING fts5(path UNINDEXED, title, body, normalized_body)")
        count = 0
        for p in sorted(root.rglob("*")):
            if not p.is_file() or p.suffix.lower() not in TEXT_EXTS:
                continue
            rel = str(p.relative_to(root)).replace("\\", "/")
            if rel.startswith(".git/") or rel.startswith("_search/") or not profile_allows(rel, governed):
                continue
            meta, body = _metadata(p, root)
            conn.execute("INSERT INTO docs VALUES(?,?,?,?,?,?,?,?,?)", (meta["path"], meta["record_id"], meta["record_type"], meta["status"], meta["authority_level"], meta["title"], meta["language_hint"], meta["content_sha256"], meta["updated"]))
            conn.execute("INSERT INTO docs_fts(path,title,body,normalized_body) VALUES(?,?,?,?)", (meta["path"], meta["title"], body, normalize_persian_for_search(body)))
            count += 1
        conn.commit()
        return {"capability": "FTS5_AVAILABLE", "indexed_documents": count, "db": str(db_path)}
    finally:
        conn.close()


def exact_resolve(root: pathlib.Path, query: str, profile_name: str) -> list[dict[str, Any]]:
    profiles = load_profiles(root); profile = profiles[profile_name]
    q = query.strip()
    hits: list[dict[str, Any]] = []
    direct = root / q
    candidates: list[pathlib.Path] = []
    if direct.is_file(): candidates.append(direct)
    for p in root.rglob("*"):
        if not p.is_file() or p.suffix.lower() not in TEXT_EXTS: continue
        rel = str(p.relative_to(root)).replace("\\", "/")
        if not profile_allows(rel, profile): continue
        if p.name == q or p.stem == q:
            candidates.append(p); continue
        if p.suffix.lower() == ".md":
            try:
                fm, _ = load_markdown_frontmatter(p)
                if str(fm.get("id") or "") == q or str(fm.get("title") or "") == q:
                    candidates.append(p)
            except Exception: pass
    seen=set()
    for p in candidates:
        rel=str(p.relative_to(root)).replace("\\","/")
        if rel in seen or not profile_allows(rel,profile): continue
        seen.add(rel); meta,_=_metadata(p,root)
        hits.append({**meta,"backend":"exact","score":0,"snippet":None,"authority_note":"retrieval ranking is not evidence"})
    return hits


def search_fts(root: pathlib.Path, db_path: pathlib.Path, query: str, profile_name: str, limit: int = 10) -> dict[str, Any]:
    profiles=load_profiles(root); profile=profiles[profile_name]
    if not db_path.exists():
        return {"capability":"FTS5_UNAVAILABLE","reason":"INDEX_MISSING","results":[]}
    conn=sqlite3.connect(db_path); conn.row_factory=sqlite3.Row
    try:
        if not probe_fts5(conn):
            return {"capability":"FTS5_UNAVAILABLE","reason":"SQLITE_BUILD","results":[]}
        norm=normalize_persian_for_search(query)
        rows=conn.execute("SELECT f.path, bm25(docs_fts) AS score, snippet(docs_fts,2,'[',']','…',18) AS snippet, d.* FROM docs_fts f JOIN docs d ON d.path=f.path WHERE docs_fts MATCH ? ORDER BY score LIMIT ?", (norm, max(limit*5,limit))).fetchall()
        out=[]
        for r in rows:
            rel=r["path"]
            if not profile_allows(rel, profile): continue
            out.append({"path":rel,"record_id":r["record_id"],"title":r["title"],"record_type":r["record_type"],"status":r["status"],"authority_level":r["authority_level"],"backend":"fts5","score":r["score"],"snippet":r["snippet"],"authority_note":"retrieval ranking is not evidence"})
            if len(out)>=limit: break
        return {"capability":"FTS5_AVAILABLE","results":out}
    except sqlite3.OperationalError as exc:
        return {"capability":"FTS5_UNAVAILABLE","reason":str(exc),"results":[]}
    finally:
        conn.close()


def open_current_result(root: pathlib.Path, result: dict[str, Any], profile_name: str) -> dict[str, Any]:
    profile=load_profiles(root)[profile_name]
    rel=str(result.get("path") or "")
    if not profile_allows(rel, profile):
        raise PermissionError(f"AUTHORITY_PROFILE_REJECTED:{rel}")
    p=repo_path(root, rel)
    if not p.is_file():
        raise FileNotFoundError(f"STALE_BACKEND_PATH:{rel}")
    text=p.read_text(encoding="utf-8",errors="replace")
    return {"path":rel,"current_content":text,"current_sha256":sha256_file(p),"backend_hint":result.get("backend"),"authority_note":"current content loaded from repository filesystem"}
