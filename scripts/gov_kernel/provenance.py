from __future__ import annotations

import collections
import copy
import hashlib
import json
import pathlib
from dataclasses import dataclass
from typing import Any

from .common import jsonl_bytes, repo_path, sha256_bytes, sha256_file, stable_json_bytes
from .findings import Finding
from .frontmatter import load_markdown_frontmatter
from .schemas import validate_record


@dataclass
class ProvenanceResult:
    rows: list[dict[str, Any]]
    corpus_state: dict[str, Any]
    findings: list[Finding]
    existing_manifest_bytes: bytes | None = None
    existing_manifest_rows: list[dict[str, Any]] | None = None
    existing_state_bytes: bytes | None = None
    existing_state: dict[str, Any] | None = None


def _load_config(root: pathlib.Path) -> dict[str, Any]:
    p = root / "00-system/configuration/governance-kernel.json"
    if not p.exists():
        raise RuntimeError(f"missing configuration: {p}")
    cfg = json.loads(p.read_text(encoding="utf-8"))
    exts = cfg.get("governed_original_extensions") or []
    if not exts:
        raise RuntimeError("governed_original_extensions is empty; map AP-SOURCE-EXTENSIONS before provenance authority cutover")
    return cfg


def _manifest_tier_filter(root: pathlib.Path):
    """Honor 00-system/policies/HOLDINGS_POLICY.json: only tiers whose manifest_row is
    'required' belong to the corpus of record. `status` decides first, as in
    validate_repo.py (status: registered <=> manifest row); holdings_tier is the fallback.
    Returns (is_manifest_row, problem). Without a policy, every record counts."""
    p = root / "00-system/policies/HOLDINGS_POLICY.json"
    if not p.exists():
        return lambda fm: (True, None)
    policy = json.loads(p.read_text(encoding="utf-8"))
    tiers = policy.get("tiers") or {}

    def classify(fm: dict[str, Any]) -> tuple[bool, str | None]:
        status, held = fm.get("status"), fm.get("holdings_tier")
        tier = status if status in tiers else held if held in tiers else None
        if tier is None:
            return False, f"status {status!r} and holdings_tier {held!r} name no tier declared in HOLDINGS_POLICY.json"
        return (tiers[tier] or {}).get("manifest_row") == "required", None

    return classify


def _existing_manifest(root: pathlib.Path) -> tuple[list[dict[str, Any]], bytes | None]:
    p = root / "00-system/registers/MATERIALS_INDEX.jsonl"
    if not p.exists():
        return [], None
    raw = p.read_bytes()
    rows: list[dict[str, Any]] = []
    for line in raw.decode("utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows, raw


def _snapshot_sha(rows: list[dict[str, Any]]) -> str:
    # Match the repository's existing validate_repo.py invariant exactly:
    # current manifest order, id:sha lines, no trailing newline.
    payload = "\n".join(f"{row['id']}:{row['sha256']}" for row in rows)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build_provenance(root: pathlib.Path) -> ProvenanceResult:
    cfg = _load_config(root)
    records_dir = repo_path(root, cfg.get("source_records_dir", "02-sources/records"))
    originals_dir = repo_path(root, cfg.get("originals_dir", "_originals"))
    schema_dir = root / "00-system/schemas"
    exts = {str(x).lower() for x in cfg["governed_original_extensions"]}

    old_rows, old_manifest_bytes = _existing_manifest(root)
    old_by_id = {str(r.get("id")): r for r in old_rows if r.get("id")}
    old_order = [str(r.get("id")) for r in old_rows if r.get("id")]
    state_path = root / "00-system/registers/CORPUS_STATE.json"
    old_state_bytes = state_path.read_bytes() if state_path.exists() else None
    old_state = json.loads(old_state_bytes.decode("utf-8")) if old_state_bytes else {}

    findings: list[Finding] = []
    built: dict[str, dict[str, Any]] = {}
    ids: dict[str, pathlib.Path] = {}
    originals_seen: dict[str, pathlib.Path] = {}
    held_originals: set[str] = set()
    in_corpus = _manifest_tier_filter(root)

    for rp in sorted(records_dir.rglob("*.md")) if records_dir.exists() else []:
        try:
            fm, _ = load_markdown_frontmatter(rp)
        except Exception as exc:
            findings.append(Finding("PROV.SOURCE_RECORD_PARSE_FAILURE", "error", str(exc), str(rp.relative_to(root)), waivable=False))
            continue
        if fm.get("type") != "source-record":
            continue
        rel = str(rp.relative_to(root)).replace("\\", "/")
        member, tier_problem = in_corpus(fm)
        if tier_problem:
            findings.append(Finding("PROV.UNKNOWN_HOLDINGS_TIER", "error", tier_problem, rel, str(fm.get("id") or ""), False))
        if not member:
            held = fm.get("original_path")
            if isinstance(held, str) and held:
                held_originals.add(held.replace("\\", "/"))
            continue
        findings.extend(validate_record(fm, schema_dir, path=rel))
        sid = str(fm.get("id") or "")
        if sid in ids:
            findings.append(Finding("IDENTITY.DUPLICATE_ID", "error", f"duplicate source id {sid}", rel, sid, False, {"other": str(ids[sid].relative_to(root))}))
        else:
            ids[sid] = rp

        opath_raw = fm.get("original_path")
        if not isinstance(opath_raw, str) or not opath_raw:
            continue
        try:
            opath = repo_path(root, opath_raw)
        except ValueError as exc:
            findings.append(Finding("PROV.INVALID_ORIGINAL_PATH", "error", str(exc), rel, sid, False))
            continue
        if not opath.exists() or not opath.is_file():
            findings.append(Finding("PROV.SOURCE_RECORD_MISSING", "error", f"missing original: {opath_raw}", rel, sid, False))
            continue
        norm_original = str(opath.relative_to(root)).replace("\\", "/")
        if norm_original in originals_seen:
            findings.append(Finding("PROV.DUPLICATE_ORIGINAL_REGISTRATION", "error", f"original registered more than once: {norm_original}", rel, sid, False, {"other": str(originals_seen[norm_original].relative_to(root))}))
        else:
            originals_seen[norm_original] = rp
        actual_sha = sha256_file(opath)
        expected_sha = str(fm.get("sha256") or "")
        if actual_sha != expected_sha:
            findings.append(Finding("PROV.CHECKSUM_MISMATCH", "error", f"expected {expected_sha}, got {actual_sha}", norm_original, sid, False))

        # Preserve existing rich manifest metadata (headings, bytes, read receipts,
        # extraction notes, etc.) while refreshing fields owned by the source record.
        row = copy.deepcopy(old_by_id.get(sid, {}))
        row.update({
            "id": sid,
            "type": "source-record",
            "title": fm.get("title"),
            "filename": fm.get("filename"),
            "format": fm.get("format"),
            "sha256": expected_sha,
            "original_path": norm_original,
            "extracted_text_path": fm.get("extracted_text_path"),
            "authority_scope": fm.get("authority_scope"),
            "validation_status": fm.get("validation_status"),
            "family": fm.get("family"),
            "version_role": fm.get("version_role"),
            "extraction_quality": fm.get("extraction_quality"),
            "source_record_path": rel,
        })
        built[sid] = row

    governed_files: set[str] = set()
    if originals_dir.exists():
        for p in originals_dir.rglob("*"):
            if p.is_file() and p.suffix.lower() in exts:
                governed_files.add(str(p.relative_to(root)).replace("\\", "/"))
    for path in sorted(governed_files - set(originals_seen) - held_originals):
        findings.append(Finding("PROV.UNREGISTERED_ORIGINAL", "error", "governed original has no source record", path, waivable=False))

    rows: list[dict[str, Any]] = []
    for sid in old_order:
        if sid in built:
            rows.append(built.pop(sid))
    rows.extend(built[sid] for sid in sorted(built))

    fmt_counts = collections.Counter(str(r.get("format") or "unknown") for r in rows)
    fam_counts = collections.Counter(str(r.get("family") or "unknown") for r in rows)
    words = 0
    for row in rows:
        if isinstance(row.get("word_count"), int):
            words += int(row["word_count"])
        else:
            etp = row.get("extracted_text_path")
            if isinstance(etp, str) and etp:
                try:
                    p = repo_path(root, etp)
                    if p.is_file(): words += len(p.read_text(encoding="utf-8", errors="replace").split())
                except Exception:
                    pass

    snapshot_sha = _snapshot_sha(rows)
    same_snapshot = bool(old_state) and old_state.get("corpus_snapshot_sha256") == snapshot_sha
    state = copy.deepcopy(old_state) if old_state else {"type": "corpus-state"}
    state["type"] = "corpus-state"
    if not same_snapshot:
        state["id"] = f"mw-corpus-{snapshot_sha[:16]}"
    state["source_material_count"] = len(rows)
    state["format_counts"] = dict(sorted(fmt_counts.items()))
    state["family_counts"] = dict(sorted(fam_counts.items()))
    state["total_extracted_words"] = words
    state["corpus_snapshot_sha256"] = snapshot_sha

    return ProvenanceResult(
        rows,
        state,
        findings,
        existing_manifest_bytes=old_manifest_bytes,
        existing_manifest_rows=old_rows,
        existing_state_bytes=old_state_bytes,
        existing_state=old_state,
    )


def expected_generated_bytes(result: ProvenanceResult) -> dict[str, bytes]:
    if result.existing_manifest_bytes is not None and result.existing_manifest_rows == result.rows:
        manifest_bytes = result.existing_manifest_bytes
    else:
        manifest_bytes = jsonl_bytes(result.rows)
    if result.existing_state_bytes is not None and result.existing_state == result.corpus_state:
        state_bytes = result.existing_state_bytes
    else:
        state_bytes = stable_json_bytes(result.corpus_state)
    return {
        "00-system/registers/MATERIALS_INDEX.jsonl": manifest_bytes,
        "00-system/registers/CORPUS_STATE.json": state_bytes,
    }
