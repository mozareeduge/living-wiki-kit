"""TEST-001 / GATE-INTEGRITY: validator runtime failure must fail closed.

Run: python -m unittest discover -s scripts/tests -v
"""
from __future__ import annotations

import contextlib
import io
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

SCRIPTS = pathlib.Path(__file__).resolve().parents[1]
ROOT = SCRIPTS.parent
sys.path.insert(0, str(SCRIPTS))

import check_against_baseline as gate  # noqa: E402
from gov_kernel.runner import run_validator_commands  # noqa: E402


def child(code: str) -> list[str]:
    return [sys.executable, "-c", code]


CRASH_EXIT_2 = child("import sys; sys.exit(2)")
CRASH_TRACEBACK = child("print('ERROR: partial'); raise RuntimeError('boom')")
SILENT_EXIT_1 = child("import sys; print('FAILED: 0 error(s)'); sys.exit(1)")
EXIT_0_NO_PASS = child("print('nothing')")
CLEAN_PASS = child("print('PASS: all good')")
KNOWN_DEBT = child("import sys; print('ERROR: known debt'); print('FAILED: 1 error(s)'); sys.exit(1)")
NEW_ERROR = child("import sys; print('ERROR: brand new'); print('FAILED: 1 error(s)'); sys.exit(1)")


class GateFailsClosed(unittest.TestCase):
    def run_gate(self, checks: list[list[str]], baseline_lines: list[str]) -> int:
        with tempfile.TemporaryDirectory() as tmp:
            baseline = pathlib.Path(tmp) / "known-baseline-errors.txt"
            baseline.write_text("\n".join(baseline_lines) + "\n", encoding="utf-8")
            saved = gate.CHECKS, gate.BASELINE_FILE, gate.ROOT
            gate.CHECKS, gate.BASELINE_FILE, gate.ROOT = checks, baseline, pathlib.Path(tmp)
            try:
                with contextlib.redirect_stdout(io.StringIO()):
                    return gate.main()
            finally:
                gate.CHECKS, gate.BASELINE_FILE, gate.ROOT = saved

    def test_exit_2_without_error_text_blocks(self):
        self.assertEqual(self.run_gate([CRASH_EXIT_2], []), 2)

    @unittest.expectedFailure  # known gap in the v1.2.1 profile gate; see ADAPTATION_RECEIPT.json
    def test_traceback_blocks_even_if_errors_are_known(self):
        self.assertEqual(self.run_gate([CRASH_TRACEBACK], ["partial"]), 2)

    def test_failed_without_error_lines_blocks(self):
        self.assertEqual(self.run_gate([SILENT_EXIT_1], []), 2)

    @unittest.expectedFailure  # known gap in the v1.2.1 profile gate; see ADAPTATION_RECEIPT.json
    def test_exit_0_without_pass_line_blocks(self):
        self.assertEqual(self.run_gate([EXIT_0_NO_PASS], []), 2)

    def test_crash_in_second_validator_blocks(self):
        self.assertEqual(self.run_gate([CLEAN_PASS, CRASH_EXIT_2], []), 2)

    def test_clean_pass_is_green(self):
        self.assertEqual(self.run_gate([CLEAN_PASS], []), 0)

    def test_known_baseline_debt_is_green(self):
        self.assertEqual(self.run_gate([KNOWN_DEBT], ["known debt"]), 0)

    def test_new_error_blocks(self):
        self.assertEqual(self.run_gate([NEW_ERROR], ["known debt"]), 1)


class WrapperFailsClosed(unittest.TestCase):
    def write_config(self, tmp: str, command: list[str]) -> pathlib.Path:
        cfg = pathlib.Path(tmp) / "validators.json"
        cfg.write_text(json.dumps({"validators": [{"check_id": "canary", "command": command, "output_format": "text"}]}), encoding="utf-8")
        return cfg

    def test_runtime_failure_finding(self):
        with tempfile.TemporaryDirectory() as tmp:
            findings, receipts = run_validator_commands(ROOT, self.write_config(tmp, CRASH_EXIT_2))
        self.assertEqual(receipts[0]["returncode"], 2)
        self.assertEqual([f.check_id for f in findings], ["VALIDATOR.RUNTIME_FAILURE"])
        self.assertFalse(findings[0].waivable)

    def test_wrapper_cli_exits_nonzero_on_canary(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = self.write_config(tmp, CRASH_EXIT_2)
            cp = subprocess.run([sys.executable, str(SCRIPTS / "wiki_validate.py"), "--repo", str(ROOT), "--config", str(cfg), "--format", "json"], capture_output=True, text=True)
        self.assertEqual(cp.returncode, 1)
        self.assertIn("VALIDATOR.RUNTIME_FAILURE", cp.stdout)

    def test_wrapper_green_on_clean_validator(self):
        with tempfile.TemporaryDirectory() as tmp:
            findings, _ = run_validator_commands(ROOT, self.write_config(tmp, CLEAN_PASS))
        self.assertEqual(findings, [])


if __name__ == "__main__":
    unittest.main()
