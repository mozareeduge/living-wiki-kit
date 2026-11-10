from __future__ import annotations

import datetime
import fnmatch
import json
import pathlib
import sqlite3
from dataclasses import dataclass
from typing import Any

from .chunking import (
    chunk_text,
    compute_source_version,
    detect_language_hint,
    normalize_derivative_text,
)
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


def build_index(
    root: pathlib.Path,
    db_path: pathlib.Path,
    *,
    chunk_profiles: tuple[str, ...] | list[str] | str | None = None,
) -> dict[str, Any]:
    profiles = load_profiles(root)
    governed = profiles.get("all-governed")
    if not governed:
        raise RuntimeError("all-governed profile is required")

    if chunk_profiles is None:
        chunk_prof_names = ("canonical", "captures", "evidence-text")
    elif isinstance(chunk_profiles, str):
        chunk_prof_names = (chunk_profiles,)
    else:
        chunk_prof_names = tuple(chunk_profiles)
    active_chunk_profs = [profiles[name] for name in chunk_prof_names if name in profiles]

    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()
    conn = sqlite3.connect(db_path)
    try:
        if not probe_fts5(conn):
            raise FTS5Unavailable("FTS5_UNAVAILABLE")
        conn.execute(
            "CREATE TABLE docs(path TEXT PRIMARY KEY, record_id TEXT, record_type TEXT, "
            "status TEXT, authority_level INTEGER, title TEXT, language_hint TEXT, "
            "content_sha256 TEXT, updated TEXT)"
        )
        conn.execute("CREATE VIRTUAL TABLE docs_fts USING fts5(path UNINDEXED, title, body, normalized_body)")
        conn.execute(
            "CREATE TABLE sources(source_ref TEXT PRIMARY KEY, source_version TEXT, path TEXT, "
            "tier TEXT, authority_level INTEGER, language_hint TEXT, indexed_at TEXT)"
        )
        conn.execute(
            "CREATE TABLE chunks(chunk_ref TEXT PRIMARY KEY, source_ref TEXT, source_version TEXT, "
            "start INTEGER, end INTEGER, heading_path TEXT, text TEXT, text_sha256 TEXT)"
        )
        conn.execute("CREATE VIRTUAL TABLE chunks_fts USING fts5(chunk_ref UNINDEXED, text, normalized_text)")

        doc_count = 0
        chunk_count = 0
        source_count = 0
        for p in sorted(root.rglob("*")):
            if not p.is_file() or p.suffix.lower() not in TEXT_EXTS:
                continue
            rel = str(p.relative_to(root)).replace("\\", "/")
            if rel.startswith(".git/") or rel.startswith("_search/") or not profile_allows(rel, governed):
                continue
            meta, body = _metadata(p, root)
            conn.execute(
                "INSERT INTO docs VALUES(?,?,?,?,?,?,?,?,?)",
                (
                    meta["path"],
                    meta["record_id"],
                    meta["record_type"],
                    meta["status"],
                    meta["authority_level"],
                    meta["title"],
                    meta["language_hint"],
                    meta["content_sha256"],
                    meta["updated"],
                ),
            )
            conn.execute(
                "INSERT INTO docs_fts(path,title,body,normalized_body) VALUES(?,?,?,?)",
                (meta["path"], meta["title"], body, normalize_persian_for_search(body)),
            )
            doc_count += 1

            # Check if this document qualifies for chunking
            if p.suffix.lower() in {".md", ".txt"} and any(profile_allows(rel, cp) for cp in active_chunk_profs):
                rec_id = meta.get("record_id")
                if rec_id:
                    s_id = str(rec_id)
                    if s_id.startswith(("rec:", "cap:", "doc:", "prop:", "hist:")):
                        src_ref = s_id
                    elif meta.get("record_type") == "capture" or "cap-" in s_id or rel.startswith(("01-inbox/captures/", "_captures/")):
                        src_ref = f"cap:{s_id}"
                    else:
                        src_ref = f"rec:{s_id}"
                else:
                    src_ref = f"doc:{meta['content_sha256']}"

                norm_body = normalize_derivative_text(body)
                src_version = compute_source_version(norm_body)
                tier = meta.get("status") or meta.get("tier") or (
                    "captures" if rel.startswith(("01-inbox/captures/", "_captures/"))
                    else ("canonical" if rel.startswith(("03-objects/", "04-notes/", "05-claims/", "06-relations/")) else "source")
                )
                auth_lvl = meta.get("authority_level")
                if auth_lvl is None:
                    if rel.startswith(("01-inbox/captures/", "_captures/")):
                        auth_lvl = 6
                    elif rel.startswith(("03-objects/", "04-notes/", "05-claims/", "06-relations/")):
                        auth_lvl = 2
                    else:
                        auth_lvl = 1

                lang = meta.get("language_hint") or detect_language_hint(body)
                indexed_at = meta.get("updated")

                conn.execute(
                    "INSERT OR REPLACE INTO sources VALUES(?,?,?,?,?,?,?)",
                    (src_ref, src_version, rel, tier, auth_lvl, lang, indexed_at),
                )
                source_count += 1

                chunks = chunk_text(
                    body,
                    source_ref=src_ref,
                    source_version=src_version,
                    language_hint=lang,
                )
                for chk in chunks:
                    conn.execute(
                        "INSERT OR REPLACE INTO chunks VALUES(?,?,?,?,?,?,?,?)",
                        (
                            chk.chunk_ref,
                            chk.source_ref,
                            chk.source_version,
                            chk.span["start"],
                            chk.span["end"],
                            json.dumps(chk.heading_path, ensure_ascii=False),
                            chk.text,
                            chk.text_sha256,
                        ),
                    )
                    norm_txt = normalize_persian_for_search(chk.text)
                    conn.execute(
                        "INSERT INTO chunks_fts(chunk_ref, text, normalized_text) VALUES(?,?,?)",
                        (chk.chunk_ref, chk.text, norm_txt),
                    )
                    chunk_count += 1

        conn.commit()
        return {
            "capability": "FTS5_AVAILABLE",
            "indexed_documents": doc_count,
            "indexed_chunks": chunk_count,
            "indexed_sources": source_count,
            "db": str(db_path),
        }
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


def index_status(root: pathlib.Path, db_path: pathlib.Path | None = None) -> dict[str, Any]:
    """Check retrieval index status across four states: empty, fresh, stale, missing.

    Empty corpus with no index returns status='empty' and degraded=False ('nothing to index' != 'stale').
    """
    if db_path is None:
        db_path = root / "_search" / "retrieval.sqlite"

    profiles = load_profiles(root)
    governed = profiles.get("all-governed")
    if not governed:
        return {
            "status": "missing",
            "degraded": True,
            "reasons": ["all-governed profile is missing from configuration"],
            "corpus_documents": 0,
            "indexed_documents": 0,
        }

    corpus_files: dict[str, pathlib.Path] = {}
    for p in root.rglob("*"):
        if not p.is_file() or p.suffix.lower() not in TEXT_EXTS:
            continue
        rel = str(p.relative_to(root)).replace("\\", "/")
        if rel.startswith(".git/") or rel.startswith("_search/") or not profile_allows(rel, governed):
            continue
        corpus_files[rel] = p

    corpus_count = len(corpus_files)
    if corpus_count == 0:
        return {
            "status": "empty",
            "degraded": False,
            "reasons": [],
            "corpus_documents": 0,
            "indexed_documents": 0,
        }

    if not db_path.exists():
        return {
            "status": "missing",
            "degraded": True,
            "reasons": ["search index database file does not exist"],
            "corpus_documents": corpus_count,
            "indexed_documents": 0,
        }

    conn = sqlite3.connect(db_path)
    try:
        tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        if "docs" not in tables:
            return {
                "status": "missing",
                "degraded": True,
                "reasons": ["docs table missing from index database"],
                "corpus_documents": corpus_count,
                "indexed_documents": 0,
            }

        rows = conn.execute("SELECT path, content_sha256 FROM docs").fetchall()
        indexed_map = {r[0]: r[1] for r in rows}
        indexed_count = len(indexed_map)

        if set(corpus_files.keys()) != set(indexed_map.keys()):
            return {
                "status": "stale",
                "degraded": True,
                "reasons": ["search index stale: document set on disk does not match indexed documents"],
                "corpus_documents": corpus_count,
                "indexed_documents": indexed_count,
            }

        for rel, p in corpus_files.items():
            curr_sha = sha256_file(p)
            if curr_sha != indexed_map.get(rel):
                return {
                    "status": "stale",
                    "degraded": True,
                    "reasons": [f"search index stale: document modified ({rel})"],
                    "corpus_documents": corpus_count,
                    "indexed_documents": indexed_count,
                }

        return {
            "status": "fresh",
            "degraded": False,
            "reasons": [],
            "corpus_documents": corpus_count,
            "indexed_documents": indexed_count,
        }
    finally:
        conn.close()


def check_index_status(root: pathlib.Path, db_path: pathlib.Path | None = None) -> dict[str, Any]:
    return index_status(root, db_path)


def get_index_status(root: pathlib.Path, db_path: pathlib.Path | None = None) -> dict[str, Any]:
    return index_status(root, db_path)


def wiki_status(root: pathlib.Path, db_path: pathlib.Path | None = None) -> dict[str, Any]:
    """Overall status reporting degraded flag and search index semantics."""
    idx = index_status(root, db_path)
    return {
        "status": idx["status"],
        "degraded": idx["degraded"],
        "reasons": list(idx["reasons"]),
        "search_index": idx,
    }

