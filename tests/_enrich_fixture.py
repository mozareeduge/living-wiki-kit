"""Shared fixture helpers for E1/E2 tests (tmp instance with a chunk index)."""
from __future__ import annotations

import hashlib
import shutil
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VER = "c" * 64
VER2 = "d" * 64
T1 = "Alpha Project began in the spring of the archive year."
T2 = "The committee later contradicted the first account entirely."


def chunk_ref(source: str, i: int) -> str:
    return "chk:" + hashlib.sha256(f"{source}:{i}".encode()).hexdigest()[:32]


def make_instance(tmp: Path, sources: dict[str, list[str]] | None = None, version: str = VER) -> Path:
    shutil.copytree(ROOT / "00-system" / "schemas", tmp / "00-system" / "schemas")
    sources = sources if sources is not None else {"src-a": [T1, T2]}
    db = tmp / "_search" / "retrieval.sqlite"
    db.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(db)
    c.execute("CREATE TABLE sources(source_ref TEXT PRIMARY KEY, source_version TEXT, path TEXT, "
              "tier TEXT, authority_level INTEGER, language_hint TEXT, indexed_at TEXT)")
    c.execute("CREATE TABLE chunks(chunk_ref TEXT PRIMARY KEY, source_ref TEXT, source_version TEXT, "
              "start INTEGER, end INTEGER, heading_path TEXT, text TEXT, text_sha256 TEXT)")
    for ref, texts in sources.items():
        c.execute("INSERT INTO sources VALUES(?,?,?,?,?,?,NULL)", (ref, version, f"{ref}.md", "derivative", 6, "en"))
        pos = 0
        for i, t in enumerate(texts):
            c.execute("INSERT INTO chunks VALUES(?,?,?,?,?,'[]',?,'h')",
                      (chunk_ref(ref, i), ref, version, pos, pos + len(t), t))
            pos += len(t) + 2
    c.commit()
    c.close()
    return tmp
