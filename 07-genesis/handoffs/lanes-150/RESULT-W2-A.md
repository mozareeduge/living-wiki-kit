# RESULT W2-A: chunk retrieval (lane A)

Branch `system/2026-11-09--w2-lane-A`, commits ef7e8a4 (A0), 39f7211 (C4), 0bba73e (C5).

| Rung | Status | Proving tests |
|---|---|---|
| A0 ingest -> chunk index | done | tests/test_a0_ingest_chunks.py (real chunk_count, span rule text[start:end], second ingest keeps first source, indexer failure -> `index-failed` warning, ingest still ok); tests/test_i1_ingest.py (placeholder `chunk_count == 0` changed to `> 0`) |
| C4 wiki_retrieve + CLI | done | tests/test_c4_retrieve.py: groups, hit shape + span rule, whole-chunk budget, oversized chunk, cursor paging, foreign cursor rejected, Persian query, alias-match, fail-closed, stale flag, determinism, CLI, handler errors |
| C5 wiki_artifact_read | done | tests/test_c5_artifact_read.py: layers + pagination, chunk prev/next, stale ref after edit+rebuild (`E_STALE_SOURCE` + current_source_version), unknown refs, tool registration |

## Final test tail
`python -m pytest -q tests scripts/tests -p no:cacheprovider` -> 1 failed, 503 passed, 2 skipped, 2 xfailed.
The 1 failure, `tests/test_kit_independence.py::test_no_tracked_file_carries_a_personal_wiki_trace`, is NOT from this lane: the handoff file placed in 0e94df3 (`07-genesis/handoffs/HANDOFF--2026-11-09--remote-ingest-chunks-enrichment.md`) contains an owner name, and the independence test flags it. Needs a decision for the handoff file (Jimmy/owner); I did not edit it.

## Deviations / design choices
1. `on_ingested(receipt)` keeps its one-argument signature (an existing test replaces it). `ingest_file` passes root, derivative path and text in a temporary `receipt["_index_ctx"]` that is removed before the receipt is returned.
2. New read-side helpers in `gov_kernel/retrieval.py`: `index_derivative` (incremental upsert, existing tables untouched), `derivative_source_ref`, `chunk_count_for`. One small change in `build_index`: a derivative `02-sources/text/<id>.extracted.md` without frontmatter gets `rec:<id>` (same as the ingest receipt) instead of `doc:<content sha>`, so the source_ref is stable across edit + rebuild. Needed for stale detection.
3. Stale detection: chunk_refs are hashes, so after a rebuild an old ref cannot be traced back to its source. `wiki_artifact_read(chunk_ref, source_ref)` returns `E_STALE_SOURCE` when the caller names the source (hits always carry `source_ref`). Without `source_ref` an unknown ref returns `E_UNKNOWN_REF`, never a remap.
4. `scope=all` returns three groups: canonical, captures, and `sources` (ingested derivatives, profile evidence-text). Scopes canonical/captures return that group only. Groups are never merged into one ranking. `limit` is per group; `budget_tokens` (4 chars per token) is shared in order canonical, captures, sources.
5. Registration: `register_retrieval_tools(registry, root)` added to `mcp_transport/registry.py` (exported from the package) plus one call line and one import line in `scripts/wiki_mcp_server.py` (outside my file list, needed for the tools to appear). Both tools are read profile, `is_write=False`.
6. Process note: for C4 I wrote the code before its tests (tests were green on first full run, after one fix to a test fixture). A0 and C5 tests were written first (C5 registration tests failed before the registry change).
7. Not done (out of scope / later waves): `enrichment-topic` reasons (E3), coverage reporting (E4), exact-id (`exact-match`) is only a verbatim-substring reason in v1.

## Open questions
- Handoff file with an owner name vs. the independence test (see above).
- Should `scope=all` keep `sources` as a third group, or should ingested derivatives be reached only via an explicit scope? (HANDOFF names only canonical/captures/all.)
