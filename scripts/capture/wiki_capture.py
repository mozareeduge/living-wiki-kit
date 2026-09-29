#!/usr/bin/env python3
"""Governed multimodal capture core — Mozare Wiki 1.2.0 (Task 3).

Single library used by ALL channels (Telegram/Hermes hook, Obsidian intake,
MCP tools, CLI). Deterministic: no network, no model calls.

Responsibilities: ID generation, original-byte SHA-256, deduplication,
atomic storage, record creation, state machine, provenance-event append,
validation. Transcription/description are stored here but EXECUTED elsewhere
(stt_contract.py adapters, explicit manual action, or enabled local engine).

Authority: capture records + derived representations are level-7 candidate,
labeled noncanonical. Nothing here writes outside approved roots or touches
canonical areas.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import secrets
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

TOOL_VERSION = "1.2.0"
CAPTURE_SCHEMA_VERSION = "1.0.0"

REPO_ROOT = Path(__file__).resolve().parents[2]
CAPTURES_ROOT = REPO_ROOT / "01-inbox" / "captures"
MEDIA_DIRNAME = "media"
ORPHAN_QUARANTINE = CAPTURES_ROOT / ".quarantine"

MAX_BYTES = 25 * 1024 * 1024  # 25 MiB default cap per capture

ALLOWED_AUDIO = {".ogg", ".opus", ".oga", ".m4a", ".mp3", ".wav", ".flac", ".amr"}
ALLOWED_IMAGE = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".heic", ".tif", ".tiff"}
ALLOWED_FILE = {".pdf", ".txt", ".md", ".csv"}

KIND_FOR_SUFFIX = {s: "voice" for s in ALLOWED_AUDIO}
KIND_FOR_SUFFIX.update({s: "image" for s in ALLOWED_IMAGE})
KIND_FOR_SUFFIX.update({s: "file" for s in ALLOWED_FILE})

CAPTURE_KINDS = {"text", "voice", "handwriting", "drawing", "image", "file", "mixed"}
CHANNELS = {"telegram-hermes", "claude-mobile", "obsidian", "mcp", "filesystem"}
LANGS = {"fa", "en", "mixed", "unknown"}

# Minimal magic-byte table for MIME/extension cross-check (spec Task 12).
MAGIC = {
    ".ogg": [b"OggS"], ".opus": [b"OggS"], ".oga": [b"OggS"],
    ".wav": [b"RIFF"], ".flac": [b"fLaC"], ".mp3": [b"ID3", b"\xff\xfb", b"\xff\xf3", b"\xff\xf2"],
    ".m4a": [b"ftyp"], ".amr": [b"#!AMR"],
    ".jpg": [b"\xff\xd8\xff"], ".jpeg": [b"\xff\xd8\xff"],
    ".png": [b"\x89PNG\r\n\x1a\n"], ".gif": [b"GIF87a", b"GIF89a"],
    ".webp": [b"RIFF"], ".pdf": [b"%PDF"],
    ".tif": [b"II*\x00", b"MM\x00*"], ".tiff": [b"II*\x00", b"MM\x00*"],
}

TRANSITIONS = {
    "received": {"processing", "reviewed"},  # reviewed directly only for duplicates
    "processing": {"transcribed", "described", "needs-review", "processing-failed"},
    "transcribed": {"reviewed"},
    "described": {"reviewed"},
    "needs-review": {"reviewed"},
    "processing-failed": {"processing", "reviewed"},
    "reviewed": {"parked", "promoted"},
    "parked": set(),
    "promoted": set(),
}
TERMINAL = {"parked", "promoted"}

ID_RE = re.compile(r"^cap-\d{8}-\d{6}-[0-9a-f]{4}$")
HEX64_RE = re.compile(r"^[0-9a-f]{64}$")


class CaptureError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


# ---------------------------------------------------------------- front matter

FIELD_ORDER = ["id", "type", "title", "status", "capture_kind", "captured_at",
               "capture_channel", "language_hint", "raw_media",
               "raw_media_available", "sha256", "bytes", "duplicate_of",
               "transcription_state", "transcription_method",
               "transcription_version", "transcription_reviewed",
               "quality_flags", "promoted_to", "schema_version"]

BODY_SECTIONS = ["User-supplied text", "Literal transcript or extraction",
                 "Machine description", "Review notes", "Provenance events"]


def _yaml_val(v) -> str:
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, int):
        return str(v)
    if isinstance(v, list):
        return "[" + ", ".join(_yaml_val(x) for x in v) + "]"
    s = str(v)
    if s == "" or any(c in s for c in ":#[]{}&*?|->!%@`,\"' \t\n"):
        return json.dumps(s, ensure_ascii=False)
    return s


def _yaml_parse_val(s: str):
    s = s.strip()
    if s == "null" or s == "~":
        return None
    if s == "true":
        return True
    if s == "false":
        return False
    if s.startswith("[") and s.endswith("]"):
        inner = s[1:-1].strip()
        if not inner:
            return []
        return [_yaml_parse_val(p) for p in inner.split(",")]
    if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
        try:
            return json.loads(s) if s.startswith('"') else s[1:-1]
        except json.JSONDecodeError:
            return s[1:-1]
    try:
        return int(s)
    except ValueError:
        return s


def parse_record_text(text: str):
    """Split a capture record into (front_matter_dict, body_sections_dict)."""
    if not text.startswith("---\n"):
        raise CaptureError("E_BAD_RECORD", "record does not start with front matter")
    end = text.find("\n---", 4)
    if end == -1:
        raise CaptureError("E_BAD_RECORD", "front matter not closed")
    fm = {}
    for line in text[4:end].splitlines():
        if not line.strip() or line.strip().startswith("#"):
            continue
        if ":" not in line:
            raise CaptureError("E_BAD_RECORD", f"bad front matter line: {line!r}")
        k, v = line.split(":", 1)
        fm[k.strip()] = _yaml_parse_val(v)
    body = text[end + 4:]
    sections: dict[str, str] = {}
    cur = None
    buf: list[str] = []
    for line in body.splitlines(keepends=True):
        m = re.match(r"^## (.+?)\s*$", line)
        if m and m.group(1) in BODY_SECTIONS:
            if cur is not None:
                sections[cur] = "".join(buf)
            cur = m.group(1)
            buf = []
        elif cur is not None:
            buf.append(line)
    if cur is not None:
        sections[cur] = "".join(buf)
    # Render emits one blank line after each ## header and one separator blank
    # line before the next header. The writer invariant is that stored bodies
    # end with exactly one newline, so strip one leading and (when the body
    # is longer than a bare newline) one trailing newline to round-trip bytes.
    for k, v in sections.items():
        if v.startswith("\n"):
            v = v[1:]
        if v.endswith("\n\n"):
            v = v[:-1]
        sections[k] = v
    return fm, sections


def render_record(fm: dict, sections: dict) -> str:
    lines = ["---"]
    for k in FIELD_ORDER:
        lines.append(f"{k}: {_yaml_val(fm.get(k))}")
    lines.append("---")
    lines.append("# Capture")
    lines.append("")
    for s in BODY_SECTIONS:
        lines.append(f"## {s}")
        lines.append("")
        content = sections.get(s, "")
        if content:
            lines.append(content.rstrip("\n"))
            lines.append("")
    return "\n".join(lines)


# ------------------------------------------------------------------- helpers

def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _new_id(now: datetime | None = None) -> str:
    now = now or datetime.now().astimezone()
    stamp = now.strftime("%Y%m%d-%H%M%S")
    for _ in range(50):
        cid = f"cap-{stamp}-{secrets.token_hex(2)}"
        if not (record_path(cid)).exists():
            return cid
    raise CaptureError("E_ID_COLLISION", "could not mint a unique capture id")


def record_path(capture_id: str) -> Path:
    m = re.match(r"^cap-(\d{4})(\d{2})(\d{2})-\d{6}-[0-9a-f]{4}$", capture_id)
    if not m:
        raise CaptureError("E_BAD_ID", f"malformed capture id: {capture_id}")
    return CAPTURES_ROOT / m.group(1) / (m.group(1) + m.group(2)) / f"{capture_id}.md"


def media_path(capture_id: str, suffix: str) -> Path:
    return record_path(capture_id).parent / MEDIA_DIRNAME / f"{capture_id}{suffix}"


def _canon(p: Path) -> str:
    """Canonical comparison key: normcase + realpath, with the Win32
    extended-path (\\?\) prefix stripped. Needed because concurrent
    resolve() calls on Windows can return prefixed and plain forms
    for paths under the same tree, breaking relative_to()."""
    s = os.path.normcase(os.path.realpath(p))
    if s.startswith("\\\\?\\"):
        s = s[4:]
    return s


def _safe_within(path: Path, root: Path) -> Path:
    dest, base = _canon(path), _canon(root)
    if dest != base and not dest.startswith(base + os.sep):
        raise CaptureError("E_TRAVERSAL", f"path escapes approved root: {path}")
    return path


def _repo_rel(p: Path) -> str:
    """Repo-relative display path; absolute fallback outside the repo (tests)."""
    try:
        return str(p.relative_to(REPO_ROOT)).replace(os.sep, "/")
    except ValueError:
        return str(p).replace(os.sep, "/")


def _resolve_media(raw: str) -> Path:
    mp = Path(raw)
    return mp if mp.is_absolute() else REPO_ROOT / raw


def _atomic_write_bytes(dest: Path, data: bytes) -> None:
    _safe_within(dest, CAPTURES_ROOT)
    dest.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(dest.parent), prefix=".tmp-")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        os.replace(tmp, dest)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _scan_records():
    """Yield (path, front_matter) for every capture record. Deterministic."""
    if not CAPTURES_ROOT.exists():
        return
    for p in sorted(CAPTURES_ROOT.rglob("cap-*.md")):
        try:
            fm, _ = parse_record_text(p.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, CaptureError):
            continue
        yield p, fm


def find_by_hash(sha256: str) -> str | None:
    for _, fm in _scan_records():
        if fm.get("sha256") == sha256:
            return fm.get("id")
    return None


def _check_magic(suffix: str, head: bytes) -> bool:
    magics = MAGIC.get(suffix)
    if not magics:
        return True  # no signature known; extension allowlist governs
    if suffix in (".m4a", ".webp"):
        return magics[0] in head
    return any(head.startswith(m) for m in magics)


def _event_line(action: str, outcome: str, detail: str) -> str:
    return f"- {_now_iso()} | {action} | wiki_capture.py {TOOL_VERSION} | {outcome} | {detail}"


def _blank_sections() -> dict:
    return {s: "" for s in BODY_SECTIONS}


# ------------------------------------------------------------------ creation

def _finalize_record(fm: dict, sections: dict) -> Path:
    dest = record_path(fm["id"])
    if dest.exists():
        raise CaptureError("E_EXISTS", f"record already exists: {fm['id']}")
    _atomic_write_bytes(dest, render_record(fm, sections).encode("utf-8"))
    return dest


def capture_text(text: str, channel: str, language_hint: str = "unknown") -> dict:
    if channel not in CHANNELS:
        raise CaptureError("E_BAD_CHANNEL", f"unknown channel: {channel}")
    if language_hint not in LANGS:
        raise CaptureError("E_BAD_LANG", f"unknown language hint: {language_hint}")
    canonical = text.rstrip("\n") + "\n" if text.strip() else ""
    if not canonical:
        raise CaptureError("E_EMPTY", "text capture is empty")
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    dup = find_by_hash(digest)
    cid = _new_id()
    sections = _blank_sections()
    sections["User-supplied text"] = canonical
    sections["Provenance events"] = _event_line("created", "ok", f"sha256:{digest[:16]}") + "\n"
    fm = {"id": cid, "type": "capture", "title": f"Capture {cid}", "status": "received",
          "capture_kind": "text", "captured_at": _now_iso(),
          "capture_channel": channel, "language_hint": language_hint,
          "raw_media": None, "raw_media_available": False,
          "sha256": digest, "bytes": len(canonical.encode("utf-8")),
          "duplicate_of": dup,
          "transcription_state": "not-requested", "transcription_method": None,
          "transcription_version": None, "transcription_reviewed": False,
          "quality_flags": [], "promoted_to": None,
          "schema_version": CAPTURE_SCHEMA_VERSION}
    if dup:
        sections["Provenance events"] += _event_line("duplicate-of", "ok", dup) + "\n"
    dest = _finalize_record(fm, sections)
    return {"ok": True, "id": cid, "status": "received", "path": _repo_rel(dest),
            "sha256": digest, "bytes": fm["bytes"], "duplicate_of": dup,
            "message": f"duplicate of {dup}" if dup else "text capture stored"}


def capture_media(src: str, kind: str, channel: str,
                  language_hint: str = "unknown") -> dict:
    if kind not in CAPTURE_KINDS or kind == "text":
        raise CaptureError("E_BAD_KIND", f"media capture needs a non-text kind: {kind}")
    if channel not in CHANNELS:
        raise CaptureError("E_BAD_CHANNEL", f"unknown channel: {channel}")
    if language_hint not in LANGS:
        raise CaptureError("E_BAD_LANG", f"unknown language hint: {language_hint}")
    src_path = Path(src)
    if src_path.is_symlink():
        raise CaptureError("E_SYMLINK", "source is a symlink; symlinks are never followed")
    if not src_path.is_file():
        raise CaptureError("E_NOT_FOUND", f"source file not found: {src}")
    suffix = src_path.suffix.lower()
    allowed = ALLOWED_AUDIO | ALLOWED_IMAGE | ALLOWED_FILE
    if suffix not in allowed:
        raise CaptureError("E_UNSUPPORTED_TYPE", f"unsupported media type: {suffix}")
    expected = KIND_FOR_SUFFIX[suffix]
    if kind in ("voice", "handwriting", "drawing", "image", "file") and kind != expected and not (
            kind in ("handwriting", "drawing") and expected == "image"):
        raise CaptureError("E_MEDIA_MISMATCH",
                           f"declared kind {kind!r} does not match file type {suffix} ({expected})")
    size = src_path.stat().st_size
    if size > MAX_BYTES:
        raise CaptureError("E_OVERSIZE", f"{size} bytes exceeds cap of {MAX_BYTES}")
    if size == 0:
        raise CaptureError("E_EMPTY", "source file is empty")
    data = src_path.read_bytes()  # bounded by MAX_BYTES check above
    if not _check_magic(suffix, data[:32]):
        raise CaptureError("E_MIME_MISMATCH",
                           f"file header does not match extension {suffix}")
    digest = hashlib.sha256(data).hexdigest()
    dup = find_by_hash(digest)
    cid = _new_id()
    dest_media = media_path(cid, suffix)
    _atomic_write_bytes(dest_media, data)  # media first; record second (recoverable gap)
    try:
        sections = _blank_sections()
        sections["Provenance events"] = _event_line("created", "ok",
                                                    f"sha256:{digest[:16]}") + "\n"
        fm = {"id": cid, "type": "capture", "title": f"Capture {cid}", "status": "received",
              "capture_kind": kind, "captured_at": _now_iso(),
              "capture_channel": channel, "language_hint": language_hint,
              "raw_media": _repo_rel(dest_media),
              "raw_media_available": True,
              "sha256": digest, "bytes": size, "duplicate_of": dup,
              "transcription_state": ("pending" if kind == "voice" else "not-requested"),
              "transcription_method": None, "transcription_version": None,
              "transcription_reviewed": False,
              "quality_flags": [], "promoted_to": None,
              "schema_version": CAPTURE_SCHEMA_VERSION}
        if dup:
            sections["Provenance events"] += _event_line("duplicate-of", "ok", dup) + "\n"
        dest = _finalize_record(fm, sections)
    except BaseException:
        try:
            dest_media.unlink()  # roll back orphaned media on record failure
        except OSError:
            pass
        raise
    return {"ok": True, "id": cid, "status": "received",
            "path": _repo_rel(dest),
            "media": fm["raw_media"], "sha256": digest, "bytes": size,
            "duplicate_of": dup,
            "message": f"duplicate of {dup}" if dup else f"{kind} capture stored"}


# -------------------------------------------------------------------- access

def _load(capture_id: str):
    if not ID_RE.match(capture_id):
        raise CaptureError("E_BAD_ID", f"malformed capture id: {capture_id}")
    p = record_path(capture_id)
    _safe_within(p, CAPTURES_ROOT)
    if not p.is_file():
        raise CaptureError("E_NOT_FOUND", f"no such capture: {capture_id}")
    return p, parse_record_text(p.read_text(encoding="utf-8"))


def read_capture(capture_id: str) -> dict:
    p, (fm, sections) = _load(capture_id)
    return {"ok": True, "id": capture_id, "path": _repo_rel(p),
            "front_matter": fm, "sections": sections}


def list_captures(state: str | None = None, kind: str | None = None,
                  channel: str | None = None, since: str | None = None) -> dict:
    rows = []
    for p, fm in _scan_records():
        if state and fm.get("status") != state:
            continue
        if kind and fm.get("capture_kind") != kind:
            continue
        if channel and fm.get("capture_channel") != channel:
            continue
        if since and str(fm.get("captured_at", "")) < since:
            continue
        rows.append({"id": fm.get("id"), "status": fm.get("status"),
                     "kind": fm.get("capture_kind"), "channel": fm.get("capture_channel"),
                     "captured_at": fm.get("captured_at"),
                     "path": _repo_rel(p)})
    return {"ok": True, "count": len(rows), "captures": rows}


def set_state(capture_id: str, new_state: str, actor: str,
              note: str = "", target: str | None = None) -> dict:
    if new_state not in TRANSITIONS:
        raise CaptureError("E_BAD_STATE", f"unknown state: {new_state}")
    if not actor.strip():
        raise CaptureError("E_NO_ACTOR", "state changes require a named human actor")
    p, (fm, sections) = _load(capture_id)
    cur = fm.get("status")
    if new_state not in TRANSITIONS.get(cur, set()):
        raise CaptureError("E_BAD_TRANSITION", f"illegal transition {cur} -> {new_state}")
    if cur == "received" and new_state == "reviewed" and not fm.get("duplicate_of"):
        raise CaptureError("E_BAD_TRANSITION",
                           "received -> reviewed is allowed only for duplicate records")
    if new_state == "promoted":
        if not target:
            raise CaptureError("E_NO_TARGET", "promotion requires a target path")
        if ".." in target or target.startswith("/") or "\\" in target:
            raise CaptureError("E_TRAVERSAL", f"illegal promotion target: {target}")
        fm["promoted_to"] = target
    fm["status"] = new_state
    if note:
        prev = sections.get("Review notes", "")
        sections["Review notes"] = (prev + f"- {_now_iso()} [{actor}] {note}\n")
    events = sections.get("Provenance events", "")
    events += _event_line(f"state:{new_state}", "ok", f"actor:{actor}") + "\n"
    sections["Provenance events"] = events
    _atomic_write_bytes(p, render_record(fm, sections).encode("utf-8"))
    return {"ok": True, "id": capture_id, "status": new_state,
            "message": f"{capture_id}: {cur} -> {new_state} by {actor}"}


def record_transcript(capture_id: str, text: str, adapter: str, version: str,
                      segments: list | None = None, reviewed: bool = False,
                      quality_flags: list | None = None) -> dict:
    """Store a literal transcript (machine or human-corrected). Never summarizes."""
    p, (fm, sections) = _load(capture_id)
    if fm.get("capture_kind") not in ("voice", "mixed"):
        raise CaptureError("E_WRONG_KIND", "transcripts attach only to voice/mixed captures")
    canonical = text.rstrip("\n") + "\n" if text.strip() else ""
    if not canonical:
        raise CaptureError("E_EMPTY", "transcript text is empty")
    sections["Literal transcript or extraction"] = canonical
    fm["transcription_state"] = "complete"
    fm["transcription_method"] = adapter
    fm["transcription_version"] = version
    fm["transcription_reviewed"] = bool(reviewed)
    if quality_flags:
        fm["quality_flags"] = sorted(set(fm.get("quality_flags", [])) | set(quality_flags))
    if segments:
        provare = sections.get("Provenance events", "")
        provare += _event_line("transcript-segments", "ok", f"n={len(segments)}") + "\n"
        sections["Provenance events"] = provare
        sidecar = p.with_suffix(".segments.json")
        _atomic_write_bytes(sidecar, json.dumps(
            {"id": capture_id, "segments": segments}, ensure_ascii=False, indent=1).encode("utf-8"))
    events = sections.get("Provenance events", "")
    events += _event_line("transcribed", "ok", f"{adapter} {version}") + "\n"
    sections["Provenance events"] = events
    _atomic_write_bytes(p, render_record(fm, sections).encode("utf-8"))
    return {"ok": True, "id": capture_id, "message": f"transcript stored ({adapter} {version})"}


def record_description(capture_id: str, literal: str, description: str,
                       adapter: str, version: str) -> dict:
    """Keep literal visible text and interpretive description strictly separate."""
    p, (fm, sections) = _load(capture_id)
    if fm.get("capture_kind") not in ("handwriting", "drawing", "image", "mixed", "file"):
        raise CaptureError("E_WRONG_KIND", "descriptions attach only to visual/file captures")
    if literal is not None:
        sections["Literal transcript or extraction"] = (
            literal.rstrip("\n") + "\n" if literal.strip() else "")
    if description is not None:
        sections["Machine description"] = (
            description.rstrip("\n") + "\n" if description.strip() else "")
    events = sections.get("Provenance events", "")
    events += _event_line("described", "ok", f"{adapter} {version}") + "\n"
    sections["Provenance events"] = events
    _atomic_write_bytes(p, render_record(fm, sections).encode("utf-8"))
    return {"ok": True, "id": capture_id, "message": f"description stored ({adapter} {version})"}


# ---------------------------------------------------------------- validation

def validate_record(capture_id_or_path: str) -> list[str]:
    errors: list[str] = []
    p = Path(capture_id_or_path)
    if not p.is_absolute():
        p = REPO_ROOT / capture_id_or_path if not ID_RE.match(capture_id_or_path) else None
    if p is None:
        p = record_path(capture_id_or_path)
    try:
        _safe_within(p, CAPTURES_ROOT)
    except CaptureError as e:
        return [f"{e.code}: {e.message}"]
    if not p.is_file():
        return ["E_NOT_FOUND: record file missing"]
    try:
        fm, sections = parse_record_text(p.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, CaptureError) as e:
        return [f"E_BAD_RECORD: {e}"]
    cid = fm.get("id")
    if not cid or not ID_RE.match(str(cid)):
        errors.append("E_BAD_ID: missing or malformed id")
    if p.name != f"{cid}.md":
        errors.append("E_FILENAME_MISMATCH: filename does not match record id")
    for f in FIELD_ORDER:
        if f not in fm:
            errors.append(f"E_MISSING_FIELD: {f}")
    if fm.get("type") != "capture":
        errors.append("E_BAD_TYPE: type must be 'capture'")
    if fm.get("status") not in TRANSITIONS:
        errors.append(f"E_BAD_STATE: {fm.get('status')}")
    if fm.get("capture_kind") not in CAPTURE_KINDS:
        errors.append(f"E_BAD_KIND: {fm.get('capture_kind')}")
    if fm.get("capture_channel") not in CHANNELS:
        errors.append(f"E_BAD_CHANNEL: {fm.get('capture_channel')}")
    if fm.get("language_hint") not in LANGS:
        errors.append(f"E_BAD_LANG: {fm.get('language_hint')}")
    if fm.get("schema_version") != CAPTURE_SCHEMA_VERSION:
        errors.append(f"E_BAD_SCHEMA: schema_version must be {CAPTURE_SCHEMA_VERSION}")
    if not fm.get("sha256") or not HEX64_RE.match(str(fm.get("sha256") or "")):
        errors.append("E_BAD_HASH: sha256 must be lowercase hex")
    for s in BODY_SECTIONS:
        if s not in sections:
            errors.append(f"E_MISSING_SECTION: {s}")
    # media integrity: recompute hash from bytes
    raw = fm.get("raw_media")
    if raw:
        if ".." in str(raw):  # containment below is the rule on every OS; a leading "/" check rejected valid Linux paths
            errors.append("E_TRAVERSAL: raw_media escapes roots")
        else:
            mp = _resolve_media(str(raw))
            try:
                _safe_within(mp, CAPTURES_ROOT)
            except CaptureError:
                errors.append("E_TRAVERSAL: raw_media escapes roots")
                mp = None
            if mp is None:
                pass
            elif not mp.is_file():
                errors.append("E_MEDIA_MISSING: referenced media file absent")
            elif hashlib.sha256(mp.read_bytes()).hexdigest() != fm.get("sha256"):
                errors.append("E_HASH_MISMATCH: media bytes do not match recorded sha256")
            elif mp.stat().st_size != fm.get("bytes"):
                errors.append("E_SIZE_MISMATCH: media size does not match recorded bytes")
            else:
                exp = KIND_FOR_SUFFIX.get(mp.suffix.lower())
                kind = fm.get("capture_kind")
                kind_ok = (kind == exp or kind == "mixed"
                           or (kind in ("handwriting", "drawing") and exp == "image"))
                if not kind_ok:
                    errors.append(f"E_MEDIA_MISMATCH: kind {kind!r} vs file type {mp.suffix}")
    else:
        if fm.get("capture_kind") == "text":
            body_text = sections.get("User-supplied text", "")
            if hashlib.sha256(body_text.encode("utf-8")).hexdigest() != fm.get("sha256"):
                errors.append("E_HASH_MISMATCH: text bytes do not match recorded sha256")
    # state-path audit from provenance events
    states = ["received"]
    for line in sections.get("Provenance events", "").splitlines():
        m = re.search(r"\|\s*state:([a-z-]+)\s*\|", line)
        if m:
            states.append(m.group(1))
    for a, b in zip(states, states[1:]):
        if b not in TRANSITIONS.get(a, set()):
            errors.append(f"E_BAD_TRANSITION: event path shows {a} -> {b}")
            break
    if fm.get("status") != states[-1]:
        errors.append(f"E_STATE_DIVERGED: status {fm.get('status')} != event path tip {states[-1]}")
    return errors


def recover_orphans() -> dict:
    """Adopt media files that lost their record (crash between the two writes)."""
    adopted, quarantined = [], []
    if not CAPTURES_ROOT.exists():
        return {"ok": True, "adopted": adopted, "quarantined": quarantined}
    known_media = set()
    for _, fm in _scan_records():
        if fm.get("raw_media"):
            known_media.add(REPO_ROOT / str(fm["raw_media"]))
    for mp in sorted(CAPTURES_ROOT.rglob(f"{MEDIA_DIRNAME}/cap-*")):
        if mp in known_media or mp.name.startswith(".tmp-"):
            continue
        try:
            digest = hashlib.sha256(mp.read_bytes()).hexdigest()
        except OSError:
            continue
        dup = find_by_hash(digest)
        if dup:
            ORPHAN_QUARANTINE.mkdir(parents=True, exist_ok=True)
            dest = ORPHAN_QUARANTINE / mp.name
            mp.replace(dest)
            quarantined.append({"file": mp.name, "duplicate_of": dup})
            continue
        m = re.match(r"^(cap-\d{8}-\d{6}-[0-9a-f]{4})", mp.name)
        cid = m.group(1) if m else _new_id()
        sections = _blank_sections()
        sections["Provenance events"] = (
            _event_line("recovered-orphan", "ok", f"sha256:{digest[:16]}") + "\n"
            + _event_line("state:processing", "ok", "recovery-replay") + "\n"
            + _event_line("state:processing-failed", "ok", "adopted-without-record") + "\n")
        fm = {"id": cid, "type": "capture", "title": f"Capture {cid}", "status": "processing-failed",
              "capture_kind": KIND_FOR_SUFFIX.get(mp.suffix.lower(), "file"),
              "captured_at": _now_iso(), "capture_channel": "filesystem",
              "language_hint": "unknown",
              "raw_media": _repo_rel(mp),
              "raw_media_available": True, "sha256": digest,
              "bytes": mp.stat().st_size, "duplicate_of": None,
              "transcription_state": "not-requested", "transcription_method": None,
              "transcription_version": None, "transcription_reviewed": False,
              "quality_flags": ["recovered-orphan"], "promoted_to": None,
              "schema_version": CAPTURE_SCHEMA_VERSION}
        dest = record_path(cid)
        if dest.exists():
            ORPHAN_QUARANTINE.mkdir(parents=True, exist_ok=True)
            mp.replace(ORPHAN_QUARANTINE / mp.name)
            quarantined.append({"file": mp.name, "reason": "id-collision"})
            continue
        _atomic_write_bytes(dest, render_record(fm, sections).encode("utf-8"))
        adopted.append(cid)
    return {"ok": True, "adopted": adopted, "quarantined": quarantined}


# ----------------------------------------------------------------------- CLI

def _out(obj: dict, as_json: bool) -> int:
    if as_json:
        print(json.dumps(obj, ensure_ascii=False, indent=1))
    else:
        if obj.get("ok"):
            print(obj.get("message", "ok"))
            for k in ("id", "status", "path", "media", "duplicate_of"):
                if obj.get(k) is not None:
                    print(f"  {k}: {obj[k]}")
        else:
            print(f"ERROR {obj.get('code')}: {obj.get('message')}", file=sys.stderr)
    return 0 if obj.get("ok") else 1


def main(argv: list[str] | None = None) -> int:
    try:
        _safe_within(CAPTURES_ROOT, REPO_ROOT)  # production invariant
    except CaptureError as e:
        print(f"ERROR {e.code}: {e.message}", file=sys.stderr)
        return 1
    ap = argparse.ArgumentParser(prog="wiki_capture",
                                 description="Governed capture core (deterministic, zero LLM calls)")
    ap.add_argument("--json", action="store_true")
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("capture-text")
    c.add_argument("--channel", required=True, choices=sorted(CHANNELS))
    c.add_argument("--lang", default="unknown", choices=sorted(LANGS))
    c.add_argument("--text", required=True)

    m = sub.add_parser("capture-media")
    m.add_argument("--src", required=True)
    m.add_argument("--kind", required=True,
                   choices=sorted(k for k in CAPTURE_KINDS if k != "text"))
    m.add_argument("--channel", required=True, choices=sorted(CHANNELS))
    m.add_argument("--lang", default="unknown", choices=sorted(LANGS))

    l = sub.add_parser("list")
    l.add_argument("--state", default=None)
    l.add_argument("--kind", default=None)
    l.add_argument("--channel", default=None)

    r = sub.add_parser("read")
    r.add_argument("id")

    s = sub.add_parser("set-state")
    s.add_argument("id")
    s.add_argument("state")
    s.add_argument("--actor", required=True)
    s.add_argument("--note", default="")
    s.add_argument("--target", default=None)

    v = sub.add_parser("validate")
    v.add_argument("id_or_path", nargs="?")  # omit to validate all

    ct = sub.add_parser("commit-transcript")
    ct.add_argument("--id", required=True)
    ct.add_argument("--adapter", default="manual")
    ct.add_argument("--version", default="v1")
    ct.add_argument("--text", default=None)
    ct.add_argument("--text-file", default=None)

    sub.add_parser("recover")
    # Accept --json before or after the subcommand (argparse subparsers
    # only honor parent flags placed before the subcommand word).
    argv = list(sys.argv[1:] if argv is None else argv)
    as_json = "--json" in argv
    argv = [a for a in argv if a != "--json"]
    args = ap.parse_args(argv)
    try:
        if args.cmd == "capture-text":
            return _out(capture_text(args.text, args.channel, args.lang), as_json)
        if args.cmd == "capture-media":
            return _out(capture_media(args.src, args.kind, args.channel, args.lang), as_json)
        if args.cmd == "list":
            obj = list_captures(args.state, args.kind, args.channel)
            if as_json:
                return _out(obj, True)
            for row in obj["captures"]:
                print(f"{row['id']}  {row['status']:16} {row['kind']:12} {row['captured_at']}")
            print(f"{obj['count']} capture(s)")
            return 0
        if args.cmd == "read":
            return _out(read_capture(args.id), as_json)
        if args.cmd == "set-state":
            return _out(set_state(args.id, args.state, args.actor, args.note, args.target), as_json)
        if args.cmd == "commit-transcript":
            text = args.text
            if args.text_file:
                text = Path(args.text_file).read_text(encoding="utf-8")
            return _out(record_transcript(args.id, text or "", args.adapter,
                                          args.version), as_json)
        if args.cmd == "validate":
            if args.id_or_path:
                errs = validate_record(args.id_or_path)
                if errs:
                    return _out({"ok": False, "code": "E_INVALID",
                                         "message": "; ".join(errs)}, as_json)
                return _out({"ok": True, "message": f"{args.id_or_path}: valid"}, as_json)
            bad = {}
            n = 0
            for _, fm in _scan_records():
                n += 1
                errs = validate_record(fm["id"])
                if errs:
                    bad[fm["id"]] = errs
            if bad:
                return _out({"ok": False, "code": "E_INVALID",
                                     "message": json.dumps(bad, ensure_ascii=False)}, as_json)
            return _out({"ok": True, "message": f"all {n} capture(s) valid"}, as_json)
        if args.cmd == "recover":
            return _out({**recover_orphans(), "message": "recovery pass complete"}, as_json)
    except CaptureError as e:
        return _out({"ok": False, "code": e.code, "message": e.message}, as_json)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
