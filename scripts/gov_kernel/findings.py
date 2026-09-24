from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class Finding:
    check_id: str
    severity: str
    message: str
    path: str | None = None
    record_id: str | None = None
    waivable: bool = False
    details: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def has_errors(findings: list[Finding]) -> bool:
    return any(f.severity == "error" for f in findings)
