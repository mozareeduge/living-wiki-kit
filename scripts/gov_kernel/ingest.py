from __future__ import annotations

import datetime
import hashlib
import importlib.util
import json
import mimetypes
import os
import pathlib
import re
import shutil
import stat
import subprocess
import sys
import unicodedata
from typing import Any, Callable

# Load to_md module dynamically without modifying it
_TO_MD_PATH = pathlib.Path(__file__).resolve().parents[1] / "file-to-md" / "to_md.py"
_spec = importlib.util.spec_from_file_location("to_md", _TO_MD_PATH)
_to_md = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_to_md)

MIME_TABLE = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".epub": "application/epub+zip",
    ".html": "text/html",
    ".htm": "text/html",
    ".txt": "text/plain",
    ".md": "text/markdown",
    ".markdown": "text/markdown",
    ".csv": "text/csv",
}

SUPPORTED_EXTENSIONS = set(_to_md.HANDLERS.keys())

ENTRY_PAGES = ("HOME.md", "README.md", "SYSTEM_DESIGN.md", "CLAUDE.md")


class IngestError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def _lock_file(f: Any) -> None:
    try:
        import fcntl
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
    except Exception:
        pass


def _unlock_file(f: Any) -> None:
    try:
        import fcntl
        fcntl.flock(f.fileno(), fcntl.LOCK_UN)
    except Exception:
        pass


class IdempotencyGuard:
    """Manages _intake/idempotency.jsonl with process concurrency locking."""

    def __init__(self, root: pathlib.Path, request_id: str, door: str, payload: Any):
        if not isinstance(request_id, str) or len(request_id) < 8 or len(request_id) > 100:
            raise IngestError("E_BAD_REQUEST_ID", "request_id must be a string of 8-100 characters")
        self.root = root
        self.request_id = request_id
        self.door = door
        self.payload = payload
        self.payload_hash = hashlib.sha256(
            json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
        ).hexdigest()
        self.intake_dir = root / "_intake"
        self.log_path = self.intake_dir / "idempotency.jsonl"
        self.lock_path = self.intake_dir / ".idempotency.lock"
        self._lock_file_obj = None

    def acquire_and_check(self) -> dict[str, Any] | None:
        self.intake_dir.mkdir(parents=True, exist_ok=True)
        intake_gi = self.intake_dir / ".gitignore"
        if not intake_gi.is_file():
            try:
                intake_gi.write_text("*.lock\n.*.lock\n.tmp*\n", encoding="utf-8")
            except OSError:
                pass
        self._lock_file_obj = open(self.lock_path, "a+")
        _lock_file(self._lock_file_obj)
        if self.log_path.is_file():
            try:
                for line in self.log_path.read_text(encoding="utf-8").splitlines():
                    if not line.strip():
                        continue
                    entry = json.loads(line)
                    if entry.get("request_id") == self.request_id:
                        if entry.get("payload_hash") == self.payload_hash:
                            self.release()
                            return entry.get("receipt")
                        else:
                            self.release()
                            raise IngestError(
                                "E_IDEMPOTENCY_CONFLICT",
                                f"request_id {self.request_id!r} already used with different payload",
                            )
            except IngestError:
                raise
            except Exception:
                pass
        return None

    def record(self, receipt: dict[str, Any]) -> None:
        try:
            entry = {
                "request_id": self.request_id,
                "door": self.door,
                "payload_hash": self.payload_hash,
                "receipt": receipt,
                "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            }
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        finally:
            self.release()

    def release(self) -> None:
        if self._lock_file_obj:
            try:
                _unlock_file(self._lock_file_obj)
                self._lock_file_obj.close()
            except Exception:
                pass
            self._lock_file_obj = None


def on_ingested(receipt: dict[str, Any]) -> None:
    """Hook for chunk indexer (wired by lane L1 in Phase C)."""
    pass


def get_instance_prefix(root: pathlib.Path) -> str:
    """Detect instance record prefix; never returns a hardcoded wiki."""
    inst_path = root / "00-system" / "registers" / "INSTANCE.json"
    if inst_path.exists():
        try:
            doc = json.loads(inst_path.read_text(encoding="utf-8"))
            if doc.get("record_prefix"):
                return doc["record_prefix"]
        except Exception:
            pass
    state_path = root / "00-system" / "registers" / "CORPUS_STATE.json"
    if state_path.exists():
        try:
            st = json.loads(state_path.read_text(encoding="utf-8"))
            cid = str(st.get("id") or "")
            m = re.match(r"^([a-z0-9]+)-corpus", cid)
            if m and m.group(1) != "wiki":
                return m.group(1)
        except Exception:
            pass
    env_p = os.environ.get("WIKI_PREFIX")
    if env_p and env_p.strip():
        return env_p.strip()
    return "mw"


def normalize_derivative_text(text: str) -> tuple[str, str]:
    """Pure function: LF line endings, NFC unicode, source_version sha256."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = unicodedata.normalize("NFC", text)
    if text.strip():
        text = text.rstrip("\n") + "\n"
    else:
        text = ""
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return text, digest


def find_existing_original(root: pathlib.Path, sha256_digest: str) -> dict[str, Any] | None:
    """Check if an original with this hash already exists."""
    records_dir = root / "02-sources" / "records"
    if not records_dir.exists():
        return None
    for p in sorted(records_dir.rglob("*.md")):
        try:
            content = p.read_text(encoding="utf-8")
            if not content.startswith("---\n"):
                continue
            end = content.find("\n---\n", 4)
            if end < 0:
                continue
            import yaml
            fm = yaml.safe_load(content[4:end]) or {}
            if fm.get("sha256") == sha256_digest:
                rid = fm.get("id")
                return {
                    "record_id": rid,
                    "source_ref": f"rec:{rid}",
                    "original_path": fm.get("original_path"),
                    "extracted_text_path": fm.get("extracted_text_path"),
                    "title": fm.get("title"),
                    "filename": fm.get("filename"),
                    "status": fm.get("status"),
                }
        except Exception:
            continue
    return None


def _update_census_and_entry_pages(root: pathlib.Path, tier: str) -> None:
    """Keep CORPUS_STATE.json and entry pages synchronized with holdings."""
    state_path = root / "00-system" / "registers" / "CORPUS_STATE.json"
    if not state_path.exists():
        return
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except Exception:
        return

    old_held = state.get("held_artifact_count")
    if old_held is None:
        return

    new_held = old_held + 1
    state["held_artifact_count"] = new_held
    by_tier = state.setdefault("holdings_by_tier", {})
    by_tier[tier] = by_tier.get(tier, 0) + 1

    state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")

    # Update entry pages if they exist
    old_marker = f"Artifacts held: {old_held}"
    new_marker = f"Artifacts held: {new_held}"
    for name in ENTRY_PAGES:
        page = root / name
        if not page.is_file():
            continue
        try:
            txt = page.read_text(encoding="utf-8")
            if old_marker in txt:
                page.write_text(txt.replace(old_marker, new_marker), encoding="utf-8")
        except Exception:
            pass


def get_last_failure(root: pathlib.Path) -> str | None:
    st_file = root / "_intake" / "commit_status.json"
    if st_file.is_file():
        try:
            data = json.loads(st_file.read_text(encoding="utf-8"))
            return data.get("last_failure")
        except Exception:
            pass
    return None


def set_commit_status(root: pathlib.Path, last_failure: str | None) -> None:
    intake = root / "_intake"
    intake.mkdir(parents=True, exist_ok=True)
    st_file = intake / "commit_status.json"
    if last_failure is None:
        if st_file.is_file():
            try:
                st_file.unlink()
            except OSError:
                pass
    else:
        data = {
            "last_failure": last_failure,
            "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
        _atomic_write(st_file, json.dumps(data, indent=2).encode("utf-8"))


def get_uncommitted_count(root: pathlib.Path) -> int:
    if not (root / ".git").exists():
        return 0
    try:
        cp = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if cp.returncode == 0:
            lines = [line for line in cp.stdout.splitlines() if line.strip()]
            return len(lines)
    except Exception:
        pass
    return 0


def get_commit_status(root: pathlib.Path) -> dict[str, Any]:
    return {
        "uncommitted": {
            "count": get_uncommitted_count(root),
            "last_failure": get_last_failure(root),
        }
    }


def wiki_status(root: pathlib.Path | None = None) -> dict[str, Any]:
    if root is None:
        root = pathlib.Path.cwd()
    root = pathlib.Path(root).resolve()
    return get_commit_status(root)


def attempt_git_commit(
    root: pathlib.Path, staged_paths: list[str], commit_message: str
) -> tuple[str, str | None]:
    if not (root / ".git").exists():
        return "uncommitted", None
    try:
        # Stage named paths only
        valid_paths = [p for p in staged_paths if (root / p).exists()]
        if valid_paths:
            cp_add = subprocess.run(
                ["git", "add", "--", *valid_paths],
                cwd=root,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            if cp_add.returncode != 0:
                err = cp_add.stderr.strip() or f"git add failed with exit {cp_add.returncode}"
                set_commit_status(root, err)
                return "uncommitted", err

        cp_commit = subprocess.run(
            ["git", "commit", "-m", commit_message],
            cwd=root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if cp_commit.returncode == 0:
            set_commit_status(root, None)
            return "committed", None
        else:
            err = (
                cp_commit.stderr.strip()
                or cp_commit.stdout.strip()
                or f"git commit failed with exit {cp_commit.returncode}"
            )
            set_commit_status(root, err)
            return "uncommitted", err
    except Exception as exc:
        err = str(exc)
        set_commit_status(root, err)
        return "uncommitted", err


def _extract_derivative(src_file: pathlib.Path) -> tuple[str, dict[str, Any]]:
    ext = src_file.suffix.lower()
    if ext not in _to_md.HANDLERS:
        raise IngestError("E_UNSUPPORTED_TYPE", f"unsupported type: {ext}")

    body, method, detail, needs_ocr = _to_md.HANDLERS[ext](src_file)
    ratio = _to_md.fa_ratio(body)
    note = _to_md.quality_note(body)
    if needs_ocr:
        extra = "" if note == "clean" else "; " + note
        note = "NEEDS-OCR: no text layer; do not quote this file; route per skill" + extra

    status = "partial" if needs_ocr else ("failed" if not body.strip() else "ok")
    extraction = {
        "method": method,
        "quality_note": note,
        "fa_ratio": round(ratio, 4),
        "status": status,
        "ok": (not needs_ocr) and bool(body.strip()),
        "flags": ["needs-ocr"] if needs_ocr else [],
    }

    md = _to_md.header(src_file, method, detail)
    if note != "clean" or needs_ocr:
        md += "> quality: " + note + "\n\n"
    md += body + "\n"
    return md, extraction


def _atomic_write(dest: pathlib.Path, data: bytes) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(f".tmp-{dest.name}-{os.getpid()}")
    tmp.write_bytes(data)
    os.replace(tmp, dest)


def ingest_file(
    staged_path: pathlib.Path | str,
    root: pathlib.Path | None = None,
    title: str | None = None,
    description: str | None = None,
    request_id: str | None = None,
    holdings_tier: str | None = None,
    auto_commit: bool = True,
) -> dict[str, Any]:
    """Ingest core for staged files.

    Flow:
    1. Compute SHA-256. If original exists, return duplicate receipt.
    2. Copy bytes to _originals/<prefix>-<yyyy>/<sha[:2]>/<sha>.<ext> (read-only).
    3. Create source record with status: pending-registration.
    4. Extract derivative via to_md library; normalize text and hash source_version.
    5. Chunk index hook on_ingested(receipt).
    6. Return receipt.
    """
    src = pathlib.Path(staged_path).resolve()
    if not src.is_file():
        raise IngestError("E_NOT_FOUND", f"file not found: {staged_path}")

    ext = src.suffix.lower()
    if ext in _to_md.REFUSED:
        raise IngestError("E_UNSUPPORTED_TYPE", _to_md.REFUSED[ext])
    if ext not in _to_md.HANDLERS:
        raise IngestError("E_UNSUPPORTED_TYPE", f"unsupported type: {ext}")

    if root is None:
        root = pathlib.Path.cwd()
    root = pathlib.Path(root).resolve()

    data = src.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    mime = MIME_TABLE.get(ext) or mimetypes.guess_type(src.name)[0] or "application/octet-stream"

    guard = None
    if request_id is not None:
        guard = IdempotencyGuard(
            root,
            request_id,
            "wiki_ingest_file",
            {"sha256": digest, "title": title or "", "description": description or ""},
        )
        cached = guard.acquire_and_check()
        if cached is not None:
            return cached

    try:
        # Step 1: Dedup check
        existing = find_existing_original(root, digest)
        if existing:
            # Re-derive source_version from existing derivative if available
            deriv_rel = existing.get("extracted_text_path")
            s_ver = digest
            if deriv_rel and (root / deriv_rel).is_file():
                _, s_ver = normalize_derivative_text((root / deriv_rel).read_text(encoding="utf-8"))
            receipt = {
                "ok": True,
                "duplicate_of": existing["source_ref"],
                "source_ref": existing["source_ref"],
                "record_id": existing["record_id"],
                "sha256": digest,
                "bytes": len(data),
                "mime": mime,
                "extraction": {"method": "dedup", "quality_note": "duplicate artifact", "fa_ratio": 0.0, "status": "ok", "ok": True, "flags": []},
                "source_version": s_ver,
                "chunk_count": 0,
                "commit_state": "committed",
            }
            if guard:
                guard.record(receipt)
            return receipt

        # Step 2: Copy to _originals/<prefix>-<yyyy>/<sha[:2]>/<sha>.<ext>
        prefix = get_instance_prefix(root)
        yyyy = datetime.datetime.now(datetime.timezone.utc).strftime("%Y")
        orig_rel = f"_originals/{prefix}-{yyyy}/{digest[:2]}/{digest}{ext}"
        orig_dest = root / orig_rel
        orig_dest.parent.mkdir(parents=True, exist_ok=True)
        _atomic_write(orig_dest, data)
        # Set read-only after write (444)
        try:
            os.chmod(orig_dest, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
        except OSError:
            pass

        # Declare holdings tier per policy
        policy_tier = "pending-registration"
        policy_path = root / "00-system" / "policies" / "HOLDINGS_POLICY.json"
        if policy_path.exists():
            try:
                pol = json.loads(policy_path.read_text(encoding="utf-8"))
                policy_tier = pol.get("default_tier_for_unregistered", "pending-registration")
            except Exception:
                pass
        chosen_tier = holdings_tier or policy_tier

        # Step 3 & 4: Extract derivative text & normalize
        md_content, extraction = _extract_derivative(orig_dest)
        norm_text, source_version = normalize_derivative_text(md_content)

        # Step 5: Mint record ID and paths
        record_id = f"{prefix}-src-{digest[:12]}"
        rec_rel = f"02-sources/records/{record_id}.md"
        deriv_rel = f"02-sources/text/{record_id}.extracted.md"

        # Write derivative text
        deriv_dest = root / deriv_rel
        _atomic_write(deriv_dest, norm_text.encode("utf-8"))

        # Construct frontmatter
        doc_title = title or src.stem.replace("-", " ").replace("_", " ").title()
        today_iso = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
        clean_format = ext.lstrip(".")
        if clean_format == "markdown":
            clean_format = "md"

        import yaml
        fm = {
            "id": record_id,
            "type": "source-record",
            "title": doc_title,
            "filename": src.name,
            "aliases": [],
            "family": None,
            "version_role": None,
            "current_priority": None,
            "authority_scope": "external",
            "format": clean_format,
            "status": "pending-registration",
            "holdings_tier": chosen_tier,
            "validation_status": "unadjudicated",
            "visibility": "private",
            "sensitivity": "ordinary",
            "created": today_iso,
            "updated": today_iso,
            "sha256": digest,
            "original_path": orig_rel,
            "extracted_text_path": deriv_rel,
            "schema_version": "1.0.0",
        }
        rec_body = f"# {doc_title}\n\n## Artifact identity\n\n## Authority and use\n\n## Extraction status\n\n"
        rec_text = "---\n" + yaml.safe_dump(fm, sort_keys=False, allow_unicode=True) + "---\n\n" + rec_body
        _atomic_write(root / rec_rel, rec_text.encode("utf-8"))

        # Update census counts
        _update_census_and_entry_pages(root, chosen_tier)

        # Attempt git commit if configured
        commit_state = "uncommitted"
        last_failure = None
        if auto_commit and (root / ".git").exists():
            staged_paths = [
                orig_rel,
                rec_rel,
                deriv_rel,
                "00-system/registers/CORPUS_STATE.json",
            ]
            for name in ENTRY_PAGES:
                if (root / name).is_file():
                    staged_paths.append(name)
            if (root / "_intake" / "idempotency.jsonl").is_file():
                staged_paths.append("_intake/idempotency.jsonl")
            if (root / "_intake" / ".gitignore").is_file():
                staged_paths.append("_intake/.gitignore")

            commit_state, last_failure = attempt_git_commit(
                root, staged_paths, f"intake: ingest {record_id} ({src.name})"
            )

        receipt = {
            "ok": True,
            "source_ref": f"rec:{record_id}",
            "record_id": record_id,
            "sha256": digest,
            "bytes": len(data),
            "mime": mime,
            "extraction": extraction,
            "source_version": source_version,
            "chunk_count": 0,
            "commit_state": commit_state,
        }
        if last_failure:
            receipt["last_failure"] = last_failure

        # Chunk index hook
        try:
            on_ingested(receipt)
        except Exception:
            pass

        if guard:
            guard.record(receipt)

        return receipt
    finally:
        if guard:
            guard.release()


wiki_ingest_file = ingest_file
