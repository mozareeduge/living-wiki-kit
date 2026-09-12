import importlib.util
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
