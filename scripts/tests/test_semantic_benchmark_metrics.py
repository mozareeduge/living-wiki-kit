"""Tests for the three new metrics in run-semantic-benchmark.py:
  - neighborhood recall@K
  - human rejection rate
  - evidence-trace completeness

Run: python -m pytest scripts/tests/test_semantic_benchmark_metrics.py -v
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

KIT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = KIT_ROOT / "scripts" / "run-semantic-benchmark.py"

# The filename has hyphens, so we can't use a normal import.
_spec = importlib.util.spec_from_file_location("run_semantic_benchmark", SCRIPT)
sb = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sb)


# ------------------------------------------------------------ helpers

def _case(cid, expected, matched, paths=None, error=None):
    """Build a minimal result dict matching run_case() output shape."""
    if paths is None:
        paths = [f"path/to/{cid}.md"] if matched else []
    return {
        "id": cid,
        "expected_suffixes": expected,
        "matched_expected": matched,
        "paths": paths,
        "error": error,
        "passed": bool(matched),
    }


# ------------------------------------------------------------ neighborhood recall@K

class TestNeighborhoodRecall:
    def test_perfect_recall(self):
        results = [
            _case("a", ["x.md", "y.md"], ["x.md", "y.md"]),
            _case("b", ["z.md"], ["z.md"]),
        ]
        r = sb.compute_neighborhood_recall(results, k=5)
        assert r["mean_recall_at_k"] == 1.0
        assert r["k"] == 5
        assert r["cases_with_expected"] == 2

    def test_partial_recall(self):
        results = [
            _case("a", ["x.md", "y.md", "z.md"], ["x.md"]),
        ]
        r = sb.compute_neighborhood_recall(results, k=5)
        assert r["mean_recall_at_k"] == round(1 / 3, 4)

    def test_zero_recall(self):
        results = [
            _case("a", ["x.md"], []),
        ]
        r = sb.compute_neighborhood_recall(results, k=5)
        assert r["mean_recall_at_k"] == 0.0

    def test_empty_expected_excluded_from_mean(self):
        results = [
            _case("a", ["x.md"], ["x.md"]),
            _case("b", [], []),  # no expected — excluded
        ]
        r = sb.compute_neighborhood_recall(results, k=5)
        assert r["mean_recall_at_k"] == 1.0
        assert r["cases_with_expected"] == 1
        # The excluded case has recall=None
        assert r["per_case"][1]["recall_at_k"] is None

    def test_all_empty_expected_returns_none(self):
        results = [_case("a", [], [])]
        r = sb.compute_neighborhood_recall(results, k=5)
        assert r["mean_recall_at_k"] is None
        assert r["cases_with_expected"] == 0

    def test_empty_results_returns_none(self):
        r = sb.compute_neighborhood_recall([], k=5)
        assert r["mean_recall_at_k"] is None
        assert r["cases_with_expected"] == 0

    def test_mixed_recall_values(self):
        results = [
            _case("a", ["x.md", "y.md"], ["x.md", "y.md"]),  # 1.0
            _case("b", ["p.md", "q.md"], ["p.md"]),           # 0.5
            _case("c", ["z.md"], []),                          # 0.0
        ]
        r = sb.compute_neighborhood_recall(results, k=5)
        expected_mean = round((1.0 + 0.5 + 0.0) / 3, 4)
        assert r["mean_recall_at_k"] == expected_mean

    def test_per_case_fields(self):
        results = [_case("a", ["x.md", "y.md"], ["x.md"])]
        r = sb.compute_neighborhood_recall(results, k=3)
        pc = r["per_case"][0]
        assert pc["id"] == "a"
        assert pc["expected_count"] == 2
        assert pc["matched_count"] == 1
        assert pc["recall_at_k"] == 0.5


# ------------------------------------------------------------ human rejection rate

class TestHumanRejectionRate:
    def test_no_rejections(self):
        results = [
            _case("a", ["x.md"], ["x.md"]),
            _case("b", ["y.md"], ["y.md"]),
        ]
        r = sb.compute_human_rejection_rate(results)
        assert r["rejection_rate"] == 0.0
        assert r["rejected"] == 0
        assert r["total"] == 2

    def test_all_rejected_on_error(self):
        results = [
            _case("a", ["x.md"], [], error="qmd failed"),
            _case("b", ["y.md"], [], error="timeout"),
        ]
        r = sb.compute_human_rejection_rate(results)
        assert r["rejection_rate"] == 1.0
        assert r["rejected"] == 2

    def test_incomplete_recall_is_rejected(self):
        results = [
            _case("a", ["x.md", "y.md"], ["x.md"]),  # incomplete
            _case("b", ["z.md"], ["z.md"]),           # complete
        ]
        r = sb.compute_human_rejection_rate(results)
        assert r["rejection_rate"] == 0.5
        assert r["rejected"] == 1
        assert r["per_case"][0]["rejected"] is True
        assert r["per_case"][0]["reason"] == "incomplete_recall"
        assert r["per_case"][1]["rejected"] is False

    def test_no_paths_is_rejected(self):
        results = [
            _case("a", ["x.md"], [], paths=[]),
        ]
        r = sb.compute_human_rejection_rate(results)
        assert r["rejection_rate"] == 1.0
        # incomplete_recall is the more specific reason (expected but not all matched)
        assert r["per_case"][0]["reason"] == "incomplete_recall"

    def test_error_takes_precedence_over_other_reasons(self):
        results = [
            _case("a", ["x.md"], [], paths=[], error="boom"),
        ]
        r = sb.compute_human_rejection_rate(results)
        assert r["per_case"][0]["reason"] == "error"

    def test_empty_results_returns_none(self):
        r = sb.compute_human_rejection_rate([])
        assert r["rejection_rate"] is None
        assert r["total"] == 0

    def test_no_expected_no_paths_not_rejected(self):
        """A case with no expected items and no paths is not rejected
        (nothing to find, nothing returned — not a failure)."""
        results = [_case("a", [], [], paths=[])]
        r = sb.compute_human_rejection_rate(results)
        assert r["rejection_rate"] == 0.0

    def test_mixed_reasons(self):
        results = [
            _case("a", ["x.md"], [], error="err"),          # error
            _case("b", ["y.md", "z.md"], ["y.md"]),          # incomplete
            _case("c", ["w.md"], ["w.md"]),                  # ok
            _case("d", [], [], paths=[]),                     # no expected, no paths — ok
        ]
        r = sb.compute_human_rejection_rate(results)
        assert r["rejected"] == 2
        assert r["rejection_rate"] == 0.5


# ------------------------------------------------------------ evidence-trace completeness

class TestEvidenceTraceCompleteness:
    def test_all_complete(self):
        results = [
            _case("a", ["x.md"], ["x.md"]),
            _case("b", ["y.md"], ["y.md"]),
        ]
        r = sb.compute_evidence_trace_completeness(results)
        assert r["completeness_rate"] == 1.0
        assert r["complete"] == 2
        assert r["total"] == 2

    def test_missing_expected(self):
        results = [_case("a", [], ["x.md"])]
        r = sb.compute_evidence_trace_completeness(results)
        assert r["completeness_rate"] == 0.0
        assert r["per_case"][0]["has_expected"] is False
        assert r["per_case"][0]["complete"] is False

    def test_missing_paths(self):
        results = [_case("a", ["x.md"], [], paths=[])]
        r = sb.compute_evidence_trace_completeness(results)
        assert r["completeness_rate"] == 0.0
        assert r["per_case"][0]["has_paths"] is False

    def test_missing_match(self):
        results = [_case("a", ["x.md"], [])]
        r = sb.compute_evidence_trace_completeness(results)
        assert r["completeness_rate"] == 0.0
        assert r["per_case"][0]["has_match"] is False

    def test_mixed_completeness(self):
        results = [
            _case("a", ["x.md"], ["x.md"]),   # complete
            _case("b", ["y.md"], []),          # missing match
            _case("c", [], ["z.md"]),          # missing expected
            _case("d", ["w.md"], ["w.md"]),    # complete
        ]
        r = sb.compute_evidence_trace_completeness(results)
        assert r["complete"] == 2
        assert r["completeness_rate"] == 0.5

    def test_empty_results_returns_none(self):
        r = sb.compute_evidence_trace_completeness([])
        assert r["completeness_rate"] is None
        assert r["total"] == 0

    def test_all_three_conditions_required(self):
        """Each condition is necessary — removing any one makes it incomplete."""
        # has expected + paths but no match
        r1 = sb.compute_evidence_trace_completeness(
            [_case("a", ["x.md"], [], paths=["some/path.md"])]
        )
        assert r1["completeness_rate"] == 0.0

        # has expected + match but no paths (edge case: matched but no paths)
        r2 = sb.compute_evidence_trace_completeness(
            [_case("a", ["x.md"], ["x.md"], paths=[])]
        )
        assert r2["completeness_rate"] == 0.0

        # has paths + match but no expected
        r3 = sb.compute_evidence_trace_completeness(
            [_case("a", [], ["x.md"], paths=["some/path.md"])]
        )
        assert r3["completeness_rate"] == 0.0


# ------------------------------------------------------------ integration: metrics in report

class TestMetricsInReport:
    def test_main_includes_metrics_in_report(self, tmp_path, monkeypatch):
        """Verify that main() computes and embeds all three metrics."""
        import json

        # Create a minimal config
        config = {
            "id": "test-benchmark",
            "top_k": 3,
            "threshold": 1,
            "cases": [
                {
                    "id": "t1",
                    "question": "What is X?",
                    "expected_suffixes": ["x.md"],
                    "collection": "test",
                },
                {
                    "id": "t2",
                    "question": "What is Y?",
                    "expected_suffixes": ["y.md", "z.md"],
                    "collection": "test",
                },
            ],
        }
        config_path = tmp_path / "config.json"
        config_path.write_text(json.dumps(config), encoding="utf-8")

        # Monkeypatch CONFIG and run_case
        monkeypatch.setattr(sb, "CONFIG", config_path)

        def fake_run_case(case, top_k, timeout):
            if case["id"] == "t1":
                return {
                    "id": "t1",
                    "question": case["question"],
                    "collection": "test",
                    "command": ["qmd", "query", "..."],
                    "returncode": 0,
                    "stderr": "",
                    "passed": True,
                    "expected_suffixes": ["x.md"],
                    "matched_expected": ["x.md"],
                    "paths": ["docs/x.md"],
                }
            else:
                return {
                    "id": "t2",
                    "question": case["question"],
                    "collection": "test",
                    "command": ["qmd", "query", "..."],
                    "returncode": 0,
                    "stderr": "",
                    "passed": False,
                    "expected_suffixes": ["y.md", "z.md"],
                    "matched_expected": ["y.md"],
                    "paths": ["docs/y.md"],
                }

        monkeypatch.setattr(sb, "run_case", fake_run_case)

        output = tmp_path / "report.json"
        monkeypatch.setattr(
            sys, "argv",
            ["run-semantic-benchmark", "--output", str(output), "--threshold", "1"],
        )

        exit_code = sb.main()
        assert exit_code == 0

        report = json.loads(output.read_text(encoding="utf-8"))
        assert "metrics" in report
        metrics = report["metrics"]

        # neighborhood recall
        assert "neighborhood_recall" in metrics
        nr = metrics["neighborhood_recall"]
        assert nr["k"] == 3
        assert nr["mean_recall_at_k"] == 0.75  # (1.0 + 0.5) / 2

        # human rejection rate
        assert "human_rejection_rate" in metrics
        hr = metrics["human_rejection_rate"]
        assert hr["rejected"] == 1  # t2 has incomplete recall
        assert hr["rejection_rate"] == 0.5

        # evidence-trace completeness
        assert "evidence_trace_completeness" in metrics
        etc = metrics["evidence_trace_completeness"]
        # Both t1 and t2 have expected + paths + match, so both are complete
        assert etc["complete"] == 2
        assert etc["completeness_rate"] == 1.0

    def test_markdown_includes_metrics(self, tmp_path):
        """Verify write_markdown renders the metrics section."""
        report = {
            "run_at": "2026-09-29T12:00:00",
            "passed": 1,
            "total": 2,
            "threshold": 1,
            "result": "PASS",
            "metrics": {
                "neighborhood_recall": {
                    "k": 5,
                    "mean_recall_at_k": 0.75,
                },
                "human_rejection_rate": {
                    "rejection_rate": 0.5,
                },
                "evidence_trace_completeness": {
                    "completeness_rate": 0.5,
                },
            },
            "cases": [
                {
                    "id": "a",
                    "collection": "test",
                    "passed": True,
                    "matched_expected": ["x.md"],
                    "paths": ["docs/x.md"],
                },
            ],
        }
        md_path = tmp_path / "report.md"
        sb.write_markdown(report, md_path)
        text = md_path.read_text(encoding="utf-8")
        assert "Metrics" in text
        assert "Neighborhood Recall@5" in text
        assert "Human Rejection Rate" in text
        assert "Evidence-Trace Completeness" in text

    def test_markdown_without_metrics_still_works(self, tmp_path):
        """Backward compat: report with no metrics key renders fine."""
        report = {
            "run_at": "2026-09-29T12:00:00",
            "passed": 1,
            "total": 1,
            "threshold": 1,
            "result": "PASS",
            "cases": [
                {
                    "id": "a",
                    "collection": "test",
                    "passed": True,
                    "matched_expected": ["x.md"],
                    "paths": ["docs/x.md"],
                },
            ],
        }
        md_path = tmp_path / "report.md"
        sb.write_markdown(report, md_path)
        text = md_path.read_text(encoding="utf-8")
        assert "Metrics" not in text
        assert "| a |" in text
