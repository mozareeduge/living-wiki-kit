#!/usr/bin/env python3
"""Deterministic validation for This Wiki.

This script checks repository structure, metadata identity, source checksums,
manifest consistency, and internal links. It does not judge literary or scholarly
quality; semantic audit is a separate workflow.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML is required. Run: python -m pip install PyYAML", file=sys.stderr)
    raise SystemExit(2)

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "00-system/registers/MATERIALS_INDEX.jsonl"
STATE = ROOT / "00-system/registers/CORPUS_STATE.json"
IGNORED_PREFIXES = (
    ".git/",
    ".harness-worktrees/",
    ".pytest_cache/",
    "_search/",
    "02-sources/provenance/",
    "_proposals/patches/",
    "_proposals/generated/",
)
SOURCE_FORMATS = {"md", "docx", "pdf", "png", "txt", "html", "epub", "pptx", "xlsx"}
CLAIM_PERMISSIONS = {
    "may-note",
    "may-describe",
    "may-argue-cautiously",
    "may-argue",
    "blocked",
}
OBJECT_KIND_BY_DIR = {
    "concepts": "concept",
    "institutions": "institution",
    "methods": "method",
    "people": "person",
    "references": "reference",
    "works": "work",
    "projects": "project",
    "collections": "collection",
}
REQUIRED_ROOT = [
    "README.md", "HOME.md", "SYSTEM_DESIGN.md", "SETUP_GUIDE_WINDOWS.md",
    "SEARCH_GUIDE.md", "CLAUDE.md", "AGENTS.md", ".mcp.json",
    "00-system/registers/MATERIALS_INDEX.jsonl",
    "00-system/registers/CORPUS_STATE.json",
]

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def parse_frontmatter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---\n", 4)
    if end < 0:
        raise ValueError("frontmatter opens but does not close")
    data = yaml.safe_load(text[4:end]) or {}
    if not isinstance(data, dict):
        raise ValueError("frontmatter must be a YAML mapping")
    return data

def load_manifest() -> list[dict]:
    rows = []
    for number, line in enumerate(MANIFEST.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"manifest line {number}: {exc}") from exc
        rows.append(row)
    return rows

def load_holdings_policy(root: Path) -> dict:
    """Load and validate 00-system/policies/HOLDINGS_POLICY.json.

    Declares the holdings-tier vocabulary (design.md section 3): which
    tiers exist, whether each is a manifest row, and which corpus-state
    count it feeds. Parsing only — not yet wired into validate(); a later
    task adds the census check that consumes this policy.
    """
    path = root / "00-system/policies/HOLDINGS_POLICY.json"
    if not path.exists():
        raise ValueError(
            f"holdings policy not found: {path} — every instance of this "
            f"kit must ship 00-system/policies/HOLDINGS_POLICY.json "
            f"(design.md section 3)"
        )
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path}: invalid JSON: {exc}") from exc
    tiers = data.get("tiers")
    if not isinstance(tiers, dict) or not tiers:
        raise ValueError(f"{path}: 'tiers' must be a non-empty object")
    default_tier = data.get("default_tier_for_unregistered")
    if default_tier not in tiers:
        raise ValueError(
            f"{path}: default_tier_for_unregistered names unknown tier "
            f"{default_tier!r}; declared tiers are {sorted(tiers)}"
        )
    for family, tier_name in (data.get("family_tier_overrides") or {}).items():
        if tier_name not in tiers:
            raise ValueError(
                f"{path}: family_tier_overrides[{family!r}] names unknown "
                f"tier {tier_name!r}; declared tiers are {sorted(tiers)}"
            )
    return data


def looks_double_encoded(s: str) -> bool:
    """Detect the classic UTF-8-bytes-read-as-cp1252 mojibake round-trip.

    A tool that opens a file with the wrong encoding and re-saves it turns
    correct text like "–" into "â€“". Re-encoding the
    (wrongly decoded) string as cp1252 and decoding the resulting bytes as
    UTF-8 collapses that back to the original text; on already-correct text
    the round trip either fails outright or leaves the string unchanged.
    A successful round trip that changes the string is therefore strong
    evidence of encoding corruption, regardless of which tool wrote it.
    """
    if not s:
        return False
    try:
        fixed = s.encode("cp1252").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return False
    return fixed != s


def is_ignored_rel(rel: str) -> bool:
    return any(rel == prefix.rstrip("/") or rel.startswith(prefix) for prefix in IGNORED_PREFIXES)


def require_fields(rel: str, fm: dict, fields: tuple[str, ...], errors: list[str]) -> None:
    for field in fields:
        if field not in fm or fm[field] in ("", None):
            errors.append(f"{rel}: missing required field '{field}'")


def validate_live_record_schema(rel: str, fm: dict, errors: list[str]) -> None:
    """Enforce the live record subset the local validators rely on."""
    if rel.startswith("02-sources/records/"):
        require_fields(
            rel,
            fm,
            ("id", "type", "title", "filename", "format", "sha256",
             "original_path", "authority_scope", "validation_status"),
            errors,
        )
        if fm.get("type") != "source-record":
            errors.append(f"{rel}: source record type must be 'source-record'")
        if fm.get("format") and fm.get("format") not in SOURCE_FORMATS:
            errors.append(f"{rel}: unsupported source format {fm.get('format')!r}")
        return

    if rel.startswith("03-objects/"):
        require_fields(rel, fm, ("id", "type", "title", "kind", "status"), errors)
        if fm.get("type") != "object":
            errors.append(f"{rel}: object type must be 'object'")
        folder = rel.split("/", 2)[1]
        expected_kind = OBJECT_KIND_BY_DIR.get(folder)
        if expected_kind and fm.get("kind") != expected_kind:
            errors.append(
                f"{rel}: object kind must be {expected_kind!r} for 03-objects/{folder}/, "
                f"got {fm.get('kind')!r}"
            )
        return

    if rel.startswith("05-claims/"):
        require_fields(
            rel,
            fm,
            ("id", "type", "title", "statement", "supporting_sources",
             "unsupported_zones", "counter_evidence", "certainty",
             "current_claim_permission", "responsible_language"),
            errors,
        )
        if fm.get("type") != "claim-object":
            errors.append(f"{rel}: claim type must be 'claim-object'")
        if fm.get("current_claim_permission") not in CLAIM_PERMISSIONS:
            errors.append(
                f"{rel}: invalid current_claim_permission "
                f"{fm.get('current_claim_permission')!r}"
            )
        for field in ("supporting_sources", "unsupported_zones", "counter_evidence"):
            if field in fm and not isinstance(fm[field], list):
                errors.append(f"{rel}: {field} must be a list")
        return

    if rel.startswith("06-relations/"):
        require_fields(
            rel,
            fm,
            ("id", "type", "title", "participants", "relation_status",
             "current_claim_permission", "supporting_sources",
             "counter_evidence"),
            errors,
        )
        if fm.get("type") != "relation-object":
            errors.append(f"{rel}: relation type must be 'relation-object'")
        if fm.get("relation_status") not in {"candidate", "proposed", "accepted", "rejected", "blocked", "superseded"}:
            errors.append(f"{rel}: invalid relation_status {fm.get('relation_status')!r}")
        if fm.get("current_claim_permission") not in CLAIM_PERMISSIONS:
            errors.append(
                f"{rel}: invalid current_claim_permission "
                f"{fm.get('current_claim_permission')!r}"
            )
        for field in ("participants", "supporting_sources", "counter_evidence"):
            if field in fm and not isinstance(fm[field], list):
                errors.append(f"{rel}: {field} must be a list")


def build_link_index() -> tuple[set[str], dict[str, list[str]]]:
    exact = set()
    stems: dict[str, list[str]] = {}
    for path in ROOT.rglob("*"):
        if not path.is_file() or ".git" in path.parts:
            continue
        rel = path.relative_to(ROOT).as_posix()
        if is_ignored_rel(rel):
            continue
        exact.add(rel)
        exact.add(rel.removesuffix(".md"))
        stems.setdefault(path.stem.casefold(), []).append(rel)
    return exact, stems

# Labelled markers every state-bearing entry page must carry, and the record
# directories whose recursive .md counts the pages must not contradict.
ENTRY_PAGES = ("HOME.md", "README.md", "SYSTEM_DESIGN.md", "CLAUDE.md")
ENTRY_LAYER_DIRS = {
    "objects": "03-objects",
    "relations": "06-relations",
    "claims": "05-claims",
    "indexes": "09-indexes",
}
REFRESH_HINT = ("refresh the entry page from the registers in the same change")


def _visible_prose(text: str) -> str:
    """Strip fenced (```/~~~) and inline (`/``) code from Markdown text."""
    text = re.sub(r"```.*?```", " ", text, flags=re.DOTALL)
    text = re.sub(r"~~~.*?~~~", " ", text, flags=re.DOTALL)
    text = re.sub(r"`[^`\n]*`", " ", text)
    return text


def check_entry_pages(root: Path, state: dict, errors: list[str]) -> None:
    """Entry-page freshness gate.

    Entry pages restate register values for human readers; hardcoding them
    lets those pages silently drift out of sync with CORPUS_STATE.json /
    MATERIALS_INDEX.jsonl after an intake or adjudication round (this
    happened in a production instance, 2026-09-16). Enforced properties:
      1. every entry page carries the exact labelled markers
         `Current corpus snapshot: `<id>`` and
         `Registered source artifacts: <count>` for the current state
         (labels prevent a coincidental numeral satisfying the check);
      2. no visible-prose `\d+ object(s)/relation(s)/claim(s)/index(es)`
         declaration contradicts the recursive .md count of its layer
         directory; fenced/inline code is exempt; every occurrence checks.
    """
    snapshot_id = str(state.get("id", "") or "")
    count = state.get("source_material_count")

    layer_actual = {}
    for layer, rel_dir in ENTRY_LAYER_DIRS.items():
        d = root / rel_dir
        layer_actual[layer] = sum(1 for p in d.rglob("*.md")) if d.exists() else 0

    layer_re = re.compile(
        r"\b(\d+)\s+(objects?|relations?|claims?|indexes?)\b", re.IGNORECASE)

    for entry_rel in ENTRY_PAGES:
        entry_path = root / entry_rel
        if not entry_path.exists():
            errors.append(f"missing entry page: {entry_rel}")
            continue
        raw = entry_path.read_text(encoding="utf-8", errors="replace")
        prose = _visible_prose(raw)

        if snapshot_id:
            marker = f"Current corpus snapshot: `{snapshot_id}`"
            if marker not in prose and marker not in raw:
                # Search the RAW text: _visible_prose() strips code spans,
                # which is where the stale id lives, so a prose-only search
                # would report a bare label and hide the observed value.
                obs = re.search(r"Current corpus snapshot:[^\n]*", raw)
                observed = f" (observed: '{obs.group(0).strip()}')" if obs else ""
                errors.append(
                    f"{entry_rel}: stale entry page: snapshot marker "
                    f"'{marker}'{observed} (id from CORPUS_STATE.json) not "
                    f"found; {REFRESH_HINT}"
                )
        if count is not None:
            marker = f"Registered source artifacts: {count}"
            if marker not in prose and marker not in raw:
                obs = re.search(r"Registered source artifacts:[^\n]*", raw)
                observed = f" (observed: '{obs.group(0).strip()}')" if obs else ""
                errors.append(
                    f"{entry_rel}: stale entry page: source-count marker "
                    f"'{marker}'{observed} (from CORPUS_STATE.json) not "
                    f"found; {REFRESH_HINT}"
                )
        for m in layer_re.finditer(prose):
            num = int(m.group(1))
            word = m.group(2).lower()
            layer = ("objects" if word.startswith("object")
                     else "relations" if word.startswith("relation")
                     else "claims" if word.startswith("claim")
                     else "indexes")
            actual = layer_actual[layer]
            if num != actual:
                errors.append(
                    f"{entry_rel}: entry page states {m.group(1)} "
                    f"{m.group(2)} but {ENTRY_LAYER_DIRS[layer]} holds "
                    f"{actual}; {REFRESH_HINT}"
                )


HOLDINGS_TIER_REGISTERED = "registered"


def check_holdings_census(root: Path, state: dict, errors: list[str]) -> None:
    """Holdings census gate (design.md sections 3-4; tasks.md A2).

    "Registered" (MATERIALS_INDEX.jsonl) and "held" (_originals/) are
    different claims and this enforces both stay honest, using the tier
    vocabulary from 00-system/policies/HOLDINGS_POLICY.json (never
    hardcoded here):
      1. Biconditional: a source record carries `status: registered` iff
         its repo-relative path is a `source_record_path` in the manifest.
         Both directions are errors, naming the record and which side
         disagrees.
      2. Coverage: every file under `_originals/` is either a manifest
         `original_path`, or is named by a source record whose
         `holdings_tier` is a declared non-'registered' tier.
      3. Tier legality: `holdings_tier: registered` implies a manifest row;
         a manifest row's record must not carry a different declared tier.
      4. Counts: `held_artifact_count` (files under `_originals/`),
         `holdings_by_tier` (must sum to it), and `source_material_count`
         (manifest row count, and must equal
         `holdings_by_tier["registered"]`) all agree. Skipped entirely,
         invariants 1-3 still run, when `held_artifact_count` is absent from
         state (an instance that has not adopted this change yet).

    Not wired into validate() — tasks.md A4 wires it.
    """
    try:
        policy = load_holdings_policy(root)
    except ValueError as exc:
        errors.append(str(exc))
        return
    declared_tiers = policy["tiers"]

    manifest_rel = "00-system/registers/MATERIALS_INDEX.jsonl"
    manifest_path = root / manifest_rel
    rows: list[dict] = []
    if manifest_path.exists():
        had_parse_error = False
        for number, line in enumerate(
            manifest_path.read_text(encoding="utf-8").splitlines(), 1
        ):
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                errors.append(f"{manifest_rel}: line {number}: {exc}")
                had_parse_error = True
        if had_parse_error:
            return

    registered_record_paths = {
        row["source_record_path"] for row in rows if row.get("source_record_path")
    }
    manifest_original_paths = {
        row["original_path"] for row in rows if row.get("original_path")
    }

    records_dir = root / "02-sources" / "records"
    records: dict[str, dict] = {}
    if records_dir.exists():
        for path in sorted(records_dir.rglob("*.md")):
            rel = path.relative_to(root).as_posix()
            try:
                records[rel] = parse_frontmatter(path)
            except Exception as exc:
                errors.append(f"{rel}: {exc}")

    # 1. Biconditional: status: registered <=> named as source_record_path.
    for rel, fm in records.items():
        claims_registered = fm.get("status") == HOLDINGS_TIER_REGISTERED
        is_manifest_row = rel in registered_record_paths
        if claims_registered and not is_manifest_row:
            errors.append(
                f"{rel}: status is 'registered' but no row in "
                f"{manifest_rel} names it as source_record_path — either "
                f"register it there or correct this record's status"
            )
        if is_manifest_row and not claims_registered:
            errors.append(
                f"{rel}: a row in {manifest_rel} names this record as "
                f"source_record_path but its status is "
                f"{fm.get('status')!r}, not 'registered'"
            )

    # 3. Tier legality.
    for rel, fm in records.items():
        tier = fm.get("holdings_tier")
        is_manifest_row = rel in registered_record_paths
        if tier is None:
            continue
        if tier not in declared_tiers:
            errors.append(
                f"{rel}: holdings_tier {tier!r} is not a declared tier in "
                f"HOLDINGS_POLICY.json; legal tiers are "
                f"{sorted(declared_tiers)}"
            )
            continue
        if tier == HOLDINGS_TIER_REGISTERED and not is_manifest_row:
            errors.append(
                f"{rel}: holdings_tier is 'registered' but no row in "
                f"{manifest_rel} names it as source_record_path"
            )
        if is_manifest_row and tier != HOLDINGS_TIER_REGISTERED:
            errors.append(
                f"{rel}: is named as source_record_path in {manifest_rel} "
                f"but holdings_tier is {tier!r}, not 'registered'"
            )

    # 2. Coverage: every file under _originals/ is accounted for.
    originals_dir = root / "_originals"
    originals_files = (
        sorted(p for p in originals_dir.rglob("*") if p.is_file())
        if originals_dir.exists() else []
    )
    covering_records = {
        fm["original_path"]: rel
        for rel, fm in records.items()
        if fm.get("original_path")
        and fm.get("holdings_tier") in declared_tiers
        and fm.get("holdings_tier") != HOLDINGS_TIER_REGISTERED
    }
    for path in originals_files:
        rel = path.relative_to(root).as_posix()
        if rel in manifest_original_paths or rel in covering_records:
            continue
        errors.append(
            f"{rel}: held under _originals/ but undeclared — it is neither "
            f"a manifest original_path in {manifest_rel} nor named by a "
            f"source record with a non-'registered' holdings_tier"
        )

    # 4. Counts — skipped entirely (invariants 1-3 still run above) if
    # held_artifact_count is absent from state.
    if "held_artifact_count" not in state:
        return

    held_declared = state.get("held_artifact_count")
    held_actual = len(originals_files)
    if held_declared != held_actual:
        errors.append(
            f"CORPUS_STATE.json: held_artifact_count is {held_declared} "
            f"but _originals/ holds {held_actual} files"
        )

    by_tier = state.get("holdings_by_tier") or {}
    tier_sum = sum(by_tier.values())
    if tier_sum != held_declared:
        errors.append(
            f"CORPUS_STATE.json: holdings_by_tier sums to {tier_sum} but "
            f"held_artifact_count is {held_declared}"
        )

    source_count = state.get("source_material_count")
    manifest_count = len(rows)
    if manifest_count != source_count:
        errors.append(
            f"CORPUS_STATE.json: source_material_count is {source_count} "
            f"but {manifest_rel} has {manifest_count} rows"
        )

    registered_tier_count = by_tier.get(HOLDINGS_TIER_REGISTERED)
    if registered_tier_count != source_count:
        errors.append(
            f"CORPUS_STATE.json: holdings_by_tier['registered'] is "
            f"{registered_tier_count} but source_material_count is "
            f"{source_count}"
        )


def validate(full: bool) -> list[str]:
    errors: list[str] = []
    warnings: list[str] = []

    for rel in REQUIRED_ROOT:
        if not (ROOT / rel).exists():
            errors.append(f"missing required path: {rel}")

    if errors:
        return errors

    try:
        state = json.loads(STATE.read_text(encoding="utf-8"))
    except Exception as exc:
        errors.append(f"cannot parse CORPUS_STATE.json: {exc}")
        return errors

    try:
        rows = load_manifest()
    except Exception as exc:
        errors.append(str(exc))
        return errors

    if len(rows) != state.get("source_material_count"):
        errors.append(
            f"manifest/state count mismatch: {len(rows)} vs "
            f"{state.get('source_material_count')}"
        )

    # Entry-page freshness gate: the four entry pages restate register values
    # for human readers, so they must never lag CORPUS_STATE.json.
    check_entry_pages(ROOT, state, errors)

    # Holdings census gate (design.md sections 3-4; tasks.md A2/A4):
    # "registered" and "held" are different claims and must stay honest.
    check_holdings_census(ROOT, state, errors)

    ids: dict[str, str] = {}
    md_files = [
        p for p in ROOT.rglob("*.md")
        if not is_ignored_rel(p.relative_to(ROOT).as_posix())
    ]
    no_frontmatter_allowed = {
        "README.md", "CLAUDE.md", "AGENTS.md", "SETUP_GUIDE_WINDOWS.md",
        "SEARCH_GUIDE.md", "GPT_WORKFLOW.md", "RUNBOOK_WEB_CAPTURE.md",
    }
    for path in md_files:
        rel = path.relative_to(ROOT).as_posix()
        try:
            fm = parse_frontmatter(path)
        except Exception as exc:
            errors.append(f"{rel}: {exc}")
            continue
        if not fm:
            if rel not in no_frontmatter_allowed and not rel.startswith(".claude/"):
                warnings.append(f"{rel}: no frontmatter")
            continue
        if rel.startswith(".claude/") or rel.startswith("00-system/templates/"):
            continue
        validate_live_record_schema(rel, fm, errors)
        for key in ("id", "type", "title"):
            if key not in fm or fm[key] in ("", None):
                errors.append(f"{rel}: missing frontmatter field '{key}'")
        record_id = str(fm.get("id", ""))
        if record_id:
            if record_id in ids:
                errors.append(f"duplicate id {record_id}: {ids[record_id]} and {rel}")
            else:
                ids[record_id] = rel

    seen_source_ids = set()
    seen_filenames = set()
    for row in rows:
        for key in ("id", "filename", "sha256", "original_path", "source_record_path"):
            if not row.get(key):
                errors.append(f"manifest row missing {key}: {row.get('filename')}")
        sid = row.get("id")
        filename = row.get("filename")
        if sid in seen_source_ids:
            errors.append(f"duplicate manifest id: {sid}")
        if filename in seen_filenames:
            errors.append(f"duplicate manifest filename: {filename}")
        seen_source_ids.add(sid)
        seen_filenames.add(filename)

        for key in ("original_path", "filename", "source_record_path", "extracted_text_path"):
            value = row.get(key)
            if value and looks_double_encoded(value):
                errors.append(
                    f"manifest row field '{key}' looks double-encoded (mojibake): "
                    f"{value!r} — a tool likely wrote this with the wrong text "
                    f"encoding; re-derive it from the actual filesystem name, "
                    f"do not hand-patch the garbled string"
                )

        original = ROOT / row["original_path"]
        source_record = ROOT / row["source_record_path"]
        if not original.exists():
            errors.append(f"missing original: {row['original_path']}")
        if not source_record.exists():
            errors.append(f"missing source record: {row['source_record_path']}")
        if full and original.exists():
            actual = sha256_file(original)
            if actual != row["sha256"]:
                errors.append(
                    f"original checksum changed: {row['original_path']} "
                    f"expected {row['sha256']} got {actual}"
                )
        derivative = row.get("extracted_text_path")
        if derivative and not (ROOT / derivative).exists():
            errors.append(f"missing extracted derivative: {derivative}")

    # Generic kit: any non-negative count is acceptable; the invariant is
    # manifest/state agreement (checked above). A concrete expected count for a
    # specific release may be declared in CORPUS_STATE.json as expected_count.
    expected = state.get("expected_count")
    if expected is not None and state.get("source_material_count") != expected:
        errors.append(
            f"CORPUS_STATE declares expected_count {expected}, state contains "
            f"{state.get('source_material_count')}"
        )

    # Validate corpus snapshot.
    payload = "\n".join(f"{row['id']}:{row['sha256']}" for row in rows)
    actual_snapshot = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    if actual_snapshot != state.get("corpus_snapshot_sha256"):
        errors.append("corpus snapshot hash does not match manifest")

    # Internal wikilinks.
    exact_paths, stems = build_link_index()
    link_re = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]+)?(?:\|[^\]]+)?\]\]")
    for path in md_files:
        rel = path.relative_to(ROOT).as_posix()
        text = path.read_text(encoding="utf-8")
        # Docs legitimately QUOTE link syntax (Obsidian templates, guides).
        # Strip fenced code blocks and inline code spans so a quoted
        # `[[...]]` snippet is not scanned as a live link.
        text = re.sub(r"```.*?(?:```|\Z)", "", text, flags=re.S)
        text = re.sub(r"`[^`\n]*`", "", text)
        for raw in link_re.findall(text):
            target = raw.strip().replace("\\", "/")
            candidates = [
                target, target.removesuffix(".md"),
                target + ".md" if not target.endswith(".md") else target
            ]
            if any(c in exact_paths for c in candidates):
                continue
            # Strip only a real trailing ".md", never use Path(...).stem here:
            # it splits on the *last* dot in the whole string, which mistakes
            # a literal dot inside an id (e.g. "yd1.1-Stephen-Hero...") for a
            # file extension and truncates the target at the wrong point.
            basename = target.rsplit("/", 1)[-1]
            if basename.lower().endswith(".md"):
                basename = basename[: -len(".md")]
            stem = basename.casefold()
            matches = stems.get(stem, [])
            if len(matches) == 1:
                continue
            if len(matches) > 1:
                warnings.append(f"{rel}: ambiguous wikilink [[{target}]] -> {matches[:4]}")
            else:
                errors.append(f"{rel}: unresolved wikilink [[{target}]]")

    for warning in warnings:
        print(f"WARNING: {warning}")

    return errors

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--full", action="store_true", help="hash every original")
    parser.add_argument("--ci", action="store_true", help="CI mode; equivalent to --full")
    parser.add_argument(
        "--research", action="store_true",
        help="also run the deterministic citation-span audit over "
             "../others/research/ (Engine 1); see scripts/check_research_spans.py",
    )
    args = parser.parse_args()

    if args.research:
        import check_research_spans  # noqa: PLC0415 - optional dependency

        research_errors = check_research_spans.collect_errors(
            check_research_spans.DEFAULT_RESEARCH)
        for error in research_errors:
            print(f"ERROR: {error}", file=sys.stderr)
        if research_errors:
            print(f"FAILED: {len(research_errors)} research-span error(s)",
                  file=sys.stderr)
            return 1
        print("PASS: research citation spans verified")

    errors = validate(full=args.full or args.ci)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        print(f"FAILED: {len(errors)} error(s)", file=sys.stderr)
        return 1
    print("PASS: repository structure, metadata, manifest, checksums, and links are valid")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

