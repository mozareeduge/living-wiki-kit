---
name: wiki-reconcile
description: Run the manifest-accounted full-corpus reconciliation required before accepted corpus-wide changes. Has side effects and must be invoked manually.
disable-model-invocation: true
---

# Full-Corpus Reconciliation

Current baseline: read the live source count and snapshot id from
`00-system/registers/CORPUS_STATE.json` at run start; stop if that file is
missing, malformed, or lacks a non-empty `id` and `source_material_count`.
(Never hardcode an instance baseline in this skill. Behavior verified
2026-09-16.)

## Step 0 — declare the run class and mode

Every run first declares one class:

- **RC-0** mechanism (tooling/shakedown, no corpus judgment);
- **RC-1** candidate intake (gates only, no batch reading);
- **RC-2** correction on accepted evidence (graph-impact scan, no full reread);
- **RC-3** new accepted evidence (batched corpus-reader runs);
- **RC-4** ontology change (batched runs + exact-once verify).

Then plan with the matching mode (full mode is unchanged behavior):

```bash
python scripts/reconcile_runner.py plan --mode incremental --class RC-1
python scripts/reconcile_runner.py plan --mode full --class RC-3
```

The plan freezes `expected.jsonl` + 8–12-item batches and writes
`run-receipt.json` carrying the class. Each completed run updates that
receipt with its verdict — a run without a classed receipt is not a run.
Incremental escalates to full automatically on any removed row, a decreased
corpus count (loss), or >30% rows changed; >3 verify conflicts escalate to a
human. Resume an interrupted run from its `_audits/<run-id>/` scaffold
across sessions; never re-freeze mid-run.

## Completion criterion

The run is complete only when every manifest row appears in exactly one batch receipt or named exception. Semantic search, prior summaries, and the materials index do not count as rereading.

## Procedure

1. Validate the current manifest and checksums.
2. Freeze the expected manifest in `_audits/<run-id>/expected.jsonl`.
3. Divide source records and derivatives into batches small enough for isolated contexts. Use 8–12 artifacts per batch unless a single artifact is unusually large.
4. Delegate each batch to the `corpus-reader` subagent.
5. Each receipt must contain:
   - every source ID and path read;
   - relevant objects, terms, versions, relations, claims, and system effects;
   - contradictions or corrections;
   - what remained unchanged;
   - extraction/access limits;
   - candidate updates;
   - no prose presented as verified beyond its evidence.
6. Use `evidence-auditor` on claims or external facts that would be strengthened, weakened, or exported.
7. Merge receipts into one impact matrix covering:
   - sources and versions;
   - works and projects;
   - chronology;
   - terminology;
   - relations and claims;
   - public/official texts;
   - system architecture;
   - indexes and search.
8. Compare receipt IDs against the expected manifest. Stop on any gap or duplicate coverage.
9. Propose changes. Do not apply them until the user approves the impact report, unless the user explicitly authorized direct implementation.
10. After approved changes, run full validation, rebuild QMD, and create a reconciliation event and handoff.
