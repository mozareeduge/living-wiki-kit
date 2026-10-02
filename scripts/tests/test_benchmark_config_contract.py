"""F2: benchmark case sets are instance-supplied; the kit ships none.

Both runners must say so in one clear line and exit non-zero, never crash
with a traceback, and must accept --config for a case set kept elsewhere.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

KIT_ROOT = Path(__file__).resolve().parents[2]
SEMANTIC = KIT_ROOT / "scripts" / "run-semantic-benchmark.py"
FAITHFUL = KIT_ROOT / "scripts" / "run_faithfulness_benchmark.py"


def _run(*cmd: str):
    return subprocess.run([sys.executable, "-B", *cmd], capture_output=True,
                          text=True, encoding="utf-8", errors="replace", cwd=KIT_ROOT)


def test_kit_ships_no_case_set():
    assert not (KIT_ROOT / "00-system/configuration/semantic-benchmark-v1.1.0.json").exists()


def test_semantic_runner_explains_a_missing_case_set(tmp_path):
    r = _run(str(SEMANTIC), "--config", str(tmp_path / "absent.json"),
             "--output", str(tmp_path / "out.json"))
    assert r.returncode != 0
    assert "Traceback" not in r.stderr
    assert "benchmarks are instance-supplied" in r.stderr


def test_faithfulness_runner_explains_a_missing_case_set(tmp_path):
    r = _run(str(FAITHFUL), "retrieve", "--config", str(tmp_path / "absent.json"))
    assert r.returncode != 0
    assert "Traceback" not in r.stderr
    assert "benchmarks are instance-supplied" in r.stderr


def test_semantic_runner_reads_an_explicit_config(tmp_path):
    cfg = tmp_path / "cases.json"
    cfg.write_text('{"id": "t", "top_k": 1, "threshold": 0, "cases": []}', encoding="utf-8")
    out = tmp_path / "out.json"
    r = _run(str(SEMANTIC), "--config", str(cfg), "--output", str(out))
    assert "Traceback" not in r.stderr, r.stderr
    assert out.exists()
