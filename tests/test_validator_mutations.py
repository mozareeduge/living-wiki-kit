import importlib.util
import inspect
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
