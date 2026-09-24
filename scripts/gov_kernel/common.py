from __future__ import annotations

import hashlib
import json
import os
import pathlib
import subprocess
from typing import Any, Iterable


def repo_path(root: pathlib.Path, relative: str) -> pathlib.Path:
    p = (root / relative).resolve()
    root_resolved = root.resolve()
    try:
        p.relative_to(root_resolved)
    except ValueError as exc:
        raise ValueError(f"path escapes repository root: {relative}") from exc
    return p


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def stable_json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def write_if_changed(path: pathlib.Path, data: bytes) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_bytes() == data:
        return False
    path.write_bytes(data)
    return True


def atomic_write(path: pathlib.Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_bytes(data)
    os.replace(tmp, path)


def jsonl_bytes(rows: Iterable[dict[str, Any]]) -> bytes:
    return b"".join(stable_json_bytes(row) for row in rows)


def git(root: pathlib.Path, *args: str, check: bool = True) -> str:
    cp = subprocess.run(["git", *args], cwd=root, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if check and cp.returncode != 0:
        raise RuntimeError(cp.stderr.strip() or f"git {' '.join(args)} failed: {cp.returncode}")
    return cp.stdout.strip()
