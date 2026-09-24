from __future__ import annotations

import pathlib
from typing import Any

try:
    import yaml
except ImportError as exc:  # pragma: no cover
    raise RuntimeError("PyYAML is required for Markdown frontmatter parsing") from exc


def load_markdown_frontmatter(path: pathlib.Path) -> tuple[dict[str, Any], str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n") and not text.startswith("---\r\n"):
        return {}, text
    lines = text.splitlines(keepends=True)
    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end is None:
        raise ValueError(f"unterminated frontmatter: {path}")
    raw = "".join(lines[1:end])
    data = yaml.safe_load(raw) or {}
    if not isinstance(data, dict):
        raise ValueError(f"frontmatter must be mapping: {path}")
    body = "".join(lines[end + 1 :])
    return data, body
