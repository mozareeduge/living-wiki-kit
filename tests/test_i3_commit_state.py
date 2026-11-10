"""Tests for Rung I3: Commit state.

Acceptance criteria:
- Write doors commit to Git in small batches or immediately.
- Receipts report commit_state ("committed" or "uncommitted").
- A failing git commit (e.g. hook rejects) yields commit_state: "uncommitted" + last_failure, never a false "committed".
- wiki_status / commit_status reports uncommitted.count and last_failure.
"""
from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from gov_kernel import ingest

FIXTURES = ROOT / "tests" / "fixtures" / "ingest"


@pytest.fixture
def git_wiki(tmp_path: Path) -> Path:
    """Create a fresh instantiated wiki with a real git repository."""
    wiki = tmp_path / "wiki"
    listed = subprocess.run(
        ["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, check=True
    ).stdout.decode("utf-8").split("\0")
    for rel in filter(None, listed):
        src = ROOT / rel
        if src.is_file():
            (wiki / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, wiki / rel)

    subprocess.run(
        [sys.executable, "scripts/instantiate.py", "--name", "Git Test Wiki", "--prefix", "gtw"],
        cwd=wiki, capture_output=True, text=True, check=True
    )

    # Initialize a git repository inside wiki
    subprocess.run(["git", "init"], cwd=wiki, capture_output=True, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=wiki, capture_output=True, check=True)
    subprocess.run(["git", "config", "user.email", "test@localhost"], cwd=wiki, capture_output=True, check=True)
    subprocess.run(["git", "add", "."], cwd=wiki, capture_output=True, check=True)
    subprocess.run(["git", "commit", "-m", "initial commit"], cwd=wiki, capture_output=True, check=True)

    return wiki


def test_successful_commit_state(git_wiki: Path) -> None:
    txt_file = FIXTURES / "sample.txt"
    receipt = ingest.ingest_file(txt_file, root=git_wiki, auto_commit=True)

    assert receipt["ok"] is True
    assert receipt["commit_state"] == "committed"
    assert receipt.get("last_failure") is None

    status = ingest.get_commit_status(git_wiki)
    assert status["uncommitted"]["count"] == 0
    assert status["uncommitted"]["last_failure"] is None


def test_failing_commit_hook_yields_uncommitted_and_last_failure(git_wiki: Path) -> None:
    # Install a pre-commit hook that always rejects
    hooks_dir = git_wiki / ".git" / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)
    pre_commit = hooks_dir / "pre-commit"
    pre_commit.write_text("#!/bin/sh\necho 'pre-commit hook error: simulated validation failure' >&2\nexit 1\n", encoding="utf-8")
    pre_commit.chmod(pre_commit.stat().st_mode | stat.S_IEXEC | stat.S_IXUSR)

    txt_file = FIXTURES / "sample.txt"
    receipt = ingest.ingest_file(txt_file, root=git_wiki, auto_commit=True)

    assert receipt["ok"] is True
    # Invariant: never report false committed
    assert receipt["commit_state"] == "uncommitted"
    assert receipt.get("last_failure") is not None
    assert "simulated validation failure" in receipt["last_failure"] or "exit 1" in str(receipt["last_failure"])

    status = ingest.get_commit_status(git_wiki)
    assert status["uncommitted"]["count"] > 0
    assert status["uncommitted"]["last_failure"] is not None


def test_wiki_status_reports_uncommitted_fields(git_wiki: Path) -> None:
    st = ingest.wiki_status(git_wiki)
    assert "uncommitted" in st
    assert "count" in st["uncommitted"]
    assert "last_failure" in st["uncommitted"]
