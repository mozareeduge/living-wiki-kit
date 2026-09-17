import importlib.util
import inspect
import json
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts" / "validate_repo.py"


spec = importlib.util.spec_from_file_location("validate_repo", VALIDATOR)
validate_repo = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(validate_repo)


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
            assert v.returncode == 0, v.stdout[-1500:] + v.stderr[-800:]


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
    assert passed_errors is errors or isinstance(passed_errors, list)


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
        assert r.returncode != 0, out[-1500:]
        assert "stale entry page" in out, out[-1500:]
        for name in ENTRY_PAGE_NAMES:
            assert name in out, f"{name} missing from gate output: {out[-800:]}"


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
