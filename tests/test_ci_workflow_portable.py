"""CI runs on any runner: GitHub-hosted Linux or a self-hosted Windows PC.

A Windows runner may have no bash on PATH (the 2026-10-14 run failed with
`bash: command not found`), and PowerShell only reports the exit code of a
step's last command. So the workflow forces no shell and every `run:` step
holds exactly one command.
"""
from __future__ import annotations

from pathlib import Path

import yaml

WORKFLOW = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "validate.yml"


def test_no_forced_shell() -> None:
    wf = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    assert "shell" not in (wf.get("defaults") or {}).get("run", {})
    for name, job in wf["jobs"].items():
        assert "shell" not in (job.get("defaults") or {}).get("run", {}), name
        for step in job["steps"]:
            assert "shell" not in step, (name, step.get("name"))


def test_every_run_step_is_one_command() -> None:
    wf = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    for name, job in wf["jobs"].items():
        for step in job["steps"]:
            if "run" in step:
                lines = [ln for ln in step["run"].splitlines() if ln.strip()]
                assert len(lines) == 1, (name, step.get("name"), lines)


def test_all_gates_still_run() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")
    for cmd in ("scripts/check_against_baseline.py",
                "scripts/wiki_validate.py --repo . --format json",
                "scripts/wiki_state.py --repo . check",
                "scripts/wiki_evidence.py --repo . check",
                "scripts/wiki_profiles.py check",
                "pytest tests scripts/tests scripts/capture/tests",
                "scripts/release_smoke.py"):
        assert cmd in text, cmd
