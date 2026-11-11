# RESULT W2-B — enrichment sidecar + chunk evidence (worktree lwk-wt-150-B)

Branch `system/2026-11-09--w2-lane-B`. Commits: `fa8b0ef` (C6), `7950a26` (E1+E2).

## Rungs

| Rung | State | Proving tests |
|---|---|---|
| C6 proposal door accepts `chk:` evidence | done | `tests/test_w1_proposal_door.py::test_c6_*` (7 tests: exact quote accepted, quote not in chunk, short quote, unknown ref, stale source_version, missing index, ref not in evidence_refs) |
| E1 sidecar store + schema + `wiki_enrichment_submit` | done | `tests/test_e1_enrichment_submit.py` (revision append and level 7, `E_REVISION_CONFLICT`, `E_STALE_SOURCE`, unknown source, missing index, idempotent replay, exact-substring mention and quote, wrong-chunk, closed relations, all §9 limits, validator unchanged by sidecar deletion, write tool hidden in read profile and `E_AUTH_REQUIRED` over HTTP) |
| E2 `wiki_enrichment_pending` | done | `tests/test_e2_enrichment_pending.py` (unannotated listing with chunk texts, skips annotated, limit capped at 5 + cursor, retry_failed, read-only, missing index, page-sized chunks) |

Files: `scripts/gov_kernel/enrichment.py`, `00-system/schemas/enrichment-revision.schema.json`,
`scripts/gov_kernel/proposals.py` (C6), `scripts/wiki_mcp_server.py` (registration), tests above and `tests/_enrich_fixture.py`.

## Design notes

- C6 shape: `source_passage = {chunk_ref, quote}` plus the same `chk:` ref listed in `evidence_refs`. Lookup goes straight to the C3 `chunks` table joined to `sources`; a chunk whose `source_version` differs from the source's current one, or a ref missing from the index, gives `E_STALE_SOURCE`. Missing index fails closed. The existing path-based passage rule is unchanged.
- Sidecar failures (`E_VALIDATION` only) are logged in `_search/enrichment/_failed/<source_ref>.jsonl`; this is what `retry_failed` means (failed current versions are hidden from the queue unless `retry_failed=true`).
- Idempotency: a repeated `idempotency_key` replays the stored revision before the concurrency check. Appends are under a file lock (reuses the I2 lock helpers from `gov_kernel.ingest`).
- `categories` limit (≤5) and `chunk_annotations` shape (`chunk_ref`, `note` ≤300, optional topics) are my choices; HANDOFF §9 leaves them open.

## Deviations

1. Tools are registered in `scripts/wiki_mcp_server.py` (13 lines before the aliases), not `scripts/mcp_transport/registry.py`: the registry file holds only the class; tool declarations live in the server module.
2. Submit is `profile="capture"` (the existing write-capable profile) and `is_write=True`, so over HTTP it returns `E_AUTH_REQUIRED` (H3 not built).
3. `wiki_validate.py` independence test runs the validator against the real worktree with a temporary `_search/enrichment/` (gitignored), and removes it afterwards.

## Final test tail

`python -m pytest -q tests scripts/tests -p no:cacheprovider`
→ `1 failed, 515 passed, 2 skipped, 2 xfailed`

The one failure, `tests/test_kit_independence.py::test_no_tracked_file_carries_a_personal_wiki_trace`, is not from this lane: it flags an owner-name literal in the tracked file `07-genesis/handoffs/HANDOFF--2026-11-09--remote-ingest-chunks-enrichment.md` (placed in base commit `0e94df3`). The lane brief reported 478 passed at the base; I did not verify why this test passed then, and I did not edit the handoff. Raw output: `.mission-evidence/M-100.5.txt`.

## Open questions

- Should the owner handoff keep a personal name, or should the privacy test exempt `07-genesis/handoffs/`? (Needs a decision before the 1.5.0 release.)
- E3/E4 (wave 3) will read the sidecar through `gov_kernel.enrichment.load_revisions`.
