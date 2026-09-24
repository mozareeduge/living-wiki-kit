#!/usr/bin/env python3
"""Run Mozare Wiki validators with accepted-debt semantics and fail-closed execution.

Known validation findings listed in .githooks/known-baseline-errors.txt remain
accepted debt. Validator runtime/infrastructure failure never becomes green.

Exit contract:
- child rc=0: normal success (any ERROR lines are still evaluated)
- child rc=1: validation findings; may pass only when every emitted ERROR line is
  already in the accepted baseline and at least one ERROR line was emitted
- child rc other than 0/1, timeout, launch failure, or rc=1 with no parseable
  ERROR line: infrastructure/runtime failure -> block
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
TIMEOUT_SECONDS = 180


def load_baseline() -> set[str]:
    if not BASELINE_FILE.exists():
        return set()
    out: set[str] = set()
    for line in BASELINE_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip("\r\n")
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        out.add(line)
    return out


def run_check(cmd: list[str]) -> tuple[int, str, str | None]:
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    try:
        result = subprocess.run(
            cmd,
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
            timeout=TIMEOUT_SECONDS,
        )
        return result.returncode, result.stdout + result.stderr, None
    except subprocess.TimeoutExpired as exc:
        out = (exc.stdout or "") + (exc.stderr or "")
        return 124, out if isinstance(out, str) else str(out), f"timeout after {TIMEOUT_SECONDS}s"
    except OSError as exc:
        return 127, "", f"launch failure: {type(exc).__name__}: {exc}"


def main() -> int:
    baseline = load_baseline()
    new_errors: list[str] = []
    runtime_failures: list[str] = []
    known_count = 0

    for cmd in CHECKS:
        rc, output, launch_error = run_check(cmd)
        print(f"$ {' '.join(cmd)}")
        print(output)
        error_lines: list[str] = []
        for line in output.splitlines():
            if line.startswith("ERROR: "):
                text = line[len("ERROR: "):]
                error_lines.append(text)
                if text in baseline:
                    known_count += 1
                else:
                    new_errors.append(text)

        label = " ".join(cmd)
        if launch_error:
            runtime_failures.append(f"{label}: {launch_error}")
        elif rc not in (0, 1):
            runtime_failures.append(f"{label}: unexpected exit code {rc}")
        elif rc == 1 and not error_lines:
            runtime_failures.append(
                f"{label}: exited 1 but emitted no parseable 'ERROR: ' findings; treating as runtime failure"
            )

    if runtime_failures:
        print(f"\nBLOCKED: {len(runtime_failures)} validator runtime/infrastructure failure(s):\n")
        for failure in runtime_failures:
            print(f"  - {failure}")
        return 2

    if new_errors:
        print(
            f"\nBLOCKED: {len(new_errors)} error(s) not in "
            f"{BASELINE_FILE.relative_to(ROOT).as_posix()}:\n"
        )
        for error in new_errors:
            print(f"  - {error}")
        print(
            "\nFix real regressions. If a finding is deliberately deferred debt, "
            "add its exact text to the baseline only in a separately reviewed change with a reason."
        )
        return 1

    if known_count:
        print(f"\nOK: {known_count} pre-existing baseline error(s), no new ones; validator execution healthy.")
    else:
        print("\nOK: validators clean; validator execution healthy.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
