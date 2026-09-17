import importlib.util
import inspect
import json
import sys
import tempfile
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts" / "validate_repo.py"


spec = importlib.util.spec_from_file_location("validate_repo", VALIDATOR)
validate_repo = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(validate_repo)

RETIER = ROOT / "scripts" / "retier_holdings.py"
_retier_spec = importlib.util.spec_from_file_location("retier_holdings", RETIER)
retier_holdings = importlib.util.module_from_spec(_retier_spec)
assert _retier_spec.loader is not None
_retier_spec.loader.exec_module(retier_holdings)


def collect(rel, frontmatter):
    errors = []
    validate_repo.validate_live_record_schema(rel, frontmatter, errors)
    return errors


def test_source_record_requires_filename():
    errors = collect("02-sources/records/ref-src-deadbeef0000.md", {
        "id": "ref-src-deadbeef0000",
        "type": "source-record",
        "title": "Example",
        "format": "md",
        "sha256": "0" * 64,
        "original_path": "_originals/example.md",
        "authority_scope": "test",
        "validation_status": "test",
    })
    assert any("filename" in error for error in errors)


def test_source_record_rejects_unknown_format():
    errors = collect("02-sources/records/ref-src-deadbeef0000.md", {
        "id": "ref-src-deadbeef0000",
        "type": "source-record",
        "title": "Example",
        "filename": "example.bin",
        "format": "bin",
        "sha256": "0" * 64,
        "original_path": "_originals/example.bin",
        "authority_scope": "test",
        "validation_status": "test",
    })
    assert any("unsupported source format" in error for error in errors)


def test_people_objects_must_use_person_kind():
    errors = collect("03-objects/people/example.md", {
        "id": "ref-obj-example",
        "type": "object",
        "title": "Example Person",
        "kind": "peopl",
        "status": "active-record",
    })
    assert any("object kind must be 'person'" in error for error in errors)


def test_claim_permission_enum_is_enforced():
    errors = collect("05-claims/example.md", {
        "id": "ref-claim-example",
        "type": "claim-object",
        "title": "Example Claim",
        "statement": "Example.",
        "supporting_sources": ["ref-src-deadbeef0000"],
        "unsupported_zones": [],
        "counter_evidence": [],
        "certainty": "candidate",
        "current_claim_permission": "sure-go-ahead",
        "responsible_language": "en",
    })
    assert any("invalid current_claim_permission" in error for error in errors)


# ---------------------------------------------------------------- entry gate
# Shared fixture helpers for check_entry_pages tests (task 1.2/1.3).

ENTRY_PAGE_NAMES = ("HOME.md", "README.md", "SYSTEM_DESIGN.md", "CLAUDE.md")


def _page_text(snapshot, count, layers):
    """Build one entry page body with the exact labelled markers."""
    parts = []
    if snapshot is not None:
        parts.append(f"Current corpus snapshot: `{snapshot}`")
    if count is not None:
        parts.append(f"Registered source artifacts: {count}")
    if layers:
        parts.append("Layer counts: " + ", ".join(layers) + ".")
    parts.append("Live truth: 00-system/registers/CORPUS_STATE.json and "
                 "MATERIALS_INDEX.jsonl.")
    return "\n\n".join(parts) + "\n"


def _fresh_pages(state_id="snap-1", count=103):
    return {
        "HOME.md": _page_text(state_id, count,
                              ["2 objects", "1 relations", "1 claims", "1 indexes"]),
        "README.md": _page_text(state_id, count,
                                ["2 objects", "1 relations", "1 claims", "1 indexes"]),
        "SYSTEM_DESIGN.md": _page_text(state_id, count, None),
        "CLAUDE.md": _page_text(state_id, count, None),
    }


def _gate_root(base, pages, objects=2, relations=1, claims=1, indexes=1):
    root = base / "repo"
    root.mkdir(parents=True, exist_ok=True)
    (root / "00-system" / "registers").mkdir(parents=True, exist_ok=True)
    (root / "00-system" / "registers" / "CORPUS_STATE.json").write_text(
        "{}", encoding="utf-8")
    for dirname, n in (("03-objects", objects), ("06-relations", relations),
                       ("05-claims", claims), ("09-indexes", indexes)):
        d = root / dirname
        d.mkdir(parents=True, exist_ok=True)
        for i in range(n):
            sub = d / f"sub{i}" if i % 2 else d  # prove recursion
            sub.mkdir(exist_ok=True)
            (sub / f"f{i}.md").write_text("x", encoding="utf-8")
    for rel, text in pages.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
    return root


def _run_gate(root, state):
    errors = []
    validate_repo.check_entry_pages(root, state, errors)
    return errors


REFRESH_HINT = "refresh the entry page from the registers in the same change"


def test_entry_pages_all_fresh_pass():
    with tempfile.TemporaryDirectory() as td:
        root = _gate_root(Path(td), _fresh_pages())
        state = {"id": "snap-1", "source_material_count": 103}
        assert _run_gate(root, state) == []


def test_entry_page_stale_snapshot_detected_per_page():
    for stale in ENTRY_PAGE_NAMES:
        with tempfile.TemporaryDirectory() as td:
            pages = _fresh_pages()
            pages[stale] = pages[stale].replace("snap-1", "snap-0")
            root = _gate_root(Path(td), pages)
            state = {"id": "snap-1", "source_material_count": 103}
            errors = _run_gate(root, state)
            assert any(
                stale in e and "snap-1" in e and "CORPUS_STATE.json" in e
                and REFRESH_HINT in e
                for e in errors
            ), f"{stale}: {errors}"
            # The message must show the value actually on the page, not a
            # bare label: the stale id lives inside a code span, which
            # _visible_prose() strips.
            assert any("observed:" in e and "snap-0" in e for e in errors), (
                f"{stale}: observed value missing from {errors}")


def test_entry_page_wrong_labelled_count_detected_per_page():
    for stale in ENTRY_PAGE_NAMES:
        with tempfile.TemporaryDirectory() as td:
            pages = _fresh_pages()
            pages[stale] = pages[stale].replace(
                "Registered source artifacts: 103",
                "Registered source artifacts: 999")
            root = _gate_root(Path(td), pages)
            state = {"id": "snap-1", "source_material_count": 103}
            errors = _run_gate(root, state)
            assert any(
                stale in e and "999" in e and "103" in e and REFRESH_HINT in e
                for e in errors
            ), f"{stale}: {errors}"


def test_unrelated_zero_does_not_satisfy_zero_marker():
    with tempfile.TemporaryDirectory() as td:
        pages = _fresh_pages(state_id="s0", count=0)
        for name in ENTRY_PAGE_NAMES:
            # replace the labelled marker with prose that merely contains a 0
            pages[name] = pages[name].replace(
                "Registered source artifacts: 0",
                "Build 0 of the entry page; snapshot anchor stays above.")
        root = _gate_root(Path(td), pages, objects=0, relations=0,
                          claims=0, indexes=0)
        state = {"id": "s0", "source_material_count": 0}
        errors = _run_gate(root, state)
        assert all(
            any(name in e and "Registered source artifacts: 0" in e
                for e in errors)
            for name in ENTRY_PAGE_NAMES
        ), errors


def test_missing_state_id_skips_only_snapshot_check():
    with tempfile.TemporaryDirectory() as td:
        pages = _fresh_pages()
        for name in ENTRY_PAGE_NAMES:
            # drop the snapshot line entirely, keep the count line
            pages[name] = pages[name].replace(
                "Current corpus snapshot: `snap-1`\n\n", "")
        root = _gate_root(Path(td), pages)
        state = {"source_material_count": 103}
        assert _run_gate(root, state) == []


def test_empty_layers_declared_zero_pass():
    with tempfile.TemporaryDirectory() as td:
        pages = _fresh_pages(state_id="s0", count=0)
        for name in ENTRY_PAGE_NAMES:
            pages[name] = pages[name].replace(
                "Layer counts: 2 objects, 1 relations, 1 claims, 1 indexes.",
                "Layer counts: 0 objects, 0 relations, 0 claims, 0 indexes.")
        root = _gate_root(Path(td), pages, objects=0, relations=0,
                          claims=0, indexes=0)
        state = {"id": "s0", "source_material_count": 0}
        assert _run_gate(root, state) == []


def test_every_layer_declaration_occurrence_is_checked():
    with tempfile.TemporaryDirectory() as td:
        pages = _fresh_pages()
        pages["HOME.md"] = pages["HOME.md"].replace(
            "2 objects", "2 objects, then later prose says 3 objects")
        root = _gate_root(Path(td), pages)
        state = {"id": "snap-1", "source_material_count": 103}
        errors = _run_gate(root, state)
        contradicting = [e for e in errors if "3 objects" in e]
        assert len(contradicting) == 1, errors
        assert "HOME.md" in contradicting[0] and "2" in contradicting[0]


def test_singular_plural_case_insensitive_layers():
    with tempfile.TemporaryDirectory() as td:
        pages = _fresh_pages()
        pages["README.md"] = pages["README.md"].replace(
            "Layer counts: 2 objects",
            "Layer counts: 1 relation, 1 Object")
        # actual: objects=2 -> "1 Object" contradicts; relations=1 -> ok
        root = _gate_root(Path(td), pages)
        state = {"id": "snap-1", "source_material_count": 103}
        errors = _run_gate(root, state)
        assert any("1 Object" in e for e in errors), errors
        assert not any("1 relation" in e and "README.md" in e for e in errors)


def test_fenced_and_inline_code_layers_ignored():
    with tempfile.TemporaryDirectory() as td:
        pages = _fresh_pages()
        pages["SYSTEM_DESIGN.md"] = _page_text("snap-1", 103, None) + (
            "\nExample block:\n\n```text\n99 objects\n```\n\n"
            "Inline `99 claims` never happened.\n"
        )
        root = _gate_root(Path(td), pages)
        state = {"id": "snap-1", "source_material_count": 103}
        assert _run_gate(root, state) == []


def test_missing_entry_page_reported():
    with tempfile.TemporaryDirectory() as td:
        pages = _fresh_pages()
        del pages["CLAUDE.md"]
        root = _gate_root(Path(td), pages)
        state = {"id": "snap-1", "source_material_count": 103}
        errors = _run_gate(root, state)
        assert any("missing entry page: CLAUDE.md" in e for e in errors)


def test_count_zero_marker_requires_label_not_coincidence():
    # snapshot marker itself must be the labelled form, not a bare id
    with tempfile.TemporaryDirectory() as td:
        pages = _fresh_pages()
        pages["README.md"] = _page_text(None, 103, None) + (
            "Mentions snap-1 in prose only.\n")
        root = _gate_root(Path(td), pages)
        state = {"id": "snap-1", "source_material_count": 103}
        errors = _run_gate(root, state)
        assert any("README.md" in e and "Current corpus snapshot:" in e
                   for e in errors), errors


def test_template_source_record_includes_filename_field():
    template = (ROOT / "00-system" / "templates"
                / "TEMPLATE_source-record.md").read_text(encoding="utf-8")
    assert "filename:" in template


def test_filled_template_source_record_has_no_filename_error():
    errors = collect("02-sources/records/ref-src-deadbeef0000.md", {
        "id": "ref-src-deadbeef0000",
        "type": "source-record",
        "title": "Example",
        "aliases": [],
        "family": "test",
        "version_role": "original",
        "current_priority": "normal",
        "authority_scope": "test",
        "format": "md",
        "status": "registered",
        "validation_status": "registered-not-fully-claim-validated",
        "visibility": "private",
        "sensitivity": "ordinary",
        "created": "2026-09-16",
        "updated": "2026-09-16",
        "sha256": "0" * 64,
        "original_path": "_originals/example.md",
        "extracted_text_path": "02-sources/text/example.md",
        "filename": "example.md",
        "schema_version": "1.0.0",
    })
    assert not any("filename" in error and "missing" in error.lower()
                   for error in errors)


def _safe(text):
    """ASCII-safe tail of captured output, for assertion messages.

    A failing assertion prints its message to the console. On Windows that
    console is cp1252, and captured validator output can carry U+FFFD (from
    errors="replace") or an em dash, which cp1252 cannot encode -- the runner
    then dies with UnicodeEncodeError instead of reporting which test failed.
    Observed 2026-09-18 while mutation-testing the A4 gate.
    """
    return (text or "")[-1200:].encode("ascii", "replace").decode("ascii")


def _copy_kit(base):
    """Copy tracked kit files (no .git) into base/kit for smoke tests."""
    import shutil, subprocess
    dst = base / "kit"
    dst.mkdir(parents=True, exist_ok=True)
    tracked = subprocess.run(
        ["git", "ls-files"], cwd=ROOT, capture_output=True, text=True,
        encoding="utf-8", errors="replace").stdout.splitlines()
    for rel in tracked:
        src = ROOT / rel
        if not src.is_file():
            continue
        target = dst / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, target)
    return dst


def _tree_hash(root):
    import hashlib
    h = hashlib.sha256()
    for p in sorted(root.rglob("*")):
        if p.is_file() and ".git" not in p.parts:
            h.update(str(p.relative_to(root)).encode())
            h.update(p.read_bytes())
    return h.hexdigest()


def _run_instantiate(cwd, *args):
    import subprocess
    return subprocess.run(
        [sys.executable, "scripts/instantiate.py", *args],
        cwd=cwd, capture_output=True, text=True, encoding="utf-8",
        errors="replace")


def test_instantiate_seeds_gate_clean_empty_instance():
    import subprocess
    with tempfile.TemporaryDirectory() as td:
        kit = _copy_kit(Path(td))
        r = _run_instantiate(kit, "--name", "Smoke Wiki", "--prefix", "swk")
        assert r.returncode == 0, r.stdout + r.stderr
        state = json.loads((kit / "00-system/registers/CORPUS_STATE.json")
                           .read_text(encoding="utf-8"))
        assert state["id"] == "swk-corpus-empty", state
        assert state["source_material_count"] == 0, state
        for name in ENTRY_PAGE_NAMES:
            text = (kit / name).read_text(encoding="utf-8")
            assert f"Current corpus snapshot: `swk-corpus-empty`" in text, name
            assert "Registered source artifacts: 0" in text, name
            assert "wiki-corpus-empty" not in text, name
        for script in ("scripts/validate_repo.py",):
            v = subprocess.run([sys.executable, script, "--full"], cwd=kit,
                               capture_output=True, text=True, encoding="utf-8",
                               errors="replace")
            assert v.returncode == 0, v.std_safe(out) + v.stderr[-800:]


def test_instantiate_is_idempotent_on_same_empty_instance():
    with tempfile.TemporaryDirectory() as td:
        kit = _copy_kit(Path(td))
        assert _run_instantiate(kit, "--name", "Smoke Wiki",
                                "--prefix", "swk").returncode == 0
        before = _tree_hash(kit)
        r = _run_instantiate(kit, "--name", "Smoke Wiki", "--prefix", "swk")
        assert r.returncode == 0, r.stdout + r.stderr
        assert _tree_hash(kit) == before, "rerun changed tracked content"


def test_instantiate_refuses_populated_state_before_writing():
    with tempfile.TemporaryDirectory() as td:
        kit = _copy_kit(Path(td))
        assert _run_instantiate(kit, "--name", "Smoke Wiki",
                                "--prefix", "swk").returncode == 0
        # simulate a registered corpus: one manifest row + nonzero count
        row = json.dumps({
            "id": "swk-src-aaaaaaaaaaaa", "filename": "a.md",
            "sha256": "0" * 64, "original_path": "_originals/a.md",
            "source_record_path": "02-sources/records/x.md",
            "extracted_text_path": "02-sources/text/x.md", "family": "t",
            "registered": "2026-09-16", "intake": "2026-09-16",
        }, ensure_ascii=False)
        idx = kit / "00-system/registers/MATERIALS_INDEX.jsonl"
        idx.write_text(row + "\n", encoding="utf-8")
        state_path = kit / "00-system/registers/CORPUS_STATE.json"
        state = json.loads(state_path.read_text(encoding="utf-8"))
        state["source_material_count"] = 1
        state_path.write_text(json.dumps(state, indent=2) + "\n",
                              encoding="utf-8")
        before = _tree_hash(kit)
        r = _run_instantiate(kit, "--name", "Smoke Wiki", "--prefix", "swk")
        assert r.returncode != 0, "populated instance must refuse"
        assert _tree_hash(kit) == before, "refusal must precede any write"


def test_instantiate_refuses_different_existing_instance():
    with tempfile.TemporaryDirectory() as td:
        kit = _copy_kit(Path(td))
        assert _run_instantiate(kit, "--name", "Smoke Wiki",
                                "--prefix", "swk").returncode == 0
        inst = kit / "00-system/registers/INSTANCE.json"
        data = json.loads(inst.read_text(encoding="utf-8"))
        data["id"] = "other-instance"
        inst.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        before = _tree_hash(kit)
        r = _run_instantiate(kit, "--name", "Smoke Wiki", "--prefix", "swk")
        assert r.returncode != 0
        assert _tree_hash(kit) == before


# ------------------------------------------- gate wiring (tasks 4.1/4.2)


def test_validate_calls_entry_gate_once_with_loaded_state():
    """The gate must run inside the normal validate() path, not only when
    a test calls the helper directly."""
    calls = []
    original = validate_repo.check_entry_pages

    def recorder(root, state, errors):
        calls.append((root, state, errors))
        return original(root, state, errors)

    validate_repo.check_entry_pages = recorder
    try:
        errors = validate_repo.validate(False)
    finally:
        validate_repo.check_entry_pages = original

    assert len(calls) == 1, f"check_entry_pages called {len(calls)} times"
    root, state, passed_errors = calls[0]
    assert root == validate_repo.ROOT
    live = json.loads(
        (ROOT / "00-system/registers/CORPUS_STATE.json").read_text(
            encoding="utf-8"))
    assert state.get("id") == live["id"], state
    assert state.get("source_material_count") == live["source_material_count"]
    # Strictly identity, never `or isinstance(..., list)`: the recorder's
    # third argument is always a list, so the isinstance form is
    # tautological and a wiring regression that routes errors into a
    # fresh throwaway list passes it (mutation-confirmed 2026-09-18).
    assert passed_errors is errors, "gate got a different errors list"


def test_stale_marker_makes_validate_repo_exit_nonzero():
    import subprocess
    with tempfile.TemporaryDirectory() as td:
        kit = _copy_kit(Path(td))
        state_path = kit / "00-system/registers/CORPUS_STATE.json"
        state = json.loads(state_path.read_text(encoding="utf-8"))
        state["id"] = "drifted-corpus-id"
        state_path.write_text(json.dumps(state, indent=2) + chr(10),
                              encoding="utf-8")
        r = subprocess.run(
            [sys.executable, "scripts/validate_repo.py", "--full"], cwd=kit,
            capture_output=True, text=True, encoding="utf-8",
            errors="replace")
        out = (r.stdout or "") + (r.stderr or "")
        assert r.returncode != 0, _safe(out)
        assert "stale entry page" in out, _safe(out)
        for name in ENTRY_PAGE_NAMES:
            assert name in out, f"{name} missing from gate output: {_safe(out)}"


def _parse_markdown_tier_names(text):
    """Extract the first-column values of the '## Holdings tier' table."""
    marker = "## Holdings tier"
    if marker not in text:
        return set()
    section = text.split(marker, 1)[1]
    next_heading = section.find("\n## ")
    if next_heading != -1:
        section = section[:next_heading]
    names = set()
    for line in section.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if not cells or not cells[0]:
            continue
        if cells[0].lower() == "value":
            continue
        if set(cells[0]) <= {"-"}:
            continue
        names.add(cells[0])
    return names


def test_holdings_policy_parses():
    policy = validate_repo.load_holdings_policy(ROOT)
    assert isinstance(policy, dict)
    assert isinstance(policy.get("tiers"), dict) and policy["tiers"]


def test_default_tier_for_unregistered_is_declared_tier():
    policy = validate_repo.load_holdings_policy(ROOT)
    assert policy["default_tier_for_unregistered"] in policy["tiers"], policy


def test_controlled_vocabulary_tier_set_matches_policy():
    policy = validate_repo.load_holdings_policy(ROOT)
    vocab_text = (ROOT / "00-system/policies/CONTROLLED_VOCABULARY.md").read_text(
        encoding="utf-8")
    vocab_tiers = _parse_markdown_tier_names(vocab_text)
    assert vocab_tiers == set(policy["tiers"]), (vocab_tiers, set(policy["tiers"]))


def test_load_holdings_policy_raises_on_unknown_tier():
    with tempfile.TemporaryDirectory() as td:
        fixture_root = Path(td)
        policies_dir = fixture_root / "00-system/policies"
        policies_dir.mkdir(parents=True)
        bad_policy = {
            "schema_version": "1.0.0",
            "tiers": {
                "registered": {
                    "description": "x",
                    "manifest_row": "required",
                    "counted_in": "source_material_count",
                },
            },
            "default_tier_for_unregistered": "not-a-declared-tier",
            "family_tier_overrides": {},
        }
        (policies_dir / "HOLDINGS_POLICY.json").write_text(
            json.dumps(bad_policy), encoding="utf-8")
        try:
            validate_repo.load_holdings_policy(fixture_root)
            assert False, "expected ValueError for unknown tier"
        except ValueError as exc:
            assert "not-a-declared-tier" in str(exc), str(exc)


def test_harness_worktree_is_ignored_by_the_validator():
    """A git worktree checked out inside the repo must not be walked.

    The harness creates .harness-worktrees/<session-id>/ for a delegated
    worker. Walking it makes every record appear twice, so validate() used
    to report ~50 duplicate-id errors that had nothing to do with the
    change under test (observed 2026-09-18 while landing rung A1).
    """
    import importlib.util as _ilu
    for script in ("validate_repo.py", "validate_content_release.py"):
        spec = _ilu.spec_from_file_location(
            f"_mod_{script}", ROOT / "scripts" / script)
        mod = _ilu.module_from_spec(spec)
        spec.loader.exec_module(mod)
        assert mod.is_ignored_rel(".harness-worktrees"), script
        assert mod.is_ignored_rel(".harness-worktrees/abc/HOME.md"), script
        assert not mod.is_ignored_rel("HOME.md"), script


# -------------------------------------------------- holdings census (A2)
# Fixture helpers for check_holdings_census. Every fixture root gets its own
# HOLDINGS_POLICY.json (mirroring the real 00-system/policies/HOLDINGS_POLICY.json
# tier set) so the helper's legal-tier names come from load_holdings_policy(root),
# never hardcoded here.


def _census_policy_dict():
    return {
        "schema_version": "1.0.0",
        "tiers": {
            "registered": {
                "description": "x", "manifest_row": "required",
                "counted_in": "source_material_count",
            },
            "pending-registration": {
                "description": "x", "manifest_row": "forbidden",
                "counted_in": "held_artifact_count",
            },
            "reference-shelf": {
                "description": "x", "manifest_row": "forbidden",
                "counted_in": "held_artifact_count",
            },
        },
        "default_tier_for_unregistered": "pending-registration",
        "family_tier_overrides": {},
    }


def _census_root(base):
    root = base / "repo"
    policies_dir = root / "00-system" / "policies"
    policies_dir.mkdir(parents=True, exist_ok=True)
    (policies_dir / "HOLDINGS_POLICY.json").write_text(
        json.dumps(_census_policy_dict()), encoding="utf-8")
    return root


def _write_original(root, rel, content=b"x"):
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


def _write_source_record(root, rel, *, status, original_path, holdings_tier=None,
                          family=None, body="Body.\n"):
    fm = {
        "id": rel.rsplit("/", 1)[-1].removesuffix(".md"),
        "type": "source-record",
        "title": "Example",
        "status": status,
        "original_path": original_path,
    }
    if holdings_tier is not None:
        fm["holdings_tier"] = holdings_tier
    if family is not None:
        fm["family"] = family
    text = "---\n" + yaml.safe_dump(fm, sort_keys=False) + "---\n\n" + body
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _write_manifest(root, rows):
    path = root / "00-system" / "registers" / "MATERIALS_INDEX.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(row) for row in rows]
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def _run_census(root, state):
    errors = []
    validate_repo.check_holdings_census(root, state, errors)
    return errors


def test_holdings_census_all_registered_and_consistent_passes():
    with tempfile.TemporaryDirectory() as td:
        root = _census_root(Path(td))
        _write_original(root, "_originals/a.pdf")
        _write_source_record(
            root, "02-sources/records/a.md",
            status="registered", original_path="_originals/a.pdf",
            holdings_tier="registered")
        _write_manifest(root, [
            {"source_record_path": "02-sources/records/a.md",
             "original_path": "_originals/a.pdf"},
        ])
        state = {
            "source_material_count": 1,
            "held_artifact_count": 1,
            "holdings_by_tier": {"registered": 1, "pending-registration": 0,
                                  "reference-shelf": 0},
        }
        assert _run_census(root, state) == []


def test_holdings_census_unregistered_original_without_record_fails():
    with tempfile.TemporaryDirectory() as td:
        root = _census_root(Path(td))
        _write_original(root, "_originals/stray.pdf")
        state = {"source_material_count": 0}
        errors = _run_census(root, state)
        assert any(
            "_originals/stray.pdf" in e and "undeclared" in e for e in errors
        ), errors


def test_holdings_census_record_claims_registered_without_manifest_row_fails():
    with tempfile.TemporaryDirectory() as td:
        root = _census_root(Path(td))
        _write_source_record(
            root, "02-sources/records/b.md",
            status="registered", original_path="_originals/b.pdf")
        state = {"source_material_count": 0}
        errors = _run_census(root, state)
        assert any(
            "02-sources/records/b.md" in e and "MATERIALS_INDEX.jsonl" in e
            for e in errors
        ), errors


def test_holdings_census_manifest_row_record_not_registered_fails():
    with tempfile.TemporaryDirectory() as td:
        root = _census_root(Path(td))
        _write_original(root, "_originals/c.pdf")
        _write_source_record(
            root, "02-sources/records/c.md",
            status="pending-registration", original_path="_originals/c.pdf",
            holdings_tier="pending-registration")
        _write_manifest(root, [
            {"source_record_path": "02-sources/records/c.md",
             "original_path": "_originals/c.pdf"},
        ])
        state = {"source_material_count": 1}
        errors = _run_census(root, state)
        assert any(
            "02-sources/records/c.md" in e and "pending-registration" in e
            for e in errors
        ), errors


def test_holdings_census_held_artifact_count_off_by_one_fails():
    with tempfile.TemporaryDirectory() as td:
        root = _census_root(Path(td))
        _write_original(root, "_originals/a.pdf")
        _write_original(root, "_originals/b.pdf")
        state = {
            "source_material_count": 0,
            "held_artifact_count": 1,
            "holdings_by_tier": {"registered": 0, "pending-registration": 1,
                                  "reference-shelf": 0},
        }
        errors = _run_census(root, state)
        assert any(
            "held_artifact_count" in e and "1" in e and "2" in e for e in errors
        ), errors


def test_holdings_census_holdings_by_tier_not_summing_fails():
    with tempfile.TemporaryDirectory() as td:
        root = _census_root(Path(td))
        _write_original(root, "_originals/a.pdf")
        _write_original(root, "_originals/b.pdf")
        state = {
            "source_material_count": 0,
            "held_artifact_count": 2,
            "holdings_by_tier": {"registered": 0, "pending-registration": 0,
                                  "reference-shelf": 0},
        }
        errors = _run_census(root, state)
        assert any("holdings_by_tier sums to" in e for e in errors), errors


def test_holdings_census_empty_originals_zero_counts_passes():
    with tempfile.TemporaryDirectory() as td:
        root = _census_root(Path(td))
        (root / "_originals").mkdir(parents=True, exist_ok=True)
        state = {
            "source_material_count": 0,
            "held_artifact_count": 0,
            "holdings_by_tier": {"registered": 0, "pending-registration": 0,
                                  "reference-shelf": 0},
        }
        assert _run_census(root, state) == []


def test_holdings_census_absent_held_artifact_count_skips_counts_only():
    with tempfile.TemporaryDirectory() as td:
        root = _census_root(Path(td))
        _write_source_record(
            root, "02-sources/records/a.md",
            status="registered", original_path="_originals/a.pdf")
        # No manifest row for a.md -> invariant 1 must still fire even though
        # held_artifact_count is absent. source_material_count is wildly
        # wrong relative to the (zero) manifest rows, which invariant 4 would
        # flag if it ran; held_artifact_count's absence must skip invariant 4
        # entirely, not just the held-count sub-check.
        state = {"source_material_count": 999}
        errors = _run_census(root, state)
        assert any("02-sources/records/a.md" in e for e in errors), errors
        assert not any("source_material_count" in e for e in errors), errors
        assert not any("held_artifact_count" in e for e in errors), errors


def test_every_holdings_census_error_names_path_and_register():
    """Acceptance (d): every error names a path and the disagreeing register."""
    with tempfile.TemporaryDirectory() as td:
        root = _census_root(Path(td))
        _write_original(root, "_originals/a.pdf")
        _write_original(root, "_originals/stray.pdf")
        _write_source_record(
            root, "02-sources/records/a.md",
            status="registered", original_path="_originals/a.pdf",
            holdings_tier="registered")
        _write_source_record(
            root, "02-sources/records/b.md",
            status="registered", original_path="_originals/b.pdf")
        _write_manifest(root, [])
        state = {
            "source_material_count": 3,
            "held_artifact_count": 5,
            "holdings_by_tier": {"registered": 0, "pending-registration": 0,
                                  "reference-shelf": 0},
        }
        errors = _run_census(root, state)
        assert len(errors) >= 4, errors
        for error in errors:
            path, sep, _ = error.partition(":")
            path = path.strip()
            assert sep, error
            assert (
                path.startswith("02-sources/records/")
                or path.startswith("_originals/")
                or path == "CORPUS_STATE.json"
            ), error
            register_named = (
                "MATERIALS_INDEX.jsonl" in error
                or "CORPUS_STATE.json" in error
                or "_originals/" in error
                or "HOLDINGS_POLICY.json" in error
            )
            assert register_named, error


# -------------------------------------------------- census gate wiring (A4)


def test_validate_calls_holdings_census_gate_exactly_once_with_loaded_state():
    """The census gate (A2's check_holdings_census) must run inside the
    normal validate() path -- task A4 -- not only when a test calls the
    helper directly. Mirrors test_validate_calls_entry_gate_once_with_loaded_state."""
    calls = []
    original = validate_repo.check_holdings_census

    def recorder(root, state, errors):
        calls.append((root, state, errors))
        return original(root, state, errors)

    validate_repo.check_holdings_census = recorder
    try:
        errors = validate_repo.validate(False)
    finally:
        validate_repo.check_holdings_census = original

    assert len(calls) == 1, f"check_holdings_census called {len(calls)} times"
    root, state, passed_errors = calls[0]
    assert root == validate_repo.ROOT
    live = json.loads(
        (ROOT / "00-system/registers/CORPUS_STATE.json").read_text(
            encoding="utf-8"))
    assert state.get("id") == live["id"], state
    assert state.get("source_material_count") == live["source_material_count"]
    # Strictly identity, never `or isinstance(..., list)`: the recorder's
    # third argument is always a list, so the isinstance form is
    # tautological and a wiring regression that routes errors into a
    # fresh throwaway list passes it (mutation-confirmed 2026-09-18).
    assert passed_errors is errors, "gate got a different errors list"


def test_undeclared_original_makes_validate_repo_exit_nonzero():
    """Subprocess smoke test (A4 acceptance a/b): planting a file under
    _originals/ that is neither a manifest original_path nor covered by a
    non-'registered' source record must fail `validate_repo.py --full`,
    naming that exact path. Planted only in a throwaway _copy_kit() copy --
    never in the real repository."""
    import subprocess
    with tempfile.TemporaryDirectory() as td:
        kit = _copy_kit(Path(td))
        undeclared_rel = "_originals/undeclared-test-artifact.txt"
        undeclared_path = kit / undeclared_rel
        undeclared_path.parent.mkdir(parents=True, exist_ok=True)
        undeclared_path.write_bytes(b"undeclared content")
        r = subprocess.run(
            [sys.executable, "scripts/validate_repo.py", "--full"], cwd=kit,
            capture_output=True, text=True, encoding="utf-8",
            errors="replace")
        out = (r.stdout or "") + (r.stderr or "")
        assert r.returncode != 0, _safe(out)
        assert undeclared_rel in out, _safe(out)
        assert "held under _originals/ but undeclared" in out, _safe(out)


# ---------------------------------------- census gate gap closure (A4 audit)
# A test-wiring audit of the A4 wiring (2026-09-18) found three branches of
# check_holdings_census reachable through validate() with no coverage, and
# proved two of them survive a mutation that silently removes their error
# reporting. These close them.


def test_holdings_census_reports_malformed_policy_instead_of_swallowing_it():
    """A broken HOLDINGS_POLICY.json must surface, not silently pass.

    Mutation probe: replacing the `except ValueError` body with a bare
    `return` left the suite at 39/39. That branch is reachable from
    validate() as of A4, so a malformed policy would have disabled the
    entire census gate without a single error line.
    """
    with tempfile.TemporaryDirectory() as td:
        root = _census_root(Path(td))
        (root / "00-system/policies/HOLDINGS_POLICY.json").write_text(
            '{"tiers": {"registered": {}}, '
            '"default_tier_for_unregistered": "nope"}', encoding="utf-8")
        errors = _run_census(root, {"source_material_count": 0})
        assert errors, "a malformed policy produced no error at all"
        assert any("HOLDINGS_POLICY.json" in e for e in errors), errors
        assert any("nope" in e for e in errors), errors


def test_holdings_census_reports_malformed_manifest_line():
    """A broken MATERIALS_INDEX.jsonl line must be named with its number."""
    with tempfile.TemporaryDirectory() as td:
        root = _census_root(Path(td))
        manifest = root / "00-system/registers/MATERIALS_INDEX.jsonl"
        manifest.parent.mkdir(parents=True, exist_ok=True)
        manifest.write_text('{"id": "a", "original_path": "_originals/a.pdf"}\n'
                            '{this is not json}\n', encoding="utf-8")
        errors = _run_census(root, {"source_material_count": 1})
        assert errors, "a malformed manifest line produced no error"
        assert any("MATERIALS_INDEX.jsonl" in e and "line 2" in e
                   for e in errors), errors


def test_biconditional_violation_surfaces_through_validate_repo_subprocess():
    """End-to-end proof for invariant 1, not just a direct helper call.

    Every other census invariant is tested by calling the helper directly.
    The auditor's finding: only the coverage branch had end-to-end proof that
    a violation actually reaches `validate_repo.py --full`. This pins the
    headline invariant -- `status: registered` iff the manifest names the
    record -- to the real command an operator runs.
    """
    import subprocess
    with tempfile.TemporaryDirectory() as td:
        kit = _copy_kit(Path(td))
        # A record that claims registration while the manifest stays empty:
        # exactly the mozare-wiki defect shape that motivated this change.
        record_rel = "02-sources/records/wiki-src-000000000000.md"
        _write_original(kit, "_originals/claimed.pdf")
        # Schema-complete on purpose: if the record were missing required
        # fields, validate_repo.py would exit nonzero for those instead and
        # the test would pass without proving anything about the census.
        (kit / record_rel).parent.mkdir(parents=True, exist_ok=True)
        (kit / record_rel).write_text(
            "---\n" + yaml.safe_dump({
                "id": "wiki-src-000000000000",
                "type": "source-record",
                "title": "Claimed but unregistered",
                "filename": "claimed.pdf",
                "format": "pdf",
                "sha256": "0" * 64,
                "original_path": "_originals/claimed.pdf",
                "authority_scope": "test",
                "validation_status": "test",
                "status": "registered",
            }, sort_keys=False) + "---\n\nBody.\n", encoding="utf-8")
        r = subprocess.run(
            [sys.executable, "scripts/validate_repo.py", "--full"], cwd=kit,
            capture_output=True, text=True, encoding="utf-8",
            errors="replace")
        out = (r.stdout or "") + (r.stderr or "")
        assert r.returncode != 0, _safe(out)
        assert record_rel in out, _safe(out)
        assert "status is 'registered' but no row in" in out, _safe(out)


# ------------------------------------------------ retier_holdings.py (A5)
# Fixture helpers mirror _census_root/_write_source_record/_write_manifest
# above, extended with a CORPUS_STATE.json (build_plan needs
# source_material_count) and an optional family_tier_overrides map.


def _retier_policy_dict(family_tier_overrides=None):
    policy = _census_policy_dict()
    if family_tier_overrides is not None:
        policy["family_tier_overrides"] = family_tier_overrides
    return policy


def _retier_root(base, *, source_material_count=0, family_tier_overrides=None):
    root = base / "repo"
    policies_dir = root / "00-system" / "policies"
    policies_dir.mkdir(parents=True, exist_ok=True)
    (policies_dir / "HOLDINGS_POLICY.json").write_text(
        json.dumps(_retier_policy_dict(family_tier_overrides)), encoding="utf-8")
    registers_dir = root / "00-system" / "registers"
    registers_dir.mkdir(parents=True, exist_ok=True)
    (registers_dir / "CORPUS_STATE.json").write_text(json.dumps({
        "id": "test-corpus",
        "source_material_count": source_material_count,
    }), encoding="utf-8")
    return root


def _run_retier(cwd, *args):
    import subprocess
    # -B: retier_holdings.py imports validate_repo, which would otherwise
    # write scripts/__pycache__/*.pyc into the fixture kit and make a
    # "writes nothing" tree-hash comparison fail on a cache artifact that
    # has nothing to do with the script's own behaviour.
    return subprocess.run(
        [sys.executable, "-B", "scripts/retier_holdings.py", *args],
        cwd=cwd, capture_output=True, text=True, encoding="utf-8",
        errors="replace")


def test_retier_plan_empty_repo_is_zero_records_to_retier():
    """Acceptance (a) at the unit level: nothing declared, nothing to do."""
    with tempfile.TemporaryDirectory() as td:
        root = _retier_root(Path(td), source_material_count=0)
        plan = retier_holdings.build_plan(root)
        assert plan["correctly_registered"] == 0, plan
        assert plan["to_retier"] == [], plan
        assert plan["held_artifact_count"] == 0, plan
        assert plan["holdings_by_tier"] == {
            "registered": 0, "pending-registration": 0, "reference-shelf": 0,
        }, plan


def test_retier_plan_flags_record_claiming_registered_without_manifest_row():
    """Acceptance (b) shape at the unit level: one held-but-unregistered
    original whose record wrongly claims `registered` is exactly one
    record to retier, resolved to the policy's default tier."""
    with tempfile.TemporaryDirectory() as td:
        root = _retier_root(Path(td), source_material_count=0)
        _write_original(root, "_originals/a.pdf")
        _write_source_record(
            root, "02-sources/records/a.md",
            status="registered", original_path="_originals/a.pdf")
        plan = retier_holdings.build_plan(root)
        assert plan["correctly_registered"] == 0, plan
        assert len(plan["to_retier"]) == 1, plan
        entry = plan["to_retier"][0]
        assert entry["rel"] == "02-sources/records/a.md", entry
        assert entry["new_tier"] == "pending-registration", entry
        assert plan["holdings_by_tier"]["pending-registration"] == 1, plan
        assert plan["held_artifact_count"] == 1, plan


def test_retier_never_touches_correctly_registered_record():
    """Negative: a record named as source_record_path in the manifest must
    never appear in to_retier, regardless of its other fields.

    Mutation probe: dropping the `continue` after `correctly_registered +=
    1` in build_plan() would fall through and evaluate this record for
    retiering too. This pins len(to_retier) == 0, not just a truthy count."""
    with tempfile.TemporaryDirectory() as td:
        root = _retier_root(Path(td), source_material_count=1)
        _write_original(root, "_originals/reg.pdf")
        _write_source_record(
            root, "02-sources/records/reg.md",
            status="registered", original_path="_originals/reg.pdf",
            holdings_tier="registered")
        _write_manifest(root, [
            {"source_record_path": "02-sources/records/reg.md",
             "original_path": "_originals/reg.pdf"},
        ])
        plan = retier_holdings.build_plan(root)
        assert plan["correctly_registered"] == 1, plan
        assert plan["to_retier"] == [], plan
        assert plan["holdings_by_tier"]["registered"] == 1, plan
        assert plan["held_artifact_count"] == 1, plan


def test_retier_family_tier_override_selects_declared_tier():
    """Tier selection is family_tier_overrides[family] when the family is
    present, not always default_tier_for_unregistered.

    Mutation probe: hardcoding `new_tier = default_tier` (ignoring
    `overrides`) would still pass a test that only checked "some tier was
    assigned"; asserting the *specific* override tier and that the default
    tier's bucket stays at 0 catches it."""
    with tempfile.TemporaryDirectory() as td:
        root = _retier_root(
            Path(td), source_material_count=0,
            family_tier_overrides={"backlog-scans": "reference-shelf"})
        _write_original(root, "_originals/b.pdf")
        _write_source_record(
            root, "02-sources/records/b.md",
            status="inbox", original_path="_originals/b.pdf",
            family="backlog-scans")
        plan = retier_holdings.build_plan(root)
        assert len(plan["to_retier"]) == 1, plan
        entry = plan["to_retier"][0]
        assert entry["new_tier"] == "reference-shelf", entry
        assert plan["per_family"] == {"backlog-scans": 1}, plan
        assert plan["holdings_by_tier"]["reference-shelf"] == 1, plan
        assert plan["holdings_by_tier"]["pending-registration"] == 0, plan


def test_retier_skips_record_already_correctly_tiered():
    """A non-registered record whose status/holdings_tier already equal the
    resolved tier needs no change and must not appear in to_retier.

    Mutation probe: removing the "already correctly tiered" early-continue
    would count and (under --apply) rewrite a record with no actual change
    -- a spurious diff on every rerun. This pins to_retier == []."""
    with tempfile.TemporaryDirectory() as td:
        root = _retier_root(Path(td), source_material_count=0)
        _write_original(root, "_originals/c.pdf")
        _write_source_record(
            root, "02-sources/records/c.md",
            status="pending-registration", original_path="_originals/c.pdf",
            holdings_tier="pending-registration")
        plan = retier_holdings.build_plan(root)
        assert plan["to_retier"] == [], plan
        assert plan["holdings_by_tier"]["pending-registration"] == 1, plan
        assert plan["held_artifact_count"] == 1, plan


def test_retier_refuses_manifest_state_count_mismatch():
    """Refusal condition 1/4 (tasks.md A5): manifest rows and
    source_material_count disagree."""
    with tempfile.TemporaryDirectory() as td:
        root = _retier_root(Path(td), source_material_count=5)
        try:
            retier_holdings.build_plan(root)
            assert False, "expected RetierRefusal for count mismatch"
        except retier_holdings.RetierRefusal as exc:
            assert "5" in str(exc) and "0" in str(exc), str(exc)


def test_retier_refuses_missing_holdings_policy():
    """Refusal condition 2/4: HOLDINGS_POLICY.json missing."""
    with tempfile.TemporaryDirectory() as td:
        root = Path(td) / "repo"
        registers_dir = root / "00-system" / "registers"
        registers_dir.mkdir(parents=True, exist_ok=True)
        (registers_dir / "CORPUS_STATE.json").write_text(
            json.dumps({"id": "x", "source_material_count": 0}),
            encoding="utf-8")
        try:
            retier_holdings.build_plan(root)
            assert False, "expected RetierRefusal for missing policy"
        except retier_holdings.RetierRefusal as exc:
            assert "HOLDINGS_POLICY.json" in str(exc), str(exc)


def test_retier_refuses_family_override_matching_no_record():
    """Refusal condition 4/4: a family_tier_overrides key names a family no
    record carries."""
    with tempfile.TemporaryDirectory() as td:
        root = _retier_root(
            Path(td), source_material_count=0,
            family_tier_overrides={"ghost-family": "reference-shelf"})
        _write_original(root, "_originals/e.pdf")
        _write_source_record(
            root, "02-sources/records/e.md",
            status="inbox", original_path="_originals/e.pdf",
            family="real-family")
        try:
            retier_holdings.build_plan(root)
            assert False, "expected RetierRefusal for unmatched family"
        except retier_holdings.RetierRefusal as exc:
            assert "ghost-family" in str(exc), str(exc)


def test_retier_rewrite_record_preserves_body_and_other_fields():
    """_rewrite_record only ever changes status and holdings_tier.

    Mutation probe: a rewrite that re-serializes the body (e.g. drops it,
    or normalizes its whitespace) would corrupt archived prose. This
    compares the body byte-for-byte and every untouched frontmatter key."""
    with tempfile.TemporaryDirectory() as td:
        root = _retier_root(Path(td), source_material_count=0)
        body = "# Title\n\nSome body text with *emphasis* and a  double space.\n"
        _write_source_record(
            root, "02-sources/records/f.md",
            status="registered", original_path="_originals/f.pdf",
            family="x", body=body)
        path = root / "02-sources/records/f.md"
        before_fm = validate_repo.parse_frontmatter(path)
        retier_holdings._rewrite_record(
            path, "pending-registration", "pending-registration")
        text = path.read_text(encoding="utf-8")
        assert text.endswith(body), repr(text[-80:])
        after_fm = validate_repo.parse_frontmatter(path)
        assert after_fm["status"] == "pending-registration", after_fm
        assert after_fm["holdings_tier"] == "pending-registration", after_fm
        for key in ("id", "title", "original_path", "family"):
            assert after_fm[key] == before_fm[key], (key, before_fm, after_fm)


def test_retier_dry_run_empty_kit_prints_zero_and_writes_nothing():
    """Acceptance (a), CLI-level: a fresh copy of the tracked empty kit."""
    with tempfile.TemporaryDirectory() as td:
        kit = _copy_kit(Path(td))
        before = _tree_hash(kit)
        r = _run_retier(kit)
        out = (r.stdout or "") + (r.stderr or "")
        assert r.returncode == 0, _safe(out)
        assert "0 records to retier" in out, _safe(out)
        assert _tree_hash(kit) == before, "dry run must write nothing"


def test_retier_dry_run_then_apply_flips_unregistered_record_and_validates():
    """Acceptance (b): dry run reports exactly 1, changes nothing; --apply
    flips status/holdings_tier to pending-registration; validate_repo.py
    --full then PASSes."""
    import subprocess
    with tempfile.TemporaryDirectory() as td:
        kit = _copy_kit(Path(td))
        record_rel = "02-sources/records/wiki-src-000000000001.md"
        _write_original(kit, "_originals/claimed.pdf")
        (kit / record_rel).parent.mkdir(parents=True, exist_ok=True)
        (kit / record_rel).write_text(
            "---\n" + yaml.safe_dump({
                "id": "wiki-src-000000000001",
                "type": "source-record",
                "title": "Claimed but unregistered",
                "filename": "claimed.pdf",
                "format": "pdf",
                "sha256": "0" * 64,
                "original_path": "_originals/claimed.pdf",
                "authority_scope": "test",
                "validation_status": "test",
                "status": "registered",
            }, sort_keys=False) + "---\n\nBody.\n", encoding="utf-8")

        before = _tree_hash(kit)
        r = _run_retier(kit)
        out = (r.stdout or "") + (r.stderr or "")
        assert r.returncode == 0, _safe(out)
        assert "1 records to retier" in out, _safe(out)
        assert _tree_hash(kit) == before, "dry run must write nothing"

        r2 = _run_retier(kit, "--apply")
        out2 = (r2.stdout or "") + (r2.stderr or "")
        assert r2.returncode == 0, _safe(out2)

        fm = validate_repo.parse_frontmatter(kit / record_rel)
        assert fm["status"] == "pending-registration", fm
        assert fm["holdings_tier"] == "pending-registration", fm

        v = subprocess.run(
            [sys.executable, "scripts/validate_repo.py", "--full"], cwd=kit,
            capture_output=True, text=True, encoding="utf-8",
            errors="replace")
        vout = (v.stdout or "") + (v.stderr or "")
        assert v.returncode == 0, _safe(vout)
        assert "PASS" in vout, _safe(vout)


def test_retier_apply_refuses_on_dirty_working_tree():
    """Acceptance (c): --apply on a dirty tree exits nonzero, names
    'dirty', and writes nothing."""
    import subprocess
    with tempfile.TemporaryDirectory() as td:
        kit = _copy_kit(Path(td))
        subprocess.run(["git", "init", "-q"], cwd=kit, check=True)
        subprocess.run(["git", "config", "user.email", "test@example.invalid"],
                       cwd=kit, check=True)
        subprocess.run(["git", "config", "user.name", "test"],
                       cwd=kit, check=True)
        subprocess.run(["git", "add", "-A"], cwd=kit, check=True)
        subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=kit, check=True)

        # Make the tree dirty: an uncommitted change to a tracked file.
        state_path = kit / "00-system/registers/CORPUS_STATE.json"
        state_path.write_text(
            state_path.read_text(encoding="utf-8") + "\n", encoding="utf-8")

        before = _tree_hash(kit)
        r = _run_retier(kit, "--apply")
        out = (r.stdout or "") + (r.stderr or "")
        assert r.returncode != 0, _safe(out)
        assert "dirty" in out.lower(), _safe(out)
        assert _tree_hash(kit) == before, "refused --apply must write nothing"


def test_retier_refuses_manifest_state_mismatch_before_any_write():
    """Acceptance (d): manifest/state disagreement exits nonzero before any
    write, proven with a tree hash equal to the pre-run hash."""
    with tempfile.TemporaryDirectory() as td:
        kit = _copy_kit(Path(td))
        state_path = kit / "00-system/registers/CORPUS_STATE.json"
        state = json.loads(state_path.read_text(encoding="utf-8"))
        state["source_material_count"] = 3  # manifest still has 0 rows
        state_path.write_text(json.dumps(state, indent=2) + "\n",
                              encoding="utf-8")

        before = _tree_hash(kit)
        r = _run_retier(kit, "--apply")
        out = (r.stdout or "") + (r.stderr or "")
        assert r.returncode != 0, _safe(out)
        assert _tree_hash(kit) == before, "refusal must precede any write"


def test_retier_never_declares_original_or_materials_index_touched():
    """Negative (tasks.md A5): the script must never edit _originals/ or
    MATERIALS_INDEX.jsonl content, even under --apply. Proven by hashing
    both before and after an --apply run that does retier a record."""
    with tempfile.TemporaryDirectory() as td:
        kit = _copy_kit(Path(td))
        original_rel = "_originals/g.pdf"
        _write_original(kit, original_rel, content=b"original bytes")
        record_rel = "02-sources/records/g.md"
        (kit / record_rel).parent.mkdir(parents=True, exist_ok=True)
        (kit / record_rel).write_text(
            "---\n" + yaml.safe_dump({
                "id": "g", "type": "source-record", "title": "G",
                "filename": "g.pdf", "format": "pdf", "sha256": "0" * 64,
                "original_path": original_rel, "authority_scope": "test",
                "validation_status": "test", "status": "registered",
            }, sort_keys=False) + "---\n\nBody.\n", encoding="utf-8")
        manifest_path = kit / "00-system/registers/MATERIALS_INDEX.jsonl"
        manifest_before = (manifest_path.read_text(encoding="utf-8")
                           if manifest_path.exists() else "")
        original_before = (kit / original_rel).read_bytes()

        r = _run_retier(kit, "--apply")
        assert r.returncode == 0, _safe((r.stdout or "") + (r.stderr or ""))

        assert (kit / original_rel).read_bytes() == original_before
        manifest_after = (manifest_path.read_text(encoding="utf-8")
                          if manifest_path.exists() else "")
        assert manifest_after == manifest_before


if __name__ == "__main__":
    tests = [
        fn for name, fn in sorted(globals().items())
        if name.startswith("test_") and inspect.isfunction(fn)
    ]
    if not tests:
        print("FAIL: no test functions discovered")
        sys.exit(2)
    failures = 0
    for fn in tests:
        try:
            fn()
            print(f"PASS {fn.__name__}")
        except AssertionError as exc:
            failures += 1
            print(f"FAIL {fn.__name__}: {exc}")
        except Exception as exc:  # noqa: BLE001 - report, keep running
            failures += 1
            print(f"ERROR {fn.__name__}: {type(exc).__name__}: {exc}")
    print(f"\n{len(tests) - failures}/{len(tests)} passed")
    sys.exit(1 if failures else 0)
