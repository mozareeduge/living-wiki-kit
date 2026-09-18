#!/usr/bin/env python3
"""Read-only holdings-census audit (tasks.md E1, design.md section 1).

Reproduces, in one command, the audit that motivated corpus-census-truth:
registered vs. held counts and their tier breakdown, records whose `status`
disagrees with the manifest, the proposal and claim adjudication backlog,
register freshness, and mojibake hits -- ending in one verdict line.

Read-only by construction: no argument here writes a file, sets a `--fix`
path, touches the network, or calls a model. `_audits/runtime/` (gitignored)
is the only directory this instrument is even permitted to write to, and it
never does so today (design.md section 1; tasks.md E1 Negative).

Degrades gracefully on an instance that has not adopted this change: the
registered/held/unregistered counts, contradiction check, proposal and claim
backlogs, and mojibake scan need only the manifest, the source records, and
the proposal/claim directories, so they run with no HOLDINGS_POLICY.json.
Only the tier breakdown (section 1's third column) and the register
freshness flags (section 5) need policy files that may not exist yet; when
they are missing, the report says so by name instead of crashing (tasks.md
E1 acceptance (d)).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
ROOT = SCRIPTS_DIR.parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))
import validate_repo  # noqa: E402 -- reuse its helpers, do not reimplement them

MANIFEST_REL = "00-system/registers/MATERIALS_INDEX.jsonl"
STATE_REL = "00-system/registers/CORPUS_STATE.json"
PROPOSALS_REL = "_proposals/proposals.jsonl"
CONTENT_RELEASE_REL = "00-system/configuration/content-release.json"
HOLDINGS_TIER_REGISTERED = validate_repo.HOLDINGS_TIER_REGISTERED


# --------------------------------------------------------------- raw loads
# Thin file-reading wrappers only. Every non-trivial rule (frontmatter
# parsing, mojibake detection, the tier policy shape, the refresh-policy
# enum and date format) comes from scripts/validate_repo.py so this report
# can never quietly drift from what the gate itself enforces.

def _long_path(p: Path) -> Path:
    """Return `p` usable for filesystem calls past Windows' 260-char limit.

    Found live (2026-09-18) auditing a throwaway clone of mozare-wiki
    nested under a deep temp directory: plain `os.scandir`/`pathlib.rglob`
    silently dropped 17 of 544 `_originals/` files whose full path exceeded
    the classic MAX_PATH -- no exception, just a wrong number, which is
    exactly what this instrument exists to catch (design.md section 1).
    The `\\\\?\\` extended-length prefix opts a Windows path out of that
    limit. POSIX has no such limit and is returned unchanged.
    """
    if os.name != "nt":
        return p
    resolved = str(p.resolve())
    if resolved.startswith("\\\\?\\"):
        return Path(resolved)
    return Path("\\\\?\\" + resolved)


def _walk_files(
    directory: Path, root: Path, suffix: str | None = None
) -> list[tuple[Path, str]]:
    """List files under `directory`, MAX_PATH-safely, as (path, rel) pairs.

    `path` is directly usable for reads (long-path-prefixed on Windows);
    `rel` is the ordinary root-relative POSIX string every other part of
    this report keys on. Optionally filtered to a filename suffix.
    """
    if not directory.exists():
        return []
    root_resolved = root.resolve()
    scan_root = _long_path(directory)
    out: list[tuple[Path, str]] = []
    for dirpath, _dirnames, filenames in os.walk(scan_root):
        clean_dirpath = dirpath[4:] if dirpath.startswith("\\\\?\\") else dirpath
        dirpath_path = Path(clean_dirpath)
        for fn in filenames:
            if suffix and not fn.endswith(suffix):
                continue
            full = dirpath_path / fn
            rel = full.relative_to(root_resolved).as_posix()
            out.append((full, rel))
    out.sort(key=lambda pair: pair[1])
    return out

def _load_manifest_rows(root: Path) -> tuple[list[dict], list[str]]:
    """Return (rows, parse_errors); a malformed line is reported, not fatal."""
    path = root / MANIFEST_REL
    if not path.exists():
        return [], []
    rows: list[dict] = []
    parse_errors: list[str] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as exc:
            parse_errors.append(f"{MANIFEST_REL}: line {number}: {exc}")
    return rows, parse_errors


def _load_state(root: Path) -> dict:
    path = root / STATE_REL
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _originals_files(root: Path) -> list[str]:
    return [rel for _path, rel in _walk_files(root / "_originals", root)]


def _load_records(root: Path) -> tuple[dict[str, dict], list[str]]:
    """rel -> frontmatter for every 02-sources/records/*.md; plus parse errors."""
    records_dir = root / "02-sources" / "records"
    records: dict[str, dict] = {}
    parse_errors: list[str] = []
    for path, rel in _walk_files(records_dir, root, suffix=".md"):
        try:
            records[rel] = validate_repo.parse_frontmatter(path)
        except Exception as exc:  # noqa: BLE001 -- report, do not crash
            parse_errors.append(f"{rel}: {exc}")
    return records, parse_errors


def _load_proposals(root: Path) -> tuple[list[dict], int]:
    path = root / PROPOSALS_REL
    if not path.exists():
        return [], 0
    proposals: list[dict] = []
    malformed = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            proposals.append(json.loads(line))
        except json.JSONDecodeError:
            malformed += 1
    return proposals, malformed


def _load_claims(root: Path) -> tuple[list[dict], list[str]]:
    claims_dir = root / "05-claims"
    claims: list[dict] = []
    parse_errors: list[str] = []
    for path, rel in _walk_files(claims_dir, root, suffix=".md"):
        try:
            claims.append(validate_repo.parse_frontmatter(path))
        except Exception as exc:  # noqa: BLE001
            parse_errors.append(f"{rel}: {exc}")
    return claims, parse_errors


# ------------------------------------------------------------ section logic

def _section1_counts_and_tiers(
    root: Path, rows: list[dict], originals: list[str], records: dict[str, dict]
) -> dict:
    manifest_original_paths = {
        row["original_path"] for row in rows if row.get("original_path")
    }
    registered = len(rows)
    held = len(originals)
    registered_held = sum(1 for rel in originals if rel in manifest_original_paths)
    unregistered = held - registered_held

    try:
        policy = validate_repo.load_holdings_policy(root)
    except ValueError as exc:
        return {
            "registered": registered,
            "held": held,
            "unregistered": unregistered,
            "tier_breakdown": None,
            "tier_breakdown_unavailable_reason": str(exc),
        }

    declared_tiers = sorted(policy["tiers"])
    original_to_tier: dict[str, str] = {}
    for fm in records.values():
        op = fm.get("original_path")
        tier = fm.get("holdings_tier")
        if op and tier in declared_tiers:
            original_to_tier[op] = tier

    breakdown = {tier: 0 for tier in declared_tiers}
    breakdown["undeclared"] = 0
    for rel in originals:
        if rel in manifest_original_paths:
            if HOLDINGS_TIER_REGISTERED in breakdown:
                breakdown[HOLDINGS_TIER_REGISTERED] += 1
            else:
                breakdown["undeclared"] += 1
            continue
        tier = original_to_tier.get(rel)
        if tier in breakdown:
            breakdown[tier] += 1
        else:
            breakdown["undeclared"] += 1

    return {
        "registered": registered,
        "held": held,
        "unregistered": unregistered,
        "tier_breakdown": breakdown,
        "tier_breakdown_unavailable_reason": None,
    }


def _section2_status_contradictions(
    rows: list[dict], records: dict[str, dict]
) -> dict:
    """Records whose `status` disagrees with manifest membership.

    Independent of HOLDINGS_POLICY.json on purpose -- an instance with no
    tier policy still has a manifest and source records, and this
    biconditional (design.md section 3 rule 1 / tasks.md A2 invariant 1) is
    checkable from those two alone. Reusing check_holdings_census here
    would silently skip this section on such an instance, because that
    helper returns early when load_holdings_policy raises.
    """
    registered_record_paths = {
        row["source_record_path"] for row in rows if row.get("source_record_path")
    }
    bad: list[str] = []
    for rel, fm in sorted(records.items()):
        claims_registered = fm.get("status") == HOLDINGS_TIER_REGISTERED
        is_manifest_row = rel in registered_record_paths
        if claims_registered != is_manifest_row:
            bad.append(rel)
    return {"count": len(bad), "first_five": bad[:5]}


def _section3_proposals(root: Path) -> dict:
    proposals, malformed = _load_proposals(root)
    by_status: Counter = Counter(p.get("status", "(missing status)") for p in proposals)
    return {
        "total": len(proposals),
        "by_status": dict(sorted(by_status.items())),
        "new": by_status.get("new", 0),
        "malformed_lines": malformed,
    }


def _section4_claims(claims: list[dict]) -> dict:
    by_permission: Counter = Counter(
        c.get("current_claim_permission", "(missing)") for c in claims
    )
    return {
        "total": len(claims),
        "by_permission": dict(sorted(by_permission.items())),
        "blocked": by_permission.get("blocked", 0),
    }


def _section5_registers(root: Path, state: dict) -> list[dict]:
    """Every .md register with its declared refresh_policy and a STALE flag.

    Mirrors validate_repo.check_register_policies' rules (per-intake vs.
    CORPUS_STATE.updated, per-release vs. content-release.json's updated,
    static never stale), but reports rather than raises: a missing or
    unknown refresh_policy, or an unparseable date, is its own row with
    `stale: None` (not determinable) instead of aborting the report.
    """
    registers_dir = root / "00-system" / "registers"

    corpus_updated = state.get("updated")

    release_path = root / CONTENT_RELEASE_REL
    release_updated = None
    if release_path.exists():
        try:
            release_cfg = json.loads(release_path.read_text(encoding="utf-8"))
            release_updated = release_cfg.get("updated")
        except json.JSONDecodeError:
            release_updated = None

    def _iso(value) -> bool:
        return isinstance(value, str) and bool(validate_repo.ISO_DATE_RE.match(value))

    rows: list[dict] = []
    for path, rel in _walk_files(registers_dir, root, suffix=".md"):
        if rel.startswith("00-system/registers/archive/"):
            continue
        try:
            fm = validate_repo.parse_frontmatter(path)
        except Exception:  # noqa: BLE001
            rows.append({"path": rel, "refresh_policy": None, "updated": None,
                         "stale": None, "note": "frontmatter did not parse"})
            continue

        policy = fm.get("refresh_policy")
        updated = fm.get("updated")
        if policy not in validate_repo.REGISTER_LEGAL_POLICIES:
            rows.append({"path": rel, "refresh_policy": policy, "updated": updated,
                         "stale": None, "note": "no legal refresh_policy declared"})
            continue
        if not _iso(updated):
            rows.append({"path": rel, "refresh_policy": policy, "updated": updated,
                         "stale": None, "note": "updated is not an ISO date"})
            continue

        stale: bool | None
        note = ""
        if policy == "static":
            stale = False
        elif policy == "per-intake":
            stale = updated < corpus_updated if _iso(corpus_updated) else None
            if stale is None:
                note = "CORPUS_STATE.updated unavailable"
        else:  # per-release
            stale = updated < release_updated if _iso(release_updated) else None
            if stale is None:
                note = f"{CONTENT_RELEASE_REL} updated unavailable"
        rows.append({"path": rel, "refresh_policy": policy, "updated": updated,
                     "stale": stale, "note": note})
    return rows


def _section6_mojibake(rows: list[dict], records: dict[str, dict]) -> dict:
    hits: Counter = Counter()
    for row in rows:
        for key in ("original_path", "filename", "source_record_path",
                    "extracted_text_path"):
            value = row.get(key)
            if isinstance(value, str) and validate_repo.looks_double_encoded(value):
                hits[key] += 1
    for fm in records.values():
        for key in ("original_path", "filename", "title"):
            value = fm.get(key)
            if isinstance(value, str) and validate_repo.looks_double_encoded(value):
                hits[key] += 1
        aliases = fm.get("aliases")
        if isinstance(aliases, list):
            for alias in aliases:
                if isinstance(alias, str) and validate_repo.looks_double_encoded(alias):
                    hits["aliases"] += 1
    return dict(sorted(hits.items()))


# ---------------------------------------------------------------- assembly

def generate_report(root: Path) -> dict:
    """Compute the full seven-section report as a JSON-serializable dict.

    Read-only: opens files under `root`, writes none, calls no subprocess,
    touches no network.
    """
    rows, manifest_parse_errors = _load_manifest_rows(root)
    state = _load_state(root)
    originals = _originals_files(root)
    records, record_parse_errors = _load_records(root)
    claims, claim_parse_errors = _load_claims(root)

    section1 = _section1_counts_and_tiers(root, rows, originals, records)
    section2 = _section2_status_contradictions(rows, records)
    section3 = _section3_proposals(root)
    section4 = _section4_claims(claims)
    section5 = _section5_registers(root, state)
    section6 = _section6_mojibake(rows, records)

    stale_count = sum(1 for r in section5 if r.get("stale") is True)
    undeclared_count = 0
    if section1["tier_breakdown"] is not None:
        undeclared_count = section1["tier_breakdown"].get("undeclared", 0)
    mojibake_total = sum(section6.values())
    findings = (
        section2["count"] + stale_count + mojibake_total + undeclared_count
    )
    verdict = "CENSUS CLEAN" if findings == 0 else f"CENSUS DRIFT: {findings} findings"

    return {
        "registered": section1["registered"],
        "held": section1["held"],
        "unregistered": section1["unregistered"],
        "tier_breakdown": section1["tier_breakdown"],
        "tier_breakdown_unavailable_reason": section1["tier_breakdown_unavailable_reason"],
        "status_contradictions": section2,
        "proposals_by_status": section3,
        "claims_by_permission": section4,
        "registers": section5,
        "mojibake_by_field": section6,
        "parse_errors": {
            "manifest": manifest_parse_errors,
            "records": record_parse_errors,
            "claims": claim_parse_errors,
        },
        "findings": findings,
        "verdict": verdict,
    }


def render_report(report: dict) -> str:
    lines: list[str] = []

    lines.append("1. Registered / held / unregistered, and tier breakdown")
    lines.append(f"   registered: {report['registered']}")
    lines.append(f"   held: {report['held']}")
    lines.append(f"   unregistered: {report['unregistered']}")
    if report["tier_breakdown"] is None:
        lines.append(
            "   tier breakdown: unavailable -- "
            f"{report['tier_breakdown_unavailable_reason']}"
        )
    else:
        for tier, count in sorted(report["tier_breakdown"].items()):
            lines.append(f"   {tier}: {count}")

    lines.append("")
    lines.append("2. Records whose status contradicts the manifest")
    sc = report["status_contradictions"]
    lines.append(f"   count: {sc['count']}")
    for path in sc["first_five"]:
        lines.append(f"   - {path}")

    lines.append("")
    lines.append("3. Proposals by status (_proposals/proposals.jsonl)")
    pr = report["proposals_by_status"]
    lines.append(f"   total: {pr['total']}")
    for status, count in pr["by_status"].items():
        lines.append(f"   {status}: {count}")
    lines.append(f"   new (adjudication backlog): {pr['new']}")
    if pr["malformed_lines"]:
        lines.append(f"   malformed lines: {pr['malformed_lines']}")

    lines.append("")
    lines.append("4. Claims by current_claim_permission (05-claims/)")
    cl = report["claims_by_permission"]
    lines.append(f"   total: {cl['total']}")
    for perm, count in cl["by_permission"].items():
        lines.append(f"   {perm}: {count}")
    lines.append(f"   blocked: {cl['blocked']}")

    lines.append("")
    lines.append("5. Registers: refresh_policy and STALE flag")
    if not report["registers"]:
        lines.append("   (no registers found)")
    for row in report["registers"]:
        stale = {True: "STALE", False: "fresh", None: "n/a"}[row["stale"]]
        note = f" ({row['note']})" if row.get("note") else ""
        lines.append(
            f"   {row['path']}: refresh_policy={row['refresh_policy']!r} "
            f"updated={row['updated']!r} {stale}{note}"
        )

    lines.append("")
    lines.append("6. Mojibake hits by field")
    mb = report["mojibake_by_field"]
    if not mb:
        lines.append("   (none)")
    for field, count in mb.items():
        lines.append(f"   {field}: {count}")

    lines.append("")
    lines.append(f"7. Verdict: {report['verdict']}")

    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--json", action="store_true",
        help="emit one JSON object instead of the human-readable sections",
    )
    args = ap.parse_args(argv)

    report = generate_report(ROOT)

    if args.json:
        # default=str: a frontmatter `updated:` written unquoted (e.g.
        # `updated: 2026-09-16`) parses through PyYAML as a datetime.date,
        # not a string -- found live against mozare-wiki's own
        # CORPUS_MAP.md. json.dumps has no default encoding for that type;
        # falling back to str() renders its ISO form instead of crashing,
        # matching what the plain-text report already shows via f-string
        # interpolation.
        print(json.dumps(report, sort_keys=True, default=str))
    else:
        print(render_report(report), end="")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
