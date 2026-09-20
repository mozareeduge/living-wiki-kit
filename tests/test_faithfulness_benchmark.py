"""Smoke + deterministic-tier tests for run_faithfulness_benchmark.py.

Only Tier 1 (no LLM, no qmd) is exercised here: token handling, the lexical
support floor, JSON extraction from model output, run bookkeeping, and the
CLI surface. The generate/entail stages need a model and are out of scope.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

KIT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = KIT_ROOT / "scripts" / "run_faithfulness_benchmark.py"
sys.path.insert(0, str(KIT_ROOT / "scripts"))

import run_faithfulness_benchmark as fb  # noqa: E402


# ------------------------------------------------------------- tokenisation

def test_norm_tokens_casefolds_and_splits_on_punctuation():
    assert fb.norm_tokens("The Black-Bird, v2!") == ["the", "black", "bird", "v2"]


def test_norm_tokens_treats_zwnj_as_a_space_and_keeps_persian_letters():
    assert fb.norm_tokens("می‌روم خانه") == ["می", "روم", "خانه"]


def test_content_words_drop_stopwords_and_single_characters():
    assert fb.content_words(["the", "archive", "is", "x", "living"]) == ["archive", "living"]


# ------------------------------------------------------- lexical support floor

def test_ordered_subsequence_respects_order():
    hay = ["a", "b", "c", "d"]
    assert fb.ordered_subsequence(["a", "c"], hay) is True
    assert fb.ordered_subsequence(["c", "a"], hay) is False
    assert fb.ordered_subsequence([], hay) is True


def test_verify_claim_supported_when_words_are_present_and_in_order():
    chunk = "The archive preserves every original artifact and never edits a checksummed original."
    r = fb.verify_claim("The archive preserves every original artifact", [chunk])
    assert r["support"] == "supported" and r["ordered"] is True and r["best_chunk"] == 0


def test_verify_claim_partial_when_only_some_words_overlap():
    chunk = "The archive preserves originals."
    # 4 content words (archive, publishes, originals, weekly); 2 present = 0.5,
    # which clears the 0.45 partial floor but not the 0.75 supported floor
    r = fb.verify_claim("The archive publishes originals weekly", [chunk])
    assert r["support"] == "partial" and r["overlap"] == 0.5


def test_verify_claim_unsupported_when_nothing_overlaps():
    r = fb.verify_claim("Bananas ripen quickly", ["The archive preserves originals."])
    assert r["support"] == "unsupported" and r["overlap"] == 0.0


def test_verify_claim_reordered_words_are_not_supported():
    chunk = "artifact original every preserves archive"
    r = fb.verify_claim("archive preserves every original artifact", [chunk])
    # every content word is present (overlap 1.0) but out of order: the ordered
    # floor must demote it to partial, never supported
    assert r["support"] == "partial" and r["overlap"] == 1.0 and r["ordered"] is False


def test_verify_claim_is_degenerate_for_stopword_only_claims():
    r = fb.verify_claim("It is what it is", ["anything at all"])
    assert r["support"] == "degenerate" and r["best_chunk"] is None


def test_verify_claim_picks_the_best_of_several_chunks():
    chunks = ["unrelated text about weather", "the ledger records every checksum change"]
    r = fb.verify_claim("the ledger records every checksum change", chunks)
    assert r["best_chunk"] == 1 and r["support"] == "supported"


# ---------------------------------------------------------- model-output parsing

def test_extract_json_reads_a_fenced_block_with_trailing_prose_ignored():
    text = '```json\n{"answer": "x", "claims": ["a", "b"]}\n```'
    assert fb.extract_json(text) == {"answer": "x", "claims": ["a", "b"]}


def test_extract_json_handles_nested_objects():
    assert fb.extract_json('noise {"a": {"b": 1}} tail') == {"a": {"b": 1}}


def test_extract_json_raises_when_there_is_no_object():
    with pytest.raises(ValueError):
        fb.extract_json("the model refused to answer")


# ------------------------------------------------------------- run bookkeeping

def test_run_records_stage_completion_and_resumes(tmp_path, monkeypatch):
    monkeypatch.setattr(fb, "RUNS_DIR", tmp_path / "runs")
    run = fb.Run("stamp-1")
    assert run.stage_done("retrieve") is False
    run.mark_done("retrieve", {"cases": 3})
    again = fb.Run("stamp-1", resume=True)
    assert again.stage_done("retrieve") is True
    assert again.state["stages"]["retrieve"]["cases"] == 3
    assert again.path_for("verify").name == "verify.json"


def test_run_refuses_to_resume_a_missing_stamp(tmp_path, monkeypatch):
    monkeypatch.setattr(fb, "RUNS_DIR", tmp_path / "runs")
    with pytest.raises(SystemExit):
        fb.Run("nope", resume=True)


# ---------------------------------------------------------------------- CLI

def _cli(*args):
    return subprocess.run([sys.executable, "-B", str(SCRIPT), *args],
                          capture_output=True, text=True, encoding="utf-8", errors="replace")


def test_cli_help_lists_every_stage():
    r = _cli("--help")
    assert r.returncode == 0
    for stage in ("retrieve", "generate", "verify", "entail", "report"):
        assert stage in r.stdout


def test_cli_without_a_stage_is_a_usage_error():
    assert _cli().returncode == 2


def test_cli_resuming_an_unknown_run_exits_nonzero_without_creating_it():
    stamp = "does-not-exist-smoke"
    r = _cli("--run", stamp, "report")
    assert r.returncode != 0
    assert "cannot resume" in (r.stdout + r.stderr)  # the intended refusal, not just any crash
    assert not (KIT_ROOT / "_audits" / "runtime" / "faithfulness" / stamp).exists()
