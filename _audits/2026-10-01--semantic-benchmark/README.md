# Semantic Benchmark 1.1.0 — 2026-10-01 run against the 3/30 baseline

This directory holds the M2 acceptance-(b) evidence: a real 30-case run of
`scripts/run-semantic-benchmark.py`, produced with the three M2 metrics
(neighborhood recall@K, human rejection rate, evidence-trace completeness)
wired into both the JSON and the markdown report.

## What was actually run

- **Runner:** `living-wiki-kit` `scripts/run-semantic-benchmark.py` at commit
  `6d2dca1` (contains the Windows UTF-8 decode fix that made the run possible).
- **Case set:** `semantic-benchmark-v1.1.0.json` — the same 30 cases used for the
  baseline (26 canonical + 4 source-record provenance questions). Copied from
  `mozare-wiki/mozare-wiki/00-system/configuration/` read-only; the kit still
  does not ship this config (finding **F2** stays open).
- **Index:** the local QMD index, `qmd status` reporting 3,463 files indexed /
  33,067+ vectors embedded / ~750 still pending at run time (M1 is **not**
  finished; embeddings were still being generated while this ran).
- **Scoring:** `qmd query <question> --no-rerank --json -n 5`, deterministic
  lexical/hybrid path; `--threshold 27` unchanged from the baseline.

## Result vs baseline

| | baseline (2026-09-20, `mozare-wiki` `9a2dd09`) | this run (2026-10-01) |
|---|---|---|
| Cases passing | **3 / 30** | **12 / 30** |
| Threshold | 27 | 27 (unchanged) |
| Verdict | FAIL | FAIL (still under threshold) |

**M2 acceptance (b) is satisfied as a *measurement*, not as a pass:** the score is
now real, committed, and directly comparable — 4x the baseline — but it is still
below the 27/30 threshold, so the benchmark is honestly **not** passing yet.

## Metrics from this run

- Neighborhood Recall@5: **0.3067**
- Human Rejection Rate: **0.8667** (26/30 cases would be sent back)
- Evidence-Trace Completeness: **0.4**

## Honest caveats (read before quoting these numbers)

1. **Recall@5 is the strict metric.** Most failures are partial-recall: the right
   file appears but not all expected neighbours inside the top 5. That is why
   recall (0.31) is much lower than the pass rate (12/30 = 0.40).
2. **Human Rejection Rate is a proxy, not a human measurement.** It is derived
   from the same expected-vs-matched signal as recall (see the docstring note in
   `compute_human_rejection_rate`); it must not be read as an independent axis.
3. **M1 was still in flight.** Embeddings were being generated during the run, so
   this is a mid-recovery score, not the final one. Re-run after
   `qmd status` reaches `Pending: 0` for the number that counts.
4. This is a single deterministic run (no rerank); it is reproducible, not noisy.