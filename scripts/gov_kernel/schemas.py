from __future__ import annotations

import json
import pathlib
from typing import Any

from .findings import Finding

try:
    import jsonschema
except ImportError as exc:  # pragma: no cover
    raise RuntimeError("jsonschema is required for governance boundary validation") from exc

TYPE_TO_SCHEMA = {
    "source-record": "source-record.schema.json",
    "relation": "relation-object.schema.json",
    "relation-object": "relation-object.schema.json",
    "claim": "claim-object.schema.json",
    "claim-object": "claim-object.schema.json",
    "capture": "capture.schema.json",
    "proposal": "proposal.schema.json",
    "adjudication": "adjudication.schema.json",
    "accepted-evidence-row": "accepted-evidence-row.schema.json",
    "system-state": "system-state.schema.json",
    "release-profile": "release-profile.schema.json",
    "release-manifest": "release-manifest.schema.json",
}


def load_schema(schema_dir: pathlib.Path, name: str) -> dict[str, Any]:
    return json.loads((schema_dir / name).read_text(encoding="utf-8"))


def validate_record(record: dict[str, Any], schema_dir: pathlib.Path, *, path: str | None = None, explicit_schema: str | None = None) -> list[Finding]:
    rtype = record.get("type")
    schema_name = explicit_schema or TYPE_TO_SCHEMA.get(str(rtype))
    if not schema_name:
        return []  # exploratory records intentionally retain lighter contracts
    schema = load_schema(schema_dir, schema_name)
    validator = jsonschema.Draft202012Validator(schema)
    findings: list[Finding] = []
    for err in sorted(validator.iter_errors(record), key=lambda e: list(e.absolute_path)):
        loc = "/".join(str(x) for x in err.absolute_path)
        findings.append(Finding(
            check_id="SCHEMA.INVALID_BOUNDARY_RECORD",
            severity="error",
            path=path,
            record_id=str(record.get("id")) if record.get("id") is not None else None,
            message=f"{schema_name}{' at '+loc if loc else ''}: {err.message}",
            waivable=False,
        ))
    return findings
