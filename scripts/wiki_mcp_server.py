#!/usr/bin/env python3
"""Mozare governance MCP server — Engine 3 (agent surfaces).

Minimal MCP server (newline-delimited JSON-RPC 2.0 on stdio) exposing the
wiki to ANY AI harness under the house authority model:

  wiki_read(path)          - read one repository file text (read-only)
  wiki_search(query, n)    - deterministic BM25 retrieval via `qmd search`
  wiki_propose(kind, body) - submit a CANDIDATE-TIER proposal

Authority semantics (SYSTEM_DESIGN.md §3, §5.6; CLAUDE.md #4/#6):
  - Everything a model produces here is level-7 candidate material.
  - Proposals NEVER touch canonical objects: they append JSONL records to
    _proposals/proposals.jsonl for human adjudication.
  - Retrieval scores organize attention and are never evidence.
  - Reads of _originals/ are allowed; writes anywhere except _proposals/ do
    not exist as operations.

Register in .mcp.json:
  "wiki-governance": {"command": "<python>", "args": ["scripts/wiki_mcp_server.py"]}
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROPOSALS_DIR = ROOT / "_proposals"
PROPOSALS_LOG = PROPOSALS_DIR / "proposals.jsonl"
MAX_READ_BYTES = 400_000
MD_PATH_RE = re.compile(r"^[\w.\-/ ]+\.md$")

sys.path.insert(0, str(ROOT / "scripts" / "capture"))
try:
    import wiki_capture as _cap
    _CAPTURE_OK = True
except Exception:  # noqa: BLE001
    _cap = None
    _CAPTURE_OK = False

TOOLS = [
    {
        "name": "wiki_read",
        "description": (
            "Read one file from the Mozare Wiki repository (text content). "
            "Read-only. Originals under _originals/ are immutable artifacts - "
            "reading them is allowed; there is no write operation."),
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string",
                         "description": "repo-relative path, e.g. 05-claims/ai-report-authority-claim.md"},
            },
            "required": ["path"],
        },
    },
    {
        "name": "wiki_search",
        "description": (
            "Deterministic BM25 search over the indexed wiki via qmd. "
            "Scores rank attention only; they are never evidence and never "
            "upgrade authority tiers."),
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "n": {"type": "integer", "minimum": 1, "maximum": 20},
            },
            "required": ["query"],
        },
    },
    {
        "name": "wiki_exact",
        "description": (
            "Exact substring search over canonical zones (02-sources, "
            "03-objects, 04-notes, 05-claims, 06-relations). Deterministic "
            "grep; zero retrieval-model dependence. Navigation only, never "
            "evidence."),
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {"type": "string"},
                "limit": {"type": "integer", "minimum": 1, "maximum": 50},
            },
            "required": ["text"],
        },
    },
    {
        "name": "wiki_propose",
        "description": (
            "Submit a proposal for HUMAN adjudication (candidate tier, "
            "authority level 7 by construction). Kinds: relation-edge "
            "(target id + proposed type + why), claim-amendment, object-note. "
            "Proposals never modify canonical records directly."),
        "inputSchema": {
            "type": "object",
            "properties": {
                "kind": {"type": "string",
                         "enum": ["relation-edge", "claim-amendment", "object-note"]},
                "body": {"type": "string",
                         "description": "Full proposal content incl. target ids and rationale"},
            },
            "required": ["kind", "body"],
        },
    },
    {
        "name": "wiki_capture_text",
        "description": ("Create an unreviewed text capture (NONCANONICAL level 7). "
                        "No summary, title, or promotion happens here."),
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {"type": "string"},
                "channel": {"type": "string", "default": "mcp"},
                "language_hint": {"type": "string", "default": "unknown"},
            },
            "required": ["text"],
        },
    },
    {
        "name": "wiki_list_captures",
        "description": "List capture records by state, kind, or channel.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "state": {"type": "string"},
                "kind": {"type": "string"},
                "channel": {"type": "string"},
            },
        },
    },
    {
        "name": "wiki_read_capture",
        "description": "Return one capture record with its provenance.",
        "inputSchema": {
            "type": "object",
            "properties": {"id": {"type": "string"}},
            "required": ["id"],
        },
    },
    {
        "name": "wiki_get_media",
        "description": ("Return media referenced by a capture (base64 if <=1MB). "
                        "Only media of an allowed capture is reachable."),
        "inputSchema": {
            "type": "object",
            "properties": {"id": {"type": "string"}},
            "required": ["id"],
        },
    },
    {
        "name": "wiki_search_captures",
        "description": ("Search the NONCANONICAL capture collection only. "
                        "Never mixed with canonical search."),
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "state": {"type": "string"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "wiki_propose_from_capture",
        "description": ("Create a candidate promotion proposal citing capture IDs "
                        "and hashes. Never promotes directly."),
        "inputSchema": {
            "type": "object",
            "properties": {
                "ids": {"type": "array", "items": {"type": "string"}},
                "note": {"type": "string"},
            },
            "required": ["ids", "note"],
        },
    },
    {
        "name": "wiki_mark_capture_reviewed",
        "description": "Record a human review decision (actor + timestamp).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "id": {"type": "string"},
                "actor": {"type": "string"},
                "note": {"type": "string"},
            },
            "required": ["id", "actor"],
        },
    },
    {
        "name": "wiki_transcribe_capture",
        "description": ("Explicit transcription. Automatic adapters refuse until a "
                        "host benchmark passes; manual stores human text."),
        "inputSchema": {
            "type": "object",
            "properties": {
                "id": {"type": "string"},
                "adapter": {"type": "string", "default": "manual"},
                "text": {"type": "string"},
            },
            "required": ["id"],
        },
    },
]


def _safe_resolve(rel: str) -> Path | None:
    if not MD_PATH_RE.match(rel) or ".." in rel:
        return None
    p = (ROOT / rel).resolve()
    try:
        p.relative_to(ROOT.resolve())
    except ValueError:
        return None
    return p


def tool_wiki_read(args: dict) -> str:
    p = _safe_resolve(str(args.get("path", "")))
    if p is None or not p.is_file():
        return json.dumps({"error": "file not found or path rejected",
                           "path": args.get("path")})
    body = p.read_text(encoding="utf-8", errors="replace")
    truncated = len(body) > MAX_READ_BYTES
    return json.dumps({
        "path": str(p.relative_to(ROOT)).replace("\\", "/"),
        "bytes": len(body),
        "truncated": truncated,
        "content": body[:MAX_READ_BYTES],
        "authority_note": "Content authority per record frontmatter; this read grants no license to assert.",
    }, ensure_ascii=False)


def _qmd_query_lexical(query: str, n: int) -> list | None:
    """Hybrid route: typed query document `lex: <query>` - deterministic, no LLM.

    qmd 2.x grammar: a multi-line query document with typed lines
    (lex:/vec:/hyde:) runs WITHOUT LLM query expansion; a bare text query
    triggers the full expand pipeline (~2 min, model-backed). The MCP
    search surface uses the typed lexical form so results stay
    deterministic and fast; the full expansion remains available to
    context_pack with an explicit long timeout.
    """
    qmd = shutil.which("qmd")
    if not qmd:
        return None
    proc = subprocess.run(
        [qmd, "query", f"lex: {query}", "--no-rerank", "--json", "-n", str(n),
         "--collection", "wiki"],
        cwd=ROOT, text=True, capture_output=True, timeout=60,
    )
    if proc.returncode != 0:
        return None
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        return None


def tool_wiki_search(args: dict) -> str:
    query = str(args.get("query", "")).strip()
    n = int(args.get("n") or 5)
    n = max(1, min(n, 20))
    lexical = _qmd_query_lexical(query, n)
    if lexical is not None:
        payload = lexical
    else:
        qmd = shutil.which("qmd")
        if not qmd:
            return json.dumps({"error": "qmd not found on PATH"})
        proc = subprocess.run(
            [qmd, "search", query, "--json", "-n", str(n),
             "--collection", "wiki"],
            cwd=ROOT, text=True, capture_output=True, timeout=60,
        )
        try:
            payload = json.loads(proc.stdout)
        except json.JSONDecodeError:
            return json.dumps({"error": "qmd returned unparseable output",
                               "stderr": proc.stderr[:300]})
    # Spec §10: captures are noncanonical and never appear in canonical
    # search, even if the wiki collection also indexes the intake area.
    if isinstance(payload, list):
        payload = [h for h in payload
                   if "wiki-captures" not in str(h.get("file", ""))
                   and "01-inbox/captures" not in str(h.get("file", ""))]
    return json.dumps({
        "results": payload,
        "mode": "lexical-hybrid" if lexical is not None else "bm25",
        "authority_note": ("Retrieval scores organize attention and are never "
                           "evidence. Capture intake is excluded; use "
                           "wiki_search_captures for the noncanonical collection."),
    }, ensure_ascii=False)


def tool_wiki_exact(args: dict) -> str:
    """Exact substring search over tracked .md files - zero retrieval-model
    dependence. Deterministic grep over 02-sources/records, 03-objects,
    04-notes, 05-claims, 06-relations. Never evidence; navigation only."""
    needle = str(args.get("text", "")).strip()
    limit = int(args.get("limit") or 12)
    if not needle:
        return json.dumps({"error": "empty text"})
    hits = []
    zones = ("02-sources", "03-objects", "04-notes", "05-claims", "06-relations")
    for zone in zones:
        zone_dir = ROOT / zone
        if not zone_dir.exists():
            continue
        for md in sorted(zone_dir.rglob("*.md")):
            try:
                text = md.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            if needle in text:
                first = text.find(needle)
                line_no = text.count("\n", 0, first) + 1
                hits.append({
                    "file": md.relative_to(ROOT).as_posix(),
                    "line": line_no,
                    "context": text[max(0, first - 80):first + 120],
                })
                if len(hits) >= max(1, min(limit, 50)):
                    return json.dumps({"matches": hits, "truncated": False},
                                      ensure_ascii=False)
    return json.dumps({"matches": hits,
                       "truncated": len(hits) >= max(1, min(limit, 50))},
                      ensure_ascii=False)


def tool_wiki_propose(args: dict) -> str:
    kind = str(args.get("kind", ""))
    body = str(args.get("body", "")).strip()
    if kind not in ("relation-edge", "claim-amendment", "object-note"):
        return json.dumps({"error": f"unsupported kind: {kind!r}"})
    if not body:
        return json.dumps({"error": "empty proposal body"})
    PROPOSALS_DIR.mkdir(parents=True, exist_ok=True)
    record = {
        "id": f"prop-{datetime.now().strftime('%Y%m%d-%H%M%S-%f')[:-3]}",
        "received": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "kind": kind,
        "authority_tier": "candidate",
        "status": "new",
        "adjudication": None,
        "body": body[:20_000],
    }
    with PROPOSALS_LOG.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    return json.dumps({
        "accepted": True,
        "proposal_id": record["id"],
        "queue": "_proposals/proposals.jsonl",
        "note": "Candidate-tier only. A human adjudicates; nothing enters canonical records automatically.",
    }, ensure_ascii=False)


CAPTURE_NOTE = ("Captures are NONCANONICAL level-7 intake objects. "
                  "Promotion to the wiki happens only via wiki_propose_from_capture "
                  "plus human approval; never directly.")


def _need_cap():
    if not _CAPTURE_OK or _cap is None:
        return json.dumps({"error": "capture core unavailable on this host"})
    return None


def tool_wiki_capture_text(args: dict) -> str:
    err = _need_cap()
    if err:
        return err
    text = str(args.get("text", ""))
    channel = str(args.get("channel", "mcp"))
    lang = str(args.get("language_hint", "unknown"))
    try:
        r = _cap.capture_text(text, channel, lang)
    except _cap.CaptureError as e:
        return json.dumps({"ok": False, "code": e.code, "message": e.message})
    r["authority_note"] = CAPTURE_NOTE
    return json.dumps(r, ensure_ascii=False)


def tool_wiki_list_captures(args: dict) -> str:
    err = _need_cap()
    if err:
        return err
    r = _cap.list_captures(args.get("state"), args.get("kind"), args.get("channel"))
    r["authority_note"] = CAPTURE_NOTE
    return json.dumps(r, ensure_ascii=False)


def tool_wiki_read_capture(args: dict) -> str:
    err = _need_cap()
    if err:
        return err
    try:
        r = _cap.read_capture(str(args.get("id", "")))
    except _cap.CaptureError as e:
        return json.dumps({"ok": False, "code": e.code, "message": e.message})
    r["authority_note"] = CAPTURE_NOTE
    return json.dumps(r, ensure_ascii=False)


def tool_wiki_get_media(args: dict) -> str:
    import base64
    err = _need_cap()
    if err:
        return err
    try:
        r = _cap.read_capture(str(args.get("id", "")))
    except _cap.CaptureError as e:
        return json.dumps({"ok": False, "code": e.code, "message": e.message})
    raw = r["front_matter"].get("raw_media")
    if not raw:
        return json.dumps({"ok": False, "code": "E_NO_MEDIA",
                           "message": "capture has no media (text-only)"})
    mp = _cap._resolve_media(str(raw))
    try:
        data = mp.read_bytes()
    except OSError:
        return json.dumps({"ok": False, "code": "E_MEDIA_MISSING",
                           "message": "referenced media absent"})
    out = {"ok": True, "id": r["id"], "sha256": r["front_matter"]["sha256"],
           "bytes": len(data), "path": r["front_matter"]["raw_media"]}
    if len(data) <= 1_000_000:
        out["base64"] = base64.b64encode(data).decode("ascii")
    else:
        out["note"] = "media over 1MB: read it via the governed host path"
    return json.dumps(out)


def tool_wiki_search_captures(args: dict) -> str:
    err = _need_cap()
    if err:
        return err
    q = str(args.get("query", "")).strip().casefold()
    state = args.get("state")
    hits = []
    for p, fm in _cap._scan_records():
        if state and fm.get("status") != state:
            continue
        try:
            _, sections = _cap.parse_record_text(p.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        blob = "\n".join(sections.values()).casefold()
        if q and q not in blob:
            continue
        hits.append({"id": fm.get("id"), "status": fm.get("status"),
                     "kind": fm.get("capture_kind")})
        if len(hits) >= 20:
            break
    return json.dumps({"ok": True, "count": len(hits), "hits": hits,
                       "authority_note": CAPTURE_NOTE}, ensure_ascii=False)


def tool_wiki_propose_from_capture(args: dict) -> str:
    err = _need_cap()
    if err:
        return err
    ids = args.get("ids") or []
    note = str(args.get("note", "")).strip()
    if not ids or not note:
        return json.dumps({"error": "ids[] and note are required"})
    try:
        for cid in ids:
            _cap.read_capture(str(cid))
    except _cap.CaptureError as e:
        return json.dumps({"ok": False, "code": e.code, "message": e.message})
    return tool_wiki_propose({
        "kind": "object-note",
        "body": (f"Promotion proposal from captures {', '.join(map(str, ids))}. "
                 f"Hashes: " + ", ".join(
                     str(_cap.read_capture(str(i))['front_matter']['sha256'])[:16]
                     for i in ids) + f". Rationale: {note}"),
    })


def tool_wiki_mark_capture_reviewed(args: dict) -> str:
    err = _need_cap()
    if err:
        return err
    try:
        r = _cap.set_state(str(args.get("id", "")), "reviewed",
                           str(args.get("actor", "")), str(args.get("note", "")))
    except _cap.CaptureError as e:
        return json.dumps({"ok": False, "code": e.code, "message": e.message})
    return json.dumps(r, ensure_ascii=False)


def tool_wiki_transcribe_capture(args: dict) -> str:
    err = _need_cap()
    if err:
        return err
    sys.path.insert(0, str(ROOT / "scripts" / "capture"))
    try:
        from stt_contract import transcribe_capture
        r = transcribe_capture(str(args.get("id", "")),
                               str(args.get("adapter", "manual")),
                               None, args.get("text"))
    except _cap.CaptureError as e:
        return json.dumps({"ok": False, "code": e.code, "message": e.message})
    except Exception as exc:  # noqa: BLE001
        return json.dumps({"ok": False, "code": "E_ADAPTER",
                           "message": f"{type(exc).__name__}: {exc}"})
    return json.dumps(r, ensure_ascii=False)


DISPATCH = {
    "wiki_read": tool_wiki_read,
    "wiki_search": tool_wiki_search,
    "wiki_exact": tool_wiki_exact,
    "wiki_propose": tool_wiki_propose,
    "wiki_capture_text": tool_wiki_capture_text,
    "wiki_list_captures": tool_wiki_list_captures,
    "wiki_read_capture": tool_wiki_read_capture,
    "wiki_get_media": tool_wiki_get_media,
    "wiki_search_captures": tool_wiki_search_captures,
    "wiki_propose_from_capture": tool_wiki_propose_from_capture,
    "wiki_mark_capture_reviewed": tool_wiki_mark_capture_reviewed,
    "wiki_transcribe_capture": tool_wiki_transcribe_capture,
}


def handle(msg: dict) -> dict | None:
    method = msg.get("method")
    msg_id = msg.get("id")
    if method == "initialize":
        return {"jsonrpc": "2.0", "id": msg_id, "result": {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "wiki-governance", "version": "1.0.0"},
        }}
    if method is None or method.startswith("notifications/"):
        return None
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": msg_id, "result": {"tools": TOOLS}}
    if method == "tools/call":
        params = msg.get("params") or {}
        name = params.get("name")
        fn = DISPATCH.get(name)
        if fn is None:
            return {"jsonrpc": "2.0", "id": msg_id, "error":
                    {"code": -32602, "message": f"unknown tool: {name}"}}
        try:
            text = fn(params.get("arguments") or {})
        except Exception as exc:  # noqa: BLE001
            text = json.dumps({"error": f"{type(exc).__name__}: {exc}"})
        return {"jsonrpc": "2.0", "id": msg_id, "result": {
            "content": [{"type": "text", "text": text}],
            "isError": False,
        }}
    if msg_id is not None:
        return {"jsonrpc": "2.0", "id": msg_id, "error":
                {"code": -32601, "message": f"method not found: {method}"}}
    return None


def main() -> int:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue
        resp = handle(msg)
        if resp is not None:
            sys.stdout.write(json.dumps(resp, ensure_ascii=False) + "\n")
            sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
