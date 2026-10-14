"""Q2 + Q3: setup instructions a new user can follow as written.

Q2 (F12): no shipped doc or script tells a user to stage everything with
`git add -A`; the bootstrap commit reviews `git status` first.
Q3 (F13 + F23): the Windows setup script works on a fresh clone. Its root
check names only paths a clone actually has (git keeps no empty
`_originals/`), and every repository file it points to exists.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HISTORY = ("07-genesis/", "_audits/", "openspec/changes/archive/", ".maws/",
           "Plans.md", "CHANGELOG.md")
SETUP = ROOT / "scripts" / "setup-after-clone.ps1"


def _tracked() -> list[str]:
    return subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True,
                          text=True, check=True).stdout.splitlines()


def test_no_instruction_to_stage_everything() -> None:
    hits = []
    for rel in _tracked():
        if rel.startswith(HISTORY) or not rel.endswith((".md", ".py", ".ps1")):
            continue
        if rel == "tests/test_q2_q3_setup.py":
            continue
        for n, line in enumerate((ROOT / rel).read_text(encoding="utf-8").splitlines(), 1):
            if re.search(r"git add (-A|--all)\b", line) and "never" not in line.lower():
                hits.append(f"{rel}:{n}: {line.strip()}")
    assert hits == []


def test_bootstrap_commit_reviews_status_first() -> None:
    for rel in ("QUICKSTART.md", "INSTANTIATE.md", "scripts/instantiate.py"):
        text = (ROOT / rel).read_text(encoding="utf-8")
        assert text.index("git status --short") < text.index("git add -- ."), rel


def test_setup_root_check_uses_paths_a_fresh_clone_has() -> None:
    text = SETUP.read_text(encoding="utf-8")
    check = next(ln for ln in text.splitlines()
                 if "Test-Path" in ln and ln.lstrip().startswith("if"))
    tracked = _tracked()
    for path in re.findall(r'Test-Path "([^"]+)"', check):
        assert any(t == path or t.startswith(path + "/") for t in tracked), path


def test_setup_points_only_to_files_that_ship() -> None:
    text = SETUP.read_text(encoding="utf-8")
    for path in set(re.findall(r"\b(?:scripts|0\d-[\w-]+)/[\w./-]+\.(?:md|ps1|py)\b", text)):
        assert (ROOT / path).is_file(), path


def test_setup_final_verification_runs_the_governance_gates() -> None:
    final = SETUP.read_text(encoding="utf-8").split('Step "Final local verification"', 1)[1]
    assert "scripts/wiki_validate.py" in final
    assert "scripts/wiki_state.py --repo . check" in final
