#!/usr/bin/env python3
"""Keep every QMD operation inside this wiki's own collections.

QMD keeps ONE index per machine (~/.cache/qmd/index.sqlite) shared by every
wiki and project on it. Its bare commands act on all of them:

  - `qmd update` re-indexes every collection on the machine;
  - `qmd embed -f` deletes every vector on the machine before re-embedding;
  - `qmd query` / `qmd search` without `-c` rank hits from other wikis.

A kit instance must never reach outside itself. This module derives the
instance's collection names from its own
`00-system/configuration/qmd-collections-v1.1.0.json` and only ever passes
those names to QMD. Before any destructive step it checks that a collection
of that name either does not exist or is registered on a path inside this
repository, so a name shared with another wiki is refused, not overwritten.

CLI (used by the PowerShell scripts):
  python scripts/qmd_scope.py names [--default|--all|--role source-records|derivatives]
  python scripts/qmd_scope.py check-owned       # exit 3 if a name belongs elsewhere
  python scripts/qmd_scope.py update            # re-index own collections only
  python scripts/qmd_scope.py embed [--force]   # embed own collections only
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QMD_CONFIG = "00-system/configuration/qmd-collections-v1.1.0.json"
ROLE_PATHS = {"source-records": "02-sources/records", "derivatives": "02-sources/text"}
UPDATE_SCRIPT = Path(__file__).with_name("qmd_scoped_update.mjs")


def load_collections(root: Path = ROOT) -> list[dict]:
    """Collection specs from the instance config; [] when there is none."""
    try:
        cfg = json.loads((root / QMD_CONFIG).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    return [c for c in cfg.get("collections", []) if c.get("name") and c.get("path")]


def names(root: Path = ROOT, which: str = "all") -> list[str]:
    cols = load_collections(root)
    if which == "default":
        return [c["name"] for c in cols if c.get("include_by_default")]
    if which in ROLE_PATHS:
        want = ROLE_PATHS[which]
        return [c["name"] for c in cols if c["path"].strip("/") == want]
    return [c["name"] for c in cols]


def scope_args(collection_names: list[str]) -> list[str]:
    """`-c name` for every name. Empty input yields no flags, so callers must
    decide what an instance without a QMD config means (usually: skip QMD)."""
    out: list[str] = []
    for n in collection_names:
        out += ["-c", n]
    return out


def _qmd() -> str | None:
    return shutil.which("qmd")


def _run(cmd: list[str], timeout: int | None = None) -> subprocess.CompletedProcess:
    env = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
    return subprocess.run(cmd, cwd=ROOT, text=True, encoding="utf-8", errors="replace",
                          capture_output=True, timeout=timeout, env=env)


def registered_path(name: str) -> str | None:
    """Path QMD has on record for collection `name`, or None if absent."""
    qmd = _qmd()
    if not qmd:
        return None
    r = _run([qmd, "collection", "show", name], timeout=60)
    if r.returncode != 0:
        return None
    m = re.search(r"^\s*Path:\s*(.+?)\s*$", r.stdout, re.MULTILINE)
    return m.group(1) if m else None


def _inside(path: str, root: Path) -> bool:
    try:
        Path(path).resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def foreign_collections(root: Path = ROOT, lookup=registered_path) -> list[tuple[str, str]]:
    """(name, path) for configured names that QMD has registered OUTSIDE root."""
    out = []
    for n in names(root):
        p = lookup(n)
        if p is not None and not _inside(p, root):
            out.append((n, p))
    return out


def update(root: Path = ROOT) -> int:
    own = names(root)
    if not own:
        print("qmd_scope: no QMD config in this instance; nothing to update")
        return 0
    node = shutil.which("node")
    if not node:
        print("qmd_scope: node not found; cannot run a scoped update", file=sys.stderr)
        return 2
    r = _run([node, str(UPDATE_SCRIPT), *own])
    sys.stdout.write(r.stdout)
    sys.stderr.write(r.stderr)
    return r.returncode


def embed(root: Path = ROOT, force: bool = False) -> int:
    qmd = _qmd()
    own = names(root)
    if not own or not qmd:
        print("qmd_scope: no QMD config or qmd not installed; nothing to embed")
        return 0
    rc = 0
    for n in own:
        cmd = [qmd, "embed", "-c", n] + (["-f"] if force else [])
        print(f"qmd_scope: {' '.join(cmd[1:])}", flush=True)
        r = _run(cmd)
        tail = [ln for ln in r.stdout.replace("\r", "\n").splitlines() if ln.strip()][-1:]
        print("  " + (tail[0] if tail else f"exit {r.returncode}"), flush=True)
        rc = rc or r.returncode
    return rc


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("names")
    g = p.add_mutually_exclusive_group()
    g.add_argument("--default", action="store_const", const="default", dest="which")
    g.add_argument("--all", action="store_const", const="all", dest="which")
    g.add_argument("--role", choices=sorted(ROLE_PATHS), dest="role")
    sub.add_parser("check-owned")
    sub.add_parser("update")
    p = sub.add_parser("embed")
    p.add_argument("--force", action="store_true")
    a = ap.parse_args(argv)

    if a.cmd == "names":
        print("\n".join(names(ROOT, a.role or a.which or "all")))
        return 0
    if a.cmd == "check-owned":
        foreign = foreign_collections(ROOT)
        for n, p in foreign:
            print(f"REFUSED: QMD collection '{n}' is registered on {p}, outside "
                  f"{ROOT}. Rename this instance's collections in {QMD_CONFIG}.",
                  file=sys.stderr)
        return 3 if foreign else 0
    if a.cmd == "update":
        return update(ROOT)
    return embed(ROOT, force=a.force)


if __name__ == "__main__":
    raise SystemExit(main())
