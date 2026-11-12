"""E1/E2: enrichment sidecar (level 7, non-evidence, outside the corpus).

Store: ``_search/enrichment/<source_ref>.jsonl`` -- append-only revisions.
Nothing here edits a record, capture, source or original. Deleting the
whole directory must not change any validator result.
"""
from __future__ import annotations

import datetime as dt
import json
import pathlib
import re
import sqlite3
from typing import Any

import jsonschema

from .ingest import _lock_file, _unlock_file

ENRICH_DIR = "_search/enrichment"
FAILED_DIR = "_search/enrichment/_failed"
SCHEMA_FILE = "enrichment-revision.schema.json"
RELATIONS = ("about", "mentions", "part_of_project", "related_to", "supports", "contradicts")
_REF_SAFE = re.compile(r"^[A-Za-z0-9._:-]{1,200}$")  # real refs are rec:<id> / doc:<sha>
_VER = re.compile(r"^[0-9a-f]{64}$")
PENDING_MAX = 5
CHUNK_CHAR_BUDGET = 6000  # page-sized chunk text per source in a pending item


class EnrichmentError(Exception):
    def __init__(self, code: str, message: str, **extra: Any):
        super().__init__(message)
        self.code, self.message, self.extra = code, message, extra

    def to_dict(self) -> dict[str, Any]:
        return {"ok": False, "code": self.code, "error": self.code, "message": self.message, **self.extra}


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _fname(source_ref: str) -> str:
    """File-safe name (':' is not allowed in Windows file names)."""
    return source_ref.replace(":", "%3A")


def _sidecar(root: pathlib.Path, source_ref: str) -> pathlib.Path:
    if not _REF_SAFE.match(source_ref or "") or source_ref.startswith("."):
        raise EnrichmentError("E_INVALID", f"unsafe source_ref: {source_ref!r}")
    return root / ENRICH_DIR / f"{_fname(source_ref)}.jsonl"


def load_revisions(root: pathlib.Path, source_ref: str) -> list[dict[str, Any]]:
    p = _sidecar(root, source_ref)
    if not p.exists():
        return []
    return [json.loads(line) for line in p.read_text(encoding="utf-8").splitlines() if line.strip()]


def _open_index(root: pathlib.Path) -> sqlite3.Connection:
    db = root / "_search" / "retrieval.sqlite"
    if not db.exists():
        raise EnrichmentError("E_INDEX_MISSING", "chunk index missing (_search/retrieval.sqlite); rebuild the index")
    return sqlite3.connect(f"file:{db.as_posix()}?mode=ro", uri=True)


def _validate_shape(root: pathlib.Path, record: dict[str, Any]) -> list[str]:
    schema = json.loads((root / "00-system/schemas" / SCHEMA_FILE).read_text(encoding="utf-8"))
    v = jsonschema.Draft202012Validator(schema)
    return [("/".join(str(x) for x in e.absolute_path) or "(root)") + ": " + e.message
            for e in sorted(v.iter_errors(record), key=lambda e: list(e.absolute_path))]


def _check_texts(conn: sqlite3.Connection, source_ref: str, version: str, ann: dict[str, Any]) -> list[str]:
    errs: list[str] = []
    cache: dict[str, str | None] = {}

    def chunk_text(ref: str, where: str) -> str | None:
        if ref not in cache:
            row = conn.execute("SELECT source_ref, source_version, text FROM chunks WHERE chunk_ref=?", (ref,)).fetchone()
            cache[ref] = row[2] if row and row[0] == source_ref and row[1] == version else None
        if cache[ref] is None:
            errs.append(f"{where}: chunk {ref} is not a current chunk of {source_ref}")
        return cache[ref]

    for i, ent in enumerate(ann.get("entities") or []):
        m = ent["mention"]
        t = chunk_text(m["chunk_ref"], f"entities[{i}].mention")
        if t is not None and m["text"] not in t:
            errs.append(f"entities[{i}].mention.text is not an exact substring of {m['chunk_ref']}")
    for i, link in enumerate(ann.get("links") or []):
        for j, ev in enumerate(link["evidence"]):
            t = chunk_text(ev["chunk_ref"], f"links[{i}].evidence[{j}]")
            if t is not None and ev["quote"] not in t:
                errs.append(f"links[{i}].evidence[{j}].quote is not an exact substring of {ev['chunk_ref']}")
    for i, ca in enumerate(ann.get("chunk_annotations") or []):
        chunk_text(ca["chunk_ref"], f"chunk_annotations[{i}]")
    return errs


def _log_failure(root: pathlib.Path, source_ref: str, version: str, errors: list[str]) -> None:
    p = root / FAILED_DIR / f"{_fname(source_ref)}.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps({"source_version": version, "at": _now(), "errors": errors[:5]}, ensure_ascii=False) + "\n")


def submit(root: pathlib.Path, args: dict[str, Any]) -> dict[str, Any]:
    """Append one revision. Returns {ok, revision, ...} or raises EnrichmentError."""
    source_ref = str(args.get("source_ref") or "")
    version = str(args.get("source_version") or "")
    key = str(args.get("idempotency_key") or "")
    exp = args.get("expected_annotation_revision")
    side = _sidecar(root, source_ref)
    if not isinstance(exp, int) or isinstance(exp, bool) or exp < 0:
        raise EnrichmentError("E_INVALID", "expected_annotation_revision (integer >= 0) is required")
    if not _VER.match(version):
        raise EnrichmentError("E_INVALID", "source_version must be 64 hex chars")
    conn = _open_index(root)
    try:
        row = conn.execute("SELECT source_version FROM sources WHERE source_ref=?", (source_ref,)).fetchone()
        if row is None:
            raise EnrichmentError("E_UNKNOWN_SOURCE", f"source_ref not in the index: {source_ref}")
        if row[0] != version:
            raise EnrichmentError("E_STALE_SOURCE", "source_version is not current", current_source_version=row[0])

        side.parent.mkdir(parents=True, exist_ok=True)
        with open(side.parent / f".{_fname(source_ref)}.lock", "a+b") as lf:
            _lock_file(lf)
            try:
                revs = load_revisions(root, source_ref)
                for r in revs:
                    if r["idempotency_key"] == key:
                        return {"ok": True, "replayed": True, "revision": r["revision"], "source_ref": source_ref}
                latest = revs[-1]["revision"] if revs else 0
                if exp != latest:
                    raise EnrichmentError("E_REVISION_CONFLICT",
                                          f"expected_annotation_revision {exp} != current {latest}",
                                          current_revision=latest)
                record = {
                    "source_ref": source_ref, "source_version": version, "revision": latest + 1,
                    "idempotency_key": key, "producer": args.get("producer"), "created_at": _now(),
                    "authority_level": 7, "non_evidence": True, "annotation": args.get("annotation"),
                }
                errs = _validate_shape(root, record)
                if not errs:
                    errs = _check_texts(conn, source_ref, version, record["annotation"])
                if errs:
                    _log_failure(root, source_ref, version, errs)
                    raise EnrichmentError("E_VALIDATION", "; ".join(errs[:10]), errors=errs)
                with open(side, "a", encoding="utf-8", newline="\n") as f:
                    f.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
                return {"ok": True, "replayed": False, "revision": latest + 1, "source_ref": source_ref,
                        "authority_level": 7, "non_evidence": True}
            finally:
                _unlock_file(lf)
    finally:
        conn.close()


def _failed_versions(root: pathlib.Path, source_ref: str) -> set[str]:
    p = root / FAILED_DIR / f"{_fname(source_ref)}.jsonl"
    if not p.exists():
        return set()
    return {json.loads(ln)["source_version"] for ln in p.read_text(encoding="utf-8").splitlines() if ln.strip()}


def pending(root: pathlib.Path, *, limit: int = PENDING_MAX, cursor: str | None = None,
            retry_failed: bool = False) -> dict[str, Any]:
    """Sources whose current version has no revision. Read-only."""
    limit = max(1, min(int(limit), PENDING_MAX))
    conn = _open_index(root)
    try:
        rows = conn.execute(
            "SELECT source_ref, source_version, tier FROM sources WHERE source_ref > ? "
            "AND source_ref IN (SELECT source_ref FROM chunks) ORDER BY source_ref", (cursor or "",)
        ).fetchall()
        items: list[dict[str, Any]] = []
        more = False
        for ref, ver, tier in rows:
            if not _REF_SAFE.match(ref) or ref.startswith("."):
                continue
            revs = load_revisions(root, ref)
            if any(r["source_version"] == ver for r in revs):
                continue
            if not retry_failed and ver in _failed_versions(root, ref):
                continue
            if len(items) == limit:
                more = True
                break
            chunks, used, total, trunc = [], 0, 0, False
            for cref, s, e, text in conn.execute(
                    "SELECT chunk_ref, start, end, text FROM chunks WHERE source_ref=? AND source_version=? "
                    "ORDER BY start", (ref, ver)):
                total += 1
                if trunc or (chunks and used + len(text) > CHUNK_CHAR_BUDGET):
                    trunc = True
                    continue
                used += len(text)
                chunks.append({"chunk_ref": cref, "span": {"start": s, "end": e}, "text": text})
            items.append({"source_ref": ref, "source_version": ver, "tier": tier,
                          "expected_annotation_revision": revs[-1]["revision"] if revs else 0,
                          "chunks": chunks, "chunks_total": total, "chunks_truncated": trunc})
        return {"ok": True, "items": items, "next_cursor": items[-1]["source_ref"] if more else None,
                "authority_note": "enrichment is level 7, non-evidence; quote only chunk text"}
    finally:
        conn.close()


def anchored_chunks(annotation: dict[str, Any]) -> list[str]:
    """Chunk refs an annotation is anchored to (chunk notes, entity mentions, link evidence), in order."""
    refs: list[str] = []
    for ca in annotation.get("chunk_annotations") or []:
        refs.append(ca["chunk_ref"])
    for ent in annotation.get("entities") or []:
        refs.append(ent["mention"]["chunk_ref"])
    for link in annotation.get("links") or []:
        refs.extend(ev["chunk_ref"] for ev in link["evidence"])
    return list(dict.fromkeys(refs))


def current_revision(root: pathlib.Path, source_ref: str, version: str) -> dict[str, Any] | None:
    """Latest revision of a source, only if it was made for the current source version."""
    try:
        revs = load_revisions(root, source_ref)
    except (EnrichmentError, ValueError, OSError):
        return None
    if revs and revs[-1].get("source_version") == version:
        return revs[-1]
    return None


def tool_submit(root: pathlib.Path, args: dict[str, Any]) -> str:
    try:
        return json.dumps(submit(root, args), ensure_ascii=False)
    except EnrichmentError as e:
        return json.dumps(e.to_dict(), ensure_ascii=False)


def tool_pending(root: pathlib.Path, args: dict[str, Any]) -> str:
    try:
        return json.dumps(pending(root, limit=args.get("limit", PENDING_MAX), cursor=args.get("cursor"),
                                  retry_failed=bool(args.get("retry_failed"))), ensure_ascii=False)
    except EnrichmentError as e:
        return json.dumps(e.to_dict(), ensure_ascii=False)
