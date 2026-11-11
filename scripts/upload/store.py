"""Single-use, TTL'd staging of uploaded bytes under ``<root>/_staging/uploads/``.

Layout per upload: ``<ref>/<sanitized name>`` plus ``<ref>/meta.json``.
Claiming renames ``meta.json`` to ``claimed.json`` (atomic, so only one
caller can win). ``finish()`` deletes the bytes and leaves a tombstone
(``used.json``) so a reused ref reports E_UPLOAD_USED until cleanup.
"""
from __future__ import annotations

import json
import os
import pathlib
import re
import secrets
import shutil
import time
import unicodedata
from typing import Any, Callable

DEFAULT_TTL_SECONDS = 24 * 3600
DEFAULT_MAX_BYTES = 50 * 1024 * 1024
REF_PREFIX = "upl-"
REF_RE = re.compile(r"^upl-[A-Za-z0-9_-]{43}$")
_NAME_BAD = re.compile(r"[^\w.\- ]", re.UNICODE)


class UploadError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def allowed_extensions() -> frozenset[str]:
    """Extensions the ingest door can handle; fails closed if it cannot load."""
    from gov_kernel import ingest

    return frozenset(ingest.SUPPORTED_EXTENSIONS)


def sanitize_filename(name: str) -> tuple[str, str]:
    """Return (safe_name, extension). Raises UploadError(E_UPLOAD_TYPE)."""
    base = unicodedata.normalize("NFC", str(name or "")).replace("\\", "/").split("/")[-1]
    base = _NAME_BAD.sub("_", base).strip(" .")
    base = base[-120:]
    stem, dot, ext = base.rpartition(".")
    ext = ("." + ext.lower()) if dot else ""
    if not stem.strip("_ ") or ext not in allowed_extensions():
        raise UploadError("E_UPLOAD_TYPE", f"file type not allowed: {ext or 'no extension'}")
    return base, ext


class ClaimedUpload:
    def __init__(self, store: "UploadStore", ref: str, path: pathlib.Path, name: str):
        self._store, self._ref = store, ref
        self.path, self.name = path, name

    def finish(self) -> None:
        """Ingest succeeded: delete the bytes, keep a tombstone."""
        d = self._store._dir(self._ref)
        for p in d.iterdir():
            if p.name != "claimed.json":
                p.unlink(missing_ok=True)
        os.replace(d / "claimed.json", d / "used.json")

    def release(self) -> None:
        """Ingest failed: make the ref usable again."""
        d = self._store._dir(self._ref)
        os.replace(d / "claimed.json", d / "meta.json")


class UploadStore:
    def __init__(
        self,
        root: pathlib.Path | str,
        ttl_seconds: int = DEFAULT_TTL_SECONDS,
        max_bytes: int = DEFAULT_MAX_BYTES,
        clock: Callable[[], float] = time.time,
    ):
        self.root = pathlib.Path(root).resolve()
        self.base = self.root / "_staging" / "uploads"
        self.ttl, self.max_bytes, self.clock = ttl_seconds, max_bytes, clock

    def _dir(self, ref: str) -> pathlib.Path:
        return self.base / ref

    def save(self, filename: str, data: bytes) -> dict[str, Any]:
        if len(data) > self.max_bytes:
            raise UploadError("E_UPLOAD_TOO_LARGE", f"upload exceeds {self.max_bytes} bytes")
        name, _ext = sanitize_filename(filename)
        if not data:
            raise UploadError("E_UPLOAD_EMPTY", "empty upload")
        ref = REF_PREFIX + secrets.token_urlsafe(32)
        d = self._dir(ref)
        d.mkdir(parents=True, exist_ok=False)
        (d / name).write_bytes(data)
        now = self.clock()
        meta = {"name": name, "bytes": len(data), "created": now, "expires": now + self.ttl}
        tmp = d / "meta.tmp"
        tmp.write_text(json.dumps(meta), encoding="utf-8")
        os.replace(tmp, d / "meta.json")
        return {"upload_ref": ref, "filename": name, "bytes": len(data), "expires_at": meta["expires"]}

    def claim(self, ref: Any) -> ClaimedUpload:
        if not isinstance(ref, str) or not REF_RE.match(ref):
            raise UploadError("E_UPLOAD_BAD_REF", "malformed upload ref")
        d = self._dir(ref)
        if not d.is_dir():
            raise UploadError("E_UPLOAD_UNKNOWN", "unknown upload ref")
        if (d / "used.json").exists() or (d / "claimed.json").exists():
            raise UploadError("E_UPLOAD_USED", "upload ref already used")
        meta_path = d / "meta.json"
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            raise UploadError("E_UPLOAD_UNKNOWN", "unknown upload ref") from None
        if self.clock() > float(meta["expires"]):
            shutil.rmtree(d, ignore_errors=True)
            raise UploadError("E_UPLOAD_EXPIRED", "upload ref expired")
        try:
            os.replace(meta_path, d / "claimed.json")
        except OSError:
            raise UploadError("E_UPLOAD_USED", "upload ref already used") from None
        path = d / meta["name"]
        if not path.is_file() or path.resolve().parent != d.resolve():
            os.replace(d / "claimed.json", meta_path)
            raise UploadError("E_UPLOAD_UNKNOWN", "upload bytes missing")
        return ClaimedUpload(self, ref, path, meta["name"])

    def cleanup(self) -> int:
        """Remove expired uploads, old tombstones and orphans. Returns the count."""
        if not self.base.is_dir():
            return 0
        removed, now = 0, self.clock()
        for d in list(self.base.iterdir()):
            if not d.is_dir():
                continue
            expires = None
            for n in ("meta.json", "used.json", "claimed.json"):
                try:
                    expires = float(json.loads((d / n).read_text(encoding="utf-8"))["expires"])
                    break
                except (OSError, ValueError, KeyError):
                    continue
            if expires is None:
                expires = d.stat().st_mtime + self.ttl
            if now > expires:
                shutil.rmtree(d, ignore_errors=True)
                removed += 1
        return removed


def default_store(root: pathlib.Path | str) -> UploadStore:
    """Store configured from LWK_UPLOAD_TTL_SECONDS and LWK_UPLOAD_MAX_BYTES."""
    return UploadStore(
        root,
        ttl_seconds=int(os.environ.get("LWK_UPLOAD_TTL_SECONDS", DEFAULT_TTL_SECONDS)),
        max_bytes=int(os.environ.get("LWK_UPLOAD_MAX_BYTES", DEFAULT_MAX_BYTES)),
    )


if __name__ == "__main__":
    import sys

    target = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else pathlib.Path.cwd()
    print(json.dumps({"removed": default_store(target).cleanup()}))
