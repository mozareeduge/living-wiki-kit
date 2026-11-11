"""HTTP handlers for GET/POST /upload (rung H2), used by mcp_transport.http.

Not authenticated. The transport enables these only when the server runs in
the capture profile with --insecure-local-only on a loopback bind.
"""
from __future__ import annotations

import html
import json
from email.parser import BytesParser
from email.policy import HTTP
from http import HTTPStatus
from typing import Any

from .store import UploadError, UploadStore

LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost", "::1", "[::1]"})
_STATUS = {
    "E_UPLOAD_TOO_LARGE": HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
    "E_UPLOAD_TYPE": HTTPStatus.UNSUPPORTED_MEDIA_TYPE,
    "E_UPLOAD_EMPTY": HTTPStatus.BAD_REQUEST,
}
_MULTIPART_OVERHEAD = 64 * 1024
_DRAIN_LIMIT = 1024 * 1024

FORM_HTML = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Upload</title></head>
<body><h1>Upload a file</h1>
<form method="post" action="/upload" enctype="multipart/form-data">
<input type="file" name="file" required>
<button type="submit">Upload</button></form>
<p>Allowed types: {types}. Max size: {mb} MB. The returned ref is single use and
expires after {hours} h. Pass it to the wiki_ingest_file tool.</p></body></html>
"""


def is_loopback_host(host: str) -> bool:
    return host.strip().lower() in LOOPBACK_HOSTS


def _host_ok(handler: Any) -> bool:
    raw = (handler.headers.get("Host") or "").strip().lower()
    host = raw.rsplit("]:", 1)[0] + "]" if raw.startswith("[") and "]:" in raw else raw.rsplit(":", 1)[0] if raw.count(":") == 1 else raw
    return host in LOOPBACK_HOSTS


def _send(handler: Any, status: int, body: bytes, ctype: str) -> None:
    handler.send_response(status)
    handler.send_header("Content-Type", ctype)
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Cache-Control", "no-store")
    handler.end_headers()
    handler.wfile.write(body)


def _json(handler: Any, status: int, obj: dict[str, Any]) -> None:
    _send(handler, int(status), (json.dumps(obj, ensure_ascii=False) + "\n").encode("utf-8"), "application/json; charset=utf-8")


def _gate(handler: Any) -> UploadStore | None:
    """Return the store if uploads are allowed for this request, else answer 403."""
    store = getattr(handler, "upload_store", None)
    enabled = bool(getattr(handler, "insecure_local_only", False)) and store is not None and handler.profile_provider() == "capture"
    if not enabled:
        _json(handler, HTTPStatus.FORBIDDEN, {
            "ok": False, "code": "E_UPLOAD_DISABLED",
            "message": "uploads need --profile capture and --insecure-local-only on a loopback bind (no auth yet)",
        })
        return None
    if not _host_ok(handler):
        _json(handler, HTTPStatus.FORBIDDEN, {"ok": False, "code": "E_UPLOAD_HOST", "message": "loopback Host header required"})
        return None
    return store


def handle_upload_get(handler: Any) -> None:
    store = _gate(handler)
    if store is None:
        return
    from .store import allowed_extensions

    page = FORM_HTML.format(
        types=html.escape(", ".join(sorted(allowed_extensions()))),
        mb=store.max_bytes // (1024 * 1024) or "<1",
        hours=max(1, store.ttl // 3600),
    )
    _send(handler, HTTPStatus.OK, page.encode("utf-8"), "text/html; charset=utf-8")


def _drain(handler: Any) -> None:
    """Consume a small unread request body so the early error reply is not lost to a reset."""
    try:
        length = int(handler.headers.get("Content-Length", "0"))
    except ValueError:
        length = 0
    if 0 < length <= _DRAIN_LIMIT:
        handler.rfile.read(length)
    elif length > _DRAIN_LIMIT:
        handler.close_connection = True


def handle_upload_post(handler: Any) -> None:
    store = getattr(handler, "upload_store", None)
    if not (bool(getattr(handler, "insecure_local_only", False)) and store is not None and handler.profile_provider() == "capture") or not _host_ok(handler):
        _drain(handler)
        _gate(handler)
        return
    ctype = handler.headers.get("Content-Type", "")
    if not ctype.lower().startswith("multipart/form-data"):
        _drain(handler)
        return _json(handler, HTTPStatus.BAD_REQUEST, {"ok": False, "code": "E_UPLOAD_FORMAT", "message": "multipart/form-data required"})
    try:
        length = int(handler.headers.get("Content-Length", ""))
    except ValueError:
        return _json(handler, HTTPStatus.LENGTH_REQUIRED, {"ok": False, "code": "E_UPLOAD_FORMAT", "message": "Content-Length required"})
    if length < 0 or length > store.max_bytes + _MULTIPART_OVERHEAD:
        handler.close_connection = True
        return _json(handler, HTTPStatus.REQUEST_ENTITY_TOO_LARGE, {"ok": False, "code": "E_UPLOAD_TOO_LARGE", "message": f"upload exceeds {store.max_bytes} bytes"})
    raw = handler.rfile.read(length)
    try:
        msg = BytesParser(policy=HTTP).parsebytes(b"Content-Type: " + ctype.encode("latin-1") + b"\r\nMIME-Version: 1.0\r\n\r\n" + raw)
        part = next((p for p in msg.iter_parts() if p.get_param("name", header="content-disposition") == "file"), None)
        filename = part.get_filename() if part is not None else None
        data = part.get_payload(decode=True) if part is not None else None
    except Exception:  # noqa: BLE001
        part, filename, data = None, None, None
    if part is None or not filename or data is None:
        return _json(handler, HTTPStatus.BAD_REQUEST, {"ok": False, "code": "E_UPLOAD_FORMAT", "message": "multipart field 'file' with a filename required"})
    try:
        store.cleanup()
        out = store.save(filename, data)
    except UploadError as exc:
        return _json(handler, _STATUS.get(exc.code, HTTPStatus.BAD_REQUEST), {"ok": False, "code": exc.code, "message": exc.message})
    _json(handler, HTTPStatus.OK, {"ok": True, **out})
