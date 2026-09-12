#!/usr/bin/env python3
"""Validate the populated This Wiki content layer.

This validator detects structural incompleteness. It does not certify literary,
historical, or interpretive truth.
"""
from __future__ import annotations

import json
from pathlib import Path
import re
import sys
from collections import Counter, defaultdict

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML is required.", file=sys.stderr)
    raise SystemExit(2)

ROOT = Path(__file__).resolve().parents[1]
IGNORED_PREFIXES = (
    ".git/",
    ".pytest_cache/",
    "_search/",
    "02-sources/provenance/",
    "_proposals/patches/",
    "_proposals/generated/",
)

# Release contract is per-instance configuration, not hard-coded wiki paths.
# The kit ships a generic config; instantiated wikis edit it as their layer grows.
import configparser  # noqa: F401  (std; placeholder to keep imports stable)

def _load_release_contract() -> dict:
    """Load the release contract from 00-system/configuration/content-release.json."""
    cfg_path = ROOT / "00-system/configuration/content-release.json"
    if not cfg_path.exists():
        # Empty-instance default: no required release paths, no minimum counts.
        return {"required": [], "base_files": [], "min_counts": {},
                "word_thresholds": {}, "system_version": None}
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    return {
        "required": cfg.get("required_paths", []),
        "base_files": cfg.get("base_files", []),
        "min_counts": cfg.get("min_counts", {}),
        "word_thresholds": cfg.get("word_thresholds", {}),
        "system_version": cfg.get("system_version"),
    }


_CONTRACT = _load_release_contract()
REQUIRED = _CONTRACT["required"]
BASE_FILES = _CONTRACT["base_files"]
MIN_COUNTS = _CONTRACT["min_counts"]
WORD_THRESHOLDS = _CONTRACT["word_thresholds"]

EXEMPT_STATUSES = {
    "candidate", "superseded", "archived", "rejected", "compatibility-record",
    "superseded-summary",
}

LINK_RE = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]+)?(?:\|[^\]]+)?\]\]")


def parse_markdown(path: Path) -> tuple[dict, str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---\n", 4)
    if end < 0:
        raise ValueError("frontmatter opens but does not close")
    data = yaml.safe_load(text[4:end]) or {}
    if not isinstance(data, dict):
        raise ValueError("frontmatter is not a mapping")
    return data, text[end + 5:]


def body_words(body: str) -> int:
    return len(re.findall(r"\b[\wâ€™'-]+\b", body))


def markdown_files() -> list[Path]:
    return [
        p for p in ROOT.rglob("*.md")
        if not is_ignored_rel(p.relative_to(ROOT).as_posix())
    ]


def is_ignored_rel(rel: str) -> bool:
    return any(rel == prefix.rstrip("/") or rel.startswith(prefix) for prefix in IGNORED_PREFIXES)


def curated(path: Path, fm: dict) -> bool:
    rel = path.relative_to(ROOT).as_posix()
    if rel.startswith(("02-sources/", ".claude/", "00-system/templates/")):
        return False
    if fm.get("type") in {"source-record", "machine-extracted-text"}:
        return False
    # Approved 1.2.0 amendment A2: capture records are level-7 noncanonical
    # intake objects, never part of the canonical release layer.
    if fm.get("type") == "capture":
        return False
    return bool(fm.get("id") and fm.get("type"))


def build_targets(files: list[Path]) -> tuple[dict[str, str], dict[str, list[str]]]:
    exact: dict[str, str] = {}
    stems: dict[str, list[str]] = defaultdict(list)
    for p in ROOT.rglob("*"):
        if not p.is_file() or ".git" in p.parts:
            continue
        rel = p.relative_to(ROOT).as_posix()
        if is_ignored_rel(rel):
            continue
        exact[rel] = rel
        if rel.endswith(".md"):
            exact[rel[:-3]] = rel
        stems[p.stem.casefold()].append(rel)
    return exact, stems


def resolve_link(target: str, exact: dict[str, str], stems: dict[str, list[str]]) -> str | None:
    target = target.strip().replace("\\", "/")
    for candidate in (target, target.removesuffix(".md"), target + ".md"):
        if candidate in exact:
            return exact[candidate]
    matches = stems.get(Path(target).stem.casefold(), [])
    return matches[0] if len(matches) == 1 else None


def validate() -> tuple[list[str], list[str], dict]:
    errors: list[str] = []
    warnings: list[str] = []
    metrics: dict = {}

    for rel in REQUIRED + BASE_FILES:
        if not (ROOT / rel).exists():
            errors.append(f"missing release path: {rel}")

    system_path = ROOT / "SYSTEM_DESIGN.md"
    if system_path.exists():
        system_fm, _ = parse_markdown(system_path)
        expected_version = _CONTRACT.get("system_version")
        if expected_version and str(system_fm.get("system_version")) != str(expected_version):
            errors.append(
                f"SYSTEM_DESIGN.md system_version must be {expected_version}")

    state = json.loads((ROOT / "00-system/registers/CORPUS_STATE.json").read_text(encoding="utf-8"))
    if not state.get("id"):
        errors.append("CORPUS_STATE.json is missing its corpus snapshot id")
    if "source_material_count" not in state:
        errors.append("CORPUS_STATE.json is missing source_material_count")

    for folder, minimum in MIN_COUNTS.items():
        count = len(list((ROOT / folder).glob("*.md")))
        metrics[folder] = count
        if count < minimum:
            errors.append(f"{folder}: expected at least {minimum} Markdown files, found {count}")

    files = markdown_files()
    parsed: dict[str, tuple[dict, str, int]] = {}
    for path in files:
        rel = path.relative_to(ROOT).as_posix()
        try:
            fm, body = parse_markdown(path)
        except Exception as exc:
            errors.append(f"{rel}: {exc}")
            continue
        parsed[rel] = (fm, body, body_words(body))

    for rel, (fm, body, words) in parsed.items():
        if not curated(ROOT / rel, fm):
            continue
        status = str(fm.get("status", "")).strip().casefold()
        if "stub" in status:
            errors.append(f"{rel}: stub status remains in active release ({status})")
        if status in EXEMPT_STATUSES:
            continue
        threshold = WORD_THRESHOLDS.get(str(fm.get("type")))
        if threshold and words < threshold:
            errors.append(
                f"{rel}: {fm.get('type')} has {words} body words; "
                f"release threshold is {threshold}"
            )

    for rel, (fm, _, _) in parsed.items():
        if rel.startswith("00-system/templates/"):
            continue
        if fm.get("type") != "claim-object":
            continue
        for field in ("supporting_sources", "certainty", "current_claim_permission", "responsible_language"):
            if field not in fm or fm[field] in (None, "", []):
                errors.append(f"{rel}: claim-object missing {field}")

    # Obsidian Base YAML and view structure.
    for rel in BASE_FILES:
        p = ROOT / rel
        if not p.exists():
            continue
        try:
            data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        except Exception as exc:
            errors.append(f"{rel}: invalid Base YAML: {exc}")
            continue
        if not isinstance(data, dict):
            errors.append(f"{rel}: Base root must be a mapping")
            continue
        if "filters" not in data:
            errors.append(f"{rel}: Base has no filters")
        views = data.get("views")
        if not isinstance(views, list) or not views:
            errors.append(f"{rel}: Base has no views")
        else:
            for i, view in enumerate(views, 1):
                if not isinstance(view, dict) or not view.get("type") or not view.get("name"):
                    errors.append(f"{rel}: view {i} requires type and name")

    # Benchmark contract.
    benchmark_path = ROOT / "00-system/configuration/semantic-benchmark.json"
    if benchmark_path.exists():
        try:
            benchmark = json.loads(benchmark_path.read_text(encoding="utf-8"))
        except Exception as exc:
            errors.append(f"semantic benchmark JSON invalid: {exc}")
            benchmark = {}
        cases = benchmark.get("cases", [])
        expected_cases = benchmark.get("expected_case_count", 30)
        if len(cases) != expected_cases:
            errors.append(
                f"semantic benchmark must contain {expected_cases} cases, found {len(cases)}")
        ids = [c.get("id") for c in cases if isinstance(c, dict)]
        if len(ids) != len(set(ids)):
            errors.append("semantic benchmark contains duplicate IDs")
        for case in cases:
            if not case.get("question") or not case.get("expected_suffixes"):
                errors.append(f"semantic benchmark case incomplete: {case.get('id')}")

    # Active curated orphan check.
    exact, stems = build_targets(files)
    inbound: Counter[str] = Counter()
    for rel, (_, body, _) in parsed.items():
        if rel.startswith("02-sources/text/"):
            continue
        for raw in LINK_RE.findall(body):
            resolved = resolve_link(raw, exact, stems)
            if resolved:
                inbound[resolved] += 1

    orphan_exempt_types = {
        "index", "register", "system-document", "system-plan", "release-record",
        "handoff", "decision-record", "evaluation-set", "audit-run",
    }
    for rel, (fm, _, _) in parsed.items():
        if not curated(ROOT / rel, fm):
            continue
        if fm.get("type") in orphan_exempt_types:
            continue
        status = str(fm.get("status", "")).casefold()
        if status in EXEMPT_STATUSES:
            continue
        if inbound[rel] == 0:
            errors.append(f"{rel}: active canonical record has no inbound wikilink")

    metrics["curated_markdown"] = sum(
        1 for rel, (fm, _, _) in parsed.items() if curated(ROOT / rel, fm)
    )
    metrics["body_words"] = sum(
        words for rel, (fm, _, words) in parsed.items() if curated(ROOT / rel, fm)
    )
    metrics["orphans"] = sum(1 for e in errors if "no inbound wikilink" in e)

    return errors, warnings, metrics


def main() -> int:
    errors, warnings, metrics = validate()
    for warning in warnings:
        print(f"WARNING: {warning}")
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        print(f"FAILED: {len(errors)} content-release error(s)", file=sys.stderr)
        return 1
    print("PASS: populated wiki content, dispositions, Bases, benchmark, and release structure are valid")
    print(json.dumps(metrics, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

