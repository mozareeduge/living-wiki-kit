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


def build_link_index() -> tuple[set[str], dict[str, list[str]]]:
    exact = set()
    stems: dict[str, list[str]] = {}
    for path in ROOT.rglob("*"):
        if not path.is_file() or ".git" in path.parts:
            continue
        rel = path.relative_to(ROOT).as_posix()
        exact.add(rel)
        exact.add(rel.removesuffix(".md"))
        stems.setdefault(path.stem.casefold(), []).append(rel)
    return exact, stems

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

    ids: dict[str, str] = {}
    md_files = [
        p for p in ROOT.rglob("*.md")
        if ".git" not in p.parts and "_search" not in p.parts
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

