# RESULT — lane W3 (E3, E4, R1-prep)

Branch `system/2026-11-09--w3-lane`, base e2f2130. No push, PR, merge, version bump, CHANGELOG or QUICKSTART edit. H3 not built (blocked by owner D-1).

## Rungs

| Rung | State | What it does |
|---|---|---|
| E3 | done | `wiki_retrieve` adds `enrichment-topic` / `enrichment-entity` reasons. Only the latest revision made for the CURRENT source version counts, and only for current chunks. Chunk-level topics and entity names/aliases attach to their own chunk; source-level topics/tags/categories attach to the chunks the annotation is anchored to. `text` is always the chunk text. A hit whose reasons are all enrichment carries `non_evidence: true`; a text hit that also matches enrichment keeps its evidence reasons and gains `non_evidence_reasons`. Enrichment-only hits score 0 and rank below text hits. Response has `enrichment: {sources_matched, non_evidence}`. |
| E4 | done | `wiki_artifact_read` (source mode) returns `annotation_coverage: {annotated_chunks, total_chunks, ratio, annotation_revision, state none/partial/full, non_evidence}`. "Annotated" = distinct current chunks the current revision is anchored to (chunk notes, entity mentions, link evidence). A stale revision (source text changed) counts as `none`. |
| R1-prep | done | `scripts/release_smoke_flow.py` + a last step in `release_smoke.py`: in the fresh instance, ingest a file, retrieve its text, submit enrichment, retrieve by the enrichment topic (non-evidence, chunk text), check coverage 1/N. `RELEASE SMOKE PASS` on the kit. |

## Defect found and fixed (W2 lane B code, needed for E3 on real data)

Real source refs are `rec:<id>` / `doc:<sha>`. `enrichment.py` and `enrichment-revision.schema.json` rejected any `:` ("unsafe source_ref"), so nothing ingested could be enriched; W2 tests used refs like `src-a` and missed it. Fix: allow `:` in the ref pattern and schema; the sidecar/lock/failed file names map `:` to `%3A` (Windows-safe). Covered by every E3/E4 test (they use `rec:tst-src-aaaa`).

## Tests and the product behaviour each protects

`tests/test_e3_e4_enrichment_retrieval.py`
- `test_enrichment_only_match_returns_chunk_text_labelled_non_evidence` — retrieval honesty: a topic-only match returns the chunk's real text (never the summary) and says it is non-evidence.
- `test_entity_name_and_alias_find_the_mention_chunk` — a reader can find a person/concept by name or alias, labelled non-evidence.
- `test_text_match_stays_evidence_and_enrichment_never_outranks_text` — evidence vs non-evidence: real text hits are never downgraded and rank above enrichment-only hits.
- `test_stale_enrichment_is_ignored_after_source_changes` — enrichment made for an old source version cannot steer retrieval or claim coverage.
- `test_coverage_reports_annotated_over_total` — coverage truth: none / partial / full, duplicates not double counted.

`tests/test_release_smoke.py`
- `test_fresh_wiki_passes_every_gate` (extended) — a fresh instance really supports ingest → retrieve → enrichment → coverage.
- `test_enrichment_that_cannot_run_in_a_fresh_wiki_fails_the_flow_step` — the release check fails and names the flow step when enrichment is broken in a new instance.

## Checks

Raw output in `.mission-evidence/M-100.7.txt` (focused tests, `release_smoke.py`, full suite, git log).

## Deviations / open

- Source-level topics/tags/categories have no chunk of their own; they attach to anchored chunks only. A source with only a summary and source-level tags and no anchored chunk yields no enrichment hit. Say if you want them to attach to all chunks.
- R1 still needs H3 (owner D-1), version bump, CHANGELOG/QUICKSTART (Jimmy).
- The proposal-door refusal of a quote taken from a summary (E3 acceptance, second half) was not touched; not in the lane scope list. Not verified here.

## Final suite

`python -m pytest -q tests scripts/tests -p no:cacheprovider` → **586 passed, 2 skipped, 2 xfailed** (base 576/6/2; skip count differs from the brief's base, not investigated). One interim failure (`test_section6_lists_every_shipped_script`) was caused by the new script and fixed with a SYSTEM_DESIGN section-6 row.

STATUS: done · CHANGED: scripts/gov_kernel/enrichment.py, scripts/retrieval/retrieve.py, 00-system/schemas/enrichment-revision.schema.json, scripts/release_smoke.py, scripts/release_smoke_flow.py, SYSTEM_DESIGN.md, tests/test_e3_e4_enrichment_retrieval.py, tests/test_release_smoke.py · CHECKED: full suite 586 passed, release_smoke PASS (.mission-evidence/M-100.7.txt) · OPEN: H3/D-1, version bump + CHANGELOG/QUICKSTART (Jimmy); source-level-only tags give no hit
