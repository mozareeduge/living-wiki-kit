#!/usr/bin/env python3
"""Mozare Wiki governance MCP server — capability-scoped vNext surface.

Default profile: read (no writes).
Capture profile: adds noncanonical capture/proposal operations only.
Canonical-write operations do not exist on this MCP surface.

Retrieval contract:
- exact + SQLite FTS5 are the correctness/portability floor;
- QMD is optional enhancement over the collections named in the instance's QMD config;
- QMD hits are reopened from the current checkout before consumption;
- ranking never upgrades evidence authority.
"""
from __future__ import annotations

import argparse
import base64
import json
import pathlib
import shutil
import subprocess
import sys
from typing import Any, Callable

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from gov_kernel.proposals import create_proposal  # noqa: E402
from gov_kernel.qmd_guard import govern_qmd_hits  # noqa: E402
from gov_kernel.retrieval import (  # noqa: E402
    build_index,
    exact_resolve,
    load_profiles,
    search_fts,
)
from gov_kernel.state import load_state  # noqa: E402

sys.path.insert(0, str(ROOT / "scripts" / "capture"))
try:
    import wiki_capture as _cap  # type: ignore  # noqa: E402
    _CAPTURE_OK = True
except Exception:  # noqa: BLE001
    _cap = None
    _CAPTURE_OK = False

MAX_READ_BYTES = 400_000
TEXT_EXTS = {".md", ".json", ".jsonl", ".yaml", ".yml", ".txt", ".base"}
FTS_DB = ROOT / "_search" / "governance.sqlite"
QMD_CONFIG = "00-system/configuration/qmd-collections-v1.1.0.json"
QMD_CANONICAL_DIRS = ("03-objects", "04-notes", "05-claims", "06-relations", "07-genesis")
QMD_PROVENANCE_DIRS = ("02-sources/records",)


def qmd_collections(root: pathlib.Path) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """(canonical, provenance) QMD collection names, chosen by folder from the
    instance's QMD config, so no instance's collection names are hardcoded.
    No config means no QMD enhancement; the portable FTS floor still works."""
    try:
        cfg = json.loads((root / QMD_CONFIG).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return (), ()
    cols = [c for c in cfg.get("collections", []) if c.get("name") and c.get("path")]
    canonical = tuple(c["name"] for c in cols if c["path"].strip("/") in QMD_CANONICAL_DIRS)
    provenance = tuple(c["name"] for c in cols if c["path"].strip("/") in QMD_PROVENANCE_DIRS)
    return canonical, provenance

ACTIVE_PROFILE = "read"


def _safe_text_path(raw: str) -> pathlib.Path | None:
    if not raw or ".." in pathlib.PurePosixPath(raw.replace("\\", "/")).parts:
        return None
    p = (ROOT / raw).resolve()
    try:
        p.relative_to(ROOT.resolve())
    except ValueError:
        return None
    if p.suffix.lower() not in TEXT_EXTS:
        return None
    return p


def _read_text(path: pathlib.Path) -> dict[str, Any]:
    if not path.is_file():
        return {"error": "file not found", "path": str(path)}
    body = path.read_text(encoding="utf-8", errors="replace")
    return {
        "path": path.relative_to(ROOT).as_posix(),
        "bytes": len(body.encode("utf-8")),
        "truncated": len(body) > MAX_READ_BYTES,
        "content": body[:MAX_READ_BYTES],
        "authority_note": "Reading exposes repository text only; authority remains record/source-specific.",
    }


def _ensure_fts() -> None:
    if FTS_DB.exists():
        return
    build_index(ROOT, FTS_DB)


def _qmd_search(query: str, collections: tuple[str, ...], n: int, profile: str) -> list[dict[str, Any]]:
    qmd = shutil.which("qmd")
    if not qmd:
        return []
    raw_hits: list[dict[str, Any]] = []
    per = max(2, min(n, 8))
    for collection in collections:
        try:
            cp = subprocess.run(
                [qmd, "search", query, "--json", "-n", str(per), "--collection", collection],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=20,
            )
        except (OSError, subprocess.TimeoutExpired):
            continue
        if cp.returncode:
            continue
        try:
            rows = json.loads(cp.stdout or "[]")
        except json.JSONDecodeError:
            continue
        if not isinstance(rows, list):
            continue
        for row in rows:
            if not isinstance(row, dict):
                continue
            raw = str(row.get("file") or row.get("path") or "").replace("\\", "/")
            # QMD versions may prefix collection/name. Strip only when a real repo path follows.
            candidates = [raw]
            if "/" in raw:
                candidates.append(raw.split("/", 1)[1])
            chosen = next((x for x in candidates if (ROOT / x).is_file()), raw)
            raw_hits.append({
                "path": chosen,
                "score": row.get("score"),
                "snippet": row.get("snippet") or row.get("text"),
                "collection": collection,
            })
    accepted, _ = govern_qmd_hits(ROOT, raw_hits, profile)
    # deterministic dedupe by path, preserving first collection-ranked occurrence
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for hit in accepted:
        path = str(hit.get("path") or "")
        if path in seen:
            continue
        seen.add(path)
        hit["backend"] = "qmd"
        hit["authority_note"] = "QMD ranks attention only; current bytes were reopened from the checkout."
        out.append(hit)
        if len(out) >= n:
            break
    return out


def tool_wiki_read_text(args: dict[str, Any]) -> str:
    p = _safe_text_path(str(args.get("path", "")))
    if p is None:
        return json.dumps({"error": "path rejected or non-text-safe extension", "path": args.get("path")})
    return json.dumps(_read_text(p), ensure_ascii=False)


def tool_wiki_get_record(args: dict[str, Any]) -> str:
    q = str(args.get("id_or_path") or args.get("id") or args.get("path") or "").strip()
    if not q:
        return json.dumps({"error": "id_or_path is required"})
    p = _safe_text_path(q)
    if p and p.is_file():
        return json.dumps(_read_text(p), ensure_ascii=False)
    hits = exact_resolve(ROOT, q, "canonical")
    if not hits:
        hits = exact_resolve(ROOT, q, "provenance")
    if not hits:
        return json.dumps({"error": "record not found", "query": q})
    path = ROOT / hits[0]["path"]
    return json.dumps({**hits[0], **_read_text(path)}, ensure_ascii=False)


def tool_wiki_search(args: dict[str, Any]) -> str:
    query = str(args.get("query", "")).strip()
    n = max(1, min(int(args.get("n") or 8), 20))
    profile = str(args.get("profile") or "canonical")
    if profile not in {"canonical", "provenance", "evidence-text", "accepted-evidence", "system"}:
        return json.dumps({"error": "profile not allowed", "profile": profile})
    try:
        _ensure_fts()
        portable = search_fts(ROOT, FTS_DB, query, profile, n)
    except Exception as exc:  # noqa: BLE001
        portable = {"capability": "FTS5_UNAVAILABLE", "reason": f"{type(exc).__name__}: {exc}", "results": []}
    canonical_cols, provenance_cols = qmd_collections(ROOT)
    qmd_cols = provenance_cols if profile == "provenance" else canonical_cols if profile == "canonical" else ()
    qmd_hits = _qmd_search(query, qmd_cols, n, profile) if qmd_cols else []
    return json.dumps({
        "profile": profile,
        "portable": portable,
        "qmd": {"available": bool(shutil.which("qmd")), "results": qmd_hits},
        "authority_note": "Retrieval ranks attention only. Opened repository/source records carry authority.",
    }, ensure_ascii=False)


def tool_wiki_resolve_id(args: dict[str, Any]) -> str:
    q = str(args.get("id", "")).strip()
    results = []
    for profile in ("canonical", "provenance", "system"):
        try:
            results.extend(exact_resolve(ROOT, q, profile))
        except Exception:
            continue
    seen: set[str] = set()
    uniq = []
    for row in results:
        if row["path"] in seen:
            continue
        seen.add(row["path"]); uniq.append(row)
    return json.dumps({"id": q, "results": uniq}, ensure_ascii=False)


def tool_wiki_get_source(args: dict[str, Any]) -> str:
    q = str(args.get("id_or_path") or args.get("id") or "").strip()
    hits = exact_resolve(ROOT, q, "provenance")
    if not hits:
        return json.dumps({"error": "source record not found", "query": q})
    p = ROOT / hits[0]["path"]
    return json.dumps({**hits[0], **_read_text(p), "note": "Binary originals are not emitted through the text MCP surface."}, ensure_ascii=False)


def tool_wiki_state(args: dict[str, Any]) -> str:
    try:
        return json.dumps(load_state(ROOT), ensure_ascii=False)
    except Exception as exc:  # noqa: BLE001
        return json.dumps({"error": f"{type(exc).__name__}: {exc}"})


def _need_capture() -> str | None:
    if ACTIVE_PROFILE != "capture":
        return json.dumps({"error": "capture capability disabled; start server with --profile capture"})
    if not _CAPTURE_OK or _cap is None:
        return json.dumps({"error": "capture core unavailable"})
    return None


def tool_wiki_capture_text(args: dict[str, Any]) -> str:
    err = _need_capture()
    if err: return err
    try:
        out = _cap.capture_text(str(args.get("text", "")), str(args.get("channel", "mcp")), str(args.get("language_hint", "unknown")))
    except _cap.CaptureError as exc:
        return json.dumps({"ok": False, "code": exc.code, "message": exc.message})
    out["authority_note"] = "Noncanonical level-7 capture; promotion requires review/adjudication."
    return json.dumps(out, ensure_ascii=False)


def tool_wiki_list_captures(args: dict[str, Any]) -> str:
    err = _need_capture()
    if err: return err
    out = _cap.list_captures(args.get("state"), args.get("kind"), args.get("channel"))
    return json.dumps(out, ensure_ascii=False)


def tool_wiki_read_capture(args: dict[str, Any]) -> str:
    err = _need_capture()
    if err: return err
    try:
        return json.dumps(_cap.read_capture(str(args.get("id", ""))), ensure_ascii=False)
    except _cap.CaptureError as exc:
        return json.dumps({"ok": False, "code": exc.code, "message": exc.message})


def tool_wiki_get_capture_media(args: dict[str, Any]) -> str:
    err = _need_capture()
    if err: return err
    try:
        rec = _cap.read_capture(str(args.get("id", "")))
        raw = rec["front_matter"].get("raw_media")
        if not raw:
            return json.dumps({"ok": False, "code": "E_NO_MEDIA"})
        p = _cap._resolve_media(str(raw))
        data = p.read_bytes()
        out = {"ok": True, "id": rec["id"], "sha256": rec["front_matter"]["sha256"], "bytes": len(data), "path": raw}
        if len(data) <= 1_000_000:
            out["base64"] = base64.b64encode(data).decode("ascii")
        else:
            out["note"] = "media over 1MB; use the governed local path"
        return json.dumps(out)
    except _cap.CaptureError as exc:
        return json.dumps({"ok": False, "code": exc.code, "message": exc.message})
    except OSError as exc:
        return json.dumps({"ok": False, "code": "E_MEDIA_MISSING", "message": str(exc)})


def tool_wiki_search_captures(args: dict[str, Any]) -> str:
    err = _need_capture()
    if err: return err
    q = str(args.get("query", "")).casefold().strip(); state = args.get("state")
    hits = []
    for p, fm in _cap._scan_records():
        if state and fm.get("status") != state: continue
        try:
            _, sections = _cap.parse_record_text(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        if q and q not in "\n".join(sections.values()).casefold(): continue
        hits.append({"id": fm.get("id"), "status": fm.get("status"), "kind": fm.get("capture_kind")})
        if len(hits) >= 20: break
    return json.dumps({"count": len(hits), "hits": hits,
                       "authority_note": "Noncanonical level-7 captures only; never canonical evidence."},
                      ensure_ascii=False)


def tool_wiki_propose(args: dict[str, Any]) -> str:
    err = _need_capture()
    if err: return err
    kind = str(args.get("kind", "")).strip(); body = str(args.get("body", "")).strip()
    if not kind or not body:
        return json.dumps({"error": "kind and body are required"})
    try:
        p = create_proposal(
            ROOT,
            kind=kind,
            body=body,
            submitted_by={"actor_type": "agent", "tool": "mcp", "session_ref": args.get("session_ref")},
            evidence_refs=[str(x) for x in (args.get("evidence_refs") or [])],
            target_refs=[str(x) for x in (args.get("target_refs") or [])],
        )
        return json.dumps({"accepted": True, "proposal_path": p.relative_to(ROOT).as_posix(), "authority_tier": "candidate"})
    except Exception as exc:  # noqa: BLE001
        return json.dumps({"error": f"{type(exc).__name__}: {exc}"})


def tool_wiki_propose_from_capture(args: dict[str, Any]) -> str:
    err = _need_capture()
    if err: return err
    ids = [str(x) for x in (args.get("ids") or [])]; note = str(args.get("note", "")).strip()
    if not ids or not note:
        return json.dumps({"error": "ids[] and note are required"})
    hashes = []
    try:
        for cid in ids:
            rec = _cap.read_capture(cid); hashes.append(str(rec["front_matter"].get("sha256") or ""))
    except _cap.CaptureError as exc:
        return json.dumps({"ok": False, "code": exc.code, "message": exc.message})
    return tool_wiki_propose({
        "kind": "capture-promotion",
        "body": f"Promotion proposal for captures {', '.join(ids)}. Rationale: {note}",
        "evidence_refs": [f"capture:{cid}:{sha}" for cid, sha in zip(ids, hashes)],
        "target_refs": [],
    })


CONTEXT_PACK_MAX_RECORDS = 30
CONTEXT_PACK_MAX_BUDGET = 16000
CONTEXT_PACK_MAX_HOPS = 2


def _clamped_int(value: Any, lo: int, hi: int, default: int) -> int:
    """int(value) clamped to [lo, hi]; only None falls back to the default
    (0 is a real answer, e.g. hops=0). A non-numeric value raises, which
    handle() reports as a JSON error."""
    if value is None:
        return default
    return max(lo, min(int(value), hi))


def tool_wiki_context_pack(args: dict[str, Any]) -> str:
    """Read-only wrapper over context_pack.build_pack (ported from
    living-wiki-kit rung W2). Writes nothing; the pack is returned inline."""
    seed = str(args.get("seed", "")).strip()
    if not seed:
        return json.dumps({"error": "empty seed"})
    hops = _clamped_int(args.get("hops"), 0, CONTEXT_PACK_MAX_HOPS, 1)
    records = _clamped_int(args.get("records"), 1, CONTEXT_PACK_MAX_RECORDS, CONTEXT_PACK_MAX_RECORDS)
    budget = _clamped_int(args.get("budget"), 1, CONTEXT_PACK_MAX_BUDGET, CONTEXT_PACK_MAX_BUDGET)
    query = str(args.get("query") or "").strip() or None
    if not (ROOT / "_search" / "graph.db").exists():
        return json.dumps({"error": "no graph index; run `python scripts/build_graph_index.py` first"})
    import context_pack as _context_pack
    try:
        pack = _context_pack.build_pack(ROOT, seed, hops, query, records, budget)
    except SystemExit:
        # build_pack signals an unknown seed with SystemExit; that must never
        # take the whole MCP server down
        return json.dumps({"error": f"seed id {seed!r} not in graph index"})
    return json.dumps(pack, ensure_ascii=False)


def tool_wiki_mark_capture_reviewed(args: dict[str, Any]) -> str:
    """Capture-state change only (received/transcribed -> reviewed); the
    capture core refuses it without a named human actor. Never promotes."""
    err = _need_capture()
    if err: return err
    try:
        out = _cap.set_state(str(args.get("id", "")), "reviewed", str(args.get("actor", "")), str(args.get("note", "")))
    except _cap.CaptureError as exc:
        return json.dumps({"ok": False, "code": exc.code, "message": exc.message})
    return json.dumps(out, ensure_ascii=False)


def tool_wiki_transcribe_capture(args: dict[str, Any]) -> str:
    """Explicit transcription through stt_contract; automatic adapters refuse
    until a host benchmark passes, `manual` stores human-supplied text."""
    err = _need_capture()
    if err: return err
    try:
        from stt_contract import transcribe_capture
        out = transcribe_capture(str(args.get("id", "")), str(args.get("adapter", "manual")), None, args.get("text"))
    except _cap.CaptureError as exc:
        return json.dumps({"ok": False, "code": exc.code, "message": exc.message})
    except Exception as exc:  # noqa: BLE001
        return json.dumps({"ok": False, "code": "E_ADAPTER", "message": f"{type(exc).__name__}: {exc}"})
    return json.dumps(out, ensure_ascii=False)


READ_TOOLS = [
    {"name": "wiki_read_text", "description": "Read a text-safe repository file.", "inputSchema": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}},
    {"name": "wiki_get_record", "description": "Resolve and read one canonical/provenance record by id or path.", "inputSchema": {"type": "object", "properties": {"id_or_path": {"type": "string"}}, "required": ["id_or_path"]}},
    {"name": "wiki_search", "description": "Governed portable search with optional QMD enhancement.", "inputSchema": {"type": "object", "properties": {"query": {"type": "string"}, "n": {"type": "integer", "minimum": 1, "maximum": 20}, "profile": {"type": "string"}}, "required": ["query"]}},
    {"name": "wiki_resolve_id", "description": "Resolve an exact record id across governed profiles.", "inputSchema": {"type": "object", "properties": {"id": {"type": "string"}}, "required": ["id"]}},
    {"name": "wiki_get_source", "description": "Read a source-record/provenance record; binary originals are not emitted.", "inputSchema": {"type": "object", "properties": {"id_or_path": {"type": "string"}}, "required": ["id_or_path"]}},
    {"name": "wiki_state", "description": "Return authoritative SYSTEM_STATE.json.", "inputSchema": {"type": "object", "properties": {}}},
    {"name": "wiki_context_pack", "description": (
        "Read-only governed context pack around ONE seed record id: the seed, its graph "
        "neighbours (0-2 hops over resolved wikilink / relation / claim edges) and optional "
        "lexical hits, each with a reason, under hard caps (30 records, 16k estimated tokens). "
        "Find the seed id first with wiki_search / wiki_resolve_id. Needs _search/graph.db "
        "(python scripts/build_graph_index.py). A navigation aid: inclusion reasons and scores "
        "are never evidence and output built from a pack stays candidate-tier."),
     "inputSchema": {"type": "object", "properties": {
         "seed": {"type": "string", "description": "record id, e.g. mw-src-1111111111"},
         "hops": {"type": "integer", "minimum": 0, "maximum": 2, "description": "graph expansion depth (default 1)"},
         "query": {"type": "string", "description": "optional lexical query to add hits"},
         "records": {"type": "integer", "minimum": 1, "maximum": 30},
         "budget": {"type": "integer", "minimum": 1, "maximum": 16000, "description": "estimated-token budget"}},
         "required": ["seed"]}},
]
CAPTURE_TOOLS = [
    {"name": "wiki_capture_text", "description": "Create a noncanonical text capture.", "inputSchema": {"type": "object", "properties": {"text": {"type": "string"}, "channel": {"type": "string"}, "language_hint": {"type": "string"}}, "required": ["text"]}},
    {"name": "wiki_list_captures", "description": "List noncanonical captures.", "inputSchema": {"type": "object", "properties": {"state": {"type": "string"}, "kind": {"type": "string"}, "channel": {"type": "string"}}}},
    {"name": "wiki_read_capture", "description": "Read one noncanonical capture.", "inputSchema": {"type": "object", "properties": {"id": {"type": "string"}}, "required": ["id"]}},
    {"name": "wiki_get_capture_media", "description": "Return governed capture media metadata/base64 when <=1MB.", "inputSchema": {"type": "object", "properties": {"id": {"type": "string"}}, "required": ["id"]}},
    {"name": "wiki_search_captures", "description": "Search only the noncanonical capture store.", "inputSchema": {"type": "object", "properties": {"query": {"type": "string"}, "state": {"type": "string"}}, "required": ["query"]}},
    {"name": "wiki_propose", "description": "Create an immutable candidate proposal. Never writes canonical records.", "inputSchema": {"type": "object", "properties": {"kind": {"type": "string"}, "body": {"type": "string"}, "evidence_refs": {"type": "array", "items": {"type": "string"}}, "target_refs": {"type": "array", "items": {"type": "string"}}, "session_ref": {"type": "string"}}, "required": ["kind", "body"]}},
    {"name": "wiki_propose_from_capture", "description": "Create a candidate proposal grounded in capture ids/hashes.", "inputSchema": {"type": "object", "properties": {"ids": {"type": "array", "items": {"type": "string"}}, "note": {"type": "string"}}, "required": ["ids", "note"]}},
    {"name": "wiki_mark_capture_reviewed", "description": "Record a human review of a capture (named actor + timestamp). Capture state only; never promotes.", "inputSchema": {"type": "object", "properties": {"id": {"type": "string"}, "actor": {"type": "string"}, "note": {"type": "string"}}, "required": ["id", "actor"]}},
    {"name": "wiki_transcribe_capture", "description": "Explicit transcription. Automatic adapters refuse until a host benchmark passes; manual stores human text.", "inputSchema": {"type": "object", "properties": {"id": {"type": "string"}, "adapter": {"type": "string", "default": "manual"}, "text": {"type": "string"}}, "required": ["id"]}},
]

DISPATCH: dict[str, Callable[[dict[str, Any]], str]] = {
    "wiki_read_text": tool_wiki_read_text,
    "wiki_get_record": tool_wiki_get_record,
    "wiki_search": tool_wiki_search,
    "wiki_resolve_id": tool_wiki_resolve_id,
    "wiki_get_source": tool_wiki_get_source,
    "wiki_state": tool_wiki_state,
    "wiki_context_pack": tool_wiki_context_pack,
    "wiki_capture_text": tool_wiki_capture_text,
    "wiki_list_captures": tool_wiki_list_captures,
    "wiki_read_capture": tool_wiki_read_capture,
    "wiki_get_capture_media": tool_wiki_get_capture_media,
    "wiki_search_captures": tool_wiki_search_captures,
    "wiki_propose": tool_wiki_propose,
    "wiki_propose_from_capture": tool_wiki_propose_from_capture,
    "wiki_mark_capture_reviewed": tool_wiki_mark_capture_reviewed,
    "wiki_transcribe_capture": tool_wiki_transcribe_capture,
    # compatibility aliases are intentionally not advertised
    "wiki_read": tool_wiki_read_text,
    "wiki_exact": tool_wiki_resolve_id,
}


def advertised_tools() -> list[dict[str, Any]]:
    return READ_TOOLS + (CAPTURE_TOOLS if ACTIVE_PROFILE == "capture" else [])


def handle(msg: dict[str, Any]) -> dict[str, Any] | None:
    method = msg.get("method"); msg_id = msg.get("id")
    if method == "initialize":
        return {"jsonrpc": "2.0", "id": msg_id, "result": {"protocolVersion": "2024-11-05", "capabilities": {"tools": {}}, "serverInfo": {"name": "wiki-governance", "version": "2.0.0"}}}
    if method is None or str(method).startswith("notifications/"):
        return None
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": msg_id, "result": {"tools": advertised_tools()}}
    if method == "tools/call":
        params = msg.get("params") or {}; name = str(params.get("name") or "")
        allowed = {x["name"] for x in advertised_tools()}
        if name not in allowed:
            return {"jsonrpc": "2.0", "id": msg_id, "error": {"code": -32602, "message": f"tool not enabled in {ACTIVE_PROFILE!r} profile: {name}"}}
        fn = DISPATCH.get(name)
        if fn is None:
            return {"jsonrpc": "2.0", "id": msg_id, "error": {"code": -32602, "message": f"unknown tool: {name}"}}
        try:
            text = fn(params.get("arguments") or {})
            is_error = False
        except Exception as exc:  # noqa: BLE001
            text = json.dumps({"error": f"{type(exc).__name__}: {exc}"}); is_error = True
        return {"jsonrpc": "2.0", "id": msg_id, "result": {"content": [{"type": "text", "text": text}], "isError": is_error}}
    if msg_id is not None:
        return {"jsonrpc": "2.0", "id": msg_id, "error": {"code": -32601, "message": f"method not found: {method}"}}
    return None


def main() -> int:
    global ACTIVE_PROFILE
    ap = argparse.ArgumentParser(); ap.add_argument("--profile", choices=["read", "capture"], default="read")
    args = ap.parse_args(); ACTIVE_PROFILE = args.profile
    # JSON-RPC over stdio is UTF-8 by contract. A piped stdio on Windows
    # defaults to the locale code page, which cannot carry Persian text.
    sys.stdin.reconfigure(encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
    # Fail closed on broken profile config at process start.
    load_profiles(ROOT)
    for line in sys.stdin:
        line = line.strip()
        if not line: continue
        try: msg = json.loads(line)
        except json.JSONDecodeError: continue
        resp = handle(msg)
        if resp is not None:
            sys.stdout.write(json.dumps(resp, ensure_ascii=False) + "\n"); sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
