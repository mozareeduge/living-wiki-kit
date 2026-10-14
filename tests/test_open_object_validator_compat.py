"""The authoritative baseline gate must accept the kit's shipped kindless template."""
import importlib.util
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('open_object_validator', ROOT / 'scripts/validate_repo.py')
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)

@pytest.mark.parametrize('path', ['03-objects/first.md', '03-objects/people/first.md', '03-objects/works/first.md'])
def test_shipped_kindless_object_passes_baseline_schema_check(path):
    errors = []
    validator.validate_live_record_schema(path, {'id': 'ab-obj-first', 'type': 'object', 'title': 'A first record',
        'status': 'active-record', 'labels': []}, errors)
    assert errors == []
