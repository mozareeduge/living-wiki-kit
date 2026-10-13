#!/usr/bin/env python3
"""Fresh-wiki release check (Q6): a brand-new wiki made from this kit passes
every gate.

Copies the kit's tracked files into a temporary directory, instantiates a
wiki there (`instantiate.py --name "CI Wiki" --prefix ciw`), then runs, in
the new wiki: both validators, the four kernel gates, the census report
(must print `CENSUS CLEAN`), and a second `instantiate.py` run that must
leave the tree byte-identical. Stops at the first failing step and names it.

Never writes inside this repository; the temporary wiki is deleted unless
`--keep` is given.

Usage:
  python scripts/release_smoke.py [--keep] [--name "CI Wiki"] [--prefix ciw]
"""
from __future__ import annotations

import argparse
import hashlib
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]


def copy_tracked(src: Path, dst: Path) -> None:
    """Tracked files only, as a fresh clone would have them (no caches,
    no local indexes, no untracked notes)."""
    listed = subprocess.run(["git", "ls-files", "-z"], cwd=src, capture_output=True,
                            check=True).stdout.decode("utf-8").split("\0")
    for rel in filter(None, listed):
        f = src / rel
        if f.is_file():
            (dst / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, dst / rel)


def tree_digest(root: Path) -> str:
    h = hashlib.sha256()
    for p in sorted(root.rglob("*")):
        if p.is_file() and "_search" not in p.parts and "__pycache__" not in p.parts:
            h.update(p.relative_to(root).as_posix().encode())
            h.update(p.read_bytes())
    return h.hexdigest()


def steps(name: str, prefix: str) -> list[tuple[str, list[str], str | None]]:
    """(label, argv, text the output must contain)."""
    py = sys.executable
    inst = [py, "scripts/instantiate.py", "--name", name, "--prefix", prefix]
    return [
        ("instantiate", inst, None),
        ("validate_repo --full", [py, "scripts/validate_repo.py", "--full"], "PASS"),
        ("validate_content_release", [py, "scripts/validate_content_release.py"], "PASS"),
        ("wiki_validate", [py, "scripts/wiki_validate.py", "--repo", ".", "--format", "json"], None),
        ("wiki_state check", [py, "scripts/wiki_state.py", "--repo", ".", "check"], None),
        ("wiki_evidence check", [py, "scripts/wiki_evidence.py", "--repo", ".", "check"], None),
        ("wiki_profiles check", [py, "scripts/wiki_profiles.py", "check"], None),
        ("report_holdings", [py, "scripts/report_holdings.py"], "CENSUS CLEAN"),
    ]


def run(kit: Path, work: Path, name: str = "CI Wiki", prefix: str = "ciw",
        after_instantiate: Callable[[Path], None] | None = None,
        echo: Callable[[str], None] = print) -> tuple[bool, list[str]]:
    """Run the release check in `work`. Returns (ok, step log)."""
    wiki = work / "wiki"
    copy_tracked(kit, wiki)
    log: list[str] = []
    for label, argv, must in steps(name, prefix):
        r = subprocess.run(argv, cwd=wiki, capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        out = r.stdout + r.stderr
        ok = r.returncode == 0 and (must is None or must in out)
        line = f"{'PASS' if ok else 'FAIL'}  {label}  (exit {r.returncode})"
        log.append(line)
        echo(line)
        if not ok:
            echo(out[-2000:])
            return False, log
        if label == "instantiate" and after_instantiate:
            after_instantiate(wiki)
    digest = tree_digest(wiki)
    r = subprocess.run(steps(name, prefix)[0][1], cwd=wiki, capture_output=True,
                       text=True, encoding="utf-8", errors="replace")
    same = r.returncode == 0 and tree_digest(wiki) == digest
    line = f"{'PASS' if same else 'FAIL'}  instantiate rerun byte-identical"
    log.append(line)
    echo(line)
    if not same:
        echo((r.stdout + r.stderr)[-2000:])
    return same, log


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--name", default="CI Wiki")
    ap.add_argument("--prefix", default="ciw")
    ap.add_argument("--keep", action="store_true", help="keep the temporary wiki")
    args = ap.parse_args(argv)
    work = Path(tempfile.mkdtemp(prefix="lwk-release-smoke-"))
    try:
        ok, _ = run(ROOT, work, args.name, args.prefix)
    finally:
        if args.keep:
            print(f"kept: {work / 'wiki'}")
        else:
            shutil.rmtree(work, ignore_errors=True)
    print("RELEASE SMOKE PASS" if ok else "RELEASE SMOKE FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
