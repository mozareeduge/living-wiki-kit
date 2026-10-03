# Semantic Benchmark 1.1.0 — 2026-10-02 final run (M1 complete)

The M1 re-run that the 2026-10-01 handoff said would be "the number that counts".

## What was run

- **Runner:** `scripts/run-semantic-benchmark.py` with
  `--config ../mozare-wiki/mozare-wiki/00-system/configuration/semantic-benchmark-v1.1.0.json`
  (read-only; F2 decision: case sets are instance data).
- **Index:** `qmd status` showed no `Pending` line (all 3,463 files embedded,
  37,487 vectors) after `qmd embed` reported
  `Embedded 1886 chunks from 271 documents`.
- **Scoring:** unchanged: `qmd query --no-rerank --json -n 5`, threshold 27.

## Result

| | baseline 2026-09-20 | 2026-10-01 (mid-embed) | **2026-10-02 (M1 done)** |
|---|---|---|---|
| Cases passing | 3 / 30 | 12 / 30 | **12 / 30** |
| mean recall@5 | n/a | 0.3067 | **0.2949** |
| evidence-trace completeness | n/a | 0.40 | **0.40** |
| Verdict | FAIL | FAIL | **FAIL** |

The same 12 cases pass in both runs (SR-10, 21, 23, 25, 30, 31, 40, 41, 44, 45,
48, 50). Finishing the embeddings did **not** move the score.

## Why the score stays at 12/30 (finding F10, new)

The local QMD index does not match the instance's own
`00-system/configuration/qmd-collections-v1.1.0.json`:

- The instance declares per-folder collections (`mozare-objects`,
  `mozare-notes`, `mozare-claims`, `mozare-relations`, `mozare-genesis`,
  `mozare-source-records`, …).
- The machine's index has **one** `mozare-wiki` collection over every `*.md`,
  plus `ref-wiki`, `zp-text` and others that are included by default.

Consequences visible in `report.json`:

1. **SRC-01…04 never ran.** They target `-c mozare-source-records`, and qmd
   answered `Collection not found: mozare-source-records`. Four of 30 cases are
   unmeasured, not failed on merit.
2. **Canonical questions are swamped by extracted source text.** Most top-5
   hits in failing SR cases are `02-sources/text/*-extracted.md` or `ref-wiki`
   / `zp-*` files, not the canonical objects the cases expect.
3. The MCP server's QMD enhancement (F9, now config-driven) resolves to those
   declared names too, so on this machine it also finds no collection.

**Fix (owner decision, machine-level, not a repo change):** rebuild the local
index from the instance's config (`scripts/configure-search.ps1` in
`mozare-wiki`), then re-embed and re-run. This rewrites the shared QMD index
that `ref-wiki` and `zarinpal-product-wiki` also use, which is why it was not
done unilaterally.
