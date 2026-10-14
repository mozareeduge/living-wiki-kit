"""D-d: choose practice profiles when creating a wiki.

`instantiate.py --profile <id>` (repeatable) writes the ids, in order, to
`active_profiles` in INSTANCE.json. An unknown or retired id is refused
before anything is written. A rerun without --profile keeps the choice.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _kit(tmp: Path) -> Path:
    dst = tmp / "kit"
    for rel in subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True,
                              text=True, check=True).stdout.splitlines():
        if (ROOT / rel).is_file():
            (dst / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / rel, dst / rel)
    return dst


def _run(kit: Path, *extra: str, script: str = "scripts/instantiate.py"):
    args = [sys.executable, script]
    if script.endswith("instantiate.py"):
        args += ["--name", "Prof Wiki", "--prefix", "pfw"]
    return subprocess.run([*args, *extra], cwd=kit, capture_output=True, text=True)


def _active(kit: Path) -> list[str]:
    return json.loads((kit / "00-system/registers/INSTANCE.json").read_text())["active_profiles"]


def _digest(root: Path) -> str:
    h = hashlib.sha256()
    for p in sorted(root.rglob("*")):
        if p.is_file() and "__pycache__" not in p.parts:
            h.update(p.relative_to(root).as_posix().encode()); h.update(p.read_bytes())
    return h.hexdigest()


def test_profiles_chosen_at_setup_are_active_and_check_clean(tmp_path: Path) -> None:
    kit = _kit(tmp_path)
    r = _run(kit, "--profile", "practice-research", "--profile", "practice-creative")
    assert r.returncode == 0, r.stdout + r.stderr
    assert _active(kit) == ["practice-research", "practice-creative"]
    c = _run(kit, "check", script="scripts/wiki_profiles.py")
    assert c.returncode == 0 and "2 active" in c.stdout, c.stdout + c.stderr
    # a rerun without --profile keeps the choice and changes nothing
    before = _digest(kit)
    assert _run(kit).returncode == 0
    assert _active(kit) == ["practice-research", "practice-creative"]
    assert _digest(kit) == before


def test_no_profile_stays_profile_neutral(tmp_path: Path) -> None:
    kit = _kit(tmp_path)
    assert _run(kit).returncode == 0
    assert _active(kit) == []


def test_unknown_profile_refused_before_writing(tmp_path: Path) -> None:
    kit = _kit(tmp_path)
    before = _digest(kit)
    r = _run(kit, "--profile", "practice-nope")
    assert r.returncode == 2
    assert "unknown profile 'practice-nope'" in r.stderr
    assert "practice-research" in r.stderr  # names what exists
    assert _digest(kit) == before
