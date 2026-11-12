"""Change ledger, agent stamp, answer trace and reversible correction (OM-888).

Owner rule OM-888 (2026-11-12): no human approval gate. Agents run intake at
any level and merge to the end; every change says WHO made it (model,
provider, effort, host, harness). Any answer that used retrieval can be traced
answer -> hit -> wiki page/claim -> verbatim source (with sha256) -> the
ledger rows that made or changed it. At any hop the owner can say "wrong",
"outdated" or "not needed"; an agent then retracts or supersedes by APPENDING
a row. History is never deleted and _originals/ is never edited.

The ledger is one append-only JSONL file. A row is never rewritten; a
correction is undone by a later `restore` row, so every step stays reversible.
"""
from __future__ import annotations

import datetime as _dt
import json
import pathlib
import re
from typing import Any

from .common import git, sha256_bytes, sha256_file, stable_json_bytes
from .frontmatter import load_markdown_frontmatter
from .retrieval import TEXT_EXTS, load_profiles, profile_allows

LEDGER_REL = "00-system/registers/CHANGE_LEDGER.jsonl"
STAMP_FIELDS = ("model", "provider", "effort", "host", "harness")
CHANGE_ACTIONS = {"intake", "reconcile", "edit", "audit", "merge"}
CORRECTION_ACTIONS = {"retract", "supersede"}
ACTIONS = CHANGE_ACTIONS | CORRECTION_ACTIONS | {"restore"}
LEVELS = {"capture", "L1", "L2", "full"}
# what the owner says at a hop -> what the agent does about it
VERDICTS = {"wrong": "retract", "not-needed": "retract", "outdated": "supersede"}
SOURCE_KEYS = ("supporting_sources", "counter_evidence", "sources", "source_records",
               "source_record", "evidence_refs", "derived_from")
_WIKILINK = re.compile(r"\[\[([^\]|#]+)")


class LedgerError(ValueError):
    pass


def ledger_path(root: pathlib.Path) -> pathlib.Path:
    return root / LEDGER_REL


def check_stamp(stamp: Any) -> dict[str, str]:
    """Every field present and non-empty. 'unknown' is an honest value; a gap is not."""
    if not isinstance(stamp, dict):
        raise LedgerError("stamp must be an object with " + ", ".join(STAMP_FIELDS))
    missing = [k for k in STAMP_FIELDS if not str(stamp.get(k) or "").strip()]
    if missing:
        raise LedgerError("stamp is missing " + ", ".join(missing))
    out = {k: str(stamp[k]).strip() for k in STAMP_FIELDS}
    for extra in ("skill", "session_ref"):
        if str(stamp.get(extra) or "").strip():
            out[extra] = str(stamp[extra]).strip()
    return out


def read_ledger(root: pathlib.Path) -> list[dict[str, Any]]:
    p = ledger_path(root)
    if not p.exists():
        return []
    rows = []
    for n, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise LedgerError(f"{LEDGER_REL} line {n}: {exc}") from exc
    return rows


def _now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def append_change(root: pathlib.Path, *, action: str, targets: list[str], stamp: dict[str, Any],
                  reason: str = "", level: str | None = None, sources: list[dict[str, str]] | None = None,
                  replaced_by: str | None = None, commit: str | None = None,
                  at: str | None = None) -> dict[str, Any]:
    """Append one stamped row and return it. Never edits earlier rows."""
    if action not in ACTIONS:
        raise LedgerError(f"action must be one of {sorted(ACTIONS)}")
    targets = [str(t).strip() for t in targets if str(t).strip()]
    if not targets:
        raise LedgerError("at least one target (record id, path or change_id) is required")
    if level is not None and level not in LEVELS:
        raise LedgerError(f"level must be one of {sorted(LEVELS)}")
    if action in CORRECTION_ACTIONS | {"restore"} and not reason.strip():
        raise LedgerError(f"{action} needs a reason (what the owner said)")
    if action == "restore":
        known = {r.get("change_id") for r in read_ledger(root) if r.get("action") in CORRECTION_ACTIONS}
        unknown = [t for t in targets if t not in known]
        if unknown:
            raise LedgerError("restore targets must be correction change_ids: " + ", ".join(unknown))
    row: dict[str, Any] = {"at": at or _now(), "action": action, "targets": targets,
                           "stamp": check_stamp(stamp)}
    if level:
        row["level"] = level
    if reason.strip():
        row["reason"] = reason.strip()
    if sources:
        row["sources"] = [{"path": str(s.get("path")), "sha256": str(s.get("sha256"))} for s in sources]
    if replaced_by:
        row["replaced_by"] = str(replaced_by)
    if commit:
        row["commit"] = str(commit)
    row["change_id"] = "chg-" + sha256_bytes(stable_json_bytes(row))[:16]
    p = ledger_path(root)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("ab") as f:
        f.write(stable_json_bytes(row))
    return row


def feedback(root: pathlib.Path, *, target: str, verdict: str, note: str, stamp: dict[str, Any],
             replaced_by: str | None = None) -> dict[str, Any]:
    """The owner's word at one hop of a trace, turned into a correction row."""
    if verdict not in VERDICTS:
        raise LedgerError(f"verdict must be one of {sorted(VERDICTS)}")
    return append_change(root, action=VERDICTS[verdict], targets=[target], stamp=stamp,
                         reason=f"owner: {verdict}. {note}".strip(), replaced_by=replaced_by)


def active_corrections(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """target -> correction rows still in force (not undone by a later restore)."""
    restored = {t for r in rows if r.get("action") == "restore" for t in r.get("targets", [])}
    out: dict[str, list[dict[str, Any]]] = {}
    for r in rows:
        if r.get("action") in CORRECTION_ACTIONS and r.get("change_id") not in restored:
            for t in r.get("targets", []):
                out.setdefault(t, []).append(r)
    return out


def check_ledger(root: pathlib.Path) -> list[str]:
    """Problems with the ledger; empty means every row is whole and stamped."""
    problems: list[str] = []
    try:
        rows = read_ledger(root)
    except LedgerError as exc:
        return [str(exc)]
    seen: set[str] = set()
    for n, r in enumerate(rows, 1):
        where = f"{LEDGER_REL} row {n}"
        cid = r.get("change_id")
        body = {k: v for k, v in r.items() if k != "change_id"}
        if not cid or cid != "chg-" + sha256_bytes(stable_json_bytes(body))[:16]:
            problems.append(f"{where}: change_id does not match the row (rows are never edited)")
        if cid in seen:
            problems.append(f"{where}: duplicate change_id {cid}")
        seen.add(cid)
        if r.get("action") not in ACTIONS:
            problems.append(f"{where}: unknown action {r.get('action')!r}")
        if not r.get("targets"):
            problems.append(f"{where}: no targets")
        try:
            check_stamp(r.get("stamp"))
        except LedgerError as exc:
            problems.append(f"{where}: {exc}")
    return problems


# ---------------------------------------------------------------- trace

def _profile_files(root: pathlib.Path, profile_name: str) -> list[pathlib.Path]:
    profile = load_profiles(root)[profile_name]
    bases = {g.split("/**")[0] for g in profile.include_globs if "/**" in g} or {"."}
    out = []
    for base in sorted(bases):
        d = root / base
        if not d.is_dir():
            continue
        for p in d.rglob("*"):
            if p.is_file() and p.suffix.lower() in TEXT_EXTS:
                rel = p.relative_to(root).as_posix()
                if profile_allows(rel, profile):
                    out.append(p)
    return out


def _index(root: pathlib.Path, profile_name: str) -> dict[str, tuple[str, dict[str, Any], str]]:
    """id / stem / relative path -> (relative path, frontmatter, body)."""
    idx: dict[str, tuple[str, dict[str, Any], str]] = {}
    for p in _profile_files(root, profile_name):
        rel = p.relative_to(root).as_posix()
        fm, body = {}, ""
        if p.suffix.lower() == ".md":
            try:
                fm, body = load_markdown_frontmatter(p)
            except Exception:  # noqa: BLE001
                pass
        entry = (rel, fm, body)
        for key in (rel, p.stem, str(fm.get("id") or "")):
            if key and key not in idx:
                idx[key] = entry
    return idx


def _refs(fm: dict[str, Any], body: str) -> list[str]:
    refs: list[str] = []
    for k in SOURCE_KEYS:
        v = fm.get(k)
        for item in (v if isinstance(v, list) else [v] if v else []):
            if isinstance(item, dict):
                item = item.get("id") or item.get("path") or item.get("source") or ""
            refs.extend(m.strip() for m in _WIKILINK.findall(str(item)) or [str(item)])
    refs.extend(m.strip() for m in _WIKILINK.findall(body))
    seen, out = set(), []
    for r in refs:
        r = r.split(":")[1] if r.startswith("capture:") and r.count(":") >= 2 else r
        if r and r not in seen:
            seen.add(r); out.append(r)
    return out


def _verify(root: pathlib.Path, rel: Any, expected: Any) -> dict[str, Any]:
    if not rel:
        return {"path": None, "state": "no-path"}
    p = root / str(rel)
    if not p.is_file():
        return {"path": str(rel), "state": "missing"}
    got = sha256_file(p)
    state = "verified" if expected and got == str(expected) else "hash-differs" if expected else "unhashed"
    return {"path": str(rel), "sha256": got, "state": state}


def _last_commit(root: pathlib.Path, rel: str) -> dict[str, str] | None:
    try:
        out = git(root, "log", "-1", "--format=%H%x1f%an%x1f%aI%x1f%s", "--", rel, check=False)
    except Exception:  # noqa: BLE001
        return None
    parts = out.split("\x1f")
    return dict(zip(("commit", "author", "date", "subject"), parts)) if len(parts) == 4 else None


def _rows_for(rows: list[dict[str, Any]], keys: set[str]) -> list[dict[str, Any]]:
    return [r for r in rows if keys & set(r.get("targets", []))
            or keys & {s.get("path") for s in r.get("sources", [])}]


def trace(root: pathlib.Path, ref: str, max_sources: int = 40) -> dict[str, Any]:
    """One hit (record id or path) -> page -> verbatim sources -> ledger rows."""
    ref = str(ref).strip()
    canon, prov = _index(root, "canonical"), _index(root, "provenance")
    entry = canon.get(ref) or prov.get(ref)
    if entry is None:
        return {"ok": False, "error": "record not found", "ref": ref}
    rel, fm, body = entry
    rows = read_ledger(root)
    corrections = active_corrections(rows)
    rid = str(fm.get("id") or "")
    keys = {k for k in (ref, rel, rid) if k}
    is_source = prov.get(rel) is not None
    # direct source refs first, then one hop through cited wiki pages ("via")
    wanted: list[tuple[str, str | None]] = []
    if is_source:
        wanted.append((rid or rel, None))
    else:
        for r in _refs(fm, body):
            if r in prov:
                wanted.append((r, None))
            elif r in canon and canon[r][0] != rel:
                vrel, vfm, vbody = canon[r]
                wanted.extend((s, str(vfm.get("id") or vrel)) for s in _refs(vfm, vbody) if s in prov)
    sources = []
    done: set[str] = set()
    for r, via in wanted:
        hit = prov.get(r)
        if hit is None or hit[0] in done or len(sources) >= max_sources:
            continue
        done.add(hit[0])
        srel, sfm, _ = hit
        sid = str(sfm.get("id") or srel)
        files = [_verify(root, sfm.get("original_path"), sfm.get("sha256"))]
        for name, digest in (sfm.get("file_sha256") or {}).items() if isinstance(sfm.get("file_sha256"), dict) else []:
            for art in sfm.get("artifact_paths") or []:
                if str(art).endswith(str(name) + ".txt") or str(art).endswith(str(name)):
                    files.append(_verify(root, art, digest))
        if sfm.get("extracted_text_path"):
            files.append({**_verify(root, sfm.get("extracted_text_path"), None), "role": "extracted-text"})
        sources.append({
            "id": sid, "via": via, "record_path": srel, "title": sfm.get("title"), "status": sfm.get("status"),
            "sha256": sfm.get("sha256"), "verbatim": files,
            "made_by": sfm.get("made_by"),
            "changes": _rows_for(rows, {sid, srel}),
            "corrections": corrections.get(sid, []) + corrections.get(srel, []),
        })
    page_corrections = [c for k in keys for c in corrections.get(k, [])]
    return {
        "ok": True,
        "record": {"id": rid or None, "path": rel, "title": fm.get("title"), "type": fm.get("type"),
                   "status": fm.get("status"), "updated": _str(fm.get("updated")),
                   "last_commit": _last_commit(root, rel)},
        "correction_state": _state(page_corrections),
        "corrections": page_corrections,
        "changes": _rows_for(rows, keys),
        "sources": sources,
        "how_to_correct": ("Say wrong / outdated / not-needed at any hop (record or source id); "
                           "an agent appends a retract or supersede row. Nothing is deleted."),
    }


def _str(v: Any) -> Any:
    return v.isoformat() if isinstance(v, (_dt.date, _dt.datetime)) else v


def _state(corrections: list[dict[str, Any]]) -> str:
    if any(c.get("action") == "retract" for c in corrections):
        return "retracted"
    if corrections:
        return "superseded"
    return "in-force"


def annotate_hits(root: pathlib.Path, hits: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Mark search hits that the owner has corrected, so an answer never leans on them unawares."""
    corrections = active_corrections(read_ledger(root))
    if not corrections:
        return hits
    for h in hits:
        found = corrections.get(str(h.get("record_id") or ""), []) + corrections.get(str(h.get("path") or ""), [])
        if found:
            h["correction_state"] = _state(found)
            h["corrections"] = [{"change_id": c["change_id"], "action": c["action"],
                                 "reason": c.get("reason"), "replaced_by": c.get("replaced_by")} for c in found]
    return hits
