"""Tests for schema_drift_fixer.py (path-derivable frontmatter repair).

Contract under test: the fixer derives corrections ONLY from a file's path or
its own sibling frontmatter, freezes them as a manifest, and applies exactly
that manifest. It never touches semantic fields and never invents a value.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

KIT_ROOT = Path(__file__).resolve().parents[1]
FIXER = KIT_ROOT / "scripts" / "schema_drift_fixer.py"
sys.path.insert(0, str(KIT_ROOT / "scripts"))

import schema_drift_fixer as fx  # noqa: E402


def _write(root: Path, rel: str, text: str) -> Path:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(text.encode("utf-8"))
    return p


def _errors(root: Path, *lines: str) -> Path:
    p = root / "validate-out.txt"
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return p


def _plan(root: Path, *lines: str):
    return fx.plan_ops(root, _errors(root, *lines))


# ------------------------------------------------------------------ planning

def test_plan_derives_filename_from_original_path(tmp_path):
    _write(tmp_path, "02-sources/records/s1.md",
           "---\nid: s1\noriginal_path: _originals/sub/Doc One.pdf\n---\nbody\n")
    ops, skipped = _plan(tmp_path,
                         "ERROR: 02-sources/records/s1.md: missing required field 'filename'")
    assert ops == [{"path": "02-sources/records/s1.md", "op": "insert",
                    "after_key": "id", "field": "filename", "value": "Doc One.pdf"}]
    assert skipped == []


def test_plan_normalizes_windows_backslash_original_path(tmp_path):
    _write(tmp_path, "02-sources/records/s1.md",
           "---\nid: s1\noriginal_path: '_originals\\\\sub\\\\scan.png'\n---\n")
    ops, _ = _plan(tmp_path,
                   "ERROR: 02-sources/records/s1.md: missing required field 'filename'")
    assert [o["value"] for o in ops] == ["scan.png"]


def test_plan_bracket_original_path_is_skipped_not_invented(tmp_path):
    _write(tmp_path, "02-sources/records/s1.md",
           "---\nid: s1\noriginal_path: _originals/[garbled name].pdf\n---\n")
    ops, skipped = _plan(tmp_path,
                         "ERROR: 02-sources/records/s1.md: missing required field 'filename'")
    # the basename starts with '[': a YAML-corrupting value must never be written
    assert ops == []
    assert len(skipped) == 1 and "underivable" in skipped[0]
    assert "02-sources/records/s1.md" in skipped[0]


def test_plan_missing_original_path_is_skipped(tmp_path):
    _write(tmp_path, "02-sources/records/s1.md", "---\nid: s1\n---\n")
    ops, skipped = _plan(tmp_path,
                         "ERROR: 02-sources/records/s1.md: missing required field 'filename'")
    assert ops == []
    assert "no original_path" in skipped[0]


def test_plan_type_and_kind_are_derived_from_zone_and_directory(tmp_path):
    ops, skipped = _plan(
        tmp_path,
        "ERROR: 02-sources/records/s1.md: source record type must be 'source-record'",
        "ERROR: 03-objects/people/p.md: object type must be 'object', got person",
        "ERROR: 03-objects/methods/m.md: missing required field 'kind'",
        "ERROR: 03-objects/works/w.md: object kind must be 'work' for 03-objects/works/, got concept",
        "ERROR: 05-claims/c.md: missing required field 'type'",
        "ERROR: 06-relations/r.md: missing required field 'type'",
    )
    by_path = {o["path"]: o for o in ops}
    assert by_path["02-sources/records/s1.md"]["value"] == "source-record"
    assert by_path["03-objects/people/p.md"] == {
        "path": "03-objects/people/p.md", "op": "set", "field": "type", "value": "object"}
    assert by_path["03-objects/methods/m.md"]["value"] == "method"
    assert by_path["03-objects/methods/m.md"]["after_key"] == "type"
    assert by_path["03-objects/works/w.md"]["value"] == "work"
    assert by_path["05-claims/c.md"]["value"] == "claim-object"
    assert by_path["06-relations/r.md"]["value"] == "relation-object"
    assert skipped == []


@pytest.mark.parametrize("folder,kind", [
    ("concepts", "concept"), ("institutions", "institution"), ("methods", "method"),
    ("people", "person"), ("references", "reference"), ("works", "work"),
    ("projects", "project"), ("collections", "collection"),
])
def test_plan_missing_kind_uses_the_pinned_directory_mapping(tmp_path, folder, kind):
    """The mapping is written out literally here so a silent edit of
    OBJECT_KIND_BY_DIR cannot pass by agreeing with itself."""
    rel = f"03-objects/{folder}/x.md"
    ops, skipped = _plan(tmp_path, f"ERROR: {rel}: missing required field 'kind'")
    assert [(o["field"], o["value"]) for o in ops] == [("kind", kind)]
    assert skipped == []


def test_plan_unknown_object_directory_is_skipped(tmp_path):
    ops, skipped = _plan(tmp_path,
                         "ERROR: 03-objects/gadgets/g.md: missing required field 'kind'")
    assert ops == []
    assert "unknown dir" in skipped[0]


def test_plan_type_error_outside_known_zones_is_skipped(tmp_path):
    ops, skipped = _plan(tmp_path,
                         "ERROR: 04-notes/n.md: missing required field 'type'")
    assert ops == []
    assert "zone unknown" in skipped[0]


def test_plan_ignores_semantic_field_errors(tmp_path):
    ops, skipped = _plan(
        tmp_path,
        "ERROR: 05-claims/c.md: missing required field 'counter_evidence'",
        "ERROR: 05-claims/c.md: unknown status 'maybe'",
        "ERROR: 02-sources/records/s1.md: alias contains mojibake",
        "ERROR: 02-sources/records/s2.md: missing required field 'title'",
        "WARNING: 04-notes/n.md: no frontmatter",
    )
    assert ops == [] and skipped == []


# ------------------------------------------------------------------ applying

def test_apply_insert_goes_after_the_anchor_and_leaves_body_untouched(tmp_path):
    p = _write(tmp_path, "03-objects/people/p.md",
               "---\nid: obj-1\ntype: object\ntitle: A\n---\nbody line\n")
    changed, failed = fx.apply_manifest(tmp_path, {"operations": [
        {"path": "03-objects/people/p.md", "op": "insert", "after_key": "type",
         "field": "kind", "value": "person"}]})
    assert (changed, failed) == (1, 0)
    assert p.read_text(encoding="utf-8") == (
        "---\nid: obj-1\ntype: object\nkind: person\ntitle: A\n---\nbody line\n")


def test_apply_set_replaces_only_the_named_field(tmp_path):
    p = _write(tmp_path, "03-objects/people/p.md",
               "---\nid: obj-1\ntype: person\ntitle: type: not this\n---\nbody\n")
    fx.apply_manifest(tmp_path, {"operations": [
        {"path": "03-objects/people/p.md", "op": "set", "field": "type", "value": "object"}]})
    assert p.read_text(encoding="utf-8") == (
        "---\nid: obj-1\ntype: object\ntitle: type: not this\n---\nbody\n")


def test_apply_insert_refuses_when_the_key_already_exists(tmp_path):
    original = "---\nid: obj-1\nkind: concept\n---\nbody\n"
    p = _write(tmp_path, "03-objects/people/p.md", original)
    changed, failed = fx.apply_manifest(tmp_path, {"operations": [
        {"path": "03-objects/people/p.md", "op": "insert", "after_key": "id",
         "field": "kind", "value": "person"}]})
    assert (changed, failed) == (0, 1)
    assert p.read_text(encoding="utf-8") == original  # never overwrites a present value


def test_apply_counts_missing_file_and_missing_frontmatter_as_failed(tmp_path):
    original = "no frontmatter here\n"
    p = _write(tmp_path, "05-claims/c.md", original)
    changed, failed = fx.apply_manifest(tmp_path, {"operations": [
        {"path": "05-claims/gone.md", "op": "set", "field": "type", "value": "claim-object"},
        {"path": "05-claims/c.md", "op": "set", "field": "type", "value": "claim-object"}]})
    assert (changed, failed) == (0, 2)
    assert p.read_text(encoding="utf-8") == original


def test_apply_keeps_the_body_when_the_file_uses_crlf(tmp_path):
    """Characterisation: the fixer reads in text mode, so CRLF files come back
    LF-normalised (git's `* text=auto` hides this). The body content must
    survive either way; only line endings may differ."""
    p = _write(tmp_path, "03-objects/people/p.md",
               "---\r\nid: obj-1\r\ntype: thing\r\n---\r\nbody\r\nsecond\r\n")
    fx.apply_manifest(tmp_path, {"operations": [
        {"path": "03-objects/people/p.md", "op": "set", "field": "type", "value": "object"}]})
    out = p.read_bytes().decode("utf-8").replace("\r\n", "\n")
    assert out == "---\nid: obj-1\ntype: object\n---\nbody\nsecond\n"


# ----------------------------------------------------------------------- CLI

def _run(root: Path, errors: Path, *extra: str):
    return subprocess.run(
        [sys.executable, "-B", str(FIXER), "--errors", str(errors), "--root", str(root), *extra],
        capture_output=True, text=True, encoding="utf-8", errors="replace")


def _manifest(root: Path) -> dict:
    found = list((root / "_audits").glob("*schema-drift-reconcile/PATCH_MANIFEST.json"))
    assert len(found) == 1, found
    return json.loads(found[0].read_text(encoding="utf-8"))


def test_cli_dry_run_writes_a_manifest_and_changes_no_content(tmp_path):
    original = "---\nid: obj-1\ntype: person\n---\nbody\n"
    p = _write(tmp_path, "03-objects/people/p.md", original)
    err = _errors(tmp_path,
                  "ERROR: 03-objects/people/p.md: object type must be 'object', got person")
    r = _run(tmp_path, err)
    assert r.returncode == 0, r.stdout + r.stderr
    assert p.read_text(encoding="utf-8") == original
    m = _manifest(tmp_path)
    assert m["status"] == "auto-derived-path-fields"
    assert len(m["operations"]) == 1 and m["skipped_underivable"] == []


def test_cli_apply_executes_exactly_the_manifest(tmp_path):
    p = _write(tmp_path, "03-objects/people/p.md", "---\nid: obj-1\ntype: person\n---\nbody\n")
    untouched = _write(tmp_path, "03-objects/people/q.md", "---\nid: obj-2\ntype: person\n---\n")
    err = _errors(tmp_path,
                  "ERROR: 03-objects/people/p.md: object type must be 'object', got person")
    r = _run(tmp_path, err, "--apply")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "applied: 1 changed, 0 failed" in r.stdout
    assert "type: object" in p.read_text(encoding="utf-8")
    assert "type: person" in untouched.read_text(encoding="utf-8")


def test_cli_apply_exits_nonzero_when_an_operation_fails(tmp_path):
    err = _errors(tmp_path,
                  "ERROR: 02-sources/records/absent.md: source record type must be 'source-record'")
    r = _run(tmp_path, err, "--apply")
    assert r.returncode == 1, r.stdout + r.stderr
    assert "1 failed" in r.stdout


def test_cli_requires_an_errors_file(tmp_path):
    r = subprocess.run([sys.executable, "-B", str(FIXER), "--root", str(tmp_path)],
                       capture_output=True, text=True)
    assert r.returncode == 2
    assert "--errors" in r.stderr
