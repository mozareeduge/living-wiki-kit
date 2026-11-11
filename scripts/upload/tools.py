"""MCP tool ``wiki_ingest_file``: consumes an upload ref, never a path."""
from __future__ import annotations

import json
import pathlib
from typing import Any, Callable

from .store import UploadError, UploadStore

INGEST_TOOL_DESCRIPTION = (
    "Ingest a file previously uploaded on the /upload page. Takes the single-use "
    "upload_ref (upl-...) returned by that page; arbitrary paths are never accepted. "
    "Returns the ingest receipt (source_ref, sha256, extraction status, chunk_count)."
)
INGEST_TOOL_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "upload_ref": {"type": "string", "description": "single-use ref from the upload page"},
        "title": {"type": "string"},
        "description": {"type": "string"},
        "request_id": {"type": "string", "description": "idempotency key"},
    },
    "required": ["upload_ref"],
}


def _fail(code: str, message: str) -> str:
    return json.dumps({"ok": False, "code": code, "message": message}, ensure_ascii=False)


def make_ingest_tool(
    root_provider: Callable[[], pathlib.Path],
    store_provider: Callable[[], UploadStore],
    ingest_fn: Callable[..., dict[str, Any]] | None = None,
) -> Callable[[dict[str, Any]], str]:
    def tool_wiki_ingest_file(args: dict[str, Any]) -> str:
        from gov_kernel import ingest as _ingest

        fn = ingest_fn or _ingest.ingest_file
        ref = args.get("upload_ref")
        if not isinstance(ref, str) or not ref:
            return _fail("E_BAD_ARGS", "upload_ref is required")
        try:
            claimed = store_provider().claim(ref)
        except UploadError as exc:
            return _fail(exc.code, exc.message)
        try:
            receipt = fn(
                claimed.path,
                root=root_provider(),
                title=args.get("title") or None,
                description=args.get("description") or None,
                request_id=args.get("request_id") or None,
            )
        except _ingest.IngestError as exc:
            claimed.release()
            return _fail(exc.code, str(exc))
        except Exception as exc:  # noqa: BLE001
            claimed.release()
            return _fail("E_INGEST", f"{type(exc).__name__}: {exc}")
        claimed.finish()
        return json.dumps(receipt, ensure_ascii=False)

    return tool_wiki_ingest_file
