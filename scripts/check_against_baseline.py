#!/usr/bin/env python3
"""Run both validators and fail only on an error not already accepted.

Shared by .githooks/pre-commit (local, any tool that runs `git commit`) and
.github/workflows/validate.yml (CI, the gate every merge to main passes
through), so a local pass and a CI pass mean the same thing. Without this,
a local hook that tolerates known corpus debt and a CI job that demands
zero errors quietly disagree, and CI ends up red for reasons nobody at the
keyboard can act on -- which is how a project stops trusting its own CI.

Baseline file: .githooks/known-baseline-errors.txt (one accepted error
string per line, blank lines and '#' comments ignored).
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASELINE_FILE = ROOT / ".githooks" / "known-baseline-errors.txt"

CHECKS = [
    [sys.executable, "scripts/validate_repo.py", "--full"],
    [sys.executable, "scripts/validate_content_release.py"],
]


def load_baseline() -> set[str]:
    if not BASELINE_FILE.exists():
        return set()
    baseline = set()
    for line in BASELINE_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip("\r\n")
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        baseline.add(line)
    return baseline


def run_check(cmd: list[str]) -> str:
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    result = subprocess.run(
        cmd,
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
    )
    return result.stdout + result.stderr


def main() -> int:
    baseline = load_baseline()
    new_errors: list[str] = []
    known_count = 0

    for cmd in CHECKS:
        output = run_check(cmd)
        print(f"$ {' '.join(cmd)}")
        print(output)
        for line in output.splitlines():
            if not line.startswith("ERROR: "):
                continue
            text = line[len("ERROR: "):]
            if text in baseline:
                known_count += 1
            else:
                new_errors.append(text)

    if new_errors:
        print(
            f"\nBLOCKED: {len(new_errors)} error(s) not in "
            f"{BASELINE_FILE.relative_to(ROOT).as_posix()}:\n"
        )
        for e in new_errors:
            print(f"  - {e}")
        print(
            "\nIf this is a real problem: fix it.\n"
            "If it is deliberately deferred corpus debt: add the exact line "
            f"to {BASELINE_FILE.relative_to(ROOT).as_posix()} in its own "
            "reviewed commit with a reason, then commit your actual change "
            "separately."
        )
        return 1

    if known_count:
        print(f"\nOK: {known_count} pre-existing baseline error(s), no new ones.")
    else:
        print("\nOK: validators clean.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
