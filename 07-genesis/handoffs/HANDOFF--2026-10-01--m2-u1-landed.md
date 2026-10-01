---
id: wiki-handoff-2026-10-01-m2-u1-landed
type: handoff
title: "M2 benchmark metrics + U1 capture breadth (URL/photo/file): salvaged, landed, verified"
branch: system/2026-09-20--next-version-plan
corpus_snapshot: wiki-corpus-empty
status: active
created: 2026-10-01
updated: 2026-10-01
schema_version: 1.0.0
---

# Handoff — M2 + U1 landed from previously uncommitted work

Supersedes nothing; adds to `HANDOFF--2026-09-29--overall-plan-and-remaining.md`,
which was written while this work sat uncommitted in the tree.

## 1. What was found

The 2026-09-29 handoff recorded the branch as "tree clean". It was not. Three
M2/U1 deliverables existed only as uncommitted working-tree changes, against two
`Plans.md` rows still marked `cc:todo`:

- M2: three benchmark metrics in `scripts/run-semantic-benchmark.py`.
- U1: `capture_url` / `capture_photo` in `scripts/capture/wiki_capture.py`,
  `capture_kind: url` in `scripts/capture/capture.schema.json`, and a new
  `scripts/capture/file_contract.py` (SingleFileAdapter).
- Tests: `scripts/tests/test_semantic_benchmark_metrics.py`,
  `scripts/capture/tests/test_url_photo_file.py`.

They passed, but were inconsistent and unsafe to land as-is.

## 2. Two defects fixed before landing

1. **Schema drift.** `scripts/capture/capture.schema.json` (client copy) gained
   `url` in `capture_kind`; the canonical contract
   `00-system/schemas/capture.schema.json` did not. The two disagreed on the
   record vocabulary, and no test caught it. Fixed by adding `url` to the
   canonical enum and adding `TestSchemaParity`, which compares the two enum
   *sets* (the files differ only in instance id/title flavour, so a full
   equality assert would be wrong).
2. **Tests writing into the repository.** `TestCLIURL` shelled out to
   `wiki_capture.py` via `subprocess`, where `CAPTURES_ROOT` is fixed to
   `REPO_ROOT/01-inbox/captures` and cannot be redirected. Every run therefore
   deposited real capture records in the real tree — the exact wart the
   2026-09-25 handoff flagged, and a direct violation of the K1c acceptance
   invariant ("a test run leaves `git status --porcelain` empty"). Fixed by
   running `wc.main(argv)` in-process with `REPO_ROOT` pointed at the temp tree
   (renamed `TestCaptureCLI`), which still exercises real argparse wiring. The
   stray `01-inbox/` captures left by earlier runs were removed; the suite no
   longer recreates them.

## 3. Product meaning, in one line each

- **M2** gives retrieval a scorecard: neighborhood recall@K, how often a
  reviewer would reject a result, and whether every answer leaves a traceable
  evidence path. This is the "measure" half of 1.3.0's wire/measure/seal.
- **U1** makes the three most common real capture gestures — *save this link*,
  *photograph this*, *attach this file* — first-class governed arrivals that
  produce the same checksummed, deduplicated, candidate-tier receipt as voice
  and text. No network fetch, no model call; a URL's own bytes are its content.
  `SingleFileAdapter` extracts text for `.txt/.md/.csv` and **flags** what it
  will not guess (PDF, binary-in-text-suffix) rather than smoothing it.

## 4. Evidence

- `pytest scripts/capture/tests -q` → 73 passed, 2 skipped
- `pytest scripts/tests -q` → 46 passed, 2 xfailed
- `pytest tests -q` → 263 passed
- `wiki_validate.py --repo . --format json` → exit 0
- `wiki_state.py --repo . check` → exit 0
- `check_against_baseline.py` → `OK: validators clean`
- Mutation: removing `url` from the canonical enum fails
  `test_capture_kind_enums_match` by name (`'url'`), then passes on restore.

## 5. What is still open (not code gaps)

- **M2 acceptance (b)** — a real 30-case score committed under `_audits/` and
  compared with the 3/30 lexical baseline — is blocked on **F2**
  (`00-system/configuration/semantic-benchmark-v1.1.0.json` is not shipped) and
  **M1** (QMD embeddings, operator lane). The metric code path is tested.
- **U1** depends on **H3** (operator, Obsidian plugin) per `Plans.md`; the
  capture core itself does not.
- `Plans.md` routing marks M2 `STAGED`, so an independent reviewer verdict is
  still owed before the row is treated as operator-approved.

## 6. Next exact operation

```bash
git config core.hooksPath .githooks
python -m pytest tests scripts/tests scripts/capture/tests -q
python scripts/wiki_validate.py --repo . --format json
python scripts/wiki_state.py --repo . check
```

Then PR #7 review → GitHub billing fix → CI → merge. Operator lane (M1, H1–H3,
U2) runs separately. F9 (port config-driven `qmd_collections()` back into
`mozare-wiki`) remains open.
